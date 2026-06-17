import json
import logging
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from src.client import OpenF1Client
from src.models import (
    Meeting, Session, CircuitHistoricalData,
    Lap, Stint, PitStop, Position, SessionResult, Overtake,
    Weather, CarData,
)

logger = logging.getLogger(__name__)

CACHE_DIR = Path("data") / "circuits"
CACHE_MAX_AGE = 86400


def _cache_path(circuit_name: str, year: int) -> Path:
    return CACHE_DIR / f"{circuit_name.lower()}_{year}.json"


def _dict_to_historical(data: dict) -> CircuitHistoricalData:
    obj = CircuitHistoricalData(
        circuit_name=data["circuit_name"],
        country=data["country"],
        year=data["year"],
        meeting_key=data["meeting_key"],
    )
    for item in data.get("sessions", []):
        obj.sessions.append(Session(**item))
    for item in data.get("laps", []):
        obj.laps.append(Lap(**item))
    for item in data.get("stints", []):
        obj.stints.append(Stint(**item))
    for item in data.get("pit_stops", []):
        obj.pit_stops.append(PitStop(**item))
    for item in data.get("positions", []):
        obj.positions.append(Position(**item))
    for item in data.get("results", []):
        obj.results.append(SessionResult(**item))
    for item in data.get("overtakes", []):
        obj.overtakes.append(Overtake(**item))
    for item in data.get("weather", []):
        obj.weather.append(Weather(**item))
    return obj


def _load_cached_data(circuit_name: str, year: int) -> Optional[CircuitHistoricalData]:
    path = _cache_path(circuit_name, year)
    if not path.exists():
        return None
    age = datetime.now(timezone.utc).timestamp() - path.stat().st_mtime
    if age > CACHE_MAX_AGE:
        return None
    with open(path, "r") as f:
        data = json.load(f)
    return _dict_to_historical(data)


def _save_cached_data(data: CircuitHistoricalData):
    path = _cache_path(data.circuit_name, data.year)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(asdict(data), f, indent=2, default=str)


def fetch_session_data(
    client: OpenF1Client, session_key: int, session_type: str
) -> dict:
    data = {}
    data["laps"] = client.get_laps(session_key)
    data["stints"] = client.get_stints(session_key)
    data["pit_stops"] = client.get_pit_stops(session_key)
    data["positions"] = client.get_positions(session_key)
    data["weather"] = client.get_weather(session_key)
    if session_type == "Race":
        data["results"] = client.get_session_results(session_key)
        data["overtakes"] = client.get_overtakes(session_key)
    return data


