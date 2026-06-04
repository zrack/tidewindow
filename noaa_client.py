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
    NWS_MARINE_ZONE,
    NWS_USER_AGENT,
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
    OWM_ONECALL_URL = "https://api.openweathermap.org/data/3.0/onecall"
    NWS_ALERTS_URL = "https://api.weather.gov/alerts/active"
    
    def __init__(self, provider_context: dict | None = None):
        provider_context = provider_context or {}
        self.tide_station = provider_context.get("tide_station", NOAA_TIDE_STATION)
        self.current_station = provider_context.get("current_station", NOAA_CURRENT_STATION)
        self.current_bin = provider_context.get("current_bin")
        self.current_bin_depth_ft = provider_context.get("current_bin_depth_ft")
        self.nws_zone = provider_context.get("nws_zone", NWS_MARINE_ZONE)
        self.lat = provider_context.get("weather_lat", WEATHER_LAT)
        self.lon = provider_context.get("weather_lon", WEATHER_LON)
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

                # Parse each response defensively so a single failing endpoint
                # (e.g. a 400 from the real-time currents product on a
                # prediction-only station) degrades just that source instead of
                # seeding the entire payload.
                tide_json = await self._safe_json(responses[0])
                current_json = await self._safe_json(responses[1])

                # Parse wind if live endpoint was hit
                live_wind = None
                if owm_active and len(responses) == 3:
                    owm_json = await self._safe_json(responses[2])
                    if owm_json.get("cod") == 200:
                        # OpenWeather returns wind speed in mph; convert to knots (1 mph = 0.868976 knots)
                        live_wind = float(owm_json.get("wind", {}).get("speed", 0)) * 0.869

                # The configured current station may be a harmonic prediction
                # station with no real-time sensor, so the real-time currents
                # product can come back empty. Fall back to NOAA current
                # predictions before resorting to seed data.
                current_predictions = []
                if not (isinstance(current_json, dict) and current_json.get("data")):
                    current_predictions = await self._fetch_current_predictions(session)

                return self._parse_payload(tide_json, current_json, live_wind, current_predictions)

            except Exception as e:
                logging.warning("Telemetry fetch failed: %s", e)
                return self.get_seed_data(reason=str(e))

    @staticmethod
    async def _safe_json(response) -> dict:
        """Parses a response body as JSON, returning {} on any failure."""
        try:
            return await response.json(content_type=None)
        except Exception:  # noqa: BLE001 - network/body parsing is best-effort
            return {}

    async def _fetch_current_predictions(self, session) -> list:
        """Fetches NOAA harmonic current predictions for the current station."""
        params = {
            "date": "today",
            "station": self.current_station,
            "product": "currents_predictions",
            "time_zone": "lst_ldt",
            "interval": "30",
            "units": "english",
            "vel_type": "speed_dir",
            "format": "json",
        }
        try:
            response = await session.get(self.NOAA_URL, params=params)
            payload = await self._safe_json(response)
            return self._parse_current_predictions(payload)
        except Exception as e:
            logging.warning("Current prediction fetch failed: %s", e)
            return []

    async def _fetch_forecast_current_predictions(self, session, start: datetime, end: datetime) -> list:
        """Fetches NOAA current predictions across the forecast planning window."""
        params = {
            "begin_date": start.strftime("%Y%m%d %H:%M"),
            "end_date": end.strftime("%Y%m%d %H:%M"),
            "station": self.current_station,
            "product": "currents_predictions",
            "time_zone": "lst_ldt",
            "interval": "30",
            "units": "english",
            "vel_type": "speed_dir",
            "format": "json",
        }
        self._apply_current_bin(params)
        try:
            response = await session.get(self.NOAA_URL, params=params)
            payload = await self._safe_json(response)
            return [
                point for point in self._parse_current_predictions(payload)
                if start <= point["time"] <= end
            ]
        except Exception as e:
            logging.warning("Forecast current prediction fetch failed: %s", e)
            return []

    @staticmethod
    def _parse_current_predictions(payload: dict | None) -> list:
        """Normalizes NOAA currents_predictions into time/speed/direction points."""
        if not isinstance(payload, dict):
            return []
        points = payload.get("current_predictions", {}).get("cp", [])
        parsed = []
        for item in points:
            timestamp = item.get("Time")
            if not timestamp:
                continue
            try:
                point_time = datetime.strptime(timestamp, "%Y-%m-%d %H:%M")
            except (ValueError, TypeError):
                continue
            raw_speed = item.get("Speed", item.get("Velocity_Major"))
            if raw_speed is None:
                continue
            try:
                speed = abs(float(raw_speed))
            except (ValueError, TypeError):
                continue
            raw_dir = item.get("Direction")
            try:
                direction = float(raw_dir) if raw_dir is not None else SEEDED_CURRENT_DIRECTION
            except (ValueError, TypeError):
                direction = SEEDED_CURRENT_DIRECTION
            parsed.append({"time": point_time, "speed": speed, "dir": direction})
        return parsed

    async def fetch_forecast(self, hours: int = FORECAST_HOURS) -> dict:
        """Fetches NOAA tide predictions and optional hourly wind forecast."""
        timeout = aiohttp.ClientTimeout(total=6.0)
        now = datetime.now()
        end = now + timedelta(hours=hours)
        tide_params = {
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
                tide_task = session.get(self.NOAA_URL, params=tide_params)
                wind_task = None
                if self.owm_api_key:
                    wind_task = session.get(
                        self.OWM_ONECALL_URL,
                        params={
                            "lat": self.lat,
                            "lon": self.lon,
                            "appid": self.owm_api_key,
                            "units": "imperial",
                            "exclude": "current,minutely,daily,alerts",
                        },
                    )

                if wind_task:
                    responses = await asyncio.gather(tide_task, wind_task)
                else:
                    responses = [await tide_task]

                tide_json = await self._safe_json(responses[0])
                wind_json = await self._safe_json(responses[1]) if wind_task else None

                forecast = self._parse_forecast_payload(tide_json, now, end)
                wind_forecast = self._parse_wind_forecast_payload(wind_json, now, end)
                forecast["wind_predictions"] = wind_forecast["predictions"]
                forecast["sources"]["wind"] = wind_forecast["source"]
                forecast["wind_fallback_reason"] = wind_forecast["fallback_reason"]

                # High/low tide, slack/max-current events, NWS alerts, and
                # current predictions are best-effort enrichments. Fetch them
                # together so one slow upstream product doesn't serially delay
                # the dashboard.
                (
                    forecast["tide_events"],
                    forecast["slack_events"],
                    forecast["alerts"],
                    forecast["current_predictions"],
                ) = await asyncio.gather(
                    self._fetch_tide_events(session, now, end),
                    self._fetch_slack_events(session, now, end),
                    self._fetch_marine_alerts(session),
                    self._fetch_forecast_current_predictions(session, now, end),
                )
                if forecast["current_predictions"]:
                    forecast["sources"]["current"] = "predicted"
            return forecast
        except Exception as e:
            logging.warning("Forecast fetch failed: %s", e)
            return self.get_seed_forecast(hours=hours, reason=str(e))

    async def _fetch_tide_events(self, session, start: datetime, end: datetime) -> list:
        """Fetches NOAA high/low tide predictions for the planning window."""
        params = {
            "begin_date": start.strftime("%Y%m%d %H:%M"),
            "end_date": end.strftime("%Y%m%d %H:%M"),
            "station": self.tide_station,
            "product": "predictions",
            "datum": "MLLW",
            "interval": "hilo",
            "time_zone": "lst_ldt",
            "units": "english",
            "format": "json",
        }
        self._apply_current_bin(params)
        try:
            response = await session.get(self.NOAA_URL, params=params)
            payload = await self._safe_json(response)
            return self._parse_tide_events(payload, start, end)
        except Exception as e:
            logging.warning("Tide event fetch failed: %s", e)
            return []

    async def _fetch_slack_events(self, session, start: datetime, end: datetime) -> list:
        """Fetches NOAA slack and max-current events for the planning window."""
        params = {
            "begin_date": start.strftime("%Y%m%d %H:%M"),
            "end_date": end.strftime("%Y%m%d %H:%M"),
            "station": self.current_station,
            "product": "currents_predictions",
            "time_zone": "lst_ldt",
            "interval": "MAX_SLACK",
            "units": "english",
            "format": "json",
        }
        self._apply_current_bin(params)
        try:
            response = await session.get(self.NOAA_URL, params=params)
            payload = await self._safe_json(response)
            return self._parse_slack_events(payload, start, end)
        except Exception as e:
            logging.warning("Slack event fetch failed: %s", e)
            return []

    async def _fetch_marine_alerts(self, session) -> list:
        """Fetches active NWS marine advisories/warnings for the configured zone."""
        params = {"zone": self.nws_zone}
        headers = {"User-Agent": NWS_USER_AGENT, "Accept": "application/geo+json"}
        try:
            response = await session.get(self.NWS_ALERTS_URL, params=params, headers=headers)
            payload = await self._safe_json(response)
            return self._parse_marine_alerts(payload)
        except Exception as e:
            logging.warning("Marine alert fetch failed: %s", e)
            return []

    @staticmethod
    def _parse_marine_alerts(payload: dict | None) -> list:
        """Normalizes NWS active-alert GeoJSON into a compact advisory list."""
        if not isinstance(payload, dict):
            return []
        severity_rank = {"Extreme": 0, "Severe": 1, "Moderate": 2, "Minor": 3, "Unknown": 4}
        alerts = []
        for feature in payload.get("features", []):
            props = feature.get("properties", {}) if isinstance(feature, dict) else {}
            event = props.get("event")
            if not event:
                continue
            alerts.append(
                {
                    "event": event,
                    "headline": props.get("headline") or "",
                    "severity": props.get("severity") or "Unknown",
                    "urgency": props.get("urgency") or "",
                    "expires": props.get("expires") or props.get("ends"),
                    "sender": props.get("senderName") or "",
                }
            )
        alerts.sort(key=lambda item: severity_rank.get(item["severity"], 5))
        return alerts

    @staticmethod
    def _parse_tide_events(payload: dict | None, start: datetime, end: datetime) -> list:
        """Normalizes NOAA hilo predictions into high/low tide events."""
        if not isinstance(payload, dict):
            return []
        labels = {"H": "High", "L": "Low", "HH": "Higher High", "LL": "Lower Low"}
        events = []
        for item in payload.get("predictions", []):
            timestamp = item.get("t")
            if not timestamp:
                continue
            try:
                event_time = datetime.strptime(timestamp, "%Y-%m-%d %H:%M")
            except (ValueError, TypeError):
                continue
            if not (start <= event_time <= end):
                continue
            try:
                tide_feet = round(float(item["v"]), 1)
            except (KeyError, ValueError, TypeError):
                continue
            events.append(
                {
                    "time": event_time,
                    "type": labels.get(item.get("type"), "Tide"),
                    "tide_feet": tide_feet,
                }
            )
        return events

    @staticmethod
    def _parse_slack_events(payload: dict | None, start: datetime, end: datetime) -> list:
        """Normalizes NOAA MAX_SLACK predictions into slack/max-current events."""
        if not isinstance(payload, dict):
            return []
        labels = {"slack": "Slack", "flood": "Max Flood", "ebb": "Max Ebb"}
        events = []
        for item in payload.get("current_predictions", {}).get("cp", []):
            timestamp = item.get("Time")
            if not timestamp:
                continue
            try:
                event_time = datetime.strptime(timestamp, "%Y-%m-%d %H:%M")
            except (ValueError, TypeError):
                continue
            if not (start <= event_time <= end):
                continue
            kind = str(item.get("Type", "")).lower()
            raw_speed = item.get("Speed", item.get("Velocity_Major"))
            try:
                speed = round(abs(float(raw_speed)), 2) if raw_speed is not None else 0.0
            except (ValueError, TypeError):
                speed = 0.0
            events.append(
                {
                    "time": event_time,
                    "type": labels.get(kind, "Current"),
                    "speed": speed,
                }
            )
        return events

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
            "wind_predictions": [],
            "current_predictions": [],
            "tide_events": [],
            "slack_events": [],
            "alerts": [],
            "sources": {"tide": "seed", "current": "derived", "wind": "fallback"},
            "fallback_reason": reason,
            "wind_fallback_reason": "using current/fallback wind for all windows",
            "updated_at": self._timestamp(),
        }

    def _build_noaa_params(self, station: str, product: str) -> dict:
        params = {
            "range": "4",           
            "station": station,
            "product": product,
            "datum": "MLLW",
            "time_zone": "lst_ldt", 
            "units": "english",     
            "format": "json"
        }
        if product == "currents":
            self._apply_current_bin(params)
        return params

    def _apply_current_bin(self, params: dict) -> None:
        if self.current_bin is not None:
            params["bin"] = str(self.current_bin)

    def _parse_payload(
        self,
        tide_json: dict,
        current_json: dict,
        live_wind: float = None,
        current_predictions: list | None = None,
    ) -> dict:
        # Default wind if the live fetch didn't return a value.
        final_wind = live_wind if live_wind is not None else DEFAULT_WIND_KNOTS
        wind_source = "live" if live_wind is not None else "fallback"
        current_predictions = current_predictions or []
        now = datetime.now()

        try:
            # Tide degrades independently of current: a missing current reading
            # should not force the tide to seed data.
            tide_list = tide_json.get("data", []) if isinstance(tide_json, dict) else []
            tide_value = None
            if tide_list:
                try:
                    tide_value = float(tide_list[-1]["v"])
                except (KeyError, IndexError, ValueError, TypeError):
                    tide_value = None
            if tide_value is not None:
                tide_feet, tide_source = tide_value, "live"
            else:
                tide_feet, tide_source = SEEDED_TIDE_FEET, "seed"

            # Current: prefer a real-time observation, then a NOAA prediction,
            # and only fall back to seed data if neither is available.
            current_list = current_json.get("data", []) if isinstance(current_json, dict) else []
            current_speed = current_dir = None
            current_source = None
            if current_list:
                try:
                    current_speed = float(current_list[-1]["s"])
                    current_dir = float(current_list[-1]["d"])
                    current_source = "live"
                except (KeyError, IndexError, ValueError, TypeError):
                    current_speed = current_dir = current_source = None
            if current_speed is None and current_predictions:
                nearest = min(
                    current_predictions,
                    key=lambda point: abs((point["time"] - now).total_seconds()),
                )
                current_speed = nearest["speed"]
                current_dir = nearest["dir"]
                current_source = "predicted"
            if current_speed is None:
                current_speed = SEEDED_CURRENT_KNOTS
                current_dir = SEEDED_CURRENT_DIRECTION
                current_source = "seed"

            phase = "Flood (South)" if 100 < current_dir < 260 else "Ebb (North)"
            if current_speed < 0.3:
                phase = "Slack Water"
            if tide_source == "seed" and current_source == "seed":
                phase = f"{phase} [SEEDED]"

            reasons = []
            if tide_source == "seed":
                reasons.append("NOAA returned no tide observation")
            if current_source == "seed":
                reasons.append("NOAA returned no current observation or prediction")
            fallback_reason = "; ".join(reasons) or None

            return {
                "tide_feet": tide_feet,
                "current_knots": current_speed,
                "current_direction": current_dir,
                "current_bin": self.current_bin,
                "current_bin_depth_ft": self.current_bin_depth_ft,
                "phase": phase,
                "wind_knots": final_wind,
                "sources": {
                    "tide": tide_source,
                    "current": current_source,
                    "wind": wind_source,
                },
                "fallback_reason": fallback_reason,
                "updated_at": self._timestamp(),
            }
        except (KeyError, IndexError, ValueError, TypeError):
            return self.get_seed_data(
                wind_override=final_wind,
                reason="unable to parse telemetry payload",
            )

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
                "wind_predictions": [],
                "sources": {"tide": "live", "current": "derived", "wind": "fallback"},
                "fallback_reason": None,
                "wind_fallback_reason": "using current wind for all windows",
                "updated_at": self._timestamp(),
            }
        except (KeyError, ValueError, TypeError):
            return self.get_seed_forecast(reason="unable to parse tide predictions")

    def _parse_wind_forecast_payload(self, wind_json: dict | None, start: datetime, end: datetime) -> dict:
        if not self.owm_api_key:
            return {
                "predictions": [],
                "source": "fallback",
                "fallback_reason": "OpenWeather API key not configured",
            }

        try:
            raw_hourly = wind_json.get("hourly", []) if wind_json else []
            if not raw_hourly:
                message = "OpenWeather hourly forecast unavailable"
                if isinstance(wind_json, dict):
                    message = wind_json.get("message", message)
                return {
                    "predictions": [],
                    "source": "missing",
                    "fallback_reason": message,
                }

            predictions = []
            for item in raw_hourly:
                forecast_time = datetime.fromtimestamp(item["dt"])
                if start <= forecast_time <= end:
                    # OpenWeather returns mph when units=imperial; convert to knots.
                    predictions.append(
                        {
                            "time": forecast_time,
                            "wind_knots": float(item["wind_speed"]) * 0.868976,
                        }
                    )

            if not predictions:
                return {
                    "predictions": [],
                    "source": "missing",
                    "fallback_reason": "OpenWeather hourly forecast had no matching points",
                }

            return {
                "predictions": predictions,
                "source": "live",
                "fallback_reason": None,
            }
        except (KeyError, TypeError, ValueError):
            return {
                "predictions": [],
                "source": "missing",
                "fallback_reason": "unable to parse OpenWeather hourly forecast",
            }

    def _timestamp(self) -> str:
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
