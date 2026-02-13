"""
OCR processor for shift schedule images.
Refactored from vaktplan_konverter.py into modular OOP structure.
"""
import logging
from typing import List, Tuple, Optional
from PIL import Image, ImageFilter, ImageOps
import pytesseract
import re
from pathlib import Path

from app.models import Shift

logger = logging.getLogger('shiftsync')


class VaktplanProcessor:
    """Main processor for shift schedule OCR."""
    
    # Norwegian month names mapping
    MONTH_NAMES = {
        'januar': 1, 'februar': 2, 'mars': 3, 'april': 4,
        'mai': 5, 'juni': 6, 'juli': 7, 'august': 8,
        'september': 9, 'oktober': 10, 'november': 11, 'desember': 12
    }
    
    # Shift type classification based on start time
    SHIFT_TYPES = {
        'tidlig': (6, 12),    # 06:00 - 11:59
        'mellom': (12, 16),   # 12:00 - 15:59
        'kveld': (16, 22),    # 16:00 - 21:59
        'natt': (22, 6)       # 22:00 - 05:59 (wraps midnight)
    }
    
    def __init__(self, tesseract_path: str, language: str = "nor"):
        """
        Initialize processor.
        
        Args:
            tesseract_path: Path to Tesseract executable
            language: OCR language code (default: 'nor' for Norwegian)
        """
        self.tesseract_path = tesseract_path
        self.language = language
        
        # Validate Tesseract installation
        if not Path(tesseract_path).exists():
            raise FileNotFoundError(
                f"Tesseract not found at: {tesseract_path}. "
                f"Install from https://github.com/UB-Mannheim/tesseract/wiki"
            )
        
        pytesseract.pytesseract.tesseract_cmd = tesseract_path
    
    # Tesseract config: PSM 6 = uniform text block (good for tabular schedules)
    # OEM 3 = auto-select best engine (LSTM + legacy fallback)
    TESSERACT_CONFIG = '--psm 6 --oem 3'

    def process_image(self, image_path: str, debug: bool = False) -> Tuple[List[Shift], float, str]:
        """
        Process shift schedule image with OCR.

        Args:
            image_path: Path to image file
            debug: Enable debug output

        Returns:
            Tuple of (list of shifts, overall confidence score, raw OCR text)
        """
        # Improve image quality for better OCR
        image = self._improve_image(image_path)

        # Perform OCR with tuned config
        ocr_text = pytesseract.image_to_string(
            image, lang=self.language, config=self.TESSERACT_CONFIG
        )

        if debug:
            logger.debug("OCR text (first 200 chars): %s...", ocr_text[:200])

        # Extract shifts from text
        shifts = self._extract_shifts(ocr_text, debug=debug)

        # Calculate overall confidence
        from app.ocr.confidence_scorer import calculate_confidence
        confidence = calculate_confidence(ocr_text, shifts)

        return shifts, confidence, ocr_text

    def _improve_image(self, image_path: str) -> Image.Image:
        """
        Multi-step image preprocessing pipeline for OCR optimization.
        1. Convert to grayscale
        2. Scale up small images (Tesseract needs ~300 DPI)
        3. Denoise with median filter
        4. Auto-contrast enhancement
        5. Sharpen edges
        6. Adaptive binarization via Otsu threshold approximation
        """
        image = Image.open(image_path)
        image = image.convert('L')  # Grayscale

        # Scale up small images - Tesseract works best at 300+ DPI
        width, height = image.size
        if width < 1500:
            scale = 2
            image = image.resize((width * scale, height * scale), Image.LANCZOS)

        # Denoise with median filter (removes salt-and-pepper noise)
        image = image.filter(ImageFilter.MedianFilter(size=3))

        # Auto-contrast: stretch histogram to full 0-255 range
        image = ImageOps.autocontrast(image, cutoff=1)

        # Sharpen to recover edges after median filter
        image = image.filter(ImageFilter.SHARPEN)

        # Adaptive binarization: Otsu threshold via histogram analysis
        threshold = self._otsu_threshold(image)
        image = image.point(lambda x: 0 if x < threshold else 255, '1')

        return image

    @staticmethod
    def _otsu_threshold(image: Image.Image) -> int:
        """Calculate optimal binarization threshold using Otsu's method."""
        histogram = image.histogram()
        total = sum(histogram)
        weight_sum = sum(i * histogram[i] for i in range(256))

        cum_count = 0
        cum_weight = 0
        max_variance = 0
        threshold = 128  # fallback

        for i in range(256):
            cum_count += histogram[i]
            if cum_count == 0:
                continue
            bg = cum_count
            fg = total - cum_count
            if fg == 0:
                break
            cum_weight += i * histogram[i]
            mean_bg = cum_weight / bg
            mean_fg = (weight_sum - cum_weight) / fg
            variance = bg * fg * (mean_bg - mean_fg) ** 2
            if variance > max_variance:
                max_variance = variance
                threshold = i

        return threshold
    
    def _extract_shifts(self, ocr_text: str, debug: bool = False) -> List[Shift]:
        """
        Extract shift information from OCR text.
        Supports multiple months in the same image (e.g., November + December).
        
        Args:
            ocr_text: Raw OCR output text
            debug: Enable debug output
            
        Returns:
            List of Shift objects
        """
        text_lower = ocr_text.lower()
        
        # Find ALL month/year occurrences with their positions
        month_year_pattern = r'(januar|februar|mars|april|mai|juni|juli|august|september|oktober|november|desember) (\d{4})'
        month_year_matches = list(re.finditer(month_year_pattern, text_lower))
        
        if not month_year_matches:
            if debug:
                logger.debug("No month/year found in OCR text")
            return []
        
        # Build month sections: each section has a month, year, start pos, end pos
        sections = []
        for i, match in enumerate(month_year_matches):
            month_name, year = match.groups()
            month_num = self.MONTH_NAMES.get(month_name)
            
            if not month_num:
                if debug:
                    logger.debug("Unknown month: %s", month_name)
                continue
            
            start_pos = match.end()  # Start looking for shifts after month header
            
            # End position is start of next month, or end of text
            if i + 1 < len(month_year_matches):
                end_pos = month_year_matches[i + 1].start()
            else:
                end_pos = len(text_lower)
            
            sections.append({
                'month': month_num,
                'year': year,
                'start_pos': start_pos,
                'end_pos': end_pos,
                'month_name': month_name
            })
            
            if debug:
                logger.debug("Found month section: %s %s (pos %d-%d)", month_name, year, start_pos, end_pos)
        
        # Find shift lines with pattern: weekday HH:MM - HH:MM \n day
        # Handles space in day numbers (e.g., "2 3" -> 23)
        # \d\s+\d must come FIRST in alternation to match multi-digit with spaces
        # Only whitespace allowed between time and day number (not arbitrary text)
        shift_pattern = r'(?:mandag|tirsdag|onsdag|torsdag|fredag|l.rdag|.rdag|søndag|s.ndag)\s+(\d{1,2}):(\d{2})\s*-\s*(\d{1,2}):(\d{2})\s{0,20}(\d\s+\d|\d{1,2})'
        shift_matches = re.finditer(shift_pattern, text_lower)

        shifts = []
        seen_shifts = set()  # Avoid duplicates

        for match in shift_matches:
            start_hour, start_min, end_hour, end_min, day = match.groups()
            match_pos = match.start()

            # Validate time values are in valid range
            try:
                sh, sm = int(start_hour), int(start_min)
                eh, em = int(end_hour), int(end_min)
                if not (0 <= sh <= 23 and 0 <= sm <= 59 and 0 <= eh <= 23 and 0 <= em <= 59):
                    if debug:
                        logger.debug("Invalid time: %s:%s - %s:%s", start_hour, start_min, end_hour, end_min)
                    continue
            except ValueError:
                continue
            
            # Find which month section this shift belongs to
            current_month = None
            current_year = None
            current_month_name = None
            
            for section in sections:
                if section['start_pos'] <= match_pos < section['end_pos']:
                    current_month = section['month']
                    current_year = section['year']
                    current_month_name = section['month_name']
                    break
            
            if not current_month:
                # Default to first section if not found
                current_month = sections[0]['month']
                current_year = sections[0]['year']
                current_month_name = sections[0]['month_name']
            
            # Clean day number (remove spaces)
            day = day.replace(' ', '')
            
            try:
                day_int = int(day)
                if not (1 <= day_int <= 31):
                    if debug:
                        logger.debug("Invalid day: %s", day)
                    continue
            except ValueError:
                if debug:
                    logger.debug("Could not parse day: %s", day)
                continue
            
            # Format date and times
            date = f"{day.zfill(2)}.{str(current_month).zfill(2)}.{current_year}"
            start_time = f"{start_hour.zfill(2)}:{start_min}"
            end_time = f"{end_hour.zfill(2)}:{end_min}"
            
            # Avoid duplicates
            shift_key = f"{date}_{start_time}_{end_time}"
            if shift_key in seen_shifts:
                if debug:
                    logger.debug("Duplicate shift skipped: %s %s-%s", date, start_time, end_time)
                continue
            
            seen_shifts.add(shift_key)
            
            # Determine shift type
            shift_type = self._determine_shift_type(start_time, end_time)
            
            shift = Shift(
                date=date,
                start_time=start_time,
                end_time=end_time,
                shift_type=shift_type,
                confidence=1.0  # Will be adjusted by confidence scorer
            )
            
            shifts.append(shift)
            
            if debug:
                logger.debug("Found shift in %s: %s %s-%s (%s)", current_month_name, date, start_time, end_time, shift_type)
        
        return shifts
    
    def _determine_shift_type(self, start_time: str, end_time: str) -> str:
        """
        Determine shift type based on start and end time.
        
        Args:
            start_time: Start time in HH:MM format
            end_time: End time in HH:MM format
            
        Returns:
            Shift type: 'tidlig', 'mellom', 'kveld', or 'natt'
        """
        start_hour = int(start_time.split(':')[0])
        end_hour = int(end_time.split(':')[0])
        
        # Night shift detection (crosses midnight)
        if start_hour >= 20 or start_hour < 6:
            if end_hour <= 10:
                return 'natt'
        
        # Standard classification
        if 6 <= start_hour < 12:
            return 'tidlig'
        elif 12 <= start_hour < 16:
            return 'mellom'
        elif 16 <= start_hour < 22:
            return 'kveld'
        else:
            return 'natt'
    
    def generate_ics(self, shifts: List[Shift], owner_name: str) -> bytes:
        """Delegate to calendar_generator module (single source of truth)."""
        from app.ocr.calendar_generator import generate_ics
        return generate_ics(shifts, owner_name)

