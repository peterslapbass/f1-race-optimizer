import logging
import statistics
from collections import defaultdict
from datetime import datetime, timezone
from typing import Optional

from src.client import OpenF1Client
from src.models import (
    CircuitHistoricalData, CircuitPrediction, StrategyOption, Meeting, Session,
)
from src.fetch import fetch_circuit_history, build_historical_data
from src.analyze import (
    calc_tire_stats, calc_race_stats, calc_weather_pattern, calc_quali_stats,
    calc_grid_finish_stats, calc_driver_overtakes, calc_consistency,
    calc_quali_pole_stats, calc_quali_gap_stats, calc_quali_consistency,
    calc_race_pace_data,
)
from src.strategy import recommend_strategy

logger = logging.getLogger(__name__)


def generate_prediction(
    client: OpenF1Client,
    meeting: Meeting,
    race_session: Optional[Session],
) -> Optional[CircuitPrediction]:
    circuit_name = meeting.circuit_short_name
    year = meeting.year
    logger.info(f"Generating prediction for {circuit_name} ({year})")
    historical = fetch_circuit_history(client, circuit_name, exclude_year=year)
    if not historical:
        logger.warning(f"No historical data found for {circuit_name}")
        return None
    prediction = CircuitPrediction(
        circuit_name=circuit_name,
        country=meeting.country_name,
        meeting_key=meeting.meeting_key,
        session_key=race_session.session_key if race_session else 0,
        year=year,
        generated_at=datetime.now(timezone.utc).isoformat(),
    )
    # Tire stats
    tire_stats = calc_tire_stats(historical)
    prediction.tire_stats = tire_stats
    # Race stats
    race_stats = calc_race_stats(historical)
    prediction.avg_winner_lap_time = race_stats.get("avg_winner_lap_time")
    prediction.avg_overtakes = race_stats.get("avg_overtakes")
    # Weather
    prediction.weather_pattern = calc_weather_pattern(historical)
    # Quali
    quali_stats = calc_quali_stats(historical)
    prediction.quali_improvement_rate = quali_stats.get("quali_improvement_rate")
    race_count = sum(1 for h in historical for s in h.sessions if s.session_type == "Race")
    prediction.safety_car_probability = 0.15
    # Strategy
    total_laps = 58
    if race_session and historical:
        for h in historical:
            for s in h.sessions:
                if s.session_type == "Race":
                    results = [r for r in h.results if r.session_key == s.session_key]
                    if results:
                        total_laps = max(r.total_laps for r in results)
                        if total_laps > 0:
                            break
    if total_laps <= 0:
        total_laps = 71
    recommended, top_strategies = recommend_strategy(historical, tire_stats, total_laps)
    prediction.recommended_strategy = recommended
    prediction.strategies = top_strategies
    # Driver map (from all historical Race sessions)
    try:
        race_sks = set()
        for h in historical:
            for s in h.sessions:
                if s.session_type == "Race":
                    race_sks.add(s.session_key)
        for sk in sorted(race_sks):
            try:
                drivers_raw = client.get_drivers(session_key=sk)
                for d in drivers_raw:
                    dn = d.get("driver_number")
                    if dn:
                        prediction.driver_map[dn] = {
                            "full_name": d.get("full_name", f"Driver {dn}"),
                            "team_name": d.get("team_name", "Unknown"),
                            "name_acronym": d.get("name_acronym", ""),
                        }
            except Exception:
                continue
    except Exception as e:
        logger.warning(f"Failed to fetch driver map: {e}")
    # Quali analysis (needs driver_map)
    try:
        quali_pole = calc_quali_pole_stats(historical, prediction.driver_map)
        prediction.quali_pole_data = quali_pole
    except Exception as e:
        logger.warning(f"Failed to compute quali pole stats: {e}")
    try:
        quali_gaps = calc_quali_gap_stats(historical, prediction.driver_map)
        prediction.quali_gap_data = quali_gaps
    except Exception as e:
        logger.warning(f"Failed to compute quali gap stats: {e}")
    try:
        quali_consistency = calc_quali_consistency(historical)
        prediction.quali_consistency_data = quali_consistency
    except Exception as e:
        logger.warning(f"Failed to compute quali consistency: {e}")
    # Race pace data
    try:
        race_pace = calc_race_pace_data(historical, prediction.driver_map, top_n=6)
        prediction.race_pace_data = race_pace
    except Exception as e:
        logger.warning(f"Failed to compute race pace data: {e}")
    # Grid vs finish
    prediction.grid_finish_data = calc_grid_finish_stats(historical)
    # Overtakes by driver
    prediction.overtake_data = calc_driver_overtakes(historical)
    # Consistency (historical)
    prediction.consistency_data = calc_consistency(historical)
    # Season consistency (2026 current season)
    logger.info("Fetching 2026 season data for consistency")
    all_sessions = client.get_sessions(year=2026, session_type="Race")
    now = datetime.now(timezone.utc)
    laps_by_driver = defaultdict(list)
    season_driver_map = {}
    for s in all_sessions:
        sk = s.get("session_key")
        if not sk:
            continue
        de = s.get("date_end")
        if de:
            try:
                de_dt = datetime.fromisoformat(de.replace("Z", "+00:00"))
                if de_dt >= now:
                    continue
            except (ValueError, TypeError):
                continue
        try:
            laps_raw = client.get_laps(session_key=sk)
        except Exception:
            continue
        if not laps_raw:
            continue
        if not season_driver_map:
            try:
                drivers_raw = client.get_drivers(session_key=sk)
                for d in drivers_raw:
                    dn = d.get("driver_number")
                    if dn:
                        season_driver_map[dn] = {
                            "full_name": d.get("full_name", f"Driver {dn}"),
                            "team_name": d.get("team_name", ""),
                        }
            except Exception:
                pass
        for lap in laps_raw:
            dn = lap.get("driver_number")
            dur = lap.get("lap_duration")
            if dn is None or not dur:
                continue
            if lap.get("is_pit_in_lap") or lap.get("is_pit_out_lap"):
                continue
            laps_by_driver[dn].append(dur)
    season_consistency = []
    for dn, laps in laps_by_driver.items():
        if len(laps) < 10:
            continue
        try:
            avg = statistics.mean(laps)
            std = statistics.stdev(laps)
            clean = [l for l in laps if abs(l - avg) < 3 * std]
            if len(clean) < 10:
                continue
            info = season_driver_map.get(dn, {})
            season_consistency.append({
                "driver_number": dn,
                "full_name": info.get("full_name", f"#{dn}"),
                "team_name": info.get("team_name", ""),
                "avg_lap_time": statistics.mean(clean),
                "std_lap_time": statistics.stdev(clean),
                "count": len(clean),
            })
        except Exception:
            continue
    season_consistency.sort(key=lambda x: x["std_lap_time"])
    prediction.season_consistency_data = season_consistency
    logger.info(f"Season consistency: {len(season_consistency)} drivers from {len(laps_by_driver)} total")
    # Last race data (most recent completed 2026 race)
    try:
        all_sessions_races = client.get_sessions(year=2026, session_type="Race")
        now = datetime.now(timezone.utc)
        last_race = None
        for s in all_sessions_races:
            de = s.get("date_end", "")
            if not de:
                continue
            try:
                de_dt = datetime.fromisoformat(de.replace("Z", "+00:00"))
                if de_dt >= now:
                    continue
                if last_race is None or de_dt > datetime.fromisoformat(last_race["date_end"].replace("Z", "+00:00")):
                    last_race = s
            except (ValueError, TypeError):
                continue
        if last_race:
            lsk = last_race.get("session_key")
            mk = last_race.get("meeting_key")
            circuit_name = last_race.get("session_name", "Unknown")
            if mk:
                try:
                    meetings = client.get_meetings(meeting_key=mk)
                    if meetings:
                        circuit_name = meetings[0].get("circuit_short_name", circuit_name)
                except Exception:
                    pass
            lr = {"circuit_name": circuit_name, "date_end": last_race.get("date_end", ""), "results": [], "fastest_lap": None, "top_speeds": []}
            results_raw = client.get_session_results(session_key=lsk) if lsk else []
            laps_raw = client.get_laps(session_key=lsk) if lsk else []
            drivers_raw = client.get_drivers(session_key=lsk) if lsk else {}
            driver_names = {}
            for d in drivers_raw:
                dn = d.get("driver_number")
                if dn:
                    driver_names[dn] = {"full_name": d.get("full_name", f"#{dn}"), "team_name": d.get("team_name", "")}
            fastest_lap_time = float("inf")
            fastest_driver = None
            lap_counts = defaultdict(list)
            for lap in laps_raw:
                dn = lap.get("driver_number")
                dur = lap.get("lap_duration")
                if dn and dur:
                    lap_counts[dn].append(dur)
            driver_best_laps = {}
            for dn, times in lap_counts.items():
                bt = min(times)
                driver_best_laps[dn] = bt
                if bt < fastest_lap_time:
                    fastest_lap_time = bt
                    fastest_driver = dn
            by_position = {}
            for r in results_raw:
                dn = r.get("driver_number")
                pos = r.get("position")
                if dn and pos:
                    by_position[pos] = dn
            for pos in sorted(by_position.keys())[:5]:
                dn = by_position[pos]
                info = driver_names.get(dn, {})
                bt = driver_best_laps.get(dn)
                lr["results"].append({
                    "position": pos,
                    "driver_number": dn,
                    "full_name": info.get("full_name", f"#{dn}"),
                    "team_name": info.get("team_name", ""),
                    "fastest_lap": bt,
                })
            if fastest_driver:
                lr["fastest_lap"] = {"driver_number": fastest_driver, "full_name": driver_names.get(fastest_driver, {}).get("full_name", f"#{fastest_driver}"), "lap_time": fastest_lap_time}
            for pos in sorted(by_position.keys())[:3]:
                dn = by_position[pos]
                info = driver_names.get(dn, {})
                try:
                    cd = client.get_car_data(session_key=lsk, driver_number=dn)
                    max_speed = 0
                    for entry in cd:
                        s = entry.get("speed") if isinstance(entry, dict) else getattr(entry, "speed", 0)
                        if s and isinstance(s, (int, float)) and s > max_speed:
                            max_speed = s
                    if max_speed > 0:
                        lr["top_speeds"].append({
                            "driver_number": dn,
                            "full_name": info.get("full_name", f"#{dn}"),
                            "top_speed": max_speed,
                        })
                except Exception:
                    continue
            prediction.last_race_data = lr
            logger.info(f"Last race data: {lr['circuit_name']}, {len(lr['results'])} results, {len(lr['top_speeds'])} speeds")
    except Exception as e:
        logger.warning(f"Failed to fetch last race data: {e}")
    return prediction



