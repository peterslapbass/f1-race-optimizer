import logging
from datetime import datetime, timezone
from typing import Optional

from src.client import OpenF1Client
from src.models import Meeting, Session

logger = logging.getLogger(__name__)


def get_next_race(client: OpenF1Client, year: int = None) -> Optional[tuple[Meeting, Session]]:
    if year is None:
        year = datetime.now(timezone.utc).year
    meetings = client.get_meetings(year=year)
    if not meetings:
        logger.warning(f"No meetings found for year {year}")
        return None
    now = datetime.now(timezone.utc)
    upcoming = []
    for m in meetings:
        try:
            start = datetime.fromisoformat(m.get("date_start", "").replace("Z", "+00:00"))
            if start > now:
                upcoming.append((start, m))
        except (ValueError, KeyError):
            continue
    if not upcoming:
        logger.info("No upcoming meetings found")
        return None
    upcoming.sort(key=lambda x: x[0])
    _, next_meeting = upcoming[0]
    meeting = Meeting(
        meeting_key=next_meeting["meeting_key"],
        meeting_name=next_meeting.get("meeting_name", ""),
        circuit_short_name=next_meeting.get("circuit_short_name", ""),
        country_name=next_meeting.get("country_name", ""),
        location=next_meeting.get("location", ""),
        year=next_meeting.get("year", year),
        date_start=next_meeting.get("date_start", ""),
        date_end=next_meeting.get("date_end", ""),
    )
    sessions = client.get_sessions(meeting_key=meeting.meeting_key)
    race_session = None
    for s in sessions:
        if s.get("session_type") == "Race":
            race_session = Session(
                session_key=s["session_key"],
                meeting_key=s["meeting_key"],
                session_name=s.get("session_name", ""),
                session_type=s.get("session_type", ""),
                date_start=s.get("date_start", ""),
                date_end=s.get("date_end", ""),
            )
            break
    return meeting, race_session


def get_meeting_by_country(client: OpenF1Client, country: str, year: int = None) -> Optional[Meeting]:
    if year is None:
        year = datetime.now(timezone.utc).year
    meetings = client.get_meetings(year=year, country_name=country)
    if not meetings:
        return None
    m = meetings[0]
    return Meeting(
        meeting_key=m["meeting_key"],
        meeting_name=m.get("meeting_name", ""),
        circuit_short_name=m.get("circuit_short_name", ""),
        country_name=m.get("country_name", ""),
        location=m.get("location", ""),
        year=m.get("year", year),
        date_start=m.get("date_start", ""),
        date_end=m.get("date_end", ""),
    )


def get_historical_meetings_for_circuit(
    client: OpenF1Client, circuit_name: str, exclude_year: int = None
) -> list[Meeting]:
    current_year = datetime.now(timezone.utc).year
    historical = []
    for year in range(current_year - 1, 2022, -1):
        if year == exclude_year:
            continue
        meetings = client.get_meetings(year=year)
        for m in meetings:
            if m.get("circuit_short_name", "").lower() == circuit_name.lower():
                historical.append(Meeting(
                    meeting_key=m["meeting_key"],
                    meeting_name=m.get("meeting_name", ""),
                    circuit_short_name=m.get("circuit_short_name", ""),
                    country_name=m.get("country_name", ""),
                    location=m.get("location", ""),
                    year=m.get("year", year),
                    date_start=m.get("date_start", ""),
                    date_end=m.get("date_end", ""),
                ))
                break
    return historical


def compute_hours_until(start_iso: str) -> float:
    try:
        start = datetime.fromisoformat(start_iso.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        delta = (start - now).total_seconds() / 3600
        return max(0, delta)
    except (ValueError, KeyError):
        return float("inf")


def compute_hours_since(end_iso: str) -> float:
    try:
        end = datetime.fromisoformat(end_iso.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        delta = (now - end).total_seconds() / 3600
        return max(0, delta)
    except (ValueError, KeyError):
        return float("inf")
