from __future__ import annotations

import sqlite3

from flask import current_app, g


SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE COLLATE NOCASE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'client',
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS intake_submissions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL UNIQUE,
    status TEXT NOT NULL DEFAULT 'draft',
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS intake_questionnaire_scores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    questionnaire_id TEXT NOT NULL,
    display_name TEXT NOT NULL DEFAULT '',
    questionnaire_version TEXT NOT NULL DEFAULT '',
    response_model TEXT NOT NULL DEFAULT '',
    raw_score REAL,
    percent_score REAL,
    interpretation TEXT NOT NULL DEFAULT '',
    completed_at TEXT,
    responses_json TEXT NOT NULL DEFAULT '[]',
    schema_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE (user_id, questionnaire_id),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_intake_questionnaire_scores_user ON intake_questionnaire_scores(user_id);

CREATE TABLE IF NOT EXISTS invitations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT NOT NULL COLLATE NOCASE,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    appointment_at TEXT,
    note TEXT NOT NULL DEFAULT '',
    token TEXT NOT NULL UNIQUE,
    expires_at TEXT NOT NULL,
    created_at TEXT NOT NULL,
    accepted_at TEXT,
    created_by INTEGER,
    accepted_user_id INTEGER,
    FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL,
    FOREIGN KEY (accepted_user_id) REFERENCES users(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_invitations_email ON invitations(email);
CREATE INDEX IF NOT EXISTS idx_invitations_token ON invitations(token);

CREATE TABLE IF NOT EXISTS appointment_slot_holds (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    invitation_id INTEGER,
    lead_id INTEGER,
    clinician_user_id INTEGER NOT NULL,
    location_id INTEGER,
    service_id INTEGER,
    appointment_type TEXT NOT NULL DEFAULT 'initial_consult',
    starts_at TEXT NOT NULL,
    ends_at TEXT,
    status TEXT NOT NULL DEFAULT 'active',
    expires_at TEXT NOT NULL,
    consumed_appointment_id INTEGER,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (invitation_id) REFERENCES invitations(id) ON DELETE SET NULL,
    FOREIGN KEY (lead_id) REFERENCES leads(id) ON DELETE SET NULL,
    FOREIGN KEY (clinician_user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (location_id) REFERENCES locations(id) ON DELETE SET NULL,
    FOREIGN KEY (service_id) REFERENCES appointment_services(id) ON DELETE SET NULL,
    FOREIGN KEY (consumed_appointment_id) REFERENCES appointments(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_appointment_slot_holds_clinician_date ON appointment_slot_holds(clinician_user_id, starts_at);
CREATE INDEX IF NOT EXISTS idx_appointment_slot_holds_status_expires ON appointment_slot_holds(status, expires_at);
CREATE INDEX IF NOT EXISTS idx_appointment_slot_holds_lead ON appointment_slot_holds(lead_id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_appointment_slot_holds_invitation_unique ON appointment_slot_holds(invitation_id);

CREATE TABLE IF NOT EXISTS leads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    email TEXT NOT NULL COLLATE NOCASE,
    phone TEXT NOT NULL DEFAULT '',
    source TEXT NOT NULL DEFAULT 'website',
    status TEXT NOT NULL DEFAULT 'new',
    preferred_service_id INTEGER,
    preferred_location_id INTEGER,
    preferred_clinician_user_id INTEGER,
    requested_starts_at TEXT,
    reason TEXT NOT NULL DEFAULT '',
    notes TEXT NOT NULL DEFAULT '',
    invitation_id INTEGER,
    converted_user_id INTEGER,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (preferred_service_id) REFERENCES appointment_services(id) ON DELETE SET NULL,
    FOREIGN KEY (preferred_location_id) REFERENCES locations(id) ON DELETE SET NULL,
    FOREIGN KEY (preferred_clinician_user_id) REFERENCES users(id) ON DELETE SET NULL,
    FOREIGN KEY (invitation_id) REFERENCES invitations(id) ON DELETE SET NULL,
    FOREIGN KEY (converted_user_id) REFERENCES users(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_leads_status_created ON leads(status, created_at);
CREATE INDEX IF NOT EXISTS idx_leads_email ON leads(email);
CREATE INDEX IF NOT EXISTS idx_leads_requested_starts_at ON leads(requested_starts_at);

CREATE TABLE IF NOT EXISTS password_reset_tokens (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    token TEXT NOT NULL UNIQUE,
    expires_at TEXT NOT NULL,
    created_at TEXT NOT NULL,
    used_at TEXT,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_password_reset_tokens_token ON password_reset_tokens(token);

CREATE TABLE IF NOT EXISTS clinician_notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_user_id INTEGER NOT NULL UNIQUE,
    clinician_user_id INTEGER,
    exam_findings TEXT NOT NULL DEFAULT '',
    assessment TEXT NOT NULL DEFAULT '',
    care_plan TEXT NOT NULL DEFAULT '',
    internal_notes TEXT NOT NULL DEFAULT '',
    next_visit_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (patient_user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (clinician_user_id) REFERENCES users(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS practitioner_journal_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    clinician_user_id INTEGER NOT NULL,
    entry_date TEXT NOT NULL,
    title TEXT NOT NULL DEFAULT '',
    reflection TEXT NOT NULL DEFAULT '',
    lesson_learned TEXT NOT NULL DEFAULT '',
    next_step TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (clinician_user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_practitioner_journal_entries_clinician ON practitioner_journal_entries(clinician_user_id);

CREATE TABLE IF NOT EXISTS practitioner_learning_progress (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    clinician_user_id INTEGER NOT NULL,
    topic_slug TEXT NOT NULL,
    is_completed INTEGER NOT NULL DEFAULT 0,
    completed_at TEXT,
    reflection TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE (clinician_user_id, topic_slug),
    FOREIGN KEY (clinician_user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_practitioner_learning_progress_clinician ON practitioner_learning_progress(clinician_user_id);
CREATE INDEX IF NOT EXISTS idx_practitioner_learning_progress_slug ON practitioner_learning_progress(topic_slug);

CREATE TABLE IF NOT EXISTS patient_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_user_id INTEGER NOT NULL,
    sender_user_id INTEGER NOT NULL,
    sender_role TEXT NOT NULL,
    topic TEXT NOT NULL DEFAULT 'appointment',
    body TEXT NOT NULL DEFAULT '',
    read_by_staff_at TEXT,
    read_by_patient_at TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (patient_user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (sender_user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_patient_messages_patient ON patient_messages(patient_user_id, created_at);
CREATE INDEX IF NOT EXISTS idx_patient_messages_unread_staff ON patient_messages(patient_user_id, read_by_staff_at);
CREATE INDEX IF NOT EXISTS idx_patient_messages_unread_patient ON patient_messages(patient_user_id, read_by_patient_at);

CREATE TABLE IF NOT EXISTS locations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    slug TEXT NOT NULL UNIQUE,
    address TEXT NOT NULL DEFAULT '',
    phone TEXT NOT NULL DEFAULT '',
    timezone TEXT NOT NULL DEFAULT 'Europe/London',
    active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_locations_slug ON locations(slug);

CREATE TABLE IF NOT EXISTS appointment_services (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    service_key TEXT NOT NULL UNIQUE,
    label TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    appointment_type TEXT NOT NULL DEFAULT 'care_plan',
    duration_minutes INTEGER NOT NULL DEFAULT 30,
    buffer_before_minutes INTEGER NOT NULL DEFAULT 0,
    buffer_after_minutes INTEGER NOT NULL DEFAULT 0,
    requires_payment INTEGER NOT NULL DEFAULT 0,
    price_amount REAL,
    currency TEXT NOT NULL DEFAULT 'GBP',
    min_notice_minutes INTEGER NOT NULL DEFAULT 0,
    max_bookings_per_day INTEGER,
    routing_mode TEXT NOT NULL DEFAULT 'specific_clinician',
    active INTEGER NOT NULL DEFAULT 1,
    display_order INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_appointment_services_active ON appointment_services(active);

CREATE TABLE IF NOT EXISTS appointments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_user_id INTEGER NOT NULL,
    clinician_user_id INTEGER,
    location_id INTEGER,
    service_id INTEGER,
    appointment_type TEXT NOT NULL DEFAULT 'initial_consult',
    status TEXT NOT NULL DEFAULT 'scheduled',
    starts_at TEXT NOT NULL,
    ends_at TEXT,
    source_invitation_id INTEGER,
    note TEXT NOT NULL DEFAULT '',
    patient_details TEXT NOT NULL DEFAULT '',
    clinical_note TEXT NOT NULL DEFAULT '',
    billing_status TEXT NOT NULL DEFAULT 'pending',
    billing_code TEXT NOT NULL DEFAULT '',
    billing_amount REAL,
    requires_payment INTEGER NOT NULL DEFAULT 0,
    payment_status TEXT NOT NULL DEFAULT 'not_required',
    payment_amount REAL,
    booking_channel TEXT NOT NULL DEFAULT 'portal',
    service_label_snapshot TEXT NOT NULL DEFAULT '',
    policy_snapshot_json TEXT NOT NULL DEFAULT '{}',
    booking_source TEXT NOT NULL DEFAULT 'staff_portal',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (patient_user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (clinician_user_id) REFERENCES users(id) ON DELETE SET NULL,
    FOREIGN KEY (location_id) REFERENCES locations(id) ON DELETE SET NULL,
    FOREIGN KEY (service_id) REFERENCES appointment_services(id) ON DELETE SET NULL,
    FOREIGN KEY (source_invitation_id) REFERENCES invitations(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_appointments_patient ON appointments(patient_user_id);
CREATE INDEX IF NOT EXISTS idx_appointments_starts_at ON appointments(starts_at);

CREATE TABLE IF NOT EXISTS care_plans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_user_id INTEGER NOT NULL,
    clinician_user_id INTEGER,
    location_id INTEGER,
    service_id INTEGER,
    title TEXT NOT NULL DEFAULT '',
    frequency_per_week INTEGER NOT NULL DEFAULT 1,
    duration_weeks INTEGER NOT NULL DEFAULT 6,
    total_visits INTEGER NOT NULL DEFAULT 0,
    midpoint_visit_number INTEGER NOT NULL DEFAULT 0,
    booking_mode TEXT NOT NULL DEFAULT 'all',
    start_date TEXT NOT NULL,
    start_slot TEXT,
    status TEXT NOT NULL DEFAULT 'active',
    patient_details TEXT NOT NULL DEFAULT '',
    note TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (patient_user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (clinician_user_id) REFERENCES users(id) ON DELETE SET NULL,
    FOREIGN KEY (location_id) REFERENCES locations(id) ON DELETE SET NULL,
    FOREIGN KEY (service_id) REFERENCES appointment_services(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_care_plans_patient ON care_plans(patient_user_id, status, id);

CREATE TABLE IF NOT EXISTS care_plan_visits (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    care_plan_id INTEGER NOT NULL,
    visit_number INTEGER NOT NULL,
    visit_kind TEXT NOT NULL DEFAULT 'follow_up',
    label TEXT NOT NULL DEFAULT '',
    suggested_date TEXT NOT NULL,
    suggested_starts_at TEXT,
    duration_minutes INTEGER NOT NULL DEFAULT 15,
    fee_amount REAL,
    status TEXT NOT NULL DEFAULT 'unbooked',
    booked INTEGER NOT NULL DEFAULT 0,
    appointment_id INTEGER,
    patient_details TEXT NOT NULL DEFAULT '',
    note TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE (care_plan_id, visit_number),
    FOREIGN KEY (care_plan_id) REFERENCES care_plans(id) ON DELETE CASCADE,
    FOREIGN KEY (appointment_id) REFERENCES appointments(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_care_plan_visits_plan ON care_plan_visits(care_plan_id, visit_number);
CREATE INDEX IF NOT EXISTS idx_care_plan_visits_appointment ON care_plan_visits(appointment_id);

CREATE TABLE IF NOT EXISTS appointment_reminders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    appointment_id INTEGER NOT NULL,
    patient_user_id INTEGER NOT NULL,
    clinician_user_id INTEGER,
    channel TEXT NOT NULL,
    delivery_mode TEXT NOT NULL DEFAULT 'outbox',
    reminder_bucket TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'logged',
    recipient TEXT NOT NULL DEFAULT '',
    subject TEXT NOT NULL DEFAULT '',
    message TEXT NOT NULL DEFAULT '',
    error_message TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    sent_at TEXT,
    FOREIGN KEY (appointment_id) REFERENCES appointments(id) ON DELETE CASCADE,
    FOREIGN KEY (patient_user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (clinician_user_id) REFERENCES users(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_appointment_reminders_appointment ON appointment_reminders(appointment_id);
CREATE INDEX IF NOT EXISTS idx_appointment_reminders_sent_at ON appointment_reminders(sent_at);

CREATE TABLE IF NOT EXISTS booking_webhook_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type TEXT NOT NULL,
    appointment_id INTEGER,
    patient_user_id INTEGER,
    payload_json TEXT NOT NULL DEFAULT '{}',
    delivery_status TEXT NOT NULL DEFAULT 'pending',
    created_at TEXT NOT NULL,
    processed_at TEXT,
    error_message TEXT NOT NULL DEFAULT '',
    FOREIGN KEY (appointment_id) REFERENCES appointments(id) ON DELETE CASCADE,
    FOREIGN KEY (patient_user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_booking_webhook_events_created ON booking_webhook_events(created_at);

CREATE TABLE IF NOT EXISTS appointment_soap_notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    appointment_id INTEGER NOT NULL UNIQUE,
    patient_user_id INTEGER NOT NULL,
    clinician_user_id INTEGER,
    subjective TEXT NOT NULL DEFAULT '',
    objective TEXT NOT NULL DEFAULT '',
    assessment TEXT NOT NULL DEFAULT '',
    plan TEXT NOT NULL DEFAULT '',
    spine_findings_json TEXT NOT NULL DEFAULT '{"left":[],"right":[]}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (appointment_id) REFERENCES appointments(id) ON DELETE CASCADE,
    FOREIGN KEY (patient_user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (clinician_user_id) REFERENCES users(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_appointment_soap_notes_appointment ON appointment_soap_notes(appointment_id);
CREATE INDEX IF NOT EXISTS idx_appointment_soap_notes_clinician ON appointment_soap_notes(clinician_user_id);

CREATE TABLE IF NOT EXISTS schedule_windows (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    clinician_user_id INTEGER,
    location_id INTEGER,
    weekday INTEGER NOT NULL,
    window_type TEXT NOT NULL DEFAULT 'shift',
    starts_time TEXT NOT NULL,
    ends_time TEXT NOT NULL,
    label TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (clinician_user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (location_id) REFERENCES locations(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_schedule_windows_weekday ON schedule_windows(weekday);
CREATE INDEX IF NOT EXISTS idx_schedule_windows_clinician ON schedule_windows(clinician_user_id);

CREATE TABLE IF NOT EXISTS visit_reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_user_id INTEGER NOT NULL,
    clinician_user_id INTEGER,
    visit_kind TEXT NOT NULL DEFAULT 'initial_consult',
    report_status TEXT NOT NULL DEFAULT 'draft',
    visit_date TEXT NOT NULL,
    assessment_payload_json TEXT NOT NULL DEFAULT '{}',
    rapport_notes TEXT NOT NULL DEFAULT '',
    subjective_summary TEXT NOT NULL DEFAULT '',
    complaint_duration TEXT NOT NULL DEFAULT '',
    first_notice TEXT NOT NULL DEFAULT '',
    complaint_frequency TEXT NOT NULL DEFAULT '',
    pain_worst INTEGER,
    pain_quality TEXT NOT NULL DEFAULT '',
    radiates INTEGER NOT NULL DEFAULT 0,
    radiation_start TEXT NOT NULL DEFAULT '',
    radiation_end TEXT NOT NULL DEFAULT '',
    accident_history TEXT NOT NULL DEFAULT '',
    microtrauma_history TEXT NOT NULL DEFAULT '',
    prior_treatment_history TEXT NOT NULL DEFAULT '',
    symptom_trend TEXT NOT NULL DEFAULT '',
    adl_impacts TEXT NOT NULL DEFAULT '',
    medical_family_history_review TEXT NOT NULL DEFAULT '',
    commitment_score INTEGER,
    obstacles_to_care TEXT NOT NULL DEFAULT '',
    education_summary TEXT NOT NULL DEFAULT '',
    posture_findings TEXT NOT NULL DEFAULT '',
    forward_head_inches REAL,
    shoulders_level TEXT NOT NULL DEFAULT '',
    hips_level TEXT NOT NULL DEFAULT '',
    range_of_motion TEXT NOT NULL DEFAULT '',
    single_leg_balance_left_seconds INTEGER,
    single_leg_balance_right_seconds INTEGER,
    heel_to_toe_walk TEXT NOT NULL DEFAULT '',
    marching_test TEXT NOT NULL DEFAULT '',
    orthopedic_findings TEXT NOT NULL DEFAULT '',
    neuro_findings TEXT NOT NULL DEFAULT '',
    palpation_findings TEXT NOT NULL DEFAULT '',
    xray_recommended INTEGER NOT NULL DEFAULT 0,
    xray_status TEXT NOT NULL DEFAULT '',
    xray_regions TEXT NOT NULL DEFAULT '',
    imaging_review TEXT NOT NULL DEFAULT '',
    assessment TEXT NOT NULL DEFAULT '',
    diagnosis TEXT NOT NULL DEFAULT '',
    care_plan TEXT NOT NULL DEFAULT '',
    home_care TEXT NOT NULL DEFAULT '',
    follow_up_plan TEXT NOT NULL DEFAULT '',
    wrap_up_notes TEXT NOT NULL DEFAULT '',
    triangle_handoff TEXT NOT NULL DEFAULT '',
    patient_summary TEXT NOT NULL DEFAULT '',
    patient_key_findings TEXT NOT NULL DEFAULT '',
    patient_recommendations TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE (patient_user_id, visit_kind),
    FOREIGN KEY (patient_user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (clinician_user_id) REFERENCES users(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_visit_reports_patient ON visit_reports(patient_user_id);

CREATE TABLE IF NOT EXISTS app_settings (
    setting_key TEXT PRIMARY KEY,
    setting_value TEXT NOT NULL DEFAULT '',
    updated_at TEXT NOT NULL
);
"""


def _table_columns(db: sqlite3.Connection, table_name: str) -> set[str]:
    return {row["name"] for row in db.execute(f"PRAGMA table_info({table_name})").fetchall()}


def _ensure_column(db: sqlite3.Connection, table_name: str, column_name: str, definition: str) -> None:
    if column_name not in _table_columns(db, table_name):
        db.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {definition}")


def _backfill_accepted_invitation_appointments(db: sqlite3.Connection) -> None:
    rows = db.execute(
        """
        SELECT id, accepted_user_id, created_by, appointment_at, note, created_at
        FROM invitations
        WHERE accepted_user_id IS NOT NULL AND appointment_at IS NOT NULL
        """
    ).fetchall()
    for row in rows:
        existing = db.execute(
            """
            SELECT id
            FROM appointments
            WHERE source_invitation_id = ?
               OR (
                    patient_user_id = ?
                AND appointment_type = 'initial_consult'
                AND starts_at = ?
               )
            LIMIT 1
            """,
            (row["id"], row["accepted_user_id"], row["appointment_at"]),
        ).fetchone()
        if existing is not None:
            continue

        note = (row["note"] or "").strip()
        if note:
            note = f"Imported from invite: {note}"

        db.execute(
            """
            INSERT INTO appointments (
                patient_user_id,
                clinician_user_id,
                appointment_type,
                status,
                starts_at,
                source_invitation_id,
                note,
                created_at,
                updated_at
            )
            VALUES (?, ?, 'initial_consult', 'scheduled', ?, ?, ?, ?, ?)
            """,
            (
                row["accepted_user_id"],
                row["created_by"],
                row["appointment_at"],
                row["id"],
                note,
                row["created_at"],
                row["created_at"],
            ),
        )


def _seed_default_locations(db: sqlite3.Connection) -> int:
    existing = db.execute(
        "SELECT id FROM locations WHERE slug = 'main-clinic' LIMIT 1"
    ).fetchone()
    if existing is not None:
        return existing["id"]

    db.execute(
        """
        INSERT INTO locations (name, slug, address, phone, timezone, active, created_at, updated_at)
        VALUES ('Main Clinic', 'main-clinic', '123 Wellness Way', '555-0101', 'Europe/London', 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """
    )
    return db.execute("SELECT id FROM locations WHERE slug = 'main-clinic' LIMIT 1").fetchone()["id"]


def _seed_default_schedule_windows(db: sqlite3.Connection) -> None:
    existing = db.execute("SELECT COUNT(*) AS count FROM schedule_windows").fetchone()
    if existing["count"]:
        return

    default_location_id = _seed_default_locations(db)
    rows = []
    for weekday in range(0, 7):
        rows.append((None, default_location_id, weekday, "shift", "09:00", "17:00", "Clinic shift"))
        rows.append((None, default_location_id, weekday, "downtime", "12:00", "13:00", "Lunch downtime"))

    db.executemany(
        """
        INSERT INTO schedule_windows (
            clinician_user_id,
            location_id,
            weekday,
            window_type,
            starts_time,
            ends_time,
            label,
            created_at,
            updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """,
        rows,
    )


def _seed_default_appointment_services(db: sqlite3.Connection) -> None:
    defaults = [
        (
            "new_patient_30",
            "New Patient Visit",
            "Comprehensive first appointment with exam and consultation.",
            "initial_consult",
            30,
            10,
            10,
            1,
            95.0,
            "GBP",
            180,
            8,
            "specific_clinician",
            1,
            10,
        ),
        (
            "report_of_findings_30",
            "Report of Findings",
            "Review findings, explain diagnosis, and confirm care plan.",
            "report_of_findings",
            30,
            5,
            10,
            0,
            None,
            "GBP",
            120,
            10,
            "specific_clinician",
            1,
            20,
        ),
        (
            "follow_up_15",
            "Follow-up Visit",
            "Standard adjustment and progress check.",
            "care_plan",
            15,
            5,
            5,
            0,
            None,
            "GBP",
            60,
            16,
            "specific_clinician",
            1,
            30,
        ),
        (
            "team_adjustment_15",
            "Team Adjustment (Any Chiropractor)",
            "Fast follow-up visit routed to any available chiropractor.",
            "care_plan",
            15,
            5,
            5,
            0,
            None,
            "GBP",
            60,
            24,
            "team_round_robin",
            1,
            40,
        ),
    ]

    db.executemany(
        """
        INSERT INTO appointment_services (
            service_key,
            label,
            description,
            appointment_type,
            duration_minutes,
            buffer_before_minutes,
            buffer_after_minutes,
            requires_payment,
            price_amount,
            currency,
            min_notice_minutes,
            max_bookings_per_day,
            routing_mode,
            active,
            display_order,
            created_at,
            updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        ON CONFLICT(service_key) DO NOTHING
        """,
        defaults,
    )


def _seed_default_app_settings(db: sqlite3.Connection) -> None:
    active_clinician_count = db.execute(
        """
        SELECT COUNT(*) AS count
        FROM users
        WHERE role = 'clinician' AND COALESCE(is_active, 1) = 1
        """
    ).fetchone()["count"]
    defaults = {
        "calendar_time_format": "24h",
        "calendar_slot_increment_minutes": "15",
        "booking_search_window_days": "21",
        "max_active_chiropractors": str(max(active_clinician_count, 3)),
    }
    db.executemany(
        """
        INSERT INTO app_settings (setting_key, setting_value, updated_at)
        VALUES (?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(setting_key) DO NOTHING
        """,
        [(setting_key, setting_value) for setting_key, setting_value in defaults.items()],
    )


def _backfill_appointment_service_defaults(db: sqlite3.Connection) -> None:
    service_map = {
        "initial_consult": "new_patient_30",
        "report_of_findings": "report_of_findings_30",
        "care_plan": "follow_up_15",
    }
    for appointment_type, service_key in service_map.items():
        service_row = db.execute(
            """
            SELECT id, label, requires_payment, price_amount
            FROM appointment_services
            WHERE service_key = ?
            LIMIT 1
            """,
            (service_key,),
        ).fetchone()
        if service_row is None:
            continue

        db.execute(
            """
            UPDATE appointments
            SET service_id = COALESCE(service_id, ?),
                service_label_snapshot = CASE
                    WHEN TRIM(COALESCE(service_label_snapshot, '')) = '' THEN ?
                    ELSE service_label_snapshot
                END,
                requires_payment = CASE
                    WHEN requires_payment IS NULL OR requires_payment = 0 THEN ?
                    ELSE requires_payment
                END,
                payment_amount = CASE
                    WHEN payment_amount IS NULL AND ? IS NOT NULL THEN ?
                    ELSE payment_amount
                END,
                payment_status = CASE
                    WHEN COALESCE(payment_status, '') = '' THEN ?
                    ELSE payment_status
                END
            WHERE appointment_type = ?
            """,
            (
                service_row["id"],
                service_row["label"],
                int(service_row["requires_payment"] or 0),
                service_row["price_amount"],
                service_row["price_amount"],
                "pending" if service_row["requires_payment"] else "not_required",
                appointment_type,
            ),
        )


def _backfill_default_location_assignments(db: sqlite3.Connection, default_location_id: int) -> None:
    db.execute(
        "UPDATE appointments SET location_id = ? WHERE location_id IS NULL",
        (default_location_id,),
    )
    db.execute(
        "UPDATE schedule_windows SET location_id = ? WHERE location_id IS NULL",
        (default_location_id,),
    )


def get_db() -> sqlite3.Connection:
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def close_db(_: object | None = None) -> None:
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db() -> None:
    db = get_db()
    db.executescript(SCHEMA)
    _ensure_column(db, "users", "role", "TEXT NOT NULL DEFAULT 'client'")
    _ensure_column(db, "users", "is_active", "INTEGER NOT NULL DEFAULT 1")
    visit_report_columns = {
        "assessment_payload_json": "TEXT NOT NULL DEFAULT '{}'",
        "rapport_notes": "TEXT NOT NULL DEFAULT ''",
        "complaint_duration": "TEXT NOT NULL DEFAULT ''",
        "first_notice": "TEXT NOT NULL DEFAULT ''",
        "complaint_frequency": "TEXT NOT NULL DEFAULT ''",
        "pain_worst": "INTEGER",
        "pain_quality": "TEXT NOT NULL DEFAULT ''",
        "radiates": "INTEGER NOT NULL DEFAULT 0",
        "radiation_start": "TEXT NOT NULL DEFAULT ''",
        "radiation_end": "TEXT NOT NULL DEFAULT ''",
        "accident_history": "TEXT NOT NULL DEFAULT ''",
        "microtrauma_history": "TEXT NOT NULL DEFAULT ''",
        "prior_treatment_history": "TEXT NOT NULL DEFAULT ''",
        "symptom_trend": "TEXT NOT NULL DEFAULT ''",
        "adl_impacts": "TEXT NOT NULL DEFAULT ''",
        "medical_family_history_review": "TEXT NOT NULL DEFAULT ''",
        "commitment_score": "INTEGER",
        "obstacles_to_care": "TEXT NOT NULL DEFAULT ''",
        "education_summary": "TEXT NOT NULL DEFAULT ''",
        "forward_head_inches": "REAL",
        "shoulders_level": "TEXT NOT NULL DEFAULT ''",
        "hips_level": "TEXT NOT NULL DEFAULT ''",
        "single_leg_balance_left_seconds": "INTEGER",
        "single_leg_balance_right_seconds": "INTEGER",
        "heel_to_toe_walk": "TEXT NOT NULL DEFAULT ''",
        "marching_test": "TEXT NOT NULL DEFAULT ''",
        "xray_recommended": "INTEGER NOT NULL DEFAULT 0",
        "xray_status": "TEXT NOT NULL DEFAULT ''",
        "xray_regions": "TEXT NOT NULL DEFAULT ''",
        "wrap_up_notes": "TEXT NOT NULL DEFAULT ''",
        "triangle_handoff": "TEXT NOT NULL DEFAULT ''",
    }
    for column_name, definition in visit_report_columns.items():
        _ensure_column(db, "visit_reports", column_name, definition)
    appointment_columns = {
        "clinician_user_id": "INTEGER",
        "location_id": "INTEGER",
        "service_id": "INTEGER",
        "appointment_type": "TEXT NOT NULL DEFAULT 'initial_consult'",
        "status": "TEXT NOT NULL DEFAULT 'scheduled'",
        "ends_at": "TEXT",
        "source_invitation_id": "INTEGER",
        "note": "TEXT NOT NULL DEFAULT ''",
        "patient_details": "TEXT NOT NULL DEFAULT ''",
        "clinical_note": "TEXT NOT NULL DEFAULT ''",
        "billing_status": "TEXT NOT NULL DEFAULT 'pending'",
        "billing_code": "TEXT NOT NULL DEFAULT ''",
        "billing_amount": "REAL",
        "requires_payment": "INTEGER NOT NULL DEFAULT 0",
        "payment_status": "TEXT NOT NULL DEFAULT 'not_required'",
        "payment_amount": "REAL",
        "booking_channel": "TEXT NOT NULL DEFAULT 'portal'",
        "service_label_snapshot": "TEXT NOT NULL DEFAULT ''",
        "policy_snapshot_json": "TEXT NOT NULL DEFAULT '{}'",
        "booking_source": "TEXT NOT NULL DEFAULT 'staff_portal'",
        "created_at": "TEXT NOT NULL DEFAULT ''",
        "updated_at": "TEXT NOT NULL DEFAULT ''",
    }
    for column_name, definition in appointment_columns.items():
        _ensure_column(db, "appointments", column_name, definition)
    db.execute("CREATE INDEX IF NOT EXISTS idx_appointments_location ON appointments(location_id)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_appointments_service ON appointments(service_id)")
    slot_hold_columns = {
        "invitation_id": "INTEGER",
        "lead_id": "INTEGER",
        "clinician_user_id": "INTEGER NOT NULL DEFAULT 0",
        "location_id": "INTEGER",
        "service_id": "INTEGER",
        "appointment_type": "TEXT NOT NULL DEFAULT 'initial_consult'",
        "starts_at": "TEXT NOT NULL DEFAULT ''",
        "ends_at": "TEXT",
        "status": "TEXT NOT NULL DEFAULT 'active'",
        "expires_at": "TEXT NOT NULL DEFAULT ''",
        "consumed_appointment_id": "INTEGER",
        "created_at": "TEXT NOT NULL DEFAULT ''",
        "updated_at": "TEXT NOT NULL DEFAULT ''",
    }
    for column_name, definition in slot_hold_columns.items():
        _ensure_column(db, "appointment_slot_holds", column_name, definition)
    db.execute("CREATE INDEX IF NOT EXISTS idx_appointment_slot_holds_clinician_date ON appointment_slot_holds(clinician_user_id, starts_at)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_appointment_slot_holds_status_expires ON appointment_slot_holds(status, expires_at)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_appointment_slot_holds_lead ON appointment_slot_holds(lead_id)")
    db.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_appointment_slot_holds_invitation_unique ON appointment_slot_holds(invitation_id)")
    schedule_window_columns = {
        "location_id": "INTEGER",
    }
    for column_name, definition in schedule_window_columns.items():
        _ensure_column(db, "schedule_windows", column_name, definition)
    soap_note_columns = {
        "spine_findings_json": "TEXT NOT NULL DEFAULT '{\"left\":[],\"right\":[]}'",
    }
    for column_name, definition in soap_note_columns.items():
        _ensure_column(db, "appointment_soap_notes", column_name, definition)
    db.execute("CREATE INDEX IF NOT EXISTS idx_schedule_windows_location ON schedule_windows(location_id)")
    appointment_service_columns = {
        "description": "TEXT NOT NULL DEFAULT ''",
        "appointment_type": "TEXT NOT NULL DEFAULT 'care_plan'",
        "duration_minutes": "INTEGER NOT NULL DEFAULT 30",
        "buffer_before_minutes": "INTEGER NOT NULL DEFAULT 0",
        "buffer_after_minutes": "INTEGER NOT NULL DEFAULT 0",
        "requires_payment": "INTEGER NOT NULL DEFAULT 0",
        "price_amount": "REAL",
        "currency": "TEXT NOT NULL DEFAULT 'GBP'",
        "min_notice_minutes": "INTEGER NOT NULL DEFAULT 0",
        "max_bookings_per_day": "INTEGER",
        "routing_mode": "TEXT NOT NULL DEFAULT 'specific_clinician'",
        "active": "INTEGER NOT NULL DEFAULT 1",
        "display_order": "INTEGER NOT NULL DEFAULT 0",
    }
    for column_name, definition in appointment_service_columns.items():
        _ensure_column(db, "appointment_services", column_name, definition)
    db.execute("CREATE INDEX IF NOT EXISTS idx_appointment_services_active ON appointment_services(active)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_booking_webhook_events_created ON booking_webhook_events(created_at)")
    default_location_id = _seed_default_locations(db)
    _seed_default_appointment_services(db)
    _seed_default_app_settings(db)
    _backfill_accepted_invitation_appointments(db)
    _seed_default_schedule_windows(db)
    _backfill_default_location_assignments(db, default_location_id)
    _backfill_appointment_service_defaults(db)
    db.commit()


def init_app(app) -> None:
    app.teardown_appcontext(close_db)
    with app.app_context():
        init_db()
