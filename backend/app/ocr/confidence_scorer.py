"""
Confidence scoring for OCR results.
Calculates reliability score based on multiple factors.
"""
import re
from typing import List
from app.ocr.processor import Shift


def calculate_confidence(ocr_text: str, extracted_shifts: List[Shift]) -> float:
    """
    Calculate overall confidence score for OCR results.
    
    Scoring factors:
    - Found month/year: +0.25
    - Found shifts: +0.25
    - Text quality (clean ratio): +0.30
    - Shift consistency (valid dates/times): +0.20
    
    Args:
        ocr_text: Raw OCR output text
        extracted_shifts: List of extracted Shift objects
        
    Returns:
        Confidence score between 0.0 and 1.0
    """
    score = 0.0
    
    # Factor 1: Found month and year (0.25)
    month_year_pattern = r'\b(januar|februar|mars|april|mai|juni|juli|august|september|oktober|november|desember)\s+\d{4}'
    if re.search(month_year_pattern, ocr_text.lower()):
        score += 0.25
    
    # Factor 2: Found at least one shift (0.25)
    if len(extracted_shifts) > 0:
        score += 0.25
    
    # Factor 3: Text quality - ratio of clean characters (0.30)
    if len(ocr_text) > 0:
        clean_chars = len(re.findall(r'[a-zA-ZæøåÆØÅ0-9\s:.-]', ocr_text))
        clean_ratio = clean_chars / len(ocr_text)
        score += clean_ratio * 0.30
    
    # Factor 4: Shift consistency - all shifts have valid data (0.20)
    if len(extracted_shifts) > 0:
        valid_count = sum(1 for shift in extracted_shifts if validate_shift(shift))
        consistency = valid_count / len(extracted_shifts)
        score += consistency * 0.20
    
    # Ensure score is between 0 and 1
    return min(max(score, 0.0), 1.0)


def validate_shift(shift: Shift) -> bool:
    """
    Validate that a shift has correct format and logical values.
    
    Args:
        shift: Shift object to validate
        
    Returns:
        True if shift is valid, False otherwise
    """
    try:
        # Validate date format (DD.MM.YYYY)
        parts = shift.date.split('.')
        if len(parts) != 3:
            return False
        
        day, month, year = map(int, parts)
        if not (1 <= day <= 31 and 1 <= month <= 12 and 2020 <= year <= 2030):
            return False
        
        # Validate time format (HH:MM)
        start_parts = shift.start_time.split(':')
        end_parts = shift.end_time.split(':')
        
        if len(start_parts) != 2 or len(end_parts) != 2:
            return False
        
        start_hour, start_min = map(int, start_parts)
        end_hour, end_min = map(int, end_parts)
        
        if not (0 <= start_hour < 24 and 0 <= start_min < 60):
            return False
        if not (0 <= end_hour < 24 and 0 <= end_min < 60):
            return False
        
        # Validate shift type
        if shift.shift_type not in ['tidlig', 'mellom', 'kveld', 'natt']:
            return False
        
        # Validate confidence
        if not (0.0 <= shift.confidence <= 1.0):
            return False
        
        return True
        
    except (ValueError, AttributeError):
        return False


def assign_individual_confidences(shifts: List[Shift], ocr_text: str) -> List[Shift]:
    """
    Assign individual confidence scores to each shift based on context.
    
    Args:
        shifts: List of Shift objects
        ocr_text: Original OCR text
        
    Returns:
        List of Shift objects with updated confidence scores
    """
    for shift in shifts:
        # Start with base confidence
        conf = 0.7
        
        # Increase if date appears clearly in text
        if shift.date.replace('.', '') in ocr_text.replace(' ', ''):
            conf += 0.1
        
        # Increase if time pattern is clear
        time_pattern = f"{shift.start_time}.*{shift.end_time}"
        if re.search(time_pattern, ocr_text):
            conf += 0.1
        
        # Decrease if odd hour combinations
        start_hour = int(shift.start_time.split(':')[0])
        end_hour = int(shift.end_time.split(':')[0])
        
        # Very short shift (< 4 hours) - lower confidence
        if 0 < (end_hour - start_hour) % 24 < 4:
            conf -= 0.1
        
        # Very long shift (> 12 hours) - lower confidence
        if (end_hour - start_hour) % 24 > 12:
            conf -= 0.1
        
        shift.confidence = min(max(conf, 0.0), 1.0)
    
    return shifts


def generate_warnings(shifts: List[Shift], overall_confidence: float) -> List[str]:
    """
    Generate warning messages based on confidence analysis.
    
    Args:
        shifts: List of Shift objects
        overall_confidence: Overall confidence score
        
    Returns:
        List of warning messages
    """
    warnings = []
    
    # Overall confidence warnings
    if overall_confidence < 0.5:
        warnings.append("Lav sikkerhet på OCR-resultat. Vennligst dobbelsjekk alle vakter.")
    elif overall_confidence < 0.7:
        warnings.append("Moderat sikkerhet. Sjekk spesielt datoer og klokkeslett.")
    
    # Individual shift warnings
    low_confidence_shifts = [s for s in shifts if s.confidence < 0.6]
    if low_confidence_shifts:
        warnings.append(
            f"{len(low_confidence_shifts)} vakt(er) har lav sikkerhet. "
            "Disse er markert med gul bakgrunn."
        )
    
    # Suspicious patterns
    for shift in shifts:
        start_hour = int(shift.start_time.split(':')[0])
        end_hour = int(shift.end_time.split(':')[0])
        duration = (end_hour - start_hour) % 24
        
        if duration < 4:
            warnings.append(
                f"Vakt {shift.date} virker veldig kort ({duration} timer). "
                "Sjekk at tidene er korrekte."
            )
        elif duration > 12:
            warnings.append(
                f"Vakt {shift.date} virker veldig lang ({duration} timer). "
                "Sjekk at tidene er korrekte."
            )
    
    return warnings

