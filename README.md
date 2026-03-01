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
- protected onboarding flow
- results page generated from the saved intake

## Run locally

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python app.py
```

Then open `http://127.0.0.1:5000`.

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
