from marine_config import (
    FORECAST_MAX_WINDOWS_PER_ACTIVITY,
    TIDE_SLOPE_TO_CURRENT_KNOTS,
    ZONES,
)


class MarineSafetyEngine:
    """Evaluates physical marine parameters across distinct Gig Harbor micro-regions."""
    
    @staticmethod
    def get_zone_telemetry(base_current: float, base_tide: float, base_wind: float) -> dict:
        """Applies geographic multipliers to the baseline Narrows telemetry."""
        zones = {}

        for zone_id, zone_config in ZONES.items():
            current = zone_config.get(
                "fixed_current",
                base_current * zone_config.get("current_multiplier", 1.0),
            )
            wind = base_wind * zone_config.get("wind_multiplier", 1.0)

            zones[zone_id] = {
                "current": current,
                "tide": base_tide,
                "wind": wind,
            }

        return zones

    def build_forecast_windows(
        self,
        tide_predictions: list,
        wind_knots: float,
        wind_predictions: list | None = None,
        wind_source: str = "fallback",
        max_windows_per_activity: int = FORECAST_MAX_WINDOWS_PER_ACTIVITY,
    ) -> list:
        """Scores upcoming tide-prediction intervals for paddling and fishing."""
        hourly_windows = self._build_hourly_forecast_windows(
            tide_predictions,
            wind_knots,
            wind_predictions or [],
            wind_source,
        )
        if not hourly_windows:
            return []

        scored = []
        for window in hourly_windows:
            for zone_id, zone_data in window["zones"].items():
                kayak = self.evaluate_kayaking(zone_id, zone_data["current"], zone_data["wind"])
                fish = self.evaluate_fly_fishing(zone_id, zone_data["current"], zone_data["tide"])

                scored.append(
                    self._forecast_entry(
                        activity="Kayak",
                        evaluation=kayak,
                        window=window,
                        zone_id=zone_id,
                        zone_data=zone_data,
                    )
                )
                scored.append(
                    self._forecast_entry(
                        activity="Fish",
                        evaluation=fish,
                        window=window,
                        zone_id=zone_id,
                        zone_data=zone_data,
                    )
                )

        windows = []
        for activity in ("Kayak", "Fish"):
            activity_windows = [
                item for item in scored if item["activity"] == activity
            ]
            activity_windows.sort(key=lambda item: item["score"], reverse=True)
            windows.extend(activity_windows[:max_windows_per_activity])

        return windows

    @staticmethod
    def evaluate_confidence(telemetry: dict, forecast: dict, wind_knots: float) -> dict:
        """Summarizes how much trust to place in the current planning view."""
        telemetry_sources = telemetry.get("sources", {})
        forecast_sources = forecast.get("sources", {})
        fallback_reasons = [
            reason for reason in (
                telemetry.get("fallback_reason"),
                forecast.get("fallback_reason"),
            )
            if reason
        ]

        all_sources = [
            telemetry_sources.get("tide"),
            telemetry_sources.get("current"),
            telemetry_sources.get("wind"),
            forecast_sources.get("tide"),
            forecast_sources.get("current"),
            forecast_sources.get("wind"),
        ]
        has_seed = "seed" in all_sources
        has_derived = "derived" in all_sources
        has_missing = "missing" in all_sources
        has_fallback = bool(fallback_reasons) or "fallback" in all_sources

        if has_seed or has_missing:
            return {
                "level": "Low",
                "color": "red",
                "note": "Seed or missing forecast data is involved.",
            }

        if not has_fallback and wind_knots < 12.0 and not has_derived:
            return {
                "level": "High",
                "color": "green",
                "note": "Live tide, current, and wind data with light wind.",
            }

        if not has_seed and forecast_sources.get("tide") == "live" and has_derived:
            return {
                "level": "Medium",
                "color": "yellow",
                "note": "Live tide forecast with derived current guidance.",
            }

        return {
            "level": "Low",
            "color": "red",
            "note": "Fallback or seed data is involved.",
        }

    def _build_hourly_forecast_windows(
        self,
        tide_predictions: list,
        wind_knots: float,
        wind_predictions: list,
        wind_source: str,
    ) -> list:
        windows = []

        for current_point, next_point in zip(tide_predictions, tide_predictions[1:]):
            hours = (next_point["time"] - current_point["time"]).total_seconds() / 3600
            if hours <= 0:
                continue

            tide_delta = next_point["tide_feet"] - current_point["tide_feet"]
            base_current = abs(tide_delta / hours) * TIDE_SLOPE_TO_CURRENT_KNOTS
            average_tide = (current_point["tide_feet"] + next_point["tide_feet"]) / 2
            phase = self._forecast_phase(tide_delta, base_current)
            window_wind, window_wind_source = self._wind_for_window(
                current_point["time"],
                next_point["time"],
                wind_knots,
                wind_predictions,
                wind_source,
            )

            windows.append(
                {
                    "start": current_point["time"],
                    "end": next_point["time"],
                    "phase": phase,
                    "base_current": base_current,
                    "average_tide": average_tide,
                    "base_wind": window_wind,
                    "wind_source": window_wind_source,
                    "zones": self.get_zone_telemetry(
                        base_current=base_current,
                        base_tide=average_tide,
                        base_wind=window_wind,
                    ),
                }
            )

        return windows

    def _forecast_entry(self, activity: str, evaluation: dict, window: dict, zone_id: str, zone_data: dict) -> dict:
        return {
            "activity": activity,
            "zone_id": zone_id,
            "zone_title": ZONES[zone_id]["title"],
            "start": window["start"],
            "end": window["end"],
            "phase": window["phase"],
            "status": evaluation["status"],
            "score": self._forecast_score(activity, evaluation["status"], zone_data),
            "current": zone_data["current"],
            "wind": zone_data["wind"],
            "wind_source": window["wind_source"],
            "tide": zone_data["tide"],
            "note": evaluation["note"],
        }

    @staticmethod
    def _wind_for_window(
        start,
        end,
        fallback_wind_knots: float,
        wind_predictions: list,
        wind_source: str,
    ) -> tuple[float, str]:
        if not wind_predictions:
            if wind_source == "missing":
                return fallback_wind_knots, "fallback"
            return fallback_wind_knots, wind_source

        midpoint = start + (end - start) / 2
        nearest = min(
            wind_predictions,
            key=lambda item: abs((item["time"] - midpoint).total_seconds()),
        )
        distance_seconds = abs((nearest["time"] - midpoint).total_seconds())
        if distance_seconds <= 5400:
            return nearest["wind_knots"], "live"

        return fallback_wind_knots, "fallback"

    @staticmethod
    def _forecast_phase(tide_delta: float, base_current: float) -> str:
        if base_current < 0.25:
            return "Slack-ish"
        if tide_delta > 0:
            return "Flood/Rising"
        return "Ebb/Falling"

    @staticmethod
    def _forecast_score(activity: str, status: str, zone_data: dict) -> float:
        status_scores = {
            "SAFE": 80,
            "OPTIMAL": 90,
            "CAUTION": 45,
            "POOR": 20,
            "DANGER": -100,
        }
        score = status_scores.get(status, 0)

        if activity == "Kayak":
            score -= zone_data["current"] * 8
            score -= zone_data["wind"] * 1.5
        else:
            score += min(zone_data["current"], 2.5) * 6
            if zone_data["tide"] > 8.0:
                score += 5

        return round(score, 2)

    @staticmethod
    def evaluate_kayaking(zone: str, current: float, wind: float) -> dict:
        """Zone-specific kayaking safety thresholds."""
        if zone == "purdy_bridge":
            if current > 2.0:
                return {"status": "DANGER", "color": "red", "note": "Purdy spit current is acting like a river. Do not paddle."}
            elif current > 1.0:
                return {"status": "CAUTION", "color": "yellow", "note": "Strong pull under the bridge. Stay near the edges."}
            return {"status": "SAFE", "color": "green", "note": "Near slack water. Safe to transit under bridge."}
            
        elif zone == "gig_harbor":
            if wind > 15.0:
                return {"status": "CAUTION", "color": "yellow", "note": "High winds creating chop inside harbor."}
            return {"status": "SAFE", "color": "green", "note": "Enclosed water. Ideal for casual paddling."}
            
        elif zone == "fox_island":
            if wind > 12.0 or current > 2.0:
                return {"status": "DANGER", "color": "red", "note": "High exposure. Dangerous fetch and currents."}
            elif wind > 8.0 or current > 1.0:
                return {"status": "CAUTION", "color": "yellow", "note": "Moderate chop in Hale Passage. Stay close to shore."}
            return {"status": "SAFE", "color": "green", "note": "Good conditions around Fox Island bridge and shores."}

        if wind > 15.0 or current > 2.0:
            return {"status": "DANGER", "color": "red", "note": "Generic threshold exceeded. Check local conditions closely."}
        if wind > 8.0 or current > 1.0:
            return {"status": "CAUTION", "color": "yellow", "note": "Generic caution threshold exceeded."}
        return {"status": "SAFE", "color": "green", "note": "Generic thresholds show manageable conditions."}

    @staticmethod
    def evaluate_fly_fishing(zone: str, current: float, tide: float) -> dict:
        """Zone-specific fly fishing thresholds."""
        if zone == "purdy_bridge":
            if current > 3.0:
                return {"status": "DANGER", "color": "red", "note": "Current too fast to safely wade the spit."}
            elif 1.0 <= current <= 3.0:
                return {"status": "OPTIMAL", "color": "green", "note": "Current is ripping bait through the channel. Cast into the seams."}
            return {"status": "POOR", "color": "yellow", "note": "Slack water. Sea-run cutthroat are likely inactive."}
            
        elif zone == "gig_harbor":
            if tide > 8.0:
                return {"status": "OPTIMAL", "color": "green", "note": "High tide pushing bait into the harbor estuaries."}
            return {"status": "POOR", "color": "yellow", "note": "Low water. Fish have moved out to deeper Narrows structure."}
            
        elif zone == "fox_island":
            if 0.5 <= current <= 2.0:
                return {"status": "OPTIMAL", "color": "green", "note": "Good current sweeping the Hale Passage drop-offs."}
            return {"status": "CAUTION", "color": "yellow", "note": "Wait for moving water to trigger feeding."}

        if 0.5 <= current <= 2.0:
            return {"status": "OPTIMAL", "color": "green", "note": "Generic moving-water window looks fishable."}
        return {"status": "POOR", "color": "yellow", "note": "Generic threshold suggests waiting for better movement."}
