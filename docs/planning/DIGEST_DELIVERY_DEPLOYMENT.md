# Digest Delivery Deployment Checklist

This checklist covers the hosted daily digest path: saved preferences, email delivery, unsubscribe links, audit review, and scheduled runs.

## Required Environment

```bash
TIDEWINDOW_PUBLIC_URL=https://your-app.example
TIDEWINDOW_DIGEST_SIGNING_SECRET=replace_with_a_long_random_secret
TIDEWINDOW_DIGEST_STORE=data/digest_preferences.json
TIDEWINDOW_DIGEST_OUTBOX=data/digest_outbox.json
```

`TIDEWINDOW_PUBLIC_URL` is used for the digest and unsubscribe links in email. Keep `TIDEWINDOW_DIGEST_SIGNING_SECRET` stable across deploys; changing it invalidates previously sent unsubscribe links.

## Email Provider Setup

Local development can use the JSON outbox without SMTP credentials. Hosted email delivery requires:

```bash
TIDEWINDOW_SMTP_HOST=smtp.example.com
TIDEWINDOW_SMTP_PORT=587
TIDEWINDOW_SMTP_USER=your_user
TIDEWINDOW_SMTP_PASSWORD=your_password
TIDEWINDOW_SMTP_FROM=digest@example.com
TIDEWINDOW_SMTP_TLS=1
```

Recommended provider checks:

- Use a verified sender/domain for `TIDEWINDOW_SMTP_FROM`.
- Confirm TLS and authentication settings with one saved preference and `POST /api/digest-deliveries/test`.
- Check spam placement before enabling scheduled delivery.
- Keep the local outbox path writable even in SMTP mode if you want fallback debugging artifacts.

## Scheduler Setup

Run due deliveries from one hosted scheduler, cron job, or platform worker:

```bash
curl -X POST "https://your-app.example/api/digest-deliveries/run?run_id=$(date +%Y%m%d%H%M%S)"
```

Safety notes:

- The runner skips preferences already delivered for the local calendar date.
- A short-lived `digest-delivery` lock prevents overlapping deployed workers from sending duplicates.
- `run_id` is optional but recommended because it makes audit review easier.
- Schedule the job at least once after the earliest supported delivery time. A 5-minute or 15-minute cadence is fine because already-delivered preferences are skipped.

## Unsubscribe Flow

Each email includes a signed `/unsubscribe` link with `client_id`, `email`, and `token`. The page posts to `/api/digest-preferences/unsubscribe`, disables the matching saved preference, and records an audit event.

Validation checklist:

- Save a digest preference from the dashboard.
- Send a test digest.
- Open the `Stop daily email` link from the outbox or email body.
- Confirm `/api/digest-preferences?client_id=...` returns `"enabled": false`.

## Audit Review

Recent events are available at:

```bash
curl "https://your-app.example/api/digest-deliveries/audit?limit=50"
```

Audit entries include event type, client id, recipient, delivered flag, mode, reason, date, and run id. Review this after provider setup, after scheduler activation, and after unsubscribe testing.
