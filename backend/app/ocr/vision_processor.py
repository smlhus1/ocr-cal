"""
GPT-4 Vision-based OCR processor for shift schedules.
Uses OpenAI's multimodal capabilities for superior accuracy.
"""
import base64
import logging
from typing import List, Tuple
from pathlib import Path
import json

from openai import OpenAI
import httpx
from app.ocr.processor import Shift
from app.config import settings

logger = logging.getLogger('shiftsync')


class VisionProcessor:
    """Process shift schedule images using GPT-4 Vision."""
    
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
        # Read and encode image
        image_data = self._encode_image(image_path)
        
        if debug:
            logger.debug(f"[DEBUG] Image encoded successfully. Size: {len(image_data)} bytes (base64)")
        
        # Create prompt for GPT-4 Vision
        prompt = """
Analyser denne vaktplanen og ekstraher ALL informasjon om vakter.

For hver vakt, returner JSON med følgende struktur:
{
    "shifts": [
        {
            "date": "DD.MM.YYYY",
            "start_time": "HH:MM",
            "end_time": "HH:MM",
            "shift_type": "tidlig|mellom|kveld|natt"
        }
    ]
}

Regler:
- "date" må være i format DD.MM.YYYY (eks: "01.12.2025")
- "start_time" og "end_time" i format HH:MM (eks: "07:30")
- "shift_type" må være: "tidlig" (06:00-11:59), "mellom" (12:00-15:59), "kveld" (16:00-21:59), eller "natt" (22:00-05:59)
- Hvis en vakt krysser midnatt, bruk "natt" som type
- Ignorer tekst som ikke er vakter (overskrifter, notater, etc.)
- Hvis du ser flere måneder, inkluder vakter fra ALLE måneder
- Vær nøye med å skille mellom tall som "1" og "14"

Returner BARE valid JSON, ingen annen tekst.
"""
        
        try:
            if debug:
                logger.debug("[DEBUG] Calling GPT-4 Vision API...")
            
            # Call GPT-4 Vision with JSON mode to ensure valid JSON response
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": prompt
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{image_data}",
                                    "detail": "high"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=2000,
                temperature=0.1,  # Low temperature for consistent extraction
                response_format={"type": "json_object"}  # Force JSON mode
            )
            
            # Parse response
            content = response.choices[0].message.content
            
            if debug:
                logger.debug(f"[DEBUG] Vision API full response: {content}")
            
            if not content or not content.strip():
                raise ValueError("Vision API returned empty response")
            
            # With JSON mode enabled, we get clean JSON directly (no markdown)
            # Parse JSON response
            data = json.loads(content)
            shifts_data = data.get("shifts", [])
            
            # Convert to Shift objects
            shifts = []
            for shift_data in shifts_data:
                shift = Shift(
                    date=shift_data["date"],
                    start_time=shift_data["start_time"],
                    end_time=shift_data["end_time"],
                    shift_type=shift_data["shift_type"],
                    confidence=0.95  # High confidence for Vision API
                )
                shifts.append(shift)
                
                if debug:
                    logger.debug(f"[DEBUG] Vision extracted shift: {shift.date} {shift.start_time}-{shift.end_time} ({shift.shift_type})")
            
            # Calculate confidence (Vision API is typically very accurate)
            overall_confidence = 0.95 if shifts else 0.0
            
            return shifts, overall_confidence
            
        except json.JSONDecodeError as e:
            error_msg = f"Vision API returned invalid JSON: {e}"
            logger.error(error_msg)
            raise ValueError(error_msg)

        except Exception as e:
            error_msg = f"Vision processing failed: {e}"
            logger.error(error_msg)
            raise ValueError(error_msg)
    
    def _encode_image(self, image_path: str) -> str:
        """
        Encode image to base64 string.
        
        Args:
            image_path: Path to image file
            
        Returns:
            Base64 encoded image string
        """
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')

