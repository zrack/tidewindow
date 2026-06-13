import json
import hashlib
import hmac
import os
import smtplib
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from email.message import EmailMessage
from math import ceil
from pathlib import Path
from re import fullmatch
from tempfile import NamedTemporaryFile
from typing import Awaitable, Callable
from urllib.parse import urlencode

from marine_config import DEFAULT_RISK_TOLERANCE, RISK_TOLERANCE_PROFILES
from marine_regions import DEFAULT_REGION_ID, get_region


DENSITY_RATIOS = {
    "compact": 0.5,
    "standard": 0.75,
    "full": 1.0,
}
DEFAULT_CLIENT_ID = "local"
DEFAULT_DELIVERY_TIME = "06:00"
DEFAULT_STORE_PATH = Path(os.getenv("TIDEWINDOW_DIGEST_STORE", "data/digest_preferences.json"))
DEFAULT_OUTBOX_PATH = Path(os.getenv("TIDEWINDOW_DIGEST_OUTBOX", "data/digest_outbox.json"))
DEFAULT_LOCK_TTL_SECONDS = 15 * 60
DIGEST_DELIVERY_LOCK = "digest-delivery"


@dataclass
class DigestPreferences:
    enabled: bool = False
    email: str = ""
    delivery_time: str = DEFAULT_DELIVERY_TIME
    region: str = DEFAULT_REGION_ID
    activity: str = "All"
    risk: str = DEFAULT_RISK_TOLERANCE
    density: str = "full"
    last_delivered_for: str | None = None

    def to_dict(self) -> dict:
        return {
            "enabled": self.enabled,
            "email": self.email,
            "delivery_time": self.delivery_time,
            "region": self.region,
            "activity": self.activity,
            "risk": self.risk,
            "density": self.density,
            "last_delivered_for": self.last_delivered_for,
        }

    @classmethod
    def from_dict(cls, data: dict | None) -> "DigestPreferences":
        if not data:
            return cls()
        return validate_preferences(data, require_email=False)


@dataclass
class DeliveryResult:
    client_id: str
    delivered: bool
    mode: str
    reason: str
    date: str | None = None
    recipient: str | None = None
    run_id: str | None = None

    def to_dict(self) -> dict:
        return {
            "client_id": self.client_id,
            "delivered": self.delivered,
            "mode": self.mode,
            "reason": self.reason,
            "date": self.date,
            "recipient": self.recipient,
            "run_id": self.run_id,
        }


class DigestPreferenceStore:
    def __init__(self, path: Path | str = DEFAULT_STORE_PATH):
        self.path = Path(path)

    def get(self, client_id: str = DEFAULT_CLIENT_ID) -> DigestPreferences:
        data = self._read()
        return DigestPreferences.from_dict(data.get("subscriptions", {}).get(client_id))

    def save(self, preferences: DigestPreferences, client_id: str = DEFAULT_CLIENT_ID) -> DigestPreferences:
        data = self._read()
        data.setdefault("subscriptions", {})[client_id] = preferences.to_dict()
        self._write(data)
        return preferences

    def all(self) -> dict[str, DigestPreferences]:
        data = self._read()
        return {
            client_id: DigestPreferences.from_dict(value)
            for client_id, value in data.get("subscriptions", {}).items()
        }

    def mark_delivered(self, client_id: str, delivered_for: str) -> None:
        preferences = self.get(client_id)
        preferences.last_delivered_for = delivered_for
        self.save(preferences, client_id)

    def append_audit(self, event: dict) -> dict:
        data = self._read()
        audit = data.setdefault("audit", [])
        entry = {
            "created_at": datetime.now().isoformat(timespec="seconds"),
            **event,
        }
        audit.append(entry)
        data["audit"] = audit[-250:]
        self._write(data)
        return entry

    def audit(self, limit: int = 50) -> list[dict]:
        data = self._read()
        limit = max(1, min(limit, 250))
        return data.get("audit", [])[-limit:]

    def acquire_lock(
        self,
        name: str,
        run_id: str,
        now: datetime | None = None,
        ttl_seconds: int = DEFAULT_LOCK_TTL_SECONDS,
    ) -> bool:
        now = now or datetime.now()
        data = self._read()
        locks = data.setdefault("locks", {})
        current = locks.get(name)
        if current:
            try:
                acquired_at = datetime.fromisoformat(current["acquired_at"])
            except (KeyError, TypeError, ValueError):
                acquired_at = now - timedelta(seconds=ttl_seconds + 1)
            if current.get("run_id") != run_id and now - acquired_at < timedelta(seconds=ttl_seconds):
                return False
        locks[name] = {
            "run_id": run_id,
            "acquired_at": now.isoformat(timespec="seconds"),
            "ttl_seconds": ttl_seconds,
        }
        self._write(data)
        return True

    def release_lock(self, name: str, run_id: str) -> None:
        data = self._read()
        locks = data.setdefault("locks", {})
        current = locks.get(name)
        if current and current.get("run_id") == run_id:
            locks.pop(name, None)
            self._write(data)

    def _read(self) -> dict:
        if not self.path.exists():
            return {"subscriptions": {}, "audit": [], "locks": {}}
        with self.path.open("r", encoding="utf-8") as file:
            data = json.load(file)
        data.setdefault("subscriptions", {})
        data.setdefault("audit", [])
        data.setdefault("locks", {})
        return data

    def _write(self, data: dict) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with NamedTemporaryFile("w", encoding="utf-8", dir=self.path.parent, delete=False) as file:
            json.dump(data, file, indent=2, sort_keys=True)
            file.write("\n")
            temp_name = file.name
        Path(temp_name).replace(self.path)


