import asyncio
import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from digest_delivery import (
    DigestEmailSender,
    DigestPreferences,
    DigestPreferenceStore,
    DigestScheduler,
    build_digest_params,
    build_digest_url,
    build_unsubscribe_url,
    delivery_time_reached,
    digest_email_body,
    sign_unsubscribe_token,
    validate_preferences,
    verify_unsubscribe_token,
)


def sample_payload(activity="Kayak"):
    return {
        "activity": activity,
        "config": {
            "region": {"id": "gig_harbor", "name": "Gig Harbor"},
            "risk_tolerance": {"id": "standard"},
        },
        "digest": {
            "tomorrow": {
                "items": [],
                "summary": "Digest summary",
            }
        },
        "text": "TideWindow Tomorrow's Best - Gig Harbor\nKayak: Inside Gig Harbor",
    }


class DigestDeliveryTests(unittest.TestCase):
    def test_validate_preferences_normalizes_and_checks_fields(self):
        preferences = validate_preferences({
            "enabled": True,
            "email": " user@example.com ",
            "delivery_time": "06:30",
            "region": "gig_harbor",
            "activity": "fishing",
            "risk": "standard",
            "density": "compact",
        })

        self.assertTrue(preferences.enabled)
        self.assertEqual(preferences.email, "user@example.com")
        self.assertEqual(preferences.activity, "Fish")
        self.assertEqual(preferences.density, "compact")

    def test_validate_preferences_rejects_invalid_email_when_enabled(self):
        with self.assertRaises(ValueError):
            validate_preferences({
                "enabled": True,
                "email": "bad",
                "delivery_time": "06:00",
            })

    def test_preference_store_round_trips_preferences(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store = DigestPreferenceStore(Path(temp_dir) / "preferences.json")
            saved = validate_preferences({
                "enabled": True,
                "email": "test@example.com",
                "delivery_time": "07:15",
                "region": "gig_harbor",
                "activity": "Kayak",
                "risk": "conservative",
                "density": "standard",
            })

            store.save(saved, "phone")
            loaded = store.get("phone")

            self.assertEqual(loaded.email, "test@example.com")
            self.assertEqual(loaded.delivery_time, "07:15")
            self.assertEqual(loaded.risk, "conservative")

    def test_digest_params_apply_density_limit(self):
        preferences = DigestPreferences(region="gig_harbor", density="compact")
        params = build_digest_params(preferences)

        self.assertEqual(params["region"], "gig_harbor")
        self.assertEqual(params["activity"], "All")
        self.assertLess(params["limit"], 13)
        self.assertGreater(params["limit"], 1)

    def test_digest_url_carries_preferences(self):
        preferences = DigestPreferences(
            region="gig_harbor",
            activity="Kayak",
            risk="aggressive",
            density="full",
        )
        url = build_digest_url(preferences, "https://example.test")

        self.assertTrue(url.startswith("https://example.test/digest?"))
        self.assertIn("activity=Kayak", url)
        self.assertIn("risk=aggressive", url)

    def test_unsubscribe_token_round_trips(self):
        token = sign_unsubscribe_token("phone", "Test@Example.com")

        self.assertTrue(verify_unsubscribe_token("phone", "test@example.com", token))
        self.assertFalse(verify_unsubscribe_token("phone", "other@example.com", token))

    def test_unsubscribe_url_and_email_body_include_disable_link(self):
        preferences = DigestPreferences(email="test@example.com")
        unsubscribe_url = build_unsubscribe_url(preferences, "phone", "https://example.test")
        body = digest_email_body(sample_payload(), "https://example.test/digest", unsubscribe_url)

        self.assertTrue(unsubscribe_url.startswith("https://example.test/unsubscribe?"))
        self.assertIn("client_id=phone", unsubscribe_url)
        self.assertIn("Stop daily email", body)
        self.assertIn(unsubscribe_url, body)

    def test_delivery_time_reached_uses_local_clock_time(self):
        self.assertFalse(delivery_time_reached("06:30", datetime(2026, 6, 13, 6, 29)))
        self.assertTrue(delivery_time_reached("06:30", datetime(2026, 6, 13, 6, 30)))

    def test_email_sender_writes_local_outbox_without_smtp(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            outbox = Path(temp_dir) / "outbox.json"
            sender = DigestEmailSender(outbox, smtp_enabled=False)
            preferences = DigestPreferences(email="test@example.com")

            result = sender.send(sample_payload(), preferences, "https://example.test/digest")

            self.assertTrue(result.delivered)
            self.assertEqual(result.mode, "outbox")
            messages = json.loads(outbox.read_text())["messages"]
            self.assertEqual(messages[0]["to"], "test@example.com")
            self.assertIn("Open digest", messages[0]["body"])

    def test_scheduler_runs_due_delivery_once_per_day(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store = DigestPreferenceStore(Path(temp_dir) / "preferences.json")
            sender = DigestEmailSender(Path(temp_dir) / "outbox.json", smtp_enabled=False)
            preferences = DigestPreferences(
                enabled=True,
                email="test@example.com",
                delivery_time="06:00",
                region="gig_harbor",
                activity="Kayak",
            )
            store.save(preferences, "local")

            async def build_digest(_preferences):
                return sample_payload(_preferences.activity)

            scheduler = DigestScheduler(store, sender, build_digest, "https://example.test")
            first = asyncio.run(scheduler.run_due(datetime(2026, 6, 13, 6, 1)))
            second = asyncio.run(scheduler.run_due(datetime(2026, 6, 13, 7, 1)))

            self.assertTrue(first[0].delivered)
            self.assertEqual(second[0].reason, "already delivered")
            audit = store.audit()
            self.assertEqual(audit[0]["event"], "delivery")
            self.assertTrue(audit[0]["delivered"])
            self.assertEqual(audit[1]["reason"], "already delivered")

    def test_scheduler_lock_prevents_parallel_delivery(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store = DigestPreferenceStore(Path(temp_dir) / "preferences.json")
            sender = DigestEmailSender(Path(temp_dir) / "outbox.json", smtp_enabled=False)
            store.save(
                DigestPreferences(
                    enabled=True,
                    email="test@example.com",
                    delivery_time="06:00",
                    region="gig_harbor",
                    activity="Kayak",
                ),
                "local",
            )
            now = datetime(2026, 6, 13, 6, 1)
            self.assertTrue(store.acquire_lock("digest-delivery", "existing-run", now))

            async def build_digest(_preferences):
                return sample_payload(_preferences.activity)

            scheduler = DigestScheduler(store, sender, build_digest, "https://example.test")
            results = asyncio.run(scheduler.run_due(now, run_id="second-run"))

            self.assertEqual(results[0].reason, "locked")
            self.assertEqual(results[0].run_id, "second-run")
            self.assertFalse((Path(temp_dir) / "outbox.json").exists())
            self.assertEqual(store.audit()[0]["reason"], "locked")


if __name__ == "__main__":
    unittest.main()
