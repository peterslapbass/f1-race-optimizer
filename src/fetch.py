import logging
from typing import Optional

from src.client import OpenF1Client
from src.models import (
    Meeting, Session, CircuitHistoricalData,
    Lap, Stint, PitStop, Position, SessionResult, Overtake,
    Weather, CarData,
)

logger = logging.getLogger(__name__)


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
        session = Session(
            session_key=s["session_key"],
            meeting_key=s["meeting_key"],
            session_name=s.get("session_name", ""),
            session_type=st,
            date_start=s.get("date_start", ""),
            date_end=s.get("date_end", ""),
        )
        historical_data.sessions.append(session)
        try:
            session_data = fetch_session_data(client, session.session_key, st)
            for lap in session_data.get("laps", []):
                historical_data.laps.append(Lap(
                    driver_number=lap["driver_number"],
                    session_key=lap["session_key"],
                    lap_number=lap["lap_number"],
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
                historical_data.stints.append(Stint(
                    driver_number=stint["driver_number"],
                    session_key=stint["session_key"],
                    stint_number=stint["stint_number"],
                    lap_start=stint["lap_start"],
                    lap_end=stint["lap_end"],
                    compound=stint.get("compound", ""),
                    tyre_age_at_start=stint.get("tyre_age_at_start"),
                ))
            for pit in session_data.get("pit_stops", []):
                historical_data.pit_stops.append(PitStop(
                    driver_number=pit["driver_number"],
                    session_key=pit["session_key"],
                    lap_number=pit["lap_number"],
                    pit_duration=pit.get("pit_duration"),
                    tyre_change=pit.get("tyre_change", False),
                ))
            for pos in session_data.get("positions", []):
                historical_data.positions.append(Position(
                    driver_number=pos["driver_number"],
                    session_key=pos["session_key"],
                    position=pos["position"],
                    date=pos.get("date", ""),
                ))
            for w in session_data.get("weather", []):
                historical_data.weather.append(Weather(
                    session_key=w["session_key"],
                    air_temperature=w.get("air_temperature"),
                    track_temperature=w.get("track_temperature"),
                    humidity=w.get("humidity"),
                    rainfall=w.get("rainfall", False),
                    wind_speed=w.get("wind_speed"),
                ))
            if st == "Race":
                for r in session_data.get("results", []):
                    historical_data.results.append(SessionResult(
                        driver_number=r["driver_number"],
                        session_key=r["session_key"],
                        position=r["position"],
                        total_laps=r.get("total_laps", 0),
                        time_penalty=r.get("time_penalty"),
                        grid_position=r.get("grid_position", 0),
                        finishing_status=r.get("finishing_status", ""),
                    ))
                for ov in session_data.get("overtakes", []):
                    historical_data.overtakes.append(Overtake(
                        driver_number=ov["driver_number"],
                        session_key=ov["session_key"],
                        overtake_count=ov["overtake_count"],
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
        logger.info(f"Fetching historical data for {circuit_name} ({meeting.year})")
        data = build_historical_data(client, meeting, meeting.year)
        if data:
            results.append(data)
    return results
