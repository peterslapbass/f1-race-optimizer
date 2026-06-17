from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional


@dataclass
class Meeting:
    meeting_key: int
    meeting_name: str
    circuit_short_name: str
    country_name: str
    location: str
    year: int
    date_start: str
    date_end: str


@dataclass
class Session:
    session_key: int
    meeting_key: int
    session_name: str
    session_type: str
    date_start: str
    date_end: str


@dataclass
class Driver:
    driver_number: int
    broadcast_name: str
    full_name: str
    name_acronym: str
    team_name: str
    team_colour: str
    country_code: str
    session_key: int


@dataclass
class Lap:
    driver_number: int
    session_key: int
    lap_number: int
    lap_duration: Optional[float]
    lap_time: Optional[float]
    is_pit_out_lap: bool
    is_pit_in_lap: bool
    duration_sector_1: Optional[float]
    duration_sector_2: Optional[float]
    duration_sector_3: Optional[float]
    segments_sector_1: Optional[int]
    segments_sector_2: Optional[int]
    segments_sector_3: Optional[int]


@dataclass
class Stint:
    driver_number: int
    session_key: int
    stint_number: int
    lap_start: int
    lap_end: int
    compound: str
    tyre_age_at_start: Optional[int]


@dataclass
class PitStop:
    driver_number: int
    session_key: int
    lap_number: int
    pit_duration: Optional[float]
    tyre_change: bool


@dataclass
class Position:
    driver_number: int
    session_key: int
    position: int
    date: str


@dataclass
class Interval:
    driver_number: int
    session_key: int
    gap_to_leader: Optional[float]
    interval: Optional[float]
    date: str


@dataclass
class SessionResult:
    driver_number: int
    session_key: int
    position: int
    total_laps: int
    time_penalty: Optional[float]
    grid_position: int
    finishing_status: str


@dataclass
class Overtake:
    driver_number: int
    session_key: int
    overtake_count: int
    date: str


@dataclass
class RaceControl:
    session_key: int
    driver_number: Optional[int]
    category: str
    flag: str
    message: str


@dataclass
class Weather:
    session_key: int
    air_temperature: Optional[float]
    track_temperature: Optional[float]
    humidity: Optional[int]
    rainfall: bool
    wind_speed: Optional[float]


@dataclass
class CarData:
    driver_number: int
    session_key: int
    speed: Optional[float]
    rpm: Optional[int]
    throttle: Optional[float]
    brake: Optional[bool]
    drs: Optional[int]
    n_gear: Optional[int]


@dataclass
class CircuitHistoricalData:
    circuit_name: str
    country: str
    year: int
    meeting_key: int
    sessions: list = field(default_factory=list)
    laps: list = field(default_factory=list)
    stints: list = field(default_factory=list)
    pit_stops: list = field(default_factory=list)
    positions: list = field(default_factory=list)
    results: list = field(default_factory=list)
    overtakes: list = field(default_factory=list)
    weather: list = field(default_factory=list)


@dataclass
class TireStats:
    compound: str
    avg_stint_length: float
    median_stint_length: float
    max_stint_length: int
    min_stint_length: int
    degradation_per_lap: float
    count: int


@dataclass
class StrategyOption:
    stints: list
    total_time: float
    total_pit_stops: int
    description: str


@dataclass
class CircuitPrediction:
    circuit_name: str
    country: str
    meeting_key: int
    session_key: int
    year: int
    tire_stats: list = field(default_factory=list)
    strategies: list = field(default_factory=list)
    recommended_strategy: Optional[StrategyOption] = None
    avg_race_time: Optional[float] = None
    avg_winner_lap_time: Optional[float] = None
    safety_car_probability: Optional[float] = None
    avg_overtakes: Optional[float] = None
    quali_improvement_rate: Optional[float] = None
    weather_pattern: Optional[dict] = None
    driver_map: dict = field(default_factory=dict)
    grid_finish_data: list = field(default_factory=list)
    overtake_data: list = field(default_factory=list)
    consistency_data: list = field(default_factory=list)
    pit_data: list = field(default_factory=list)
    generated_at: str = ""


@dataclass
class I18nString:
    en: str
    es: str

    def __getitem__(self, lang: str) -> str:
        return self.es if lang == "es" else self.en
