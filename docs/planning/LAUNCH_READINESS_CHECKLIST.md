# Launch Readiness Checklist

_Last updated: 2026-08-19._

This checklist turns the remaining pre-launch work into an executable pass. Local simulation has already covered the protected scheduler/admin/PWA routes; the remaining risk is mostly physical-device behavior and hosted delivery configuration.

## Goal

TideWindow is launch-ready when a user can install the app, reopen it offline, save a daily digest preference, receive the next scheduled digest through the hosted email provider, unsubscribe cleanly, and let the operator confirm those events from `/admin`.

## Local Verification

Run the app locally:

```bash
.venv/bin/uvicorn web_app:app --reload
```

Run the launch checker:

```bash
.venv/bin/python scripts/check_launch_readiness.py http://127.0.0.1:8000
```

With admin readiness enabled:

```bash
TIDEWINDOW_ADMIN_TOKEN=replace_with_a_long_random_admin_token \
  .venv/bin/python scripts/check_launch_readiness.py \
  http://127.0.0.1:8000 \
  --admin-token replace_with_a_long_random_admin_token
```

Expected local result:

- App health, shell routes, manifest, service worker inventory, and admin contracts pass.
- OpenWeather can warn if `OPENWEATHER_API_KEY` is not set.
- Hosted delivery config can warn locally because JSON outbox delivery is valid for development.

## Hosted Delivery Activation

Before enabling hosted cron:

- Set `TIDEWINDOW_PUBLIC_URL` to the production origin.
- Set stable, long random values for `TIDEWINDOW_DIGEST_SIGNING_SECRET`, `TIDEWINDOW_ADMIN_TOKEN`, and `TIDEWINDOW_SCHEDULER_TOKEN`.
- Point `TIDEWINDOW_DIGEST_STORE` and `TIDEWINDOW_DIGEST_OUTBOX` at persistent storage.
- Configure SMTP with verified sender/domain credentials.
- Run one test digest from `/admin`.
- Confirm the received email has a working digest link and signed unsubscribe link.

Run the hosted checker with production email required:

```bash
.venv/bin/python scripts/check_launch_readiness.py \
  https://your-app.example \
  --admin-token "$TIDEWINDOW_ADMIN_TOKEN" \
  --require-email-provider
```

Enable the scheduler only after the hosted checker passes.

## Scheduler Activation

Use one hosted cron/platform scheduler to call:

```bash
curl -X POST "https://your-app.example/api/digest-deliveries/run?run_id=$(date +%Y%m%d%H%M%S)&scheduler_token=$TIDEWINDOW_SCHEDULER_TOKEN"
```

After the first scheduled run:

- Confirm `/admin` shows the expected `last_run_id`.
- Confirm delivered/skipped/error counts match the saved preferences.
- Confirm audit rows include test delivery, scheduled delivery, and unsubscribe events.
- Confirm repeated scheduler calls do not duplicate the same day's delivery.

## Physical-Device PWA QA

Run this on real devices against the hosted origin:

- iPhone Safari: Add to Home Screen, launch from icon, verify title/icon, then reopen after killing the app.
- Android Chrome: verify install prompt or manual install, launch from icon, verify title/icon, then reopen after killing the app.
- Offline: load the app once, enable airplane mode, reopen from the installed icon, and confirm the shell loads.
- Offline map: confirm the app remains understandable when third-party map tiles are unavailable.
- Upgrade: install once, deploy a cache-bumped build, reopen, and confirm the new shell/assets load.

## Launch Exit Criteria

- Hosted checker passes with `--require-email-provider`.
- Physical-device PWA QA passes on at least one iOS and one Android device.
- First live scheduled digest is delivered.
- Signed unsubscribe disables the saved preference and appears in audit.
- `/admin` shows no unexpected delivery errors after the first scheduled run.
