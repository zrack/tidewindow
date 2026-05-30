import asyncio
import os
import aiohttp
import logging
from datetime import datetime, timedelta
from dotenv import load_dotenv
from marine_config import (
    DEFAULT_WIND_KNOTS,
    FORECAST_HOURS,
    NOAA_CURRENT_STATION,
    NOAA_TIDE_STATION,
    SEEDED_CURRENT_DIRECTION,
    SEEDED_CURRENT_KNOTS,
    SEEDED_TIDE_FEET,
    WEATHER_LAT,
    WEATHER_LON,
)

# Load environment variables from .env file
load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

class NoaaMarineClient:
    """Async client aggregating NOAA CO-OPS and OpenWeatherMap telemetry."""
    
    NOAA_URL = "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter"
    OWM_URL = "https://api.openweathermap.org/data/2.5/weather"
    
    def __init__(self):
        self.tide_station = NOAA_TIDE_STATION
        self.current_station = NOAA_CURRENT_STATION
        self.lat = WEATHER_LAT
        self.lon = WEATHER_LON
        self.owm_api_key = os.getenv("OPENWEATHER_API_KEY")

    def get_seed_data(self, wind_override=None, reason="live telemetry unavailable") -> dict:
        """Provides local cache data if network calls drop entirely."""
        return {
            "tide_feet": SEEDED_TIDE_FEET,
            "current_knots": SEEDED_CURRENT_KNOTS,
            "current_direction": SEEDED_CURRENT_DIRECTION,
            "phase": "Flood (South) [SEEDED]",
            "wind_knots": wind_override if wind_override is not None else DEFAULT_WIND_KNOTS,
            "sources": {
                "tide": "seed",
                "current": "seed",
                "wind": "fallback" if wind_override is not None else "seed",
            },
            "fallback_reason": reason,
            "updated_at": self._timestamp(),
        }

    async def fetch_telemetry(self) -> dict:
        """Fetches live tide, current, and wind telemetry concurrently."""
        timeout = aiohttp.ClientTimeout(total=4.0)
        
        async with aiohttp.ClientSession(timeout=timeout) as session:
            # Set up concurrent tasks
            tasks = [
                session.get(self.NOAA_URL, params=self._build_noaa_params(self.tide_station, "water_level")),
                session.get(self.NOAA_URL, params=self._build_noaa_params(self.current_station, "currents"))
            ]
            
            # Only append OpenWeather task if an API key exists
            owm_active = bool(self.owm_api_key)
            if owm_active:
                owm_params = {
                    "lat": self.lat,
                    "lon": self.lon,
                    "appid": self.owm_api_key,
                    "units": "imperial"
                }
                tasks.append(session.get(self.OWM_URL, params=owm_params))

            try:
                responses = await asyncio.gather(*tasks)
                
                tide_json = await responses[0].json()
                current_json = await responses[1].json()
                
                # Parse wind if live endpoint was hit
                live_wind = None
                if owm_active and len(responses) == 3:
                    owm_json = await responses[2].json()
                    if owm_json.get("cod") == 200:
                        # OpenWeather returns wind speed in mph; convert to knots (1 mph = 0.868976 knots)
                        live_wind = float(owm_json.get("wind", {}).get("speed", 0)) * 0.869
                
                return self._parse_payload(tide_json, current_json, live_wind)
                
            except Exception as e:
                logging.warning("Telemetry fetch failed: %s", e)
                return self.get_seed_data(reason=str(e))

    async def fetch_forecast(self, hours: int = FORECAST_HOURS) -> dict:
        """Fetches NOAA tide predictions for the upcoming planning window."""
        timeout = aiohttp.ClientTimeout(total=6.0)
        now = datetime.now()
        end = now + timedelta(hours=hours)
        params = {
            "begin_date": now.strftime("%Y%m%d"),
            "end_date": end.strftime("%Y%m%d"),
            "station": self.tide_station,
            "product": "predictions",
            "datum": "MLLW",
            "interval": "h",
            "time_zone": "lst_ldt",
            "units": "english",
            "format": "json",
        }

        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(self.NOAA_URL, params=params) as response:
                    tide_json = await response.json()
            return self._parse_forecast_payload(tide_json, now, end)
        except Exception as e:
            logging.warning("Forecast fetch failed: %s", e)
            return self.get_seed_forecast(hours=hours, reason=str(e))

    def get_seed_forecast(self, hours: int = FORECAST_HOURS, reason="forecast unavailable") -> dict:
        """Builds a minimal forecast if NOAA predictions are unavailable."""
        now = datetime.now().replace(minute=0, second=0, microsecond=0)
        predictions = []
        for offset in range(hours + 1):
            predictions.append(
                {
                    "time": now + timedelta(hours=offset),
                    "tide_feet": SEEDED_TIDE_FEET,
                }
            )

        return {
            "predictions": predictions,
            "sources": {"tide": "seed", "current": "derived"},
            "fallback_reason": reason,
            "updated_at": self._timestamp(),
        }

    def _build_noaa_params(self, station: str, product: str) -> dict:
        return {
            "range": "4",           
            "station": station,
            "product": product,
            "datum": "MLLW",
            "time_zone": "lst_ldt", 
            "units": "english",     
            "format": "json"
        }

    def _parse_payload(self, tide_json: dict, current_json: dict, live_wind: float = None) -> dict:
        try:
            tide_list = tide_json.get("data", [])
            current_list = current_json.get("data", [])
            
            # Default wind if live fetch didn't return a value
            final_wind = live_wind if live_wind is not None else DEFAULT_WIND_KNOTS
            wind_source = "live" if live_wind is not None else "fallback"

            if not tide_list or not current_list:
                return self.get_seed_data(
                    wind_override=final_wind,
                    reason="NOAA returned an empty tide or current payload",
                )

            tide_val = float(tide_list[-1]["v"])
            current_speed = float(current_list[-1]["s"])
            current_dir = float(current_list[-1]["d"])
            
            phase = "Flood (South)" if 100 < current_dir < 260 else "Ebb (North)"
            if current_speed < 0.3:
                phase = "Slack Water"

            return {
                "tide_feet": tide_val,
                "current_knots": current_speed,
                "current_direction": current_dir,
                "phase": phase,
                "wind_knots": final_wind,
                "sources": {
                    "tide": "live",
                    "current": "live",
                    "wind": wind_source,
                },
                "fallback_reason": None,
                "updated_at": self._timestamp(),
            }
        except (KeyError, IndexError, ValueError, TypeError):
            return self.get_seed_data(reason="unable to parse telemetry payload")

    def _parse_forecast_payload(self, tide_json: dict, start: datetime, end: datetime) -> dict:
        try:
            raw_predictions = tide_json.get("predictions", [])
            predictions = []

            for item in raw_predictions:
                prediction_time = datetime.strptime(item["t"], "%Y-%m-%d %H:%M")
                if start <= prediction_time <= end:
                    predictions.append(
                        {
                            "time": prediction_time,
                            "tide_feet": float(item["v"]),
                        }
                    )

            if len(predictions) < 2:
                return self.get_seed_forecast(
                    reason="NOAA returned too few tide predictions",
                )

            return {
                "predictions": predictions,
                "sources": {"tide": "live", "current": "derived"},
                "fallback_reason": None,
                "updated_at": self._timestamp(),
            }
        except (KeyError, ValueError, TypeError):
            return self.get_seed_forecast(reason="unable to parse tide predictions")

    def _timestamp(self) -> str:
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
