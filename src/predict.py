import logging
from datetime import datetime, timezone
from typing import Optional

from src.client import OpenF1Client
from src.models import (
    CircuitHistoricalData, CircuitPrediction, StrategyOption, Meeting, Session,
)
from src.fetch import fetch_circuit_history, build_historical_data
from src.analyze import (
    calc_tire_stats, calc_race_stats, calc_weather_pattern, calc_quali_stats,
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
    # Safety car probability
    sc_count = 0
    total_races = 0
    for h in historical:
        for s in h.sessions:
            if s.session_type == "Race":
                total_races += 1
                race_control_msgs = []
                for h2 in historical:
                    pass
    prediction.safety_car_probability = (sc_count / total_races) if total_races > 0 else 0.15
    # Strategy
    total_laps = 58
    if race_session and historical:
        for h in historical:
            for s in h.sessions:
                if s.session_type == "Race":
                    results = [r for r in h.results if r.session_key == s.session_key]
                    if results:
                        total_laps = max(r.total_laps for r in results)
                        break
    recommended, top_strategies = recommend_strategy(historical, tire_stats, total_laps)
    prediction.recommended_strategy = recommended
    prediction.strategies = top_strategies
    return prediction


def load_prediction_from_cache(circuit_name: str, year: int) -> Optional[CircuitPrediction]:
    import json
    import os
    path = f"data/circuits/{circuit_name.lower()}_{year}.json"
    if os.path.exists(path):
        with open(path) as f:
            data = json.load(f)
        return CircuitPrediction(**data)
    return None


def save_prediction_cache(prediction: CircuitPrediction):
    import json
    import os
    path = f"data/circuits/{prediction.circuit_name.lower()}_{prediction.year}.json"
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(prediction.__dict__, f, indent=2, default=str)
