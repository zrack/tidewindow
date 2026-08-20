"""Print a provider/station confidence report for configured TideWindow regions."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from marine_regions import REGIONS, get_region, ranked_spots_for_region


def format_station(station: str | None, name: str | None, station_type: str | None) -> str:
    if not station:
        return "Missing"
    suffix = f" ({station_type})" if station_type else ""
    return f"{station} {name or ''}{suffix}".strip()


def spot_exposure_summary(region_id: str) -> str:
    spots = ranked_spots_for_region(region_id)
    reviewed = sum(1 for spot in spots if spot.get("wind_exposure_basis") == "spot_reviewed")
    explicit = sum(1 for spot in spots if spot.get("wind_exposure_basis") == "spot")
    family = sum(1 for spot in spots if spot.get("wind_exposure_basis") == "shoreline_family")
    missing = len(spots) - reviewed - explicit - family
    summary = f"{reviewed} reviewed, {explicit} spot, {family} family"
    return f"{summary}, {missing} missing" if missing else summary


def warning_count(context: dict) -> int:
    return len(context.get("provider_strategy", {}).get("warnings", ()) or ())


def provider_row(region_id: str) -> dict:
    region = get_region(region_id)
    context = region["provider_context"]
    confidence = context.get("provider_confidence", {})
    strategy = context.get("provider_strategy", {})
    return {
        "region": region["name"],
        "type": region["type"],
        "profile": strategy.get("headline", "Station-backed"),
        "confidence": confidence.get("label") or confidence.get("level") or "Unknown",
        "tide": format_station(context.get("tide_station"), context.get("tide_station_name"), context.get("tide_station_type")),
        "current": format_station(context.get("current_station"), context.get("current_station_name"), context.get("current_station_type")),
        "bin": context.get("current_bin") or "",
        "depth": context.get("current_bin_depth_ft") or "",
        "spots": str(len(region["spot_ids"])),
        "exposure": spot_exposure_summary(region_id),
        "warnings": str(warning_count(context)),
    }


def markdown_table(rows: list[dict]) -> str:
    headers = [
        "Region",
        "Type",
        "Profile",
        "Confidence",
        "Tide",
        "Current",
        "Bin",
        "Depth ft",
        "Spots",
        "Exposure basis",
        "Warnings",
    ]
    keys = ["region", "type", "profile", "confidence", "tide", "current", "bin", "depth", "spots", "exposure", "warnings"]
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows:
        values = [str(row[key]).replace("|", "/") for key in keys]
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Report TideWindow provider context coverage.")
    parser.add_argument("--low-confidence-only", action="store_true", help="show only regions below high station fit or with warnings")
    args = parser.parse_args()

    rows = [provider_row(region_id) for region_id in REGIONS]
    if args.low_confidence_only:
        rows = [
            row
            for row in rows
            if "High station fit" not in row["confidence"] or row["warnings"] != "0"
        ]
    print(markdown_table(rows))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
