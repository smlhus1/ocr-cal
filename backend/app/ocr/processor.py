"""
OCR processor for shift schedule images.
Refactored from vaktplan_konverter.py into modular OOP structure.
"""
from dataclasses import dataclass
from typing import List, Tuple, Optional
from PIL import Image
import pytesseract
from datetime import datetime, timedelta
from icalendar import Calendar, Event
import re
from pathlib import Path
import nh3


def sanitize_calendar_text(text: str, max_length: int = 100) -> str:
    """
    Sanitize text for use in calendar fields.
    Removes HTML, JavaScript, and other potentially dangerous content.
    
    Args:
        text: Input text to sanitize
        max_length: Maximum allowed length (default: 100)
        
    Returns:
        Sanitized text string
    """
    if not text:
        return ""
    
    # Remove all HTML tags and JavaScript
    clean = nh3.clean(text, tags=set())
    
    # Remove any remaining angle brackets
    clean = re.sub(r'[<>]', '', clean)
    
    # Remove control characters except newlines
    clean = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', clean)
    
    # Normalize whitespace
    clean = ' '.join(clean.split())
    
    # Truncate to max length
    if len(clean) > max_length:
        clean = clean[:max_length-3] + '...'
    
    return clean.strip()


@dataclass
class Shift:
    """Represents a single work shift."""
    date: str  # Format: DD.MM.YYYY
    start_time: str  # Format: HH:MM
    end_time: str  # Format: HH:MM
    shift_type: str  # tidlig, mellom, kveld, natt
    confidence: float = 1.0  # 0.0 to 1.0


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
    
    def process_image(self, image_path: str, debug: bool = False) -> Tuple[List[Shift], float]:
        """
        Process shift schedule image with OCR.
        
        Args:
            image_path: Path to image file
            debug: Enable debug output
            
        Returns:
            Tuple of (list of shifts, overall confidence score)
        """
        # Improve image quality for better OCR
        image = self._improve_image(image_path)
        
        # Perform OCR
        ocr_text = pytesseract.image_to_string(image, lang=self.language)
        
        if debug:
            print(f"[DEBUG] OCR text (first 200 chars): {ocr_text[:200]}...")
        
        # Extract shifts from text
        shifts = self._extract_shifts(ocr_text, debug=debug)
        
        # Calculate overall confidence
        from app.ocr.confidence_scorer import calculate_confidence
        confidence = calculate_confidence(ocr_text, shifts)
        
        return shifts, confidence
    
    def _improve_image(self, image_path: str) -> Image.Image:
        """
        Improve image quality for better OCR results.
        - Convert to grayscale
        - Increase contrast
        """
        image = Image.open(image_path)
        image = image.convert('L')  # Grayscale
        image = image.point(lambda x: 0 if x < 128 else 255, '1')  # High contrast
        return image
    
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
                print("[DEBUG] No month/year found in OCR text")
            return []
        
        # Build month sections: each section has a month, year, start pos, end pos
        sections = []
        for i, match in enumerate(month_year_matches):
            month_name, year = match.groups()
            month_num = self.MONTH_NAMES.get(month_name)
            
            if not month_num:
                if debug:
                    print(f"[DEBUG] Unknown month: {month_name}")
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
                print(f"[DEBUG] Found month section: {month_name} {year} (pos {start_pos}-{end_pos})")
        
        # Find shift lines with pattern: weekday HH:MM - HH:MM \n day
        # Handles space in day numbers (e.g., "2 3" -> 23)
        # \d\s+\d must come FIRST in alternation to match multi-digit with spaces
        shift_pattern = r'(?:mandag|tirsdag|onsdag|torsdag|fredag|l.rdag|.rdag|søndag|s.ndag)\s+(\d{1,2}):(\d{2})\s*-\s*(\d{1,2}):(\d{2})\s*[^\d]{0,30}?(\d\s+\d|\d{1,2})'
        shift_matches = re.finditer(shift_pattern, text_lower)
        
        shifts = []
        seen_shifts = set()  # Avoid duplicates
        
        for match in shift_matches:
            start_hour, start_min, end_hour, end_min, day = match.groups()
            match_pos = match.start()
            
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
                        print(f"[DEBUG] Invalid day: {day}")
                    continue
            except ValueError:
                if debug:
                    print(f"[DEBUG] Could not parse day: {day}")
                continue
            
            # Format date and times
            date = f"{day.zfill(2)}.{str(current_month).zfill(2)}.{current_year}"
            start_time = f"{start_hour.zfill(2)}:{start_min}"
            end_time = f"{end_hour.zfill(2)}:{end_min}"
            
            # Avoid duplicates
            shift_key = f"{date}_{start_time}_{end_time}"
            if shift_key in seen_shifts:
                if debug:
                    print(f"[DEBUG] Duplicate shift skipped: {date} {start_time}-{end_time}")
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
                print(f"[DEBUG] Found shift in {current_month_name}: {date} {start_time}-{end_time} ({shift_type})")
        
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
        """
        Generate iCalendar (.ics) file from shifts.
        
        Args:
            shifts: List of Shift objects
            owner_name: Name of shift owner (will be sanitized)
            
        Returns:
            iCalendar file content as bytes
        """
        # Sanitize owner name to prevent XSS/injection
        safe_name = sanitize_calendar_text(owner_name, max_length=50)
        if not safe_name:
            safe_name = "Ansatt"
        
        calendar = Calendar()
        calendar.add('prodid', '-//ShiftSync//OCR to iCal//NO')
        calendar.add('version', '2.0')
        calendar.add('calscale', 'GREGORIAN')
        calendar.add('x-wr-calname', f'Vakter - {safe_name}')
        
        for shift in shifts:
            event = self._create_event(shift, safe_name)
            calendar.add_component(event)
        
        return calendar.to_ical()
    
    def _create_event(self, shift: Shift, owner_name: str) -> Event:
        """
        Create iCalendar event from shift.
        
        Args:
            shift: Shift object
            owner_name: Name of shift owner
            
        Returns:
            iCalendar Event object
        """
        # Parse start datetime
        start_dt = datetime.strptime(
            f"{shift.date} {shift.start_time}",
            "%d.%m.%Y %H:%M"
        )
        
        # Parse end time
        end_time_obj = datetime.strptime(shift.end_time, "%H:%M")
        
        # Calculate end datetime (handle midnight crossing)
        if end_time_obj.hour < start_dt.hour or \
           (end_time_obj.hour == start_dt.hour and end_time_obj.minute < start_dt.minute):
            # Crosses midnight - add 1 day
            end_dt = start_dt + timedelta(days=1)
            end_dt = end_dt.replace(hour=end_time_obj.hour, minute=end_time_obj.minute)
        else:
            # Same day
            end_dt = start_dt.replace(hour=end_time_obj.hour, minute=end_time_obj.minute)
        
        # Create event
        event = Event()
        event.add('summary', f"{owner_name} jobber {shift.shift_type}")
        event.add('dtstart', start_dt)
        event.add('dtend', end_dt)
        event.add('description', 
                  f'Vakt importert fra vaktplan-bilde via OCR\n'
                  f'Tid: {shift.start_time} - {shift.end_time}\n'
                  f'Type: {shift.shift_type.capitalize()}')
        event.add('uid', f'{start_dt.isoformat()}-{owner_name}@shiftsync.no')
        
        return event

