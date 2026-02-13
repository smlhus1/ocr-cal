"""
GPT-4 Vision-based OCR processor for shift schedules.
Uses OpenAI's multimodal capabilities for superior accuracy.
"""
import base64
import io
import logging
from typing import List, Tuple
from pathlib import Path
import json

from openai import OpenAI, RateLimitError, APITimeoutError, APIConnectionError
from pydantic import ValidationError
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from PIL import Image

from app.models import Shift
from app.config import settings

logger = logging.getLogger('shiftsync')


SUPPORTED_MIME_TYPES = {
    '.jpg': 'image/jpeg',
    '.jpeg': 'image/jpeg',
    '.png': 'image/png',
    '.gif': 'image/gif',
    '.webp': 'image/webp',
}

SYSTEM_MESSAGE = (
    "Du er en presis OCR-assistent spesialisert på norske vaktplaner. "
    "Din oppgave er å ekstrahere vakter fra bilder av arbeidsplaner. "
    "Du returnerer ALLTID valid JSON. Hvis du ikke kan lese bildet eller finner ingen vakter, "
    'returner {"shifts": [], "notes": "beskrivelse av problemet"}. '
    "Vær EKSTREMT nøyaktig med tall - skill mellom 1/7, 3/8, 6/0 osv."
)

USER_PROMPT = """Ekstraher ALLE vakter fra denne vaktplanen.

Returner JSON med denne strukturen:
{
    "shifts": [
        {
            "date": "DD.MM.YYYY",
            "start_time": "HH:MM",
            "end_time": "HH:MM",
            "shift_type": "tidlig|mellom|kveld|natt",
            "confidence": 0.0-1.0
        }
    ],
    "notes": null
}

Regler for shift_type (basert på starttid):
- "tidlig": 06:00-11:59
- "mellom": 12:00-15:59
- "kveld": 16:00-21:59
- "natt": 22:00-05:59 eller krysser midnatt

Regler for confidence (per vakt):
- 1.0: Tallene er helt tydelige og entydige
- 0.8-0.9: Litt usikker på ett tall (f.eks. 1 vs 7)
- 0.5-0.7: Flere usikre tall
- Under 0.5: Kvalifisert gjetning

Eksempel: Bilde med "desember 2025, mandag 07:00 - 15:00, 1, tirsdag 14:00 - 22:00, 2"
Forventet output:
{
    "shifts": [
        {"date": "01.12.2025", "start_time": "07:00", "end_time": "15:00", "shift_type": "tidlig", "confidence": 0.95},
        {"date": "02.12.2025", "start_time": "14:00", "end_time": "22:00", "shift_type": "mellom", "confidence": 0.95}
    ],
    "notes": null
}

Viktig:
- Alle måneder og datoer i bildet skal inkluderes
- Datoformat ALLTID DD.MM.YYYY (null-padded)
- Tidsformat ALLTID HH:MM (null-padded, 24-timers)
- Returner BARE JSON, ingen markdown eller forklaring"""


