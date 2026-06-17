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
            if stint_length > 1:
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
    humidity_readings = []
    wind_speed_readings = []
    for h in historical:
        for w in h.weather:
            total_sessions += 1
            if w.rainfall:
                rain_count += 1
            if w.air_temperature:
                temp_readings.append(w.air_temperature)
            if w.track_temperature:
                track_temp_readings.append(w.track_temperature)
            if w.humidity is not None:
                humidity_readings.append(w.humidity)
            if w.wind_speed is not None:
                wind_speed_readings.append(w.wind_speed)
    return {
        "rain_probability": rain_count / total_sessions if total_sessions > 0 else 0,
        "avg_air_temp": statistics.mean(temp_readings) if temp_readings else None,
        "avg_track_temp": statistics.mean(track_temp_readings) if track_temp_readings else None,
        "avg_humidity": statistics.mean(humidity_readings) if humidity_readings else None,
        "avg_wind_speed": statistics.mean(wind_speed_readings) if wind_speed_readings else None,
    }


def calc_grid_finish_stats(historical: list[CircuitHistoricalData]) -> list[dict]:
    results_by_driver = defaultdict(list)
    for h in historical:
        for s in h.sessions:
            if s.session_type != "Race":
                continue
            sk = s.session_key
            positions_sk = [p for p in h.positions if p.session_key == sk]
            positions_sorted = sorted(positions_sk, key=lambda p: p.date if p.date else "")
            positions_by_driver = {}
            for p in positions_sorted:
                if p.driver_number not in positions_by_driver:
                    positions_by_driver[p.driver_number] = p.position
            for r in h.results:
                if r.session_key != sk:
                    continue
                grid = positions_by_driver.get(r.driver_number, 0)
                finish = r.position
                if grid and finish and grid > 0 and finish > 0:
                    results_by_driver[r.driver_number].append({
                        "grid": grid,
                        "finish": finish,
                        "delta": grid - finish,
                    })
    stats = []
    for dn, entries in results_by_driver.items():
        avg_grid = statistics.mean(e["grid"] for e in entries)
        avg_finish = statistics.mean(e["finish"] for e in entries)
        avg_delta = statistics.mean(e["delta"] for e in entries)
        stats.append({
            "driver_number": dn,
            "avg_grid": avg_grid,
            "avg_finish": avg_finish,
            "avg_delta": avg_delta,
            "count": len(entries),
        })
    stats.sort(key=lambda x: x["avg_delta"], reverse=True)
    return stats


def calc_driver_overtakes(historical: list[CircuitHistoricalData]) -> list[dict]:
    overtakes_by_driver = defaultdict(list)
    for h in historical:
        for ov in h.overtakes:
            dn = ov.driver_number
            if dn:
                overtakes_by_driver[dn].append(ov.overtake_count)
    stats = []
    for dn, counts in overtakes_by_driver.items():
        stats.append({
            "driver_number": dn,
            "avg": statistics.mean(counts),
            "max": max(counts),
            "total": sum(counts),
            "count": len(counts),
        })
    stats.sort(key=lambda x: x["total"], reverse=True)
    return stats


def calc_consistency(historical: list[CircuitHistoricalData]) -> list[dict]:
    by_driver = defaultdict(list)
    for h in historical:
        for s in h.sessions:
            if s.session_type != "Race":
                continue
            for lap in h.laps:
                if lap.session_key != s.session_key:
                    continue
                if not lap.lap_duration:
                    continue
                if lap.is_pit_in_lap or lap.is_pit_out_lap:
                    continue
                by_driver[lap.driver_number].append(lap.lap_duration)
    stats = []
    for dn, laps in by_driver.items():
        if len(laps) < 5:
            continue
        stats.append({
            "driver_number": dn,
            "avg_lap_time": statistics.mean(laps),
            "std_lap_time": statistics.stdev(laps),
            "count": len(laps),
        })
    stats.sort(key=lambda x: x["std_lap_time"])
    return stats


