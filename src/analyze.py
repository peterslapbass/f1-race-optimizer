import logging
import statistics
from collections import defaultdict
from typing import Optional

import pandas as pd
import numpy as np

from src.models import CircuitHistoricalData, TireStats, SessionResult

logger = logging.getLogger(__name__)


def calc_tire_degradation(laps: list, stints: list, session_key: int) -> dict[str, float]:
    laps_df = pd.DataFrame([l.__dict__ for l in laps if l.session_key == session_key])
    stints_df = pd.DataFrame([s.__dict__ for s in stints if s.session_key == session_key])
    if laps_df.empty or stints_df.empty:
        return {}
    laps_df = laps_df.dropna(subset=["lap_duration"])
    stints_df = stints_df.dropna(subset=["lap_start", "lap_end"])
    merged = pd.merge(
        laps_df, stints_df[["driver_number", "stint_number", "lap_start", "lap_end", "compound"]],
        on="driver_number", suffixes=("", "_stint")
    )
    merged = merged[
        (merged["lap_number"] >= merged["lap_start"]) &
        (merged["lap_number"] <= merged["lap_end"])
    ]
    merged = merged[merged["is_pit_out_lap"] == False]
    merged = merged[merged["is_pit_in_lap"] == False]
    if merged.empty:
        return {}
    merged["lap_in_stint"] = merged["lap_number"] - merged["lap_start"]
    degradation = {}
    for compound, group in merged.groupby("compound"):
        if len(group) < 10:
            continue
        lap_series = group.groupby("driver_number")["lap_in_stint"].apply(list)
        time_series = group.groupby("driver_number")["lap_duration"].apply(list)
        slopes = []
        for driver_id in lap_series.index:
            x = np.array(lap_series[driver_id])
            y = np.array(time_series[driver_id])
            if len(x) < 3:
                continue
            slope, _ = np.polyfit(x, y, 1)
            slopes.append(slope)
        if slopes:
            degradation[compound] = float(np.median(slopes))
    return degradation


def calc_tire_stats(historical: list[CircuitHistoricalData]) -> list[TireStats]:
    all_stints = []
    for h in historical:
        for s in h.stints:
            if not s.compound:
                continue
            stint_length = s.lap_end - s.lap_start + 1
            if stint_length > 2:
                all_stints.append((s.compound, stint_length))
    compound_groups = defaultdict(list)
    for compound, length in all_stints:
        compound_groups[compound].append(length)
    stats = []
    for compound, lengths in compound_groups.items():
        if len(lengths) < 3:
            continue
        stats.append(TireStats(
            compound=compound,
            avg_stint_length=statistics.mean(lengths),
            median_stint_length=statistics.median(lengths),
            max_stint_length=max(lengths),
            min_stint_length=min(lengths),
            degradation_per_lap=0.0,
            count=len(lengths),
        ))
    for h in historical:
        for session in h.sessions:
            if session.session_type == "Race":
                deg = calc_tire_degradation(h.laps, h.stints, session.session_key)
                for ts in stats:
                    if ts.compound in deg:
                        ts.degradation_per_lap = deg[ts.compound]
    return stats


def calc_race_stats(historical: list[CircuitHistoricalData]) -> dict:
    race_times = []
    winner_lap_times = []
    overtake_counts = []
    safety_car_periods = 0
    total_races = 0
    for h in historical:
        for session in h.sessions:
            if session.session_type != "Race":
                continue
            total_races += 1
            session_results = [r for r in h.results if r.session_key == session.session_key]
            if session_results:
                winner = next((r for r in session_results if r.position == 1), None)
                if winner:
                    winner_laps = [l for l in h.laps if l.session_key == session.session_key and l.driver_number == winner.driver_number]
                    valid_laps = [l.lap_duration for l in winner_laps if l.lap_duration and not l.is_pit_in_lap and not l.is_pit_out_lap]
                    if valid_laps:
                        winner_lap_times.append(statistics.median(valid_laps))
            session_overtakes = [o for o in h.overtakes if o.session_key == session.session_key]
            if session_overtakes:
                overtake_counts.append(max(o.overtake_count for o in session_overtakes))
    return {
        "total_races": total_races,
        "avg_winner_lap_time": statistics.median(winner_lap_times) if winner_lap_times else None,
        "avg_overtakes": statistics.mean(overtake_counts) if overtake_counts else None,
    }


def calc_weather_pattern(historical: list[CircuitHistoricalData]) -> dict:
    rain_count = 0
    total_sessions = 0
    temp_readings = []
    track_temp_readings = []
    for h in historical:
        for w in h.weather:
            total_sessions += 1
            if w.rainfall:
                rain_count += 1
            if w.air_temperature:
                temp_readings.append(w.air_temperature)
            if w.track_temperature:
                track_temp_readings.append(w.track_temperature)
    return {
        "rain_probability": rain_count / total_sessions if total_sessions > 0 else 0,
        "avg_air_temp": statistics.mean(temp_readings) if temp_readings else None,
        "avg_track_temp": statistics.mean(track_temp_readings) if track_temp_readings else None,
    }


def calc_quali_stats(historical: list[CircuitHistoricalData]) -> dict:
    quali_sessions = []
    for h in historical:
        for s in h.sessions:
            if s.session_type == "Qualifying":
                quali_sessions.append(s)
    improvements = []
    for qs in quali_sessions:
        laps = [l for l in h.laps for h in historical if l.session_key == qs.session_key]
        laps_df = pd.DataFrame([l.__dict__ for l in laps])
        if laps_df.empty:
            continue
        laps_df = laps_df.dropna(subset=["lap_duration"])
        if laps_df.empty:
            continue
        best = laps_df.groupby("driver_number")["lap_duration"].min()
        if len(best) >= 10:
            q1_best = best.nsmallest(15).median()
            q3_best = best.nsmallest(10).median()
            if q1_best and q3_best and q1_best > 0:
                improvements.append((q1_best - q3_best) / q1_best * 100)
    return {
        "quali_improvement_rate": statistics.mean(improvements) if improvements else None,
    }
