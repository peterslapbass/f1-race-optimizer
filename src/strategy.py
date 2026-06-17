import logging
import itertools
from typing import Optional

import numpy as np

from src.models import TireStats, StrategyOption, CircuitHistoricalData

logger = logging.getLogger(__name__)

PIT_STOP_TIME = 22.0
OUT_LAP_PENALTY = 3.5
IN_LAP_PENALTY = 2.0
BASE_LAP_TIME = 85.0


def simulate_strategy(
    stint_compounds: list[str],
    total_laps: int,
    tire_stats: dict[str, TireStats],
    base_lap_time: float = BASE_LAP_TIME,
) -> Optional[StrategyOption]:
    total_time = 0.0
    current_lap = 1
    stints_desc = []
    for i, compound in enumerate(stint_compounds):
        ts = tire_stats.get(compound)
        if ts is None:
            stint_length = total_laps // len(stint_compounds)
        else:
            stint_length = min(int(ts.avg_stint_length), total_laps - current_lap + 1)
        if stint_length <= 0:
            return None
        if current_lap + stint_length - 1 > total_laps:
            stint_length = total_laps - current_lap + 1
        if stint_length <= 0:
            break
        deg = ts.degradation_per_lap if ts else 0.3
        for lap in range(stint_length):
            lap_time = base_lap_time + deg * lap
            if lap == 0 and i > 0:
                lap_time += OUT_LAP_PENALTY
            elif lap == stint_length - 1 and i < len(stint_compounds) - 1:
                lap_time += IN_LAP_PENALTY
            total_time += lap_time
        stints_desc.append(f"{compound}({stint_length})")
        current_lap += stint_length
        if i < len(stint_compounds) - 1:
            total_time += PIT_STOP_TIME
    if current_lap <= total_laps:
        remaining = total_laps - current_lap + 1
        last_compound = stint_compounds[-1]
        ts = tire_stats.get(last_compound)
        deg = ts.degradation_per_lap if ts else 0.3
        for lap in range(remaining):
            lap_time = base_lap_time + deg * lap
            total_time += lap_time
        stints_desc[-1] = f"{last_compound}({stints_desc[-1].split('(')[1].rstrip(')').split('(')[0] if '(' in stints_desc[-1] else ''}{remaining})"
    return StrategyOption(
        stints=stints_desc,
        total_time=total_time,
        total_pit_stops=len(stint_compounds) - 1,
        description=" → ".join(stints_desc),
    )


def generate_strategies(
    tire_stats_list: list[TireStats],
    total_laps: int = 58,
    max_pit_stops: int = 3,
) -> list[StrategyOption]:
    valid_compounds = [ts.compound for ts in tire_stats_list if ts.count >= 3]
    if not valid_compounds:
        return []
    preferred_order = ["SOFT", "MEDIUM", "HARD", "INTERMEDIATE", "WET"]
    valid_compounds.sort(key=lambda c: preferred_order.index(c) if c in preferred_order else 99)
    tire_stats_dict = {ts.compound: ts for ts in tire_stats_list}
    strategies = []
    n_stops_range = range(1, max_pit_stops + 1)
    for n_stops in n_stops_range:
        for combo in itertools.product(valid_compounds, repeat=n_stops + 1):
            if len(set(combo)) == 1 and n_stops > 0:
                continue
            strategy = simulate_strategy(list(combo), total_laps, tire_stats_dict)
            if strategy:
                strategies.append(strategy)
    strategies.sort(key=lambda s: s.total_time)
    return strategies


def recommend_strategy(
    historical: list[CircuitHistoricalData],
    tire_stats_list: list[TireStats],
    total_laps: int = 58,
) -> tuple[Optional[StrategyOption], list[StrategyOption]]:
    strategies = generate_strategies(tire_stats_list, total_laps)
    recommended = strategies[0] if strategies else None
    return recommended, strategies[:5]