class DigestEmailSender:
    def __init__(self, outbox_path: Path | str = DEFAULT_OUTBOX_PATH, smtp_enabled: bool | None = None):
        self.outbox_path = Path(outbox_path)
        self.smtp_enabled = smtp_enabled

    def send(
        self,
        payload: dict,
        preferences: DigestPreferences,
        digest_url: str = "",
        unsubscribe_url: str = "",
    ) -> DeliveryResult:
        body = digest_email_body(payload, digest_url, unsubscribe_url)
        subject = digest_email_subject(payload)
        use_smtp = self.smtp_enabled if self.smtp_enabled is not None else smtp_configured()
        if use_smtp:
            send_smtp_message(preferences.email, subject, body)
            return DeliveryResult(
                client_id="",
                delivered=True,
                mode="smtp",
                reason="sent",
                recipient=preferences.email,
            )

        self._append_outbox(
            {
                "created_at": datetime.now().isoformat(timespec="seconds"),
                "to": preferences.email,
                "subject": subject,
                "body": body,
                "digest_url": digest_url,
                "unsubscribe_url": unsubscribe_url,
                "region": payload.get("config", {}).get("region", {}).get("id"),
                "activity": payload.get("activity"),
            }
        )
        return DeliveryResult(
            client_id="",
            delivered=True,
            mode="outbox",
            reason="queued",
            recipient=preferences.email,
        )

    def _append_outbox(self, message: dict) -> None:
        self.outbox_path.parent.mkdir(parents=True, exist_ok=True)
        messages = []
        if self.outbox_path.exists():
            with self.outbox_path.open("r", encoding="utf-8") as file:
                messages = json.load(file).get("messages", [])
        messages.append(message)
        messages = messages[-50:]
        with NamedTemporaryFile("w", encoding="utf-8", dir=self.outbox_path.parent, delete=False) as file:
            json.dump({"messages": messages}, file, indent=2, sort_keys=True)
            file.write("\n")
            temp_name = file.name
        Path(temp_name).replace(self.outbox_path)


