"""
Calendar generation from shift data.
Decoupled from OCR processor to avoid Tesseract dependency for calendar endpoints.
"""
import logging
import re
import uuid
from datetime import datetime, timedelta
from typing import List
from zoneinfo import ZoneInfo

from icalendar import Calendar, Event
import nh3

from app.models import Shift

logger = logging.getLogger('shiftsync')


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


def generate_ics(shifts: List[Shift], owner_name: str) -> bytes:
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
        event = _create_event(shift, safe_name)
        calendar.add_component(event)

    return calendar.to_ical()


def _create_event(shift: Shift, owner_name: str) -> Event:
    """
    Create iCalendar event from shift.

    Args:
        shift: Shift object
        owner_name: Name of shift owner

    Returns:
        iCalendar Event object
    """
    tz = ZoneInfo("Europe/Oslo")

    # Parse start datetime with timezone
    start_dt = datetime.strptime(
        f"{shift.date} {shift.start_time}",
        "%d.%m.%Y %H:%M"
    ).replace(tzinfo=tz)

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
    event.add('uid', f'{uuid.uuid4()}@shiftsync.no')

    return event