def calc_quali_stats(historical: list[CircuitHistoricalData]) -> dict:
    quali_sessions = []
    for hist in historical:
        for s in hist.sessions:
            if s.session_type == "Qualifying":
                quali_sessions.append(s)
    improvements = []
    laps_by_session = {}
    for hist in historical:
        for l in hist.laps:
            laps_by_session.setdefault(l.session_key, []).append(l)
    for qs in quali_sessions:
        laps = laps_by_session.get(qs.session_key, [])
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


def calc_quali_pole_stats(historical: list[CircuitHistoricalData], driver_lookup: dict) -> list[dict]:
    poles_by_driver = defaultdict(int)
    pole_times = []
    for h in historical:
        for s in h.sessions:
            if s.session_type not in ("Qualifying",):
                continue
            sk = s.session_key
            results_sk = [r for r in h.results if r.session_key == sk]
            pole = next((r for r in results_sk if r.position == 1), None)
            if pole is None:
                continue
            pole_laps = [l for l in h.laps if l.session_key == sk and l.driver_number == pole.driver_number and l.lap_duration and not l.is_pit_in_lap and not l.is_pit_out_lap]
            best = min(pole_laps, key=lambda x: x.lap_duration) if pole_laps else None
            info = driver_lookup.get(pole.driver_number, {})
            poles_by_driver[pole.driver_number] += 1
            pole_times.append({
                "driver_number": pole.driver_number,
                "full_name": info.get("full_name", f"#{pole.driver_number}"),
                "year": h.year,
                "lap_time": best.lap_duration if best else None,
            })
    pole_counts = [{"driver_number": dn, "full_name": driver_lookup.get(dn, {}).get("full_name", f"#{dn}"), "count": c}
                   for dn, c in poles_by_driver.items()]
    pole_counts.sort(key=lambda x: x["count"], reverse=True)
    pole_times.sort(key=lambda x: x["year"])
    return {"pole_counts": pole_counts, "pole_times": pole_times}


def calc_quali_gap_stats(historical: list[CircuitHistoricalData], driver_lookup: dict) -> list[dict]:
    gaps_by_position = defaultdict(list)
    for h in historical:
        for s in h.sessions:
            if s.session_type not in ("Qualifying",):
                continue
            sk = s.session_key
            intv_sk = [i for i in h.intervals if i.session_key == sk]
            results_sk = {r.driver_number: r.position for r in h.results if r.session_key == sk}
            for i in intv_sk:
                pos = results_sk.get(i.driver_number)
                if pos is not None and i.gap_to_leader is not None and pos <= 20:
                    gaps_by_position[pos].append(i.gap_to_leader)
    gap_stats = []
    for pos in sorted(gaps_by_position.keys()):
        vals = gaps_by_position[pos]
        if len(vals) < 2:
            continue
        gap_stats.append({
            "position": pos,
            "avg_gap": statistics.mean(vals),
            "min_gap": min(vals),
            "max_gap": max(vals),
            "count": len(vals),
        })
    return gap_stats


def calc_quali_consistency(historical: list[CircuitHistoricalData]) -> list[dict]:
    by_driver = defaultdict(list)
    for h in historical:
        for s in h.sessions:
            if s.session_type not in ("Qualifying",):
                continue
            sk = s.session_key
            for r in h.results:
                if r.session_key != sk:
                    continue
                if r.position is None or r.position > 20:
                    continue
                by_driver[r.driver_number].append(r.position)
    stats = []
    for dn, positions in by_driver.items():
        if len(positions) < 2:
            continue
        stats.append({
            "driver_number": dn,
            "avg_position": statistics.mean(positions),
            "best_position": min(positions),
            "worst_position": max(positions),
            "std_position": statistics.stdev(positions) if len(positions) > 1 else 0,
            "count": len(positions),
        })
    stats.sort(key=lambda x: x["avg_position"])
    return stats