@dataclass
class DigestScheduler:
    store: DigestPreferenceStore
    sender: DigestEmailSender
    build_digest: Callable[[DigestPreferences], Awaitable[dict]]
    public_base_url: str = ""

    async def run_due(self, now: datetime | None = None, run_id: str | None = None) -> list[DeliveryResult]:
        now = now or datetime.now()
        run_id = run_id or new_run_id(now)
        results: list[DeliveryResult] = []
        if not self.store.acquire_lock(DIGEST_DELIVERY_LOCK, run_id, now):
            result = DeliveryResult("*", False, "skipped", "locked", now.date().isoformat(), run_id=run_id)
            self._append_result_audit(result)
            return [result]

        try:
            for client_id, preferences in self.store.all().items():
                delivered_for = now.date().isoformat()
                if not preferences.enabled:
                    result = DeliveryResult(client_id, False, "skipped", "disabled", delivered_for, run_id=run_id)
                    results.append(result)
                    self._append_result_audit(result)
                    continue
                if not preferences.email:
                    result = DeliveryResult(client_id, False, "skipped", "missing email", delivered_for, run_id=run_id)
                    results.append(result)
                    self._append_result_audit(result)
                    continue
                if preferences.last_delivered_for == delivered_for:
                    result = DeliveryResult(client_id, False, "skipped", "already delivered", delivered_for, preferences.email, run_id)
                    results.append(result)
                    self._append_result_audit(result)
                    continue
                if not delivery_time_reached(preferences.delivery_time, now):
                    result = DeliveryResult(client_id, False, "skipped", "not due", delivered_for, preferences.email, run_id)
                    results.append(result)
                    self._append_result_audit(result)
                    continue

                try:
                    payload = await self.build_digest(preferences)
                    digest_url = build_digest_url(preferences, self.public_base_url)
                    unsubscribe_url = build_unsubscribe_url(preferences, client_id, self.public_base_url)
                    result = self.sender.send(payload, preferences, digest_url, unsubscribe_url)
                    result.client_id = client_id
                    result.date = delivered_for
                    result.run_id = run_id
                    self.store.mark_delivered(client_id, delivered_for)
                except Exception as exc:
                    result = DeliveryResult(client_id, False, "error", str(exc), delivered_for, preferences.email, run_id)
                results.append(result)
                self._append_result_audit(result)
        finally:
            self.store.release_lock(DIGEST_DELIVERY_LOCK, run_id)
        return results

    async def send_test(self, preferences: DigestPreferences, client_id: str = DEFAULT_CLIENT_ID) -> DeliveryResult:
        run_id = new_run_id(prefix="digest-test")
        payload = await self.build_digest(preferences)
        result = self.sender.send(
            payload,
            preferences,
            build_digest_url(preferences, self.public_base_url),
            build_unsubscribe_url(preferences, client_id, self.public_base_url),
        )
        result.client_id = client_id
        result.date = datetime.now().date().isoformat()
        result.run_id = run_id
        self._append_result_audit(result, event="test_delivery")
        return result

    def _append_result_audit(self, result: DeliveryResult, event: str = "delivery") -> None:
        self.store.append_audit({
            "event": event,
            "client_id": result.client_id,
            "delivered": result.delivered,
            "mode": result.mode,
            "reason": result.reason,
            "date": result.date,
            "recipient": result.recipient,
            "run_id": result.run_id,
        })


def validate_preferences(data: dict, require_email: bool = True) -> DigestPreferences:
    enabled = bool(data.get("enabled", False))
    email = str(data.get("email", "")).strip()
    delivery_time = str(data.get("delivery_time") or DEFAULT_DELIVERY_TIME).strip()
    region = str(data.get("region") or DEFAULT_REGION_ID).strip()
    activity = normalize_activity(data.get("activity", "All"))
    risk = str(data.get("risk") or DEFAULT_RISK_TOLERANCE).strip().lower()
    density = str(data.get("density") or "full").strip().lower()
    last_delivered_for = data.get("last_delivered_for")

    get_region(region)
    if risk not in RISK_TOLERANCE_PROFILES:
        raise ValueError(f"Unsupported risk tolerance: {risk}")
    if density not in DENSITY_RATIOS:
        raise ValueError(f"Unsupported digest density: {density}")
    if not valid_delivery_time(delivery_time):
        raise ValueError("Delivery time must use HH:MM 24-hour format")
    if (enabled or require_email or email) and not valid_email(email):
        raise ValueError("A valid email address is required")

    return DigestPreferences(
        enabled=enabled,
        email=email,
        delivery_time=delivery_time,
        region=region,
        activity=activity,
        risk=risk,
        density=density,
        last_delivered_for=last_delivered_for,
    )


def normalize_activity(activity: str) -> str:
    value = str(activity or "All").strip().lower()
    if value == "kayak":
        return "Kayak"
    if value in {"fish", "fishing"}:
        return "Fish"
    return "All"


def valid_email(email: str) -> bool:
    return bool(fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email))


