import os
import asyncio
import aiohttp
import logging
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

class NoaaMarineClient:
    """Async client aggregating NOAA CO-OPS and OpenWeatherMap telemetry."""
    
    NOAA_URL = "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter"
    OWM_URL = "https://api.openweathermap.org/data/2.5/weather"
    
    def __init__(self):
        self.tide_station = "9446484"     # Tacoma Narrows Bridge
        self.current_station = "PCT1601"  # Narrows North
        # Coordinates for Tacoma Narrows / Gig Harbor basin
        self.lat = "47.2690"
        self.lon = "-122.5517"
        self.owm_api_key = os.getenv("OPENWEATHER_API_KEY")

    def get_seed_data(self, wind_override=None) -> dict:
        """Provides local cache data if network calls drop entirely."""
        return {
            "tide_feet": 5.4,
            "current_knots": 1.85,
            "current_direction": 140.0,
            "phase": "Flood (South) [SEEDED]",
            "wind_knots": wind_override if wind_override is not None else 7.5
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
                # If everything fails, fall back to seed data
                return self.get_seed_data()

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
            final_wind = live_wind if live_wind is not None else 6.5

            if not tide_list or not current_list:
                return self.get_seed_data(wind_override=final_wind)

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
                "wind_knots": final_wind  
            }
        except (KeyError, IndexError, ValueError, TypeError):
            return self.get_seed_data()
