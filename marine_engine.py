from marine_config import ZONES


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
