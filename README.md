# Life Chiropractic Portal

Local Flask MVP that turns the `life-chiro-intake.html` and `life-chiro-results.html` prototypes into a working client portal with:

- email/password client accounts
- clinician/staff roles
- SQLite-backed intake persistence
- appointment-linked invite onboarding
- local password reset flow
- clinician private notes
- chiropractor-entered initial consultation and physical exam reports
- published care-plan/results sections in the client portal
- staff reminder center for appointment email/SMS outbox workflows
- patient self-service booking from the portal
- multi-location scheduling and location-aware availability templates
- appointment-linked billing and clinical note fields
- REST API endpoints for locations, availability, and appointments
- protected onboarding flow
- results page generated from the saved intake

## Run locally

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python app.py
```

Then open `http://127.0.0.1:5000`.

## Reminder delivery

The local build defaults to an outbox workflow for appointment reminders:

- `REMINDER_EMAIL_MODE=outbox`
- `REMINDER_SMS_MODE=outbox`

To enable direct email delivery, configure SMTP and set:

```bash
export REMINDER_EMAIL_MODE=smtp
export REMINDER_EMAIL_FROM="appointments@example.com"
export SMTP_HOST="smtp.example.com"
export SMTP_PORT=587
export SMTP_USERNAME="smtp-user"
export SMTP_PASSWORD="smtp-password"
```

## Scheduling API

Session-authenticated endpoints now include:

- `GET /api/locations`
- `GET /api/availability?date=YYYY-MM-DD&clinician_user_id=...&location_id=...&duration_minutes=...`
- `GET /api/appointments`
- `POST /api/appointments`

## Create a staff account

```bash
.venv/bin/python scripts/create_staff.py \
  --first-name "Dr" \
  --last-name "Stone" \
  --email "staff@example.com" \
  --password "staffpass123"
```

## Run tests

```bash
.venv/bin/python -m unittest discover -s tests -v
```