class VisionProcessor:
    """Process shift schedule images using GPT-4 Vision."""

    # Max image file size before compression (2MB)
    MAX_RAW_SIZE = 2 * 1024 * 1024
    # Max image dimension for GPT-4o Vision "high" detail
    MAX_DIMENSION = 2048

    def __init__(self, api_key: str):
        """
        Initialize Vision processor.

        Args:
            api_key: OpenAI API key
        """
        if not api_key:
            raise ValueError("OpenAI API key is required for Vision processing")

        # Create httpx client without proxies to avoid compatibility issues
        http_client = httpx.Client(timeout=60.0)
        self.client = OpenAI(api_key=api_key, http_client=http_client)

    def process_image(self, image_path: str, debug: bool = False) -> Tuple[List[Shift], float]:
        """
        Process shift schedule image with GPT-4 Vision.

        Args:
            image_path: Path to image file
            debug: Enable debug output

        Returns:
            Tuple of (list of shifts, overall confidence score)
        """
        # Encode image (with compression if needed)
        image_data, mime_type = self._encode_image(image_path)

        if debug:
            logger.debug("Image encoded: %d bytes base64, MIME: %s", len(image_data), mime_type)

        try:
            # Call Vision API with retry logic
            data = self._call_vision_api(image_data, mime_type, debug)

            # Parse shifts from response
            shifts_data = data.get("shifts", [])
            notes = data.get("notes")

            if notes:
                logger.info("Vision API notes: %s", notes)

            # Convert to Shift objects with graceful error handling
            shifts = []
            for shift_data in shifts_data:
                try:
                    confidence = min(max(float(shift_data.get("confidence", 0.85)), 0.0), 1.0)
                    shift = Shift(
                        date=shift_data["date"],
                        start_time=shift_data["start_time"],
                        end_time=shift_data["end_time"],
                        shift_type=shift_data["shift_type"],
                        confidence=confidence,
                    )
                    shifts.append(shift)

                    if debug:
                        logger.debug(
                            "Vision shift: %s %s-%s (%s, conf=%.2f)",
                            shift.date, shift.start_time, shift.end_time,
                            shift.shift_type, shift.confidence,
                        )
                except (KeyError, ValueError, ValidationError) as e:
                    logger.warning("Skipping invalid shift from Vision: %s (data: %s)", e, shift_data)
                    continue

            # Overall confidence = average of individual, or 0.0 if empty
            overall_confidence = (
                sum(s.confidence for s in shifts) / len(shifts) if shifts else 0.0
            )

            return shifts, overall_confidence

        except json.JSONDecodeError as e:
            error_msg = f"Vision API returned invalid JSON: {e}"
            logger.error(error_msg)
            raise ValueError(error_msg)

        except (RateLimitError, APITimeoutError, APIConnectionError) as e:
            # These should have been retried by tenacity; if we get here, all retries failed
            error_msg = f"Vision API unavailable after retries: {e}"
            logger.error(error_msg)
            raise ValueError(error_msg)

        except ValueError:
            raise

        except Exception as e:
            error_msg = f"Vision processing failed: {e}"
            logger.error(error_msg)
            raise ValueError(error_msg)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        retry=retry_if_exception_type((RateLimitError, APITimeoutError, APIConnectionError)),
        before_sleep=lambda state: logger.warning(
            "Vision API retry %d/3 after: %s", state.attempt_number, state.outcome.exception()
        ),
        reraise=True,
    )
    def _call_vision_api(self, image_data: str, mime_type: str, debug: bool) -> dict:
        """Call Vision API with retry logic for transient failures."""
        if debug:
            logger.debug("Calling Vision API (model: %s)...", settings.openai_model)

        response = self.client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {"role": "system", "content": SYSTEM_MESSAGE},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": USER_PROMPT},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime_type};base64,{image_data}",
                                "detail": "high",
                            },
                        },
                    ],
                },
            ],
            max_tokens=4000,
            temperature=0.1,
            response_format={"type": "json_object"},
        )

        # Log token usage for cost tracking
        if response.usage:
            logger.info(
                "Vision tokens: prompt=%d, completion=%d, total=%d",
                response.usage.prompt_tokens,
                response.usage.completion_tokens,
                response.usage.total_tokens,
            )

        content = response.choices[0].message.content

        if debug:
            logger.debug("Vision API response: %s", content[:500] if content else "(empty)")

        if not content or not content.strip():
            raise ValueError("Vision API returned empty response")

        return json.loads(content)

    def close(self):
        """Close the underlying httpx client to free resources."""
        if hasattr(self, 'client') and hasattr(self.client, '_client'):
            try:
                self.client._client.close()
            except Exception:
                pass

    def _encode_image(self, image_path: str) -> Tuple[str, str]:
        """
        Encode image to base64, compressing large files to save tokens/cost.

        Returns:
            Tuple of (base64_data, mime_type)
        """
        path = Path(image_path)
        file_ext = path.suffix.lower()
        mime_type = SUPPORTED_MIME_TYPES.get(file_ext, 'image/jpeg')

        file_size = path.stat().st_size

        if file_size > self.MAX_RAW_SIZE:
            # Compress large images
            logger.info("Compressing large image (%d bytes) before Vision API", file_size)
            image = Image.open(image_path)

            # Resize if dimensions exceed Vision API limits
            if max(image.size) > self.MAX_DIMENSION:
                image.thumbnail((self.MAX_DIMENSION, self.MAX_DIMENSION), Image.LANCZOS)

            buffer = io.BytesIO()
            image.save(buffer, format='JPEG', quality=85, optimize=True)
            buffer.seek(0)
            return base64.b64encode(buffer.read()).decode('utf-8'), 'image/jpeg'

        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode('utf-8'), mime_type
