"""Smoke-test digest preferences, outbox delivery, and scheduler logic.

Runs without a web server or external email credentials.
"""

import asyncio
import json
import sys
import tempfile
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from digest_delivery import (
    DigestEmailSender,
    DigestPreferences,
    DigestPreferenceStore,
    DigestScheduler,
    validate_preferences,
)


def sample_payload(activity: str = "Kayak") -> dict:
    return {
        "activity": activity,
        "config": {
            "region": {"id": "gig_harbor", "name": "Gig Harbor"},
            "risk_tolerance": {"id": "standard"},
        },
        "digest": {"tomorrow": {"items": [], "summary": "Smoke digest"}},
        "text": f"TideWindow Tomorrow's Best - Gig Harbor\n{activity}: Inside Gig Harbor",
    }


async def main() -> None:
    validate_preferences({
        "enabled": True,
        "email": "smoke@example.com",
        "delivery_time": "06:00",
        "region": "gig_harbor",
        "activity": "Kayak",
        "risk": "standard",
        "density": "compact",
    })

    with tempfile.TemporaryDirectory() as temp_dir:
        base = Path(temp_dir)
        store = DigestPreferenceStore(base / "preferences.json")
        sender = DigestEmailSender(base / "outbox.json", smtp_enabled=False)
        store.save(
            DigestPreferences(
                enabled=True,
                email="smoke@example.com",
                delivery_time="06:00",
                region="gig_harbor",
                activity="Kayak",
                density="compact",
            ),
            "smoke",
        )

        async def build_digest(preferences: DigestPreferences) -> dict:
            return sample_payload(preferences.activity)

        scheduler = DigestScheduler(store, sender, build_digest, "http://127.0.0.1:8765")
        first = await scheduler.run_due(datetime(2026, 6, 13, 6, 1))
        second = await scheduler.run_due(datetime(2026, 6, 13, 7, 1))
        store.acquire_lock("digest-delivery", "existing-run", datetime(2026, 6, 14, 6, 1))
        locked = await scheduler.run_due(datetime(2026, 6, 14, 6, 1), run_id="second-run")
        outbox = json.loads((base / "outbox.json").read_text())["messages"]
        audit = store.audit()

        assert first[0].delivered, first[0]
        assert second[0].reason == "already delivered", second[0]
        assert locked[0].reason == "locked", locked[0]
        assert len(outbox) == 1, outbox
        assert "Open digest" in outbox[0]["body"], outbox[0]
        assert "Stop daily email" in outbox[0]["body"], outbox[0]
        assert audit[-1]["reason"] == "locked", audit[-1]

    print("digest delivery smoke ok")


if __name__ == "__main__":
    asyncio.run(main())
