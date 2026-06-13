import json
import os
import smtplib
from dataclasses import dataclass
from datetime import datetime
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

    def to_dict(self) -> dict:
        return {
            "client_id": self.client_id,
            "delivered": self.delivered,
            "mode": self.mode,
            "reason": self.reason,
            "date": self.date,
            "recipient": self.recipient,
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

    def _read(self) -> dict:
        if not self.path.exists():
            return {"subscriptions": {}}
        with self.path.open("r", encoding="utf-8") as file:
            return json.load(file)

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

    def send(self, payload: dict, preferences: DigestPreferences, digest_url: str = "") -> DeliveryResult:
        body = digest_email_body(payload, digest_url)
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

    async def run_due(self, now: datetime | None = None) -> list[DeliveryResult]:
        now = now or datetime.now()
        results: list[DeliveryResult] = []
        for client_id, preferences in self.store.all().items():
            if not preferences.enabled:
                results.append(DeliveryResult(client_id, False, "skipped", "disabled"))
                continue
            if not preferences.email:
                results.append(DeliveryResult(client_id, False, "skipped", "missing email"))
                continue
            delivered_for = now.date().isoformat()
            if preferences.last_delivered_for == delivered_for:
                results.append(DeliveryResult(client_id, False, "skipped", "already delivered", delivered_for))
                continue
            if not delivery_time_reached(preferences.delivery_time, now):
                results.append(DeliveryResult(client_id, False, "skipped", "not due", delivered_for))
                continue

            payload = await self.build_digest(preferences)
            digest_url = build_digest_url(preferences, self.public_base_url)
            result = self.sender.send(payload, preferences, digest_url)
            result.client_id = client_id
            result.date = delivered_for
            self.store.mark_delivered(client_id, delivered_for)
            results.append(result)
        return results

    async def send_test(self, preferences: DigestPreferences, client_id: str = DEFAULT_CLIENT_ID) -> DeliveryResult:
        payload = await self.build_digest(preferences)
        result = self.sender.send(payload, preferences, build_digest_url(preferences, self.public_base_url))
        result.client_id = client_id
        result.date = datetime.now().date().isoformat()
        return result


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


def digest_email_subject(payload: dict) -> str:
    region = payload.get("config", {}).get("region", {}).get("name", "TideWindow")
    activity = payload.get("activity", "All")
    return f"TideWindow Tomorrow's Best - {region} ({activity})"


def digest_email_body(payload: dict, digest_url: str = "") -> str:
    body = payload.get("text", "TideWindow digest is available.")
    if digest_url:
        return f"{body}\n\nOpen digest: {digest_url}"
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
