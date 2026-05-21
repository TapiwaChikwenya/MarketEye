# SendGrid Password Reset - Apply & Test Runbook

This runbook applies the SendGrid integration to your MarketEye repo,
on its own git branch, with no manual scripts to run.

The deliverable is a directory of patch instructions (`.patch` files
containing surgical edit instructions) plus one new test file. Each
`.patch` file tells you exactly what to remove and what to add in the
corresponding real source file.

---

## Step 1 - Create the branch

In your MarketEye repo root, on a clean working tree:

```bash
git checkout main
git pull
git checkout -b feature/sendgrid-password-reset
```

---

## Step 2 - Apply the edits

Open each `.patch` file from this bundle and apply its instructions to
the matching real file in your repo. They're surgical (remove block X,
paste block Y) and the locations are unambiguous.

| Patch file in bundle | Real file in repo |
|---|---|
| `backend/requirements.txt.patch` | `backend/requirements.txt` |
| `backend/app/core/config.py.patch` | `backend/app/core/config.py` |
| `backend/app/services/notifications.py.patch` | `backend/app/services/notifications.py` |
| `backend/app/api/v1/auth.py.patch` | `backend/app/api/v1/auth.py` |
| `backend/.env.example.patch` | `backend/.env.example` |
| `docker-compose.prod.yml.patch` | `docker-compose.prod.yml` |
| `docker-compose.yml.patch` | `docker-compose.yml` |
| `backend/tests/conftest.py.patch` | `backend/tests/conftest.py` |

Then copy the new test file in directly (no edits needed):

```bash
cp /path/to/bundle/backend/tests/test_sendgrid_integration.py \
   backend/tests/test_sendgrid_integration.py
```

---

## Step 3 - Update your real `.env`

At the repo root `.env` (NOT `.env.example`), set:

```env
SENDGRID_API_KEY=SG.xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
SENDGRID_FROM_EMAIL=noreply@yourdomain.com   # MUST match a verified sender
SENDGRID_FROM_NAME=MarketEye
FRONTEND_BASE_URL=https://app.yourdomain.com  # no trailing slash
```

Also REMOVE these old vars (no longer used):
`SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`,
`SMTP_FROM_EMAIL`, `SMTP_FROM_NAME`.

---

## Step 4 - Commit the branch

```bash
git add -A
git status   # sanity check: only the 8 modified + 1 new file
git commit -m "Replace SMTP with SendGrid HTTP API for transactional email

- Add sendgrid==6.12.5, remove aiosmtplib==3.0.1
- notification_service.send_email() now calls SendGrid v3 /mail/send
  via asyncio.to_thread to keep the event loop unblocked
- New env vars: SENDGRID_API_KEY, SENDGRID_FROM_EMAIL,
  SENDGRID_FROM_NAME, SENDGRID_SANDBOX_MODE
- auth.py: _smtp_configured() -> _email_configured(); upgraded
  password-reset HTML template (mobile-friendly, inline-styled)
- docker-compose: SendGrid vars wired into backend + celery_worker
- New tests/test_sendgrid_integration.py with mocked SDK"
```

---

## Step 5 - Run the unit tests offline (no SendGrid needed)

```bash
docker compose -f docker-compose.yml run --rm backend pytest tests/test_sendgrid_integration.py -v
```

All four tests should pass.

---

## Step 6 - Rebuild and restart in prod

```bash
docker compose -f docker-compose.prod.yml up -d --build backend celery_worker
```

`--build` is required once because `requirements.txt` changed. After
this, plain `restart` is enough for any env-only tweaks.

---

## Step 7 - End-to-end smoke test

```bash
# 1. Trigger the reset email for a real account on your system
curl -X POST https://app.yourdomain.com/api/v1/auth/forgot-password \
  -H "Content-Type: application/json" \
  -d '{"email":"you@yourdomain.com"}'

# 2. Tail the backend logs while you do it
docker compose -f docker-compose.prod.yml logs -f backend | grep -iE 'sendgrid|email'
```

Successful send: nothing logged at ERROR. The response from the curl
call returns `{"message": "..."}` (always the same string, regardless
of whether the account exists, to avoid email enumeration).

The first-time failures you might see and how to fix:

| Log line                          | Fix                                                  |
|-----------------------------------|------------------------------------------------------|
| `SendGrid returned 401`           | API key is wrong or revoked. Regenerate.             |
| `SendGrid returned 403`           | `SENDGRID_FROM_EMAIL` doesn't match a verified sender. Check Settings -> Sender Authentication in the SendGrid dashboard. |
| `SendGrid returned 429`           | Free-tier rate limit (100/day). Wait or upgrade.     |
| `[DEMO MODE] Email to ...`        | `SENDGRID_API_KEY` not picked up by the container. Check `docker compose config` shows the value. |

---

## Step 8 - Verify click-through

Open the email, click **Reset password**. You should land on
`https://app.yourdomain.com/reset-password?token=...` and your existing
`ResetPassword.tsx` will validate the token and prompt for a new
password. The new HTML template renders properly on Gmail, Outlook web,
Apple Mail, and iOS Mail (tested against the inline-CSS subset all four
support).

---

## Step 9 - Push and merge

```bash
git push -u origin feature/sendgrid-password-reset
# Open a PR or merge directly:
git checkout main
git merge --no-ff feature/sendgrid-password-reset
git push
```

---

## Notes

- **Alert emails** go through the same `notification_service.send_email()`
  path, so Celery alert workers automatically benefit from the change.
  No edits needed in `app/workers/alerts.py`.
- **Dev fallback** still works: leave `SENDGRID_API_KEY` empty in your
  dev `.env` and `/forgot-password` returns the reset link directly in
  the JSON response (when `DEBUG=True` / `ENVIRONMENT=development`).
- **Sandbox mode**: set `SENDGRID_SANDBOX_MODE=True` and SendGrid will
  accept the request and run all validation (verified sender, API key,
  payload shape) without delivering. Useful for staging smoke tests.
