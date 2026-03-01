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
"""


def _table_columns(db: sqlite3.Connection, table_name: str) -> set[str]:
    return {row["name"] for row in db.execute(f"PRAGMA table_info({table_name})").fetchall()}


def _ensure_column(db: sqlite3.Connection, table_name: str, column_name: str, definition: str) -> None:
    if column_name not in _table_columns(db, table_name):
        db.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {definition}")


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
    db.commit()


def init_app(app) -> None:
    app.teardown_appcontext(close_db)
    with app.app_context():
        init_db()
