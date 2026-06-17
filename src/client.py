import time
import logging
from datetime import datetime
from typing import Optional

import requests
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

logger = logging.getLogger(__name__)

BASE_URL = "https://api.openf1.org/v1"


class OpenF1Client:
    def __init__(self, rate_per_second: int = 3, rate_per_minute: int = 30):
        self.session = requests.Session()
        self.session.headers.update({"Accept": "application/json"})
        self.min_interval = 1.0 / rate_per_second
        self.last_request = 0.0
        self.req_count = 0
        self.minute_start = time.monotonic()
        self.rate_per_minute = rate_per_minute

    def _wait_for_rate_limit(self):
        now = time.monotonic()
        elapsed = now - self.minute_start
        if elapsed >= 60:
            self.req_count = 0
            self.minute_start = now
        if self.req_count >= self.rate_per_minute:
            sleep_time = 60 - elapsed
            if sleep_time > 0:
                logger.info(f"Rate limit reached, sleeping {sleep_time:.1f}s")
                time.sleep(sleep_time)
            self.req_count = 0
            self.minute_start = time.monotonic()
        since_last = now - self.last_request
        if since_last < self.min_interval:
            time.sleep(self.min_interval - since_last)
        self.last_request = time.monotonic()
        self.req_count += 1

    @retry(
        stop=stop_after_attempt(4),
        wait=wait_exponential(multiplier=2, min=2, max=60),
        retry=retry_if_exception_type((requests.exceptions.RequestException,)),
    )
    def _get(self, endpoint: str, params: dict = None) -> list:
        self._wait_for_rate_limit()
        url = f"{BASE_URL}/{endpoint}"
        resp = self.session.get(url, params=params, timeout=30)
        resp.raise_for_status()
        return resp.json()

    def get_meetings(self, year: Optional[int] = None, country_name: Optional[str] = None) -> list:
        params = {}
        if year:
            params["year"] = year
        if country_name:
            params["country_name"] = country_name
        return self._get("meetings", params)

    def get_sessions(self, meeting_key: Optional[int] = None, session_type: Optional[str] = None, year: Optional[int] = None) -> list:
        params = {}
        if meeting_key:
            params["meeting_key"] = meeting_key
        if session_type:
            params["session_type"] = session_type
        if year:
            params["year"] = year
        return self._get("sessions", params)

    def get_drivers(self, session_key: Optional[int] = None) -> list:
        params = {}
        if session_key:
            params["session_key"] = session_key
        return self._get("drivers", params)

    def get_laps(self, session_key: int, driver_number: Optional[int] = None) -> list:
        params = {"session_key": session_key}
        if driver_number:
            params["driver_number"] = driver_number
        return self._get("laps", params)

    def get_stints(self, session_key: int, driver_number: Optional[int] = None) -> list:
        params = {"session_key": session_key}
        if driver_number:
            params["driver_number"] = driver_number
        return self._get("stints", params)

    def get_pit_stops(self, session_key: int, driver_number: Optional[int] = None) -> list:
        params = {"session_key": session_key}
        if driver_number:
            params["driver_number"] = driver_number
        return self._get("pit", params)

    def get_positions(self, session_key: int, driver_number: Optional[int] = None) -> list:
        params = {"session_key": session_key}
        if driver_number:
            params["driver_number"] = driver_number
        return self._get("position", params)

    def get_session_results(self, session_key: int) -> list:
        return self._get("session_result", {"session_key": session_key})

    def get_overtakes(self, session_key: int) -> list:
        return self._get("overtakes", {"session_key": session_key})

    def get_weather(self, session_key: int) -> list:
        return self._get("weather", {"session_key": session_key})

    def get_car_data(self, session_key: int, driver_number: Optional[int] = None) -> list:
        params = {"session_key": session_key}
        if driver_number:
            params["driver_number"] = driver_number
        return self._get("car_data", params)

    def get_race_control(self, session_key: int) -> list:
        return self._get("race_control", {"session_key": session_key})

    def get_intervals(self, session_key: int) -> list:
        return self._get("intervals", {"session_key": session_key})

    def get_starting_grid(self, session_key: int) -> list:
        return self._get("starting_grid", {"session_key": session_key})

    def get_championship_drivers(self, session_key: Optional[int] = None) -> list:
        params = {}
        if session_key:
            params["session_key"] = session_key
        return self._get("championship_drivers", params)

    def get_championship_teams(self, session_key: Optional[int] = None) -> list:
        params = {}
        if session_key:
            params["session_key"] = session_key
        return self._get("championship_teams", params)

    def close(self):
        self.session.close()
