from marine_config import (
    DEFAULT_RISK_TOLERANCE,
    FISH_RULES_BY_ZONE,
    FORECAST_MAX_WINDOWS_PER_ACTIVITY,
    GENERIC_FISH_RULES,
    GENERIC_KAYAK_RULES,
    KAYAK_RULES_BY_ZONE,
    RISK_TOLERANCE_PROFILES,
    STATUS_COLORS,
    TIDE_SLOPE_TO_CURRENT_KNOTS,
    ZONES,
)


class MarineSafetyEngine:
    """Evaluates physical marine parameters across distinct Gig Harbor micro-regions."""

    def __init__(self, risk_tolerance: str = DEFAULT_RISK_TOLERANCE):
        self.risk_tolerance = self.normalize_risk_tolerance(risk_tolerance)
    
    @staticmethod
    def get_zone_telemetry(
        base_current: float,
        base_tide: float,
        base_wind: float,
        base_wind_direction: float | None = None,
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
            wind = base_wind * MarineSafetyEngine.wind_exposure_multiplier(
                zone_config,
                base_wind_direction,
            )

            zones[zone_id] = {
                "current": current,
                "tide": base_tide,
                "wind": wind,
                "wind_direction": base_wind_direction,
                "wind_exposure": MarineSafetyEngine.wind_exposure_label(
                    zone_config,
                    base_wind_direction,
                ),
            }

        return zones

    def build_forecast_windows(
        self,
        tide_predictions: list,
        wind_knots: float,
        wind_direction: float | None = None,
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
            fallback_wind_direction=wind_direction,
        )
        if not hourly_windows:
            return []

        scored = []
        for window in hourly_windows:
            for zone_id, zone_data in window["zones"].items():
                kayak = self.evaluate_kayaking(
                    zone_id,
                    zone_data["current"],
                    zone_data["wind"],
                    risk_tolerance=self.risk_tolerance,
                )
                fish = self.evaluate_fly_fishing(
                    zone_id,
                    zone_data["current"],
                    zone_data["tide"],
                    risk_tolerance=self.risk_tolerance,
                )

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
        wind_direction: float | None = None,
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
            fallback_wind_direction=wind_direction,
        )
        timeline = []

        for window in hourly_windows:
            zone_scores = {}
            for zone_id, zone_data in window["zones"].items():
                kayak = self.evaluate_kayaking(
                    zone_id,
                    zone_data["current"],
                    zone_data["wind"],
                    risk_tolerance=self.risk_tolerance,
                )
                fish = self.evaluate_fly_fishing(
                    zone_id,
                    zone_data["current"],
                    zone_data["tide"],
                    risk_tolerance=self.risk_tolerance,
                )
                zone_scores[zone_id] = {
                    "current": round(zone_data["current"], 2),
                    "wind": round(zone_data["wind"], 1),
                    "wind_direction": zone_data.get("wind_direction"),
                    "wind_exposure": zone_data.get("wind_exposure"),
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
        fallback_wind_direction: float | None = None,
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
            window_wind, window_wind_direction, window_wind_source = self._wind_for_window(
                current_point["time"],
                next_point["time"],
                wind_knots,
                fallback_wind_direction,
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
                    "base_wind_direction": window_wind_direction,
                    "wind_source": window_wind_source,
                    "zones": self.get_zone_telemetry(
                        base_current=base_current,
                        base_tide=average_tide,
                        base_wind=window_wind,
                        base_wind_direction=window_wind_direction,
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
            "wind_direction": zone_data.get("wind_direction"),
            "wind_exposure": zone_data.get("wind_exposure"),
            "wind_source": window["wind_source"],
            "tide": zone_data["tide"],
            "note": evaluation["note"],
        }

    @staticmethod
    def _wind_for_window(
        start,
        end,
        fallback_wind_knots: float,
        fallback_wind_direction: float | None,
        wind_predictions: list,
        wind_source: str,
    ) -> tuple[float, float | None, str]:
        if not wind_predictions:
            if wind_source == "missing":
                return fallback_wind_knots, fallback_wind_direction, "fallback"
            return fallback_wind_knots, fallback_wind_direction, wind_source

        midpoint = start + (end - start) / 2
        nearest = min(
            wind_predictions,
            key=lambda item: abs((item["time"] - midpoint).total_seconds()),
        )
        distance_seconds = abs((nearest["time"] - midpoint).total_seconds())
        if distance_seconds <= 5400:
            return nearest["wind_knots"], nearest.get("wind_direction"), "live"

        return fallback_wind_knots, fallback_wind_direction, "fallback"

    @staticmethod
    def wind_exposure_multiplier(zone_config: dict, wind_direction: float | None) -> float:
        base_multiplier = zone_config.get("wind_multiplier", 1.0)
        exposure_bearing = zone_config.get("wind_exposure_bearing")
        if wind_direction is None or exposure_bearing is None:
            return base_multiplier

        spread = max(1.0, float(zone_config.get("wind_exposure_spread", 90.0)))
        difference = MarineSafetyEngine._bearing_difference(wind_direction, exposure_bearing)
        exposure = max(0.0, 1.0 - (difference / spread))
        shadow = float(zone_config.get("wind_shadow_multiplier", 0.72))
        exposed = float(zone_config.get("wind_exposed_multiplier", 1.28))
        direction_factor = shadow + ((exposed - shadow) * exposure)
        return base_multiplier * direction_factor

    @staticmethod
    def wind_exposure_label(zone_config: dict, wind_direction: float | None) -> str:
        exposure_bearing = zone_config.get("wind_exposure_bearing")
        if wind_direction is None or exposure_bearing is None:
            return "unmodeled"

        difference = MarineSafetyEngine._bearing_difference(wind_direction, exposure_bearing)
        if difference <= 35:
            return "exposed"
        if difference >= 110:
            return "sheltered"
        return "partial"

    @staticmethod
    def _bearing_difference(first: float, second: float) -> float:
        return abs((first - second + 180) % 360 - 180)

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
    def normalize_risk_tolerance(risk_tolerance: str | None) -> str:
        if risk_tolerance in RISK_TOLERANCE_PROFILES:
            return risk_tolerance
        return DEFAULT_RISK_TOLERANCE

    @staticmethod
    def evaluate_kayaking(
        zone: str,
        current: float,
        wind: float,
        risk_tolerance: str = DEFAULT_RISK_TOLERANCE,
    ) -> dict:
        """Evaluates kayaking safety from configured thresholds."""
        rules = KAYAK_RULES_BY_ZONE.get(zone, GENERIC_KAYAK_RULES)
        metrics = {"current": current, "wind": wind}
        return MarineSafetyEngine._evaluate_rules(metrics, rules, risk_tolerance)

    @staticmethod
    def evaluate_fly_fishing(
        zone: str,
        current: float,
        tide: float,
        risk_tolerance: str = DEFAULT_RISK_TOLERANCE,
    ) -> dict:
        """Evaluates fly-fishing quality from configured thresholds."""
        rules = FISH_RULES_BY_ZONE.get(zone, GENERIC_FISH_RULES)
        metrics = {"current": current, "tide": tide}
        return MarineSafetyEngine._evaluate_rules(metrics, rules, risk_tolerance)

    @staticmethod
    def _evaluate_rules(metrics: dict, rules: tuple[dict, ...], risk_tolerance: str) -> dict:
        for rule in rules:
            if MarineSafetyEngine._rule_matches(metrics, rule, risk_tolerance):
                status = rule["status"]
                return {
                    "status": status,
                    "color": STATUS_COLORS.get(status, "yellow"),
                    "note": rule["note"],
                }
        return {
            "status": "CAUTION",
            "color": STATUS_COLORS["CAUTION"],
            "note": "No configured threshold matched these conditions.",
        }

    @staticmethod
    def _rule_matches(metrics: dict, rule: dict, risk_tolerance: str) -> bool:
        all_conditions = rule.get("all", ())
        any_conditions = rule.get("any", ())

        if all_conditions and not all(
            MarineSafetyEngine._condition_matches(metrics, condition, risk_tolerance)
            for condition in all_conditions
        ):
            return False
        if any_conditions and not any(
            MarineSafetyEngine._condition_matches(metrics, condition, risk_tolerance)
            for condition in any_conditions
        ):
            return False
        return True

    @staticmethod
    def _condition_matches(metrics: dict, condition: dict, risk_tolerance: str) -> bool:
        actual = metrics[condition["metric"]]
        expected = float(condition["value"])
        if condition.get("risk_adjust"):
            profile = RISK_TOLERANCE_PROFILES[
                MarineSafetyEngine.normalize_risk_tolerance(risk_tolerance)
            ]
            expected *= profile["safety_threshold_multiplier"]

        op = condition["op"]
        if op == ">":
            return actual > expected
        if op == ">=":
            return actual >= expected
        if op == "<":
            return actual < expected
        if op == "<=":
            return actual <= expected
        if op == "==":
            return actual == expected
        raise ValueError(f"Unsupported threshold operator: {op}")