def valid_delivery_time(value: str) -> bool:
    if not fullmatch(r"\d{2}:\d{2}", value):
        return False
    hour, minute = [int(part) for part in value.split(":")]
    return 0 <= hour <= 23 and 0 <= minute <= 59


def delivery_time_reached(delivery_time: str, now: datetime) -> bool:
    hour, minute = [int(part) for part in delivery_time.split(":")]
    return (now.hour, now.minute) >= (hour, minute)


def digest_limit_for_density(region_id: str, density: str) -> int:
    region = get_region(region_id)
    ratio = DENSITY_RATIOS[density]
    return max(1, min(len(region["spot_ids"]), ceil(len(region["spot_ids"]) * ratio)))


def build_digest_params(preferences: DigestPreferences) -> dict:
    return {
        "region": preferences.region,
        "limit": digest_limit_for_density(preferences.region, preferences.density),
        "risk": preferences.risk,
        "activity": preferences.activity,
    }


def build_digest_url(preferences: DigestPreferences, public_base_url: str = "") -> str:
    params = build_digest_params(preferences)
    query = urlencode(params)
    return f"{public_base_url.rstrip('/')}/digest?{query}" if public_base_url else f"/digest?{query}"


def build_unsubscribe_url(preferences: DigestPreferences, client_id: str, public_base_url: str = "") -> str:
    query = urlencode({
        "client_id": client_id,
        "email": preferences.email,
        "token": sign_unsubscribe_token(client_id, preferences.email),
    })
    return f"{public_base_url.rstrip('/')}/unsubscribe?{query}" if public_base_url else f"/unsubscribe?{query}"


def sign_unsubscribe_token(client_id: str, email: str) -> str:
    message = f"{client_id}|{email.strip().lower()}".encode("utf-8")
    return hmac.new(digest_signing_secret(), message, hashlib.sha256).hexdigest()


def verify_unsubscribe_token(client_id: str, email: str, token: str) -> bool:
    expected = sign_unsubscribe_token(client_id, email)
    return hmac.compare_digest(expected, token or "")


def digest_signing_secret() -> bytes:
    return os.getenv("TIDEWINDOW_DIGEST_SIGNING_SECRET", "dev-tidewindow-digest-secret").encode("utf-8")


def new_run_id(now: datetime | None = None, prefix: str = "digest-run") -> str:
    timestamp = (now or datetime.now()).strftime("%Y%m%dT%H%M%S")
    return f"{prefix}-{timestamp}-{uuid.uuid4().hex[:8]}"


def digest_email_subject(payload: dict) -> str:
    region = payload.get("config", {}).get("region", {}).get("name", "TideWindow")
    activity = payload.get("activity", "All")
    return f"TideWindow Tomorrow's Best - {region} ({activity})"


def digest_email_body(payload: dict, digest_url: str = "", unsubscribe_url: str = "") -> str:
    body = payload.get("text", "TideWindow digest is available.")
    links = []
    if digest_url:
        links.append(f"Open digest: {digest_url}")
    if unsubscribe_url:
        links.append(f"Stop daily email: {unsubscribe_url}")
    if links:
        return f"{body}\n\n" + "\n".join(links)
    return body


def smtp_configured() -> bool:
    return bool(os.getenv("TIDEWINDOW_SMTP_HOST") and os.getenv("TIDEWINDOW_SMTP_FROM"))


def send_smtp_message(recipient: str, subject: str, body: str) -> None:
    host = os.environ["TIDEWINDOW_SMTP_HOST"]
    port = int(os.getenv("TIDEWINDOW_SMTP_PORT", "587"))
    username = os.getenv("TIDEWINDOW_SMTP_USER")
    password = os.getenv("TIDEWINDOW_SMTP_PASSWORD")
    sender = os.environ["TIDEWINDOW_SMTP_FROM"]
    use_tls = os.getenv("TIDEWINDOW_SMTP_TLS", "1") != "0"

    message = EmailMessage()
    message["From"] = sender
    message["To"] = recipient
    message["Subject"] = subject
    message.set_content(body)

    with smtplib.SMTP(host, port, timeout=15) as smtp:
        if use_tls:
            smtp.starttls()
        if username and password:
            smtp.login(username, password)
        smtp.send_message(message)