def build_historical_data(
    client: OpenF1Client, meeting: Meeting, year: int
) -> Optional[CircuitHistoricalData]:
    sessions = client.get_sessions(meeting_key=meeting.meeting_key)
    historical_data = CircuitHistoricalData(
        circuit_name=meeting.circuit_short_name,
        country=meeting.country_name,
        year=year,
        meeting_key=meeting.meeting_key,
    )
    for s in sessions:
        st = s.get("session_type", "")
        if st not in ("Race", "Qualifying", "Practice", "Sprint"):
            continue
        sk = s.get("session_key")
        if not sk:
            continue
        session = Session(
            session_key=sk,
            meeting_key=s.get("meeting_key", 0),
            session_name=s.get("session_name", ""),
            session_type=st,
            date_start=s.get("date_start", ""),
            date_end=s.get("date_end", ""),
        )
        historical_data.sessions.append(session)
        try:
            session_data = fetch_session_data(client, session.session_key, st)
            for lap in session_data.get("laps", []):
                dn = lap.get("driver_number")
                if dn is None:
                    continue
                historical_data.laps.append(Lap(
                    driver_number=dn,
                    session_key=lap.get("session_key", session.session_key),
                    lap_number=lap.get("lap_number", 0),
                    lap_duration=lap.get("lap_duration"),
                    lap_time=lap.get("lap_duration"),
                    is_pit_out_lap=lap.get("is_pit_out_lap", False),
                    is_pit_in_lap=lap.get("is_pit_in_lap", False),
                    duration_sector_1=lap.get("duration_sector_1"),
                    duration_sector_2=lap.get("duration_sector_2"),
                    duration_sector_3=lap.get("duration_sector_3"),
                    segments_sector_1=lap.get("segments_sector_1"),
                    segments_sector_2=lap.get("segments_sector_2"),
                    segments_sector_3=lap.get("segments_sector_3"),
                ))
            for stint in session_data.get("stints", []):
                dn = stint.get("driver_number")
                if dn is None:
                    continue
                historical_data.stints.append(Stint(
                    driver_number=dn,
                    session_key=stint.get("session_key", session.session_key),
                    stint_number=stint.get("stint_number", 0),
                    lap_start=stint.get("lap_start", 0),
                    lap_end=stint.get("lap_end", 0),
                    compound=stint.get("compound") or "",
                    tyre_age_at_start=stint.get("tyre_age_at_start"),
                ))
            for pit in session_data.get("pit_stops", []):
                dn = pit.get("driver_number")
                if dn is None:
                    continue
                historical_data.pit_stops.append(PitStop(
                    driver_number=dn,
                    session_key=pit.get("session_key", session.session_key),
                    lap_number=pit.get("lap_number", 0),
                    pit_duration=pit.get("pit_duration"),
                    tyre_change=pit.get("tyre_change", False),
                ))
            for pos in session_data.get("positions", []):
                dn = pos.get("driver_number")
                if dn is None:
                    continue
                historical_data.positions.append(Position(
                    driver_number=dn,
                    session_key=pos.get("session_key", session.session_key),
                    position=pos.get("position", 0),
                    date=pos.get("date", ""),
                ))
            for w in session_data.get("weather", []):
                historical_data.weather.append(Weather(
                    session_key=w.get("session_key", session.session_key),
                    air_temperature=w.get("air_temperature"),
                    track_temperature=w.get("track_temperature"),
                    humidity=w.get("humidity"),
                    rainfall=w.get("rainfall", False),
                    wind_speed=w.get("wind_speed"),
                ))
            if st == "Race":
                for r in session_data.get("results", []):
                    dn = r.get("driver_number")
                    if dn is None:
                        continue
                    historical_data.results.append(SessionResult(
                        driver_number=dn,
                        session_key=r.get("session_key", session.session_key),
                        position=r.get("position", 0),
                        total_laps=r.get("total_laps", 0),
                        time_penalty=r.get("time_penalty"),
                        grid_position=r.get("grid_position", 0),
                        finishing_status=r.get("finishing_status", ""),
                    ))
                for ov in session_data.get("overtakes", []):
                    dn = ov.get("driver_number")
                    if dn is None:
                        continue
                    historical_data.overtakes.append(Overtake(
                        driver_number=dn,
                        session_key=ov.get("session_key", session.session_key),
                        overtake_count=ov.get("overtake_count", 0),
                        date=ov.get("date", ""),
                    ))
        except Exception as e:
            logger.warning(f"Error fetching session {session.session_key}: {e}")
            continue
    return historical_data


def fetch_circuit_history(
    client: OpenF1Client, circuit_name: str, exclude_year: int = None
) -> list[CircuitHistoricalData]:
    from src.calendar import get_historical_meetings_for_circuit
    meetings = get_historical_meetings_for_circuit(client, circuit_name, exclude_year)
    results = []
    for meeting in meetings:
        cached = _load_cached_data(circuit_name, meeting.year)
        if cached is not None:
            logger.info(f"Using cached data for {circuit_name} ({meeting.year})")
            results.append(cached)
            continue
        logger.info(f"Fetching historical data for {circuit_name} ({meeting.year})")
        data = build_historical_data(client, meeting, meeting.year)
        if data:
            _save_cached_data(data)
            results.append(data)
    return results
