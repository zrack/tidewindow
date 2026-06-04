"""Local sunrise/sunset computation for TideWindow.

Uses the standard sunrise/sunset almanac algorithm so the dashboard can shade
non-daylight hours without depending on any external API or key. Returns naive
local datetimes, consistent with the rest of the app's time handling.
"""

import math
from datetime import date as date_cls
from datetime import datetime, timedelta

# Zenith angles (degrees) for different definitions of sunrise/sunset.
ZENITH_OFFICIAL = 90.8333
ZENITH_CIVIL = 96.0


def _norm_360(value: float) -> float:
    return value % 360.0


def _norm_24(value: float) -> float:
    return value % 24.0


def _local_utc_offset_hours(day: date_cls) -> float:
    """UTC offset in hours for the local timezone on the given date (DST-aware)."""
    noon_local = datetime(day.year, day.month, day.day, 12).astimezone()
    return noon_local.utcoffset().total_seconds() / 3600.0


def _sun_event(lat: float, lon: float, day: date_cls, rising: bool, zenith: float):
    """Returns the naive-local datetime of a sun event, or None if it doesn't occur."""
    day_of_year = day.timetuple().tm_yday
    lng_hour = lon / 15.0

    approx = day_of_year + (((6 if rising else 18) - lng_hour) / 24.0)
    mean_anomaly = (0.9856 * approx) - 3.289
    true_long = _norm_360(
        mean_anomaly
        + (1.916 * math.sin(math.radians(mean_anomaly)))
        + (0.020 * math.sin(math.radians(2 * mean_anomaly)))
        + 282.634
    )

    right_ascension = _norm_360(math.degrees(math.atan(0.91764 * math.tan(math.radians(true_long)))))
    # Put right ascension in the same quadrant as the true longitude.
    long_quadrant = (math.floor(true_long / 90.0)) * 90.0
    ra_quadrant = (math.floor(right_ascension / 90.0)) * 90.0
    right_ascension = (right_ascension + (long_quadrant - ra_quadrant)) / 15.0

    sin_dec = 0.39782 * math.sin(math.radians(true_long))
    cos_dec = math.cos(math.asin(sin_dec))

    cos_hour = (math.cos(math.radians(zenith)) - (sin_dec * math.sin(math.radians(lat)))) / (
        cos_dec * math.cos(math.radians(lat))
    )
    if cos_hour > 1 or cos_hour < -1:
        # Sun never rises (polar night) or never sets (midnight sun) that day.
        return None

    if rising:
        hour_angle = 360.0 - math.degrees(math.acos(cos_hour))
    else:
        hour_angle = math.degrees(math.acos(cos_hour))
    hour_angle /= 15.0

    mean_time = hour_angle + right_ascension - (0.06571 * approx) - 6.622
    universal_time = _norm_24(mean_time - lng_hour)

    local_time = _norm_24(universal_time + _local_utc_offset_hours(day))
    return datetime(day.year, day.month, day.day) + timedelta(hours=local_time)


def sun_events(lat: float, lon: float, day: date_cls) -> dict:
    """Returns sunrise, sunset, and civil dawn/dusk for a date at a location.

    Values are naive local datetimes, or None when the event does not occur.
    """
    return {
        "sunrise": _sun_event(lat, lon, day, rising=True, zenith=ZENITH_OFFICIAL),
        "sunset": _sun_event(lat, lon, day, rising=False, zenith=ZENITH_OFFICIAL),
        "dawn": _sun_event(lat, lon, day, rising=True, zenith=ZENITH_CIVIL),
        "dusk": _sun_event(lat, lon, day, rising=False, zenith=ZENITH_CIVIL),
    }


if __name__ == "__main__":
    # Quick self-check for Gig Harbor / Tacoma Narrows.
    events = sun_events(47.2690, -122.5517, datetime.now().date())
    for label, value in events.items():
        printable = value.strftime("%I:%M %p") if value else "n/a"
        print(f"{label:>8}: {printable}")
