from marine_config import (
    FORECAST_MAX_WINDOWS_PER_ACTIVITY,
    TIDE_SLOPE_TO_CURRENT_KNOTS,
    ZONES,
)


class MarineSafetyEngine:
    """Evaluates physical marine parameters across distinct Gig Harbor micro-regions."""
    
    @staticmethod
    def get_zone_telemetry(
        base_current: float,
        base_tide: float,
        base_wind: float,
        zones_config: dict | None = None,
    ) -> dict:
        """Applies geographic multipliers to the baseline Narrows telemetry."""
        zones = {}
        zones_config = zones_config or ZONES

        for zone_id, zone_config in zones_config.items():
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
        current_predictions: list | None = None,
        current_source: str = "derived",
        wind_source: str = "fallback",
        max_windows_per_activity: int = FORECAST_MAX_WINDOWS_PER_ACTIVITY,
        zones_config: dict | None = None,
    ) -> list:
        """Scores upcoming tide-prediction intervals for paddling and fishing."""
        zones_config = zones_config or ZONES
        hourly_windows = self._build_hourly_forecast_windows(
            tide_predictions,
            wind_knots,
            wind_predictions or [],
            current_predictions or [],
            current_source,
            wind_source,
            zones_config,
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
                        zones_config=zones_config,
                    )
                )
                scored.append(
                    self._forecast_entry(
                        activity="Fish",
                        evaluation=fish,
                        window=window,
                        zone_id=zone_id,
                        zone_data=zone_data,
                        zones_config=zones_config,
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

    def build_hourly_timeline(
        self,
        tide_predictions: list,
        wind_knots: float,
        wind_predictions: list | None = None,
        current_predictions: list | None = None,
        current_source: str = "derived",
        wind_source: str = "fallback",
        zones_config: dict | None = None,
    ) -> list:
        """Builds an hourly planning timeline with per-zone kayak and fish scores."""
        zones_config = zones_config or ZONES
        hourly_windows = self._build_hourly_forecast_windows(
            tide_predictions,
            wind_knots,
            wind_predictions or [],
            current_predictions or [],
            current_source,
            wind_source,
            zones_config,
        )
        timeline = []

        for window in hourly_windows:
            zone_scores = {}
            for zone_id, zone_data in window["zones"].items():
                kayak = self.evaluate_kayaking(zone_id, zone_data["current"], zone_data["wind"])
                fish = self.evaluate_fly_fishing(zone_id, zone_data["current"], zone_data["tide"])
                zone_scores[zone_id] = {
                    "current": round(zone_data["current"], 2),
                    "wind": round(zone_data["wind"], 1),
                    "tide": round(zone_data["tide"], 1),
                    "kayak": kayak,
                    "fish": fish,
                    "kayak_score": self._forecast_score("Kayak", kayak["status"], zone_data),
                    "fish_score": self._forecast_score("Fish", fish["status"], zone_data),
                }

            timeline.append(
                {
                    "start": window["start"],
                    "end": window["end"],
                    "phase": window["phase"],
                    "base_current": round(window["base_current"], 2),
                    "current_source": window["current_source"],
                    "tide": round(window["average_tide"], 1),
                    "wind": round(window["base_wind"], 1),
                    "wind_source": window["wind_source"],
                    "zones": zone_scores,
                }
            )

        return timeline

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
        has_predicted = "predicted" in all_sources
        has_derived = "derived" in all_sources
        has_missing = "missing" in all_sources
        has_fallback = bool(fallback_reasons) or "fallback" in all_sources

        if has_seed or has_missing:
            return {
                "level": "Low",
                "color": "red",
                "note": "Seed or missing forecast data is involved.",
            }

        if telemetry.get("stale") or forecast.get("stale"):
            return {
                "level": "Medium",
                "color": "yellow",
                "note": "Showing the last good marine data; check source age.",
            }

        if not has_fallback and wind_knots < 12.0 and not has_derived:
            return {
                "level": "High",
                "color": "green",
                "note": "Live data with NOAA predicted current guidance." if has_predicted else "Live tide, current, and wind data with light wind.",
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
        current_predictions: list,
        current_source: str,
        wind_source: str,
        zones_config: dict,
    ) -> list:
        windows = []

        for current_point, next_point in zip(tide_predictions, tide_predictions[1:]):
            hours = (next_point["time"] - current_point["time"]).total_seconds() / 3600
            if hours <= 0:
                continue

            tide_delta = next_point["tide_feet"] - current_point["tide_feet"]
            derived_current = abs(tide_delta / hours) * TIDE_SLOPE_TO_CURRENT_KNOTS
            average_tide = (current_point["tide_feet"] + next_point["tide_feet"]) / 2
            base_current, current_direction, window_current_source = self._current_for_window(
                current_point["time"],
                next_point["time"],
                derived_current,
                current_predictions,
                current_source,
            )
            phase = self._forecast_phase(
                tide_delta,
                base_current,
                current_direction=current_direction,
                current_source=window_current_source,
            )
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
                    "current_source": window_current_source,
                    "average_tide": average_tide,
                    "base_wind": window_wind,
                    "wind_source": window_wind_source,
                    "zones": self.get_zone_telemetry(
                        base_current=base_current,
                        base_tide=average_tide,
                        base_wind=window_wind,
                        zones_config=zones_config,
                    ),
                }
            )

        return windows

    def _forecast_entry(
        self,
        activity: str,
        evaluation: dict,
        window: dict,
        zone_id: str,
        zone_data: dict,
        zones_config: dict,
    ) -> dict:
        return {
            "activity": activity,
            "zone_id": zone_id,
            "zone_title": zones_config[zone_id]["title"],
            "start": window["start"],
            "end": window["end"],
            "phase": window["phase"],
            "status": evaluation["status"],
            "score": self._forecast_score(activity, evaluation["status"], zone_data),
            "current": zone_data["current"],
            "current_source": window["current_source"],
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
    def _current_for_window(
        start,
        end,
        derived_current_knots: float,
        current_predictions: list,
        current_source: str,
    ) -> tuple[float, float | None, str]:
        if not current_predictions:
            return derived_current_knots, None, "derived"

        midpoint = start + (end - start) / 2
        nearest = min(
            current_predictions,
            key=lambda item: abs((item["time"] - midpoint).total_seconds()),
        )
        distance_seconds = abs((nearest["time"] - midpoint).total_seconds())
        if distance_seconds <= 5400:
            return nearest["speed"], nearest.get("dir"), current_source if current_source != "derived" else "predicted"

        return derived_current_knots, None, "derived"

    @staticmethod
    def _forecast_phase(
        tide_delta: float,
        base_current: float,
        current_direction: float | None = None,
        current_source: str = "derived",
    ) -> str:
        if base_current < 0.25:
            return "Slack-ish"
        if current_source == "predicted" and current_direction is not None:
            if 100 < current_direction < 260:
                return "Flood/South"
            return "Ebb/North"
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

        elif zone == "sunrise_beach":
            if wind > 14.0 or current > 1.8:
                return {"status": "DANGER", "color": "red", "note": "Open shoreline exposure. Avoid marginal paddling windows."}
            elif wind > 9.0 or current > 1.0:
                return {"status": "CAUTION", "color": "yellow", "note": "Exposed beach. Watch for chop and landing conditions."}
            return {"status": "SAFE", "color": "green", "note": "Manageable shoreline conditions near Sunrise Beach."}

        elif zone == "narrows_park":
            if current > 1.8 or wind > 12.0:
                return {"status": "DANGER", "color": "red", "note": "Narrows exposure can build fast. Strong current risk."}
            elif current > 0.8 or wind > 8.0:
                return {"status": "CAUTION", "color": "yellow", "note": "Stay alert near Narrows Park; conditions can change quickly."}
            return {"status": "SAFE", "color": "green", "note": "Lower current window along the Narrows shoreline."}

        elif zone == "fox_island_pier":
            if wind > 12.0 or current > 2.0:
                return {"status": "DANGER", "color": "red", "note": "Pier area is exposed to fetch and current."}
            elif wind > 8.0 or current > 1.0:
                return {"status": "CAUTION", "color": "yellow", "note": "Use caution around pier structure and wind chop."}
            return {"status": "SAFE", "color": "green", "note": "Reasonable conditions around the fishing pier."}

        elif zone == "purdy_sand_spit":
            if current > 2.0:
                return {"status": "DANGER", "color": "red", "note": "Strong flow near the spit and bridge. Avoid paddling."}
            elif current > 1.0 or wind > 12.0:
                return {"status": "CAUTION", "color": "yellow", "note": "Watch the spit edges and bridge current."}
            return {"status": "SAFE", "color": "green", "note": "Manageable spit conditions near slack or slower water."}

        elif zone == "kopachuck":
            if wind > 15.0 or current > 1.8:
                return {"status": "DANGER", "color": "red", "note": "Henderson Bay exposure can create rough landings."}
            elif wind > 9.0 or current > 1.0:
                return {"status": "CAUTION", "color": "yellow", "note": "Moderate exposure off Kopachuck. Mind beach landing."}
            return {"status": "SAFE", "color": "green", "note": "Good sheltered-to-moderate beach conditions."}

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

        elif zone == "sunrise_beach":
            if 0.4 <= current <= 1.8:
                return {"status": "OPTIMAL", "color": "green", "note": "Good moving water along Sunrise Beach structure."}
            return {"status": "POOR", "color": "yellow", "note": "Look for more current along the shoreline."}

        elif zone == "narrows_park":
            if 0.5 <= current <= 1.8:
                return {"status": "OPTIMAL", "color": "green", "note": "Current is moving bait along the Narrows shoreline."}
            elif current > 2.5:
                return {"status": "DANGER", "color": "red", "note": "Too much current for comfortable shore casting."}
            return {"status": "CAUTION", "color": "yellow", "note": "Wait for a stronger but manageable current push."}

        elif zone == "fox_island_pier":
            if 0.5 <= current <= 2.0:
                return {"status": "OPTIMAL", "color": "green", "note": "Good current around pier structure and drop-offs."}
            return {"status": "CAUTION", "color": "yellow", "note": "Better when water is moving around the pier."}

        elif zone == "purdy_sand_spit":
            if 1.0 <= current <= 2.8:
                return {"status": "OPTIMAL", "color": "green", "note": "Moving water along the spit can concentrate bait."}
            elif current > 3.0:
                return {"status": "DANGER", "color": "red", "note": "Current too fast near the spit and bridge."}
            return {"status": "POOR", "color": "yellow", "note": "Slack water around the spit is often less productive."}

        elif zone == "kopachuck":
            if tide > 8.0 and current > 0.3:
                return {"status": "OPTIMAL", "color": "green", "note": "Higher water and movement can work the beach edge."}
            return {"status": "POOR", "color": "yellow", "note": "Wait for higher water or more beach movement."}

        if 0.5 <= current <= 2.0:
            return {"status": "OPTIMAL", "color": "green", "note": "Generic moving-water window looks fishable."}
        return {"status": "POOR", "color": "yellow", "note": "Generic threshold suggests waiting for better movement."}
