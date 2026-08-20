"""Check TideWindow launch-readiness contracts against a running server.

This script is intentionally network-light and dependency-free. It verifies the
local app shell, PWA metadata, service worker shell inventory, health payload,
and optional admin readiness endpoint. Production-only checks such as SMTP can
be treated as warnings locally or required on a hosted environment.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any


DEFAULT_BASE_URL = "http://127.0.0.1:8000"


@dataclass
class CheckResult:
    label: str
    ok: bool
    detail: str = ""
    warning: bool = False


def request_text(base_url: str, path: str, token: str | None = None, timeout: int = 20) -> str:
    headers = {}
    if token:
        headers["X-TideWindow-Admin-Token"] = token
    request = urllib.request.Request(f"{base_url.rstrip('/')}{path}", headers=headers)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read().decode("utf-8")


def request_json(base_url: str, path: str, token: str | None = None, timeout: int = 20) -> dict[str, Any]:
    return json.loads(request_text(base_url, path, token=token, timeout=timeout))


def ok(label: str, detail: str = "") -> CheckResult:
    return CheckResult(label, True, detail)


def fail(label: str, detail: str = "") -> CheckResult:
    return CheckResult(label, False, detail)


def warn(label: str, detail: str = "") -> CheckResult:
    return CheckResult(label, True, detail, warning=True)


def check_health(base_url: str, timeout: int) -> list[CheckResult]:
    payload = request_json(base_url, "/health", timeout=timeout)
    results = [
        ok("health endpoint reachable") if payload.get("status") == "ok" else fail("health endpoint status", str(payload)),
        ok("regions configured", f"{payload.get('regions')} regions")
        if int(payload.get("regions") or 0) > 0
        else fail("regions configured", "expected at least one region"),
    ]
    provider_regions = payload.get("providers", {}).get("regions", [])
    results.append(
        ok("provider contexts exposed", f"{len(provider_regions)} provider contexts")
        if provider_regions
        else fail("provider contexts exposed", "missing providers.regions")
    )
    openweather = payload.get("providers", {}).get("openweather")
    if openweather == "configured":
        results.append(ok("OpenWeather configured"))
    else:
        results.append(warn("OpenWeather optional", "wind data will be fallback or missing without OPENWEATHER_API_KEY"))
    return results


def check_shell(base_url: str, timeout: int) -> list[CheckResult]:
    home = request_text(base_url, "/", timeout=timeout)
    digest = request_text(base_url, "/digest", timeout=timeout)
    admin = request_text(base_url, "/admin", timeout=timeout)
    unsubscribe = request_text(base_url, "/unsubscribe", timeout=timeout)

    checks = [
        ("dashboard shell", home, ("TideWindow", "rel=\"manifest\"", "apple-mobile-web-app-capable")),
        ("digest shell", digest, ("TideWindow Tomorrow's Best", "rel=\"manifest\"")),
        ("admin shell", admin, ("TideWindow Admin", "/static/admin.js")),
        ("unsubscribe shell", unsubscribe, ("TideWindow Daily Email", "/static/unsubscribe.js")),
    ]
    results: list[CheckResult] = []
    for label, text, needles in checks:
        missing = [needle for needle in needles if needle not in text]
        results.append(ok(label) if not missing else fail(label, f"missing: {', '.join(missing)}"))
    return results


def check_manifest(base_url: str, timeout: int) -> list[CheckResult]:
    manifest = request_json(base_url, "/static/manifest.webmanifest", timeout=timeout)
    results = [
        ok("manifest name", manifest.get("name", ""))
        if manifest.get("name") == "TideWindow"
        else fail("manifest name", str(manifest.get("name"))),
        ok("manifest display", manifest.get("display", ""))
        if manifest.get("display") == "standalone"
        else fail("manifest display", str(manifest.get("display"))),
        ok("manifest scope", manifest.get("scope", ""))
        if manifest.get("scope") == "/"
        else fail("manifest scope", str(manifest.get("scope"))),
    ]
    icons = manifest.get("icons", [])
    has_maskable = any("maskable" in icon.get("purpose", "") for icon in icons)
    results.append(ok("manifest icon", f"{len(icons)} icons") if icons and has_maskable else fail("manifest icon", "missing maskable icon"))
    return results


def check_service_worker(base_url: str, timeout: int) -> list[CheckResult]:
    service_worker = request_text(base_url, "/service-worker.js", timeout=timeout)
    required = (
        'const CACHE = "tidewindow-',
        '"/"',
        '"/digest"',
        '"/unsubscribe"',
        '"/admin"',
        '"/static/app.js"',
        '"/static/digest.js"',
        '"/static/unsubscribe.js"',
        '"/static/admin.js"',
        '"/static/manifest.webmanifest"',
        '"/static/icon.svg"',
        '"/api/digest-admin"',
    )
    missing = [item for item in required if item not in service_worker]
    return [ok("service worker shell inventory") if not missing else fail("service worker shell inventory", f"missing: {', '.join(missing)}")]


def check_admin(base_url: str, token: str | None, timeout: int, require_email_provider: bool) -> list[CheckResult]:
    if not token:
        return [warn("admin readiness skipped", "set TIDEWINDOW_ADMIN_TOKEN or pass --admin-token")]

    payload = request_json(base_url, "/api/digest-admin?limit=20", token=token, timeout=timeout)
    readiness = payload.get("readiness", {})
    health = payload.get("health", {})
    checks = readiness.get("checks", [])
    failed_checks = [check.get("id") for check in checks if not check.get("ok")]

    results = [
        ok("admin endpoint authorized"),
        ok("admin health payload") if "total_preferences" in health else fail("admin health payload", str(health)),
        ok("admin readiness payload") if checks else fail("admin readiness payload", str(readiness)),
    ]
    hosted_config_failures = [
        item
        for item in failed_checks
        if item in {"public_url", "signing_secret", "scheduler_token", "email_provider"}
    ]
    storage_failures = [
        item
        for item in failed_checks
        if item not in {"public_url", "signing_secret", "scheduler_token", "email_provider"}
    ]
    if hosted_config_failures:
        message = ", ".join(hosted_config_failures)
        results.append(
            fail("hosted delivery readiness", message)
            if require_email_provider
            else warn("hosted delivery readiness", message)
        )
    elif checks:
        results.append(ok("hosted delivery readiness"))
    results.append(ok("local admin/storage readiness") if not storage_failures else fail("local admin/storage readiness", ", ".join(storage_failures)))
    return results


def print_results(results: list[CheckResult]) -> None:
    for result in results:
        prefix = "WARN" if result.warning else "PASS" if result.ok else "FAIL"
        detail = f" - {result.detail}" if result.detail else ""
        print(f"{prefix}: {result.label}{detail}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Check TideWindow launch-readiness contracts.")
    parser.add_argument("base_url", nargs="?", default=DEFAULT_BASE_URL, help=f"server URL, default {DEFAULT_BASE_URL}")
    parser.add_argument("--admin-token", default=os.getenv("TIDEWINDOW_ADMIN_TOKEN"), help="admin token for /api/digest-admin")
    parser.add_argument("--require-email-provider", action="store_true", help="fail when SMTP/email provider readiness is missing")
    parser.add_argument("--timeout", type=int, default=20, help="request timeout in seconds")
    args = parser.parse_args()

    all_results: list[CheckResult] = []
    try:
        all_results.extend(check_health(args.base_url, args.timeout))
        all_results.extend(check_shell(args.base_url, args.timeout))
        all_results.extend(check_manifest(args.base_url, args.timeout))
        all_results.extend(check_service_worker(args.base_url, args.timeout))
        all_results.extend(check_admin(args.base_url, args.admin_token, args.timeout, args.require_email_provider))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        print(f"FAIL: unable to complete launch-readiness check - {exc}")
        return 1

    print_results(all_results)
    hard_failures = [result for result in all_results if not result.ok]
    warnings = [result for result in all_results if result.warning]
    if hard_failures:
        print(f"launch readiness failed: {len(hard_failures)} hard failure(s), {len(warnings)} warning(s)")
        return 1
    print(f"launch readiness passed with {len(warnings)} warning(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
