from __future__ import annotations

import calendar as month_calendar
import os
import json
import re
import secrets
import urllib.error
import urllib.request
from datetime import date, datetime, time, timedelta
from functools import wraps
from pathlib import Path

from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    g,
    jsonify,
    redirect,
    render_template,
    request,
    send_file,
    session,
    url_for,
)
from werkzeug.security import check_password_hash, generate_password_hash

from .db import get_db
from .intake import (
    SUMMIT_ORTHO_REGIONS,
    SUMMIT_ROM_SECTIONS,
    SUMMIT_SPINE_REGIONS,
    build_summit_assessment,
    build_clinician_context,
    build_results_context,
    build_seed_payload,
    format_schedule as intake_format_schedule,
    iso_now,
    split_lines,
    validate_submission,
    validate_visit_report,
)
from .reminders import build_delivery_launch_link, deliver_reminder, reminder_preview_payload


bp = Blueprint("main", __name__)


APPOINTMENT_TYPE_META = {
    "initial_consult": {
        "label": "Initial Consultation",
        "short_label": "Initial",
        "tone": "life",
    },
    "report_of_findings": {
        "label": "Report of Findings",
        "short_label": "ROF",
        "tone": "sky",
    },
    "care_plan": {
        "label": "Care Plan Visit",
        "short_label": "Care Plan",
        "tone": "warm",
    },
}

APPOINTMENT_STATUS_META = {
    "scheduled": {"label": "Scheduled", "tone": "sky"},
    "completed": {"label": "Completed", "tone": "life"},
    "cancelled": {"label": "Cancelled", "tone": "rose"},
}

BILLING_STATUS_META = {
    "pending": {"label": "Pending", "tone": "warm"},
    "ready": {"label": "Ready", "tone": "sky"},
    "billed": {"label": "Billed", "tone": "life"},
    "void": {"label": "Void", "tone": "rose"},
}

REMINDER_CHANNEL_META = {
    "email": {"label": "Email", "tone": "sky"},
    "sms": {"label": "SMS", "tone": "warm"},
}

REMINDER_DELIVERY_STATUS_META = {
    "sent": {"label": "Sent", "tone": "life"},
    "logged": {"label": "Logged", "tone": "sky"},
    "failed": {"label": "Failed", "tone": "rose"},
}

SCHEDULE_WINDOW_TYPE_META = {
    "shift": {"label": "Shift", "tone": "life"},
    "downtime": {"label": "Downtime", "tone": "rose"},
}

WEEKDAY_OPTIONS = [
    {"value": 0, "label": "Monday", "short_label": "Mon"},
    {"value": 1, "label": "Tuesday", "short_label": "Tue"},
    {"value": 2, "label": "Wednesday", "short_label": "Wed"},
    {"value": 3, "label": "Thursday", "short_label": "Thu"},
    {"value": 4, "label": "Friday", "short_label": "Fri"},
    {"value": 5, "label": "Saturday", "short_label": "Sat"},
    {"value": 6, "label": "Sunday", "short_label": "Sun"},
]

APPOINTMENT_DURATION_OPTIONS = [
    {"value": 15, "label": "15 minutes"},
    {"value": 20, "label": "20 minutes"},
    {"value": 30, "label": "30 minutes"},
    {"value": 45, "label": "45 minutes"},
    {"value": 60, "label": "60 minutes"},
]

APPOINTMENT_DURATION_DEFAULTS = {
    "initial_consult": 30,
    "report_of_findings": 30,
    "care_plan": 15,
}

MESSAGE_TOPIC_META = {
    "appointment": {"label": "Appointment", "tone": "sky"},
    "treatment": {"label": "Treatment Query", "tone": "life"},
    "exercise": {"label": "Home Exercise", "tone": "warm"},
    "symptoms": {"label": "Symptom Update", "tone": "rose"},
    "billing": {"label": "Billing / Insurance", "tone": "sky"},
}

BOOKING_ROUTING_MODE_META = {
    "specific_clinician": {"label": "Specific chiropractor"},
    "team_round_robin": {"label": "Any available chiropractor"},
}

CARE_PLAN_VISIT_META = {
    "follow_up": {"label": "Follow-up", "tone": "life", "icon": "->"},
    "progress_check": {"label": "Progress Check", "tone": "warm", "icon": "<>"},
    "reassessment": {"label": "Reassessment", "tone": "purple", "icon": "**"},
}

CARE_PLAN_BOOKING_MODE_META = {
    "all": {"label": "Book all now", "description": "Try to sync every visit into the live calendar immediately."},
    "as_you_go": {"label": "Book as you go", "description": "Book only the first visit now and stage the rest for later."},
}

CARE_PLAN_FREQUENCY_OPTIONS = [
    {"value": 1, "label": "Once a week", "short_label": "1x / week"},
    {"value": 2, "label": "Twice a week", "short_label": "2x / week"},
]

CARE_PLAN_WEEK_OPTIONS = [3, 6, 9, 12]

DEFAULT_SLOT_INCREMENT_MINUTES = 15
SLOT_INCREMENT_OPTIONS = [5, 10, 15, 20, 30, 60]
TIME_FORMAT_OPTIONS = [
    {"value": "24h", "label": "24-hour"},
    {"value": "12h", "label": "12-hour am/pm"},
]
DEFAULT_TIME_FORMAT = "24h"
DEFAULT_BOOKING_SEARCH_WINDOW_DAYS = 21
DEFAULT_MAX_ACTIVE_CHIROPRACTORS = 3
APP_SETTING_DEFAULTS = {
    "practice_practitioner_name": "",
    "practice_registration_number": "",
    "practice_qualifications": "",
    "practice_clinic_name": "Life Chiropractic",
    "practice_email": "",
    "practice_phone": "",
    "practice_address": "",
    "practice_bio": "",
    "clinic_open_days": "Mon,Tue,Wed,Thu,Fri",
    "clinic_open_time": "08:00",
    "clinic_close_time": "18:00",
    "clinic_lunch_start": "13:00",
    "clinic_lunch_end": "14:00",
    "clinic_rooms": "2",
    "clinic_multi_practitioner_mode": "1",
    "calendar_time_format": DEFAULT_TIME_FORMAT,
    "calendar_slot_increment_minutes": str(DEFAULT_SLOT_INCREMENT_MINUTES),
    "booking_search_window_days": str(DEFAULT_BOOKING_SEARCH_WINDOW_DAYS),
    "max_active_chiropractors": str(DEFAULT_MAX_ACTIVE_CHIROPRACTORS),
    "booking_enable_online": "1",
    "booking_allow_same_day": "1",
    "booking_cancellation_hours": "24",
    "booking_no_show_fee": "",
    "notifications_confirmation_email": "1",
    "notifications_confirmation_sms": "1",
    "notifications_reminder_24h": "1",
    "notifications_reminder_1h": "0",
    "notifications_post_visit_email": "0",
    "notifications_recall_enabled": "1",
    "notifications_recall_days": "60",
    "clinical_outcome_measures": "NDI,ODI",
    "clinical_reexam_interval": "12",
    "clinical_use_mcid": "1",
    "clinical_auto_assign_intake": "1",
    "clinical_include_consent": "1",
    "billing_initial_fee": "",
    "billing_followup_fee": "",
    "billing_payment_methods": "Card",
    "billing_auto_invoice": "0",
    "billing_email_receipts": "0",
    "security_two_factor": "0",
    "security_session_timeout": "30",
    "data_ico_reference": "",
    "data_retention_period": "7y",
    "data_auto_anonymize": "0",
    "data_daily_backups": "1",
    "appearance_theme": "light",
    "appearance_brand_color": "#3b7a57",
    "appearance_font_style": "modern",
    "appearance_show_portal_branding": "1",
    "integration_payment_provider": "",
    "integration_calendar_sync": "",
    "integration_email_provider": "",
    "integration_sms_provider": "",
}
CLAUDE_DDX_ARTIFACT_PATH = Path(__file__).resolve().parent.parent / "life-chiro-ddx-tx (1).jsx"

DECISION_SUPPORT_REGION_LABELS = {
    "neck": "Neck Pain",
    "low_back": "Low Back Pain",
    "shoulder": "Shoulder",
    "headache": "Headache",
}

SPINE_SEGMENT_ORDER = [
    *[f"C{i}" for i in range(1, 8)],
    *[f"T{i}" for i in range(1, 13)],
    *[f"L{i}" for i in range(1, 6)],
    *[f"S{i}" for i in range(1, 6)],
]
SPINE_SEGMENT_INDEX = {segment: index for index, segment in enumerate(SPINE_SEGMENT_ORDER)}

LEARNING_PATH_TOPICS = [
    {
        "slug": "anatomy-spine-joints",
        "category": "Anatomy",
        "title": "Spinal Anatomy Foundations",
        "description": "Learn vertebral landmarks, disc mechanics, and segmental function before advanced adjustments.",
        "outcome": "Describe core anatomical structures and common dysfunction mechanisms.",
        "duration": "10 min",
    },
    {
        "slug": "chiropractic-adjustments-principles",
        "category": "Adjustments",
        "title": "Adjustment Biomechanics",
        "description": "Understand setup, vector, force application, and safety checks for each thrust technique.",
        "outcome": "Plan and perform safer, more consistent adjustment setup.",
        "duration": "12 min",
    },
    {
        "slug": "segmental-dysfunction-detection",
        "category": "Assessment",
        "title": "Segmental Dysfunction Detection",
        "description": "Sharpen palpation and movement analysis to identify objective segment findings.",
        "outcome": "Create a repeatable dysfunction hypothesis and test it clinically.",
        "duration": "15 min",
    },
    {
        "slug": "patient-intake-clinical-history",
        "category": "Clinical Workflow",
        "title": "Clinical Intake & History",
        "description": "Improve questioning around pain behavior, red flags, and meaningful functional limits.",
        "outcome": "Capture cleaner consult notes that drive better outcomes planning.",
        "duration": "8 min",
    },
    {
        "slug": "rehab-exercise-prescriptions",
        "category": "Exercise",
        "title": "Prescribing Rehab Exercises",
        "description": "Match exercise selection to complaint, stage, and tolerance level.",
        "outcome": "Deliver practical home programs with better adherence.",
        "duration": "9 min",
    },
    {
        "slug": "communication-case-management",
        "category": "Practice Growth",
        "title": "Patient Communication",
        "description": "Translate findings into clear, empathetic language for treatment planning.",
        "outcome": "Build stronger patient trust and adherence through communication.",
        "duration": "7 min",
    },
    {
        "slug": "chiropractic-ethics-safety",
        "category": "Professional Standards",
        "title": "Ethics & Safety in Chiropractic Care",
        "description": "Review consent, documentation, escalation criteria, and safe referral pathways.",
        "outcome": "Operate with higher consistency and confidence in risk management.",
        "duration": "11 min",
    },
    {
        "slug": "evidence-based-updates",
        "category": "Professional Standards",
        "title": "Evidence and Best-Practice Updates",
        "description": "Read and apply practical updates from modern chiropractic literature.",
        "outcome": "Bring current evidence into routine care decisions.",
        "duration": "10 min",
    },
]


def is_staff(user) -> bool:
    return bool(user and user["role"] in {"clinician", "admin"})


def is_admin(user) -> bool:
    return bool(user and user["role"] == "admin")


def is_clinician(user) -> bool:
    return bool(user and user["role"] == "clinician")


def parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def get_app_settings() -> dict[str, str]:
    cached = getattr(g, "app_settings_cache", None)
    if cached is not None:
        return cached

    settings = dict(APP_SETTING_DEFAULTS)
    rows = get_db().execute(
        """
        SELECT setting_key, setting_value
        FROM app_settings
        """
    ).fetchall()
    for row in rows:
        settings[row["setting_key"]] = row["setting_value"]
    g.app_settings_cache = settings
    return settings


def get_app_setting(setting_key: str, default: str | None = None) -> str | None:
    settings = get_app_settings()
    if setting_key in settings:
        return settings[setting_key]
    if default is not None:
        return default
    return APP_SETTING_DEFAULTS.get(setting_key)


def set_app_setting(setting_key: str, setting_value: str) -> None:
    get_db().execute(
        """
        INSERT INTO app_settings (setting_key, setting_value, updated_at)
        VALUES (?, ?, ?)
        ON CONFLICT(setting_key) DO UPDATE
        SET setting_value = excluded.setting_value,
            updated_at = excluded.updated_at
        """,
        (setting_key, setting_value, iso_now()),
    )
    if hasattr(g, "app_settings_cache"):
        delattr(g, "app_settings_cache")


def current_time_format() -> str:
    raw_value = str(get_app_setting("calendar_time_format", DEFAULT_TIME_FORMAT) or "").strip().lower()
    if raw_value in {"24h", "12h"}:
        return raw_value
    return DEFAULT_TIME_FORMAT


def current_booking_search_window_days() -> int:
    parsed = int_or_none(get_app_setting("booking_search_window_days", str(DEFAULT_BOOKING_SEARCH_WINDOW_DAYS)))
    if isinstance(parsed, int) and 1 <= parsed <= 120:
        return parsed
    return DEFAULT_BOOKING_SEARCH_WINDOW_DAYS


def current_max_active_chiropractors() -> int:
    parsed = int_or_none(get_app_setting("max_active_chiropractors", str(DEFAULT_MAX_ACTIVE_CHIROPRACTORS)))
    if isinstance(parsed, int) and 1 <= parsed <= 100:
        return parsed
    return DEFAULT_MAX_ACTIVE_CHIROPRACTORS


def setting_enabled(setting_key: str, default: bool = False) -> bool:
    raw_value = str(get_app_setting(setting_key, "1" if default else "0") or "").strip().lower()
    return raw_value in {"1", "true", "yes", "on"}


def setting_list(setting_key: str, default: list[str] | None = None) -> list[str]:
    raw_value = str(get_app_setting(setting_key, "") or "").strip()
    if not raw_value:
        return list(default or [])
    items = []
    seen = set()
    for part in raw_value.split(","):
        value = part.strip()
        if not value or value in seen:
            continue
        items.append(value)
        seen.add(value)
    return items


def clinic_display_name() -> str:
    return (get_app_setting("practice_clinic_name", "Life Chiropractic") or "Life Chiropractic").strip() or "Life Chiropractic"


def appearance_brand_color() -> str:
    value = str(get_app_setting("appearance_brand_color", "#3b7a57") or "").strip()
    if re.fullmatch(r"#[0-9A-Fa-f]{6}", value):
        return value
    return "#3b7a57"


def appearance_theme_value() -> str:
    value = str(get_app_setting("appearance_theme", "light") or "").strip().lower()
    if value in {"light", "dark", "auto"}:
        return value
    return "light"


def appearance_font_style_value() -> str:
    value = str(get_app_setting("appearance_font_style", "modern") or "").strip().lower()
    if value in {"modern", "classic", "clean"}:
        return value
    return "modern"


def online_booking_enabled() -> bool:
    return setting_enabled("booking_enable_online", True)


def same_day_booking_enabled() -> bool:
    return setting_enabled("booking_allow_same_day", True)


def current_session_timeout_minutes() -> int:
    parsed = int_or_none(get_app_setting("security_session_timeout", "30"))
    if isinstance(parsed, int) and parsed in {15, 30, 60, 120}:
        return parsed
    return 30


def current_cancellation_window_minutes() -> int:
    parsed = int_or_none(get_app_setting("booking_cancellation_hours", "24"))
    if isinstance(parsed, int) and 0 <= parsed <= 336:
        return parsed * 60
    return 24 * 60


def reminder_channel_enabled(channel: str) -> bool:
    if channel == "email":
        return setting_enabled("notifications_confirmation_email", True)
    if channel == "sms":
        return setting_enabled("notifications_confirmation_sms", False)
    return True


def format_time_label(value: datetime | time | None) -> str:
    if value is None:
        return ""
    display_value = datetime.combine(date.today(), value) if isinstance(value, time) else value
    if current_time_format() == "12h":
        return display_value.strftime("%I:%M %p").lstrip("0")
    return display_value.strftime("%H:%M")


def format_time_range(start_value: datetime | time | None, end_value: datetime | time | None) -> str:
    return f"{format_time_label(start_value)} - {format_time_label(end_value)}".strip()


def format_clock_time(value: str | None) -> str:
    parsed = time_from_value(value)
    if parsed is None:
        return value or ""
    return format_time_label(parsed)


def format_schedule(value: str | None) -> str | None:
    if not value:
        return None
    parsed = parse_iso(value)
    if parsed is None:
        return intake_format_schedule(value)
    return f"{parsed.strftime('%d %b %Y')} · {format_time_label(parsed)}"


def format_file_size(size_bytes: int | None) -> str:
    if not isinstance(size_bytes, int) or size_bytes < 0:
        return "Unknown"
    units = ["B", "KB", "MB", "GB"]
    size = float(size_bytes)
    for unit in units:
        if size < 1024 or unit == units[-1]:
            if unit == "B":
                return f"{int(size)} {unit}"
            return f"{size:.1f} {unit}"
        size /= 1024
    return "Unknown"


@bp.app_context_processor
def inject_ui_settings() -> dict:
    return {
        "ui_branding": {
            "clinic_name": clinic_display_name(),
            "brand_color": appearance_brand_color(),
            "theme": appearance_theme_value(),
            "font_style": appearance_font_style_value(),
            "show_portal_branding": setting_enabled("appearance_show_portal_branding", True),
        }
    }


def is_expired(value: str | None) -> bool:
    parsed = parse_iso(value)
    if parsed is None:
        return True
    return parsed <= datetime.now(parsed.tzinfo)


def normalize_spine_findings(raw_value: str | None) -> dict[str, list[str]]:
    findings = {"left": [], "right": []}
    if not raw_value:
        return findings

    try:
        parsed = json.loads(raw_value)
    except (json.JSONDecodeError, TypeError):
        return findings

    if not isinstance(parsed, dict):
        return findings

    for side in ("left", "right"):
        raw_segments = parsed.get(side)
        if not isinstance(raw_segments, list):
            continue

        normalized_side = []
        seen = set()
        for segment in raw_segments:
            if not isinstance(segment, str):
                continue
            key = segment.strip().upper()
            if key not in SPINE_SEGMENT_INDEX or key in seen:
                continue
            normalized_side.append(key)
            seen.add(key)

        normalized_side.sort(key=lambda segment_key: SPINE_SEGMENT_INDEX[segment_key])
        findings[side] = normalized_side

    return findings


def login_required(view):
    @wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None:
            return redirect(url_for("main.login"))
        return view(**kwargs)

    return wrapped_view


def client_required(view):
    @wraps(view)
    @login_required
    def wrapped_view(**kwargs):
        if is_staff(g.user):
            flash("That page is only available to client accounts.", "error")
            return redirect(url_for("main.dashboard"))
        return view(**kwargs)

    return wrapped_view


def staff_required(view):
    @wraps(view)
    @login_required
    def wrapped_view(**kwargs):
        if not is_staff(g.user):
            abort(403)
        return view(**kwargs)

    return wrapped_view


def can_access_staff_appointment(user, appointment_row) -> bool:
    if user is None or appointment_row is None or not is_staff(user):
        return False
    if is_admin(user):
        return True
    return appointment_row["clinician_user_id"] == user["id"]


def dashboard_redirect_for(user) -> str:
    return url_for("main.dashboard") if user else url_for("main.login")


def current_local_timestamp() -> str:
    return datetime.now().replace(second=0, microsecond=0).isoformat(timespec="minutes")


def format_datetime_local(value: datetime | None) -> str:
    if value is None:
        return ""
    return value.replace(second=0, microsecond=0).isoformat(timespec="minutes")


def int_or_none(value: str | None):
    if value in (None, ""):
        return None
    try:
        return int(value)
    except ValueError:
        return value


def float_or_none(value: str | None):
    if value in (None, ""):
        return None
    try:
        return float(value)
    except ValueError:
        return value


def numeric_or_none(value):
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def normalize_questionnaire_scores(payload: dict | None) -> list[dict]:
    if not isinstance(payload, dict):
        return []

    functional = payload.get("functionalOutcomeMeasures")
    if not isinstance(functional, dict):
        return []

    schemas = functional.get("questionnaireSchemas")
    if not isinstance(schemas, dict):
        schemas = {}

    questionnaires = functional.get("questionnaires")
    if not isinstance(questionnaires, list):
        return []

    normalized: dict[str, dict] = {}
    for entry in questionnaires:
        if not isinstance(entry, dict):
            continue

        questionnaire_id = str(entry.get("questionnaireId") or "").strip().lower()
        if not questionnaire_id:
            continue

        schema_entry = schemas.get(questionnaire_id)
        if not isinstance(schema_entry, dict):
            schema_entry = {}

        responses = entry.get("responses")
        if not isinstance(responses, list):
            responses = []

        completed_at_raw = entry.get("completedAt")
        completed_at = completed_at_raw.strip() if isinstance(completed_at_raw, str) else None
        if completed_at == "":
            completed_at = None

        normalized[questionnaire_id] = {
            "questionnaire_id": questionnaire_id,
            "display_name": str(entry.get("displayName") or questionnaire_id).strip(),
            "questionnaire_version": str(entry.get("version") or "").strip(),
            "response_model": str(entry.get("responseModel") or "").strip(),
            "raw_score": numeric_or_none(entry.get("rawScore")),
            "percent_score": numeric_or_none(entry.get("percent")),
            "interpretation": str(entry.get("interpretation") or "").strip(),
            "completed_at": completed_at,
            "responses_json": json.dumps(responses, separators=(",", ":")),
            "schema_json": json.dumps(schema_entry, separators=(",", ":")),
        }

    return [normalized[key] for key in sorted(normalized.keys())]


def persist_intake_questionnaire_scores(db, user_id: int, payload: dict | None, now: str) -> None:
    rows = normalize_questionnaire_scores(payload)
    db.execute("DELETE FROM intake_questionnaire_scores WHERE user_id = ?", (user_id,))
    if not rows:
        return

    db.executemany(
        """
        INSERT INTO intake_questionnaire_scores (
            user_id,
            questionnaire_id,
            display_name,
            questionnaire_version,
            response_model,
            raw_score,
            percent_score,
            interpretation,
            completed_at,
            responses_json,
            schema_json,
            created_at,
            updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                user_id,
                row["questionnaire_id"],
                row["display_name"],
                row["questionnaire_version"],
                row["response_model"],
                row["raw_score"],
                row["percent_score"],
                row["interpretation"],
                row["completed_at"],
                row["responses_json"],
                row["schema_json"],
                now,
                now,
            )
            for row in rows
        ],
    )


def slugify_service_key(value: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", "_", (value or "").strip().lower()).strip("_")
    return cleaned[:48] or "service"


def infer_decision_support_region(payload: dict | None) -> str:
    payload = payload or {}
    pain_areas = [str(item).strip().lower() for item in (payload.get("pain") or {}).get("areas", []) if item]
    complaint = str((payload.get("reasonForVisit") or {}).get("chiefComplaint", "")).strip().lower()

    if any(term in complaint for term in ("shoulder", "rotator cuff", "labrum")) or "shoulder" in pain_areas:
        return "shoulder"
    if any(term in complaint for term in ("headache", "migraine", "head pain")) or "head" in pain_areas:
        return "headache"
    if any(term in complaint for term in ("low back", "lumbar", "sciatica", "sacroiliac")):
        return "low_back"
    if any(area in {"low back", "back", "hip", "leg"} for area in pain_areas):
        return "low_back"
    if any(term in complaint for term in ("neck", "cervical")) or "neck" in pain_areas:
        return "neck"
    return "neck"


def decision_support_storage_key(user_id: int) -> str:
    return f"life_chiro_ddx_export:{user_id}"


def build_claude_artifact_source() -> str | None:
    if not CLAUDE_DDX_ARTIFACT_PATH.exists():
        return None

    source = CLAUDE_DDX_ARTIFACT_PATH.read_text(encoding="utf-8")
    source = source.replace(
        'import { useState, useMemo } from "react";',
        "const { useState, useMemo } = React;",
        1,
    )
    source = source.replace(
        'const[rId,setRId]=useState("neck");',
        'const[rId,setRId]=useState((window.LIFE_CHIRO_ARTIFACT_CONTEXT && window.LIFE_CHIRO_ARTIFACT_CONTEXT.initialRegion) || "neck");',
        1,
    )
    source = source.replace(
        '  const[showSpine,setShowSpine]=useState(false);',
        '  const[showSpine,setShowSpine]=useState(false);\n'
        '  const[exportStatus,setExportStatus]=useState("");',
        1,
    )
    source = source.replace(
        '  const results=useMemo(()=>bayes(reg,res),[reg,res]);\n'
        '  const tested=Object.values(res).filter(Boolean).length;\n'
        '  const switchReg=r=>{setRId(r);setRes({});setOp({});setView("assess");setExpDx(null);setTxCond(null);setSpineSegs([]);setShowSpine(false)};',
        '  const results=useMemo(()=>bayes(reg,res),[reg,res]);\n'
        '  const tested=Object.values(res).filter(Boolean).length;\n'
        '  const artifactContext=window.LIFE_CHIRO_ARTIFACT_CONTEXT||{};\n'
        '  const selectedCondition=results.find(c=>c.id===txCond)||results[0]||null;\n'
        '  const selectedTx=selectedCondition?TX[selectedCondition.id]:null;\n'
        '  const buildExportPayload=()=>{\n'
        '    if(!selectedCondition) return null;\n'
        '    const topDiagnoses=results.slice(0,3).map(c=>`${c.name} (${(c.post*100).toFixed(1)}%)`);\n'
        '    const support=selectedCondition.ap.slice(0,4).map(a=>`${a.n} ${a.r} (LR ${a.lr.toFixed(2)})`);\n'
        '    const sessionFocus=(selectedTx?.session||[]).slice(0,3).map(s=>`${s.p}: ${s.tasks.slice(0,2).join(", ")}`);\n'
        '    const reexamSchedule=(selectedTx?.reexam?.schedule||[]).map(s=>`${s.visit}: ${s.focus}`);\n'
        '    return {\n'
        '      source:"claude_artifact",\n'
        '      region:reg.id,\n'
        '      leadingConditionId:selectedCondition.id,\n'
        '      leadingConditionName:selectedCondition.name,\n'
        '      exportedAt:new Date().toISOString(),\n'
        '      assessment:[\n'
        '        `${selectedCondition.name} is the current leading working diagnosis from the DDx tool (${(selectedCondition.post*100).toFixed(1)}% posterior probability).`,\n'
        '        support.length?`Most supportive findings: ${support.join("; ")}.`:"",\n'
        '        selectedTx?.prog?.t||""\n'
        '      ].filter(Boolean).join(" "),\n'
        '      diagnosis:topDiagnoses.join("\\n"),\n'
        '      care_plan:[\n'
        '        selectedTx?.freq?`Frequency: ${selectedTx.freq}`:"",\n'
        '        selectedTx?.visits?`Expected course: ${selectedTx.visits}`:"",\n'
        '        sessionFocus.length?`Session focus: ${sessionFocus.join("; ")}`:""\n'
        '      ].filter(Boolean).join("\\n"),\n'
        '      home_care:(selectedTx?.hep||[]).join("\\n"),\n'
        '      follow_up_plan:[\n'
        '        reexamSchedule.length?`Re-exam schedule: ${reexamSchedule.join(" | ")}`:"",\n'
        '        selectedTx?.reexam?.onTrack?`On track: ${selectedTx.reexam.onTrack}`:"",\n'
        '        selectedTx?.reexam?.offTrack?`Off track: ${selectedTx.reexam.offTrack}`:""\n'
        '      ].filter(Boolean).join("\\n"),\n'
        '      summary:`${selectedCondition.name} · ${(selectedCondition.post*100).toFixed(1)}% · ${reg.label}`\n'
        '    };\n'
        '  };\n'
        '  const exportToAssessment=()=>{\n'
        '    const payload=buildExportPayload();\n'
        '    if(!payload||!artifactContext.storageKey){\n'
        '      setExportStatus("No assessment export target is configured.");\n'
        '      return;\n'
        '    }\n'
        '    window.localStorage.setItem(artifactContext.storageKey, JSON.stringify(payload));\n'
        '    setExportStatus("Draft sent to Summit Assessment.");\n'
        '    if(artifactContext.assessmentUrl){\n'
        '      window.location.href=`${artifactContext.assessmentUrl}#sec-publish`;\n'
        '    }\n'
        '  };\n'
        '  const switchReg=r=>{setRId(r);setRes({});setOp({});setView("assess");setExpDx(null);setTxCond(null);setSpineSegs([]);setShowSpine(false);setExportStatus("")};',
        1,
    )
    source = source.replace(
        '    <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700;800&family=Source+Sans+3:wght@300;400;500;600;700;800&display=swap" rel="stylesheet"/>',
        "",
        1,
    )
    source = source.replace(
        '        <p style={{fontSize:10,color:"#444",margin:0,fontFamily:"mono"}}>{tested} findings{results[0]?.ap.length>0?` · Leading: ${results[0].name}`:""}</p>',
        '        <p style={{fontSize:10,color:"#444",margin:0,fontFamily:"mono"}}>{tested} findings{results[0]?.ap.length>0?` · Leading: ${results[0].name}`:""}</p>\n'
        '        {selectedCondition&&artifactContext.assessmentUrl&&<div style={{display:"flex",gap:8,alignItems:"center",flexWrap:"wrap",marginTop:8}}>\n'
        '          <button onClick={exportToAssessment} style={{padding:"6px 10px",border:`1px solid ${selectedCondition.color}`,borderRadius:6,background:selectedCondition.color+"18",color:selectedCondition.color,fontSize:10,fontWeight:700,fontFamily:"mono",cursor:"pointer"}}>Send to Summit Assessment</button>\n'
        '          {exportStatus&&<span style={{fontSize:9,color:"#6b7280",fontFamily:"mono"}}>{exportStatus}</span>}\n'
        '        </div>}',
        1,
    )
    source = source.replace("export default function App(){", "function App(){", 1)
    source += (
        '\nconst claudeArtifactRoot = ReactDOM.createRoot(document.getElementById("claude-artifact-root"));'
        "\nclaudeArtifactRoot.render(<App />);\n"
    )
    return source


def get_submission_for_user(user_id: int):
    return get_db().execute(
        "SELECT * FROM intake_submissions WHERE user_id = ?",
        (user_id,),
    ).fetchone()


def get_client_user(user_id: int):
    return get_db().execute(
        "SELECT * FROM users WHERE id = ? AND role = 'client'",
        (user_id,),
    ).fetchone()


def get_notes_for_patient(patient_user_id: int):
    return get_db().execute(
        "SELECT * FROM clinician_notes WHERE patient_user_id = ?",
        (patient_user_id,),
    ).fetchone()


def _message_summary_item(row) -> dict:
    if row is None:
        return {}
    patient_name = " ".join(part for part in [row["patient_first_name"], row["patient_last_name"]] if part).strip() or "Unknown patient"
    topic = row["last_topic"] or "appointment"
    topic_meta = message_topic_meta(topic)
    return {
        "patient_user_id": row["patient_user_id"],
        "patient_name": patient_name,
        "patient_email": row["patient_email"],
        "last_body": row["last_body"] or "",
        "last_created_at": row["last_created_at"],
        "last_created_label": format_schedule(row["last_created_at"]) if row["last_created_at"] else "No messages yet",
        "last_topic": topic,
        "last_topic_label": topic_meta["label"],
        "last_topic_tone": topic_meta["tone"],
        "unread_for_staff": int(row["unread_for_staff"] or 0),
    }


def get_staff_message_threads(search_query: str | None = None) -> list[dict]:
    search_query = (search_query or "").strip().lower()
    rows = get_db().execute(
        """
        SELECT
            u.id AS patient_user_id,
            u.first_name AS patient_first_name,
            u.last_name AS patient_last_name,
            u.email AS patient_email,
            (
                SELECT pm.topic
                FROM patient_messages pm
                WHERE pm.patient_user_id = u.id
                ORDER BY pm.created_at DESC, pm.id DESC
                LIMIT 1
            ) AS last_topic,
            (
                SELECT pm.body
                FROM patient_messages pm
                WHERE pm.patient_user_id = u.id
                ORDER BY pm.created_at DESC, pm.id DESC
                LIMIT 1
            ) AS last_body,
            (
                SELECT pm.created_at
                FROM patient_messages pm
                WHERE pm.patient_user_id = u.id
                ORDER BY pm.created_at DESC, pm.id DESC
                LIMIT 1
            ) AS last_created_at,
            (
                SELECT COUNT(*)
                FROM patient_messages pm
                WHERE pm.patient_user_id = u.id
                  AND pm.sender_role = 'client'
                  AND pm.read_by_staff_at IS NULL
            ) AS unread_for_staff
        FROM users u
        WHERE u.role = 'client'
        ORDER BY
            unread_for_staff DESC,
            COALESCE(last_created_at, u.created_at) DESC,
            u.last_name ASC,
            u.first_name ASC,
            u.id ASC
        """
    ).fetchall()

    items = [_message_summary_item(row) for row in rows]
    if not search_query:
        return items
    filtered = []
    for item in items:
        haystack = " ".join(
            [
                item["patient_name"].lower(),
                (item["patient_email"] or "").lower(),
                (item["last_body"] or "").lower(),
            ]
        )
        if search_query in haystack:
            filtered.append(item)
    return filtered


def get_patient_message_thread(patient_user_id: int) -> list[dict]:
    rows = get_db().execute(
        """
        SELECT
            pm.*,
            sender.first_name AS sender_first_name,
            sender.last_name AS sender_last_name
        FROM patient_messages pm
        LEFT JOIN users sender ON sender.id = pm.sender_user_id
        WHERE pm.patient_user_id = ?
        ORDER BY pm.created_at ASC, pm.id ASC
        """,
        (patient_user_id,),
    ).fetchall()

    messages = []
    for row in rows:
        sender_name = " ".join(part for part in [row["sender_first_name"], row["sender_last_name"]] if part).strip()
        if not sender_name:
            sender_name = "Chiropractor" if row["sender_role"] in {"admin", "clinician"} else "Patient"
        topic_meta = message_topic_meta(row["topic"] or "appointment")
        messages.append(
            {
                "id": row["id"],
                "sender_user_id": row["sender_user_id"],
                "sender_role": row["sender_role"],
                "sender_name": sender_name,
                "topic": row["topic"] or "appointment",
                "topic_label": topic_meta["label"],
                "topic_tone": topic_meta["tone"],
                "body": row["body"] or "",
                "created_at": row["created_at"],
                "created_label": format_schedule(row["created_at"]) or row["created_at"],
            }
        )
    return messages


def mark_patient_messages_read_for_staff(patient_user_id: int) -> None:
    now = iso_now()
    get_db().execute(
        """
        UPDATE patient_messages
        SET read_by_staff_at = ?
        WHERE patient_user_id = ?
          AND sender_role = 'client'
          AND read_by_staff_at IS NULL
        """,
        (now, patient_user_id),
    )


def mark_patient_messages_read_for_patient(patient_user_id: int) -> None:
    now = iso_now()
    get_db().execute(
        """
        UPDATE patient_messages
        SET read_by_patient_at = ?
        WHERE patient_user_id = ?
          AND sender_role IN ('admin', 'clinician')
          AND read_by_patient_at IS NULL
        """,
        (now, patient_user_id),
    )


def insert_patient_message(patient_user_id: int, sender_user_id: int, sender_role: str, topic: str, body: str) -> None:
    now = iso_now()
    read_by_staff_at = now if sender_role in {"admin", "clinician"} else None
    read_by_patient_at = now if sender_role == "client" else None
    get_db().execute(
        """
        INSERT INTO patient_messages (
            patient_user_id,
            sender_user_id,
            sender_role,
            topic,
            body,
            read_by_staff_at,
            read_by_patient_at,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            patient_user_id,
            sender_user_id,
            sender_role,
            topic,
            body,
            read_by_staff_at,
            read_by_patient_at,
            now,
        ),
    )


def get_practitioner_journal_entries(clinician_user_id: int):
    return get_db().execute(
        """
        SELECT *
        FROM practitioner_journal_entries
        WHERE clinician_user_id = ?
        ORDER BY entry_date DESC, created_at DESC, id DESC
        """,
        (clinician_user_id,),
    ).fetchall()


def _journal_entry_block(entry: dict) -> str:
    title = (entry["title"] or "").strip()
    reflection = (entry["reflection"] or "").strip()
    lesson = (entry["lesson_learned"] or "").strip()
    next_step = (entry["next_step"] or "").strip()

    heading = entry["entry_date"]
    if title:
        heading = f"{heading} · {title}"

    parts: list[str] = []
    if reflection:
        parts.append(f"Reflection: {reflection}")
    if lesson:
        parts.append(f"Learned: {lesson}")
    if next_step:
        parts.append(f"Next action: {next_step}")

    return f"{heading}\n" + "\n".join(parts)


def _selected_journal_entries_for_user(clinician_user_id: int, entry_ids: list[int] | None = None, *, default_limit: int = 5):
    entries = [dict(entry) for entry in get_practitioner_journal_entries(clinician_user_id)]
    if not entries:
        return []

    if not entry_ids:
        return entries[:default_limit]

    by_id = {entry["id"]: entry for entry in entries}
    selected = [by_id[entry_id] for entry_id in entry_ids if entry_id in by_id]
    return selected


def _build_journal_context_prompt(clinician_name: str, selected_entries: list[dict], user_prompt: str) -> str:
    lines = [
        f"Clinician: {clinician_name}",
        "Use the journal snippets below to tailor a practical, safety-focused, professional chiropractic coaching response.",
        "Answer in a concise tone with 3–5 actionable points and clear next steps.",
    ]

    if selected_entries:
        lines.append("Journal entries:")
        for index, entry in enumerate(selected_entries, start=1):
            lines.append(f"{index}. { _journal_entry_block(entry) }")
    else:
        lines.append("No journal entries selected for this request.")

    lines.append("User request:")
    lines.append(user_prompt or "Provide a useful improvement-oriented coaching response.")
    return "\n".join(lines)


def _fallback_claude_reply(user_prompt: str, selected_entries: list[dict]) -> str:
    prompt = (user_prompt or "").strip().lower()
    if not selected_entries and not prompt:
        return "I can help you review progress, but I need either a prompt or some journal entries to analyse."

    reflection_notes = []
    action_notes = []
    learning_notes = []
    for entry in selected_entries:
        if entry.get("reflection"):
            reflection_notes.append(entry["reflection"])
        if entry.get("lesson_learned"):
            learning_notes.append(entry["lesson_learned"])
        if entry.get("next_step"):
            action_notes.append(entry["next_step"])

    top_reflections = (reflection_notes[:2] or ["No recent reflections were provided."])
    top_learning = (learning_notes[:2] or ["No learning notes were provided."])
    top_actions = (action_notes[:2] or ["No explicit next actions were set."])

    if any(term in prompt for term in ("reflect", "review", "summary", "pattern")):
        return (
            "Reflection summary from selected entries:\n"
            f"- Core observations: {'; '.join(top_reflections)}\n"
            f"- Learning themes: {'; '.join(top_learning)}\n"
            "Actionable guidance:\n"
            "1) State one clinical principle to test at your next treatment.\n"
            "2) Keep the same note structure for all cases (observation, hypothesis, intervention, outcome).\n"
            "3) Add one measurable outcome target to each treatment plan.\n"
            "4) End with one coaching check-in question for yourself before clinic ends."
        )
    if any(term in prompt for term in ("plan", "next", "step", "action", "improve")):
        return (
            "Based on your selected entries, a practical plan:\n"
            f"- Reinforce: {top_learning[0]}\n"
            f"- Immediate tweak: {top_actions[0]}\n"
            "- Keep the patient-facing explanation short and outcome-focused.\n"
            "- Revisit your top two hypotheses in the next 24 hours before reassessing.\n"
            f"- Record your next action for tomorrow: {top_actions[1] if len(top_actions) > 1 else 'set one concrete treatment check this week.'}\n"
        )
    return (
        "Here is a focused coach-style response:\n"
        f"- Key reflection signal: {top_reflections[0]}\n"
        f"- Learning signal: {top_learning[0]}\n"
        "- Suggested priorities: safety review, assessment calibration, and communication clarity.\n"
        "- If one recurring issue appears in your log, run a targeted 30-minute case review before the next clinic day.\n"
        "- Translate one journal learning into an explicit objective goal for your next appointment."
    )


def _call_claude_api(prompt: str) -> str | None:
    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        return None

    request_payload = {
        "model": "claude-3-haiku-20240307",
        "max_tokens": 700,
        "system": (
            "You are a confidential coaching assistant for chiropractors. "
            "Use the provided journal context to offer safe, practical, evidence-aware reflections. "
            "Do not provide diagnosis or emergency medical advice and avoid definitive claims."
        ),
        "messages": [
            {"role": "user", "content": prompt},
        ],
    }

    request_body = json.dumps(request_payload).encode("utf-8")
    http_request = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        method="POST",
        data=request_body,
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
    )

    try:
        with urllib.request.urlopen(http_request, timeout=20) as response:
            raw = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, urllib.error.HTTPError, ValueError, TimeoutError) as exc:
        raise RuntimeError(f"Claude request failed: {exc}") from exc

    content = raw.get("content")
    if not content:
        raise RuntimeError("Invalid Claude response payload.")
    text_chunks: list[str] = []
    for chunk in content:
        if isinstance(chunk, dict) and chunk.get("type") == "text":
            text = chunk.get("text", "")
            if isinstance(text, str) and text.strip():
                text_chunks.append(text)
    return "\n".join(text_chunks).strip() if text_chunks else None


def get_learning_progress_for_clinician(clinician_user_id: int):
    rows = get_db().execute(
        """
        SELECT *
        FROM practitioner_learning_progress
        WHERE clinician_user_id = ?
        """,
        (clinician_user_id,),
    ).fetchall()
    return {row["topic_slug"]: row for row in rows}


def get_visit_report_for_patient(patient_user_id: int, visit_kind: str = "initial_consult"):
    return get_db().execute(
        """
        SELECT *
        FROM visit_reports
        WHERE patient_user_id = ? AND visit_kind = ?
        """,
        (patient_user_id, visit_kind),
    ).fetchone()


def get_locations(active_only: bool = True):
    query = """
        SELECT *
        FROM locations
    """
    params: tuple = ()
    if active_only:
        query += " WHERE active = 1"
    query += " ORDER BY name ASC, id ASC"
    return get_db().execute(query, params).fetchall()


def get_location(location_id: int):
    return get_db().execute(
        "SELECT * FROM locations WHERE id = ?",
        (location_id,),
    ).fetchone()


def get_latest_invitation_for_user(user_id: int):
    return get_db().execute(
        """
        SELECT *
        FROM invitations
        WHERE accepted_user_id = ?
        ORDER BY COALESCE(accepted_at, created_at) DESC
        LIMIT 1
        """,
        (user_id,),
    ).fetchone()


def get_invitation_by_token(token: str):
    return get_db().execute(
        "SELECT * FROM invitations WHERE token = ?",
        (token,),
    ).fetchone()


def get_reset_token(token: str):
    return get_db().execute(
        """
        SELECT prt.*, u.email, u.first_name, u.last_name
        FROM password_reset_tokens prt
        JOIN users u ON u.id = prt.user_id
        WHERE prt.token = ?
        """,
        (token,),
    ).fetchone()


def get_appointment_services(active_only: bool = True):
    query = """
        SELECT *
        FROM appointment_services
    """
    if active_only:
        query += " WHERE active = 1"
    query += " ORDER BY display_order ASC, label ASC, id ASC"
    return get_db().execute(query).fetchall()


def get_appointment_service(service_id: int):
    return get_db().execute(
        """
        SELECT *
        FROM appointment_services
        WHERE id = ?
        LIMIT 1
        """,
        (service_id,),
    ).fetchone()


def get_appointment_service_by_key(service_key: str):
    return get_db().execute(
        """
        SELECT *
        FROM appointment_services
        WHERE service_key = ?
        LIMIT 1
        """,
        (service_key,),
    ).fetchone()


def get_recent_booking_events(limit: int = 30):
    return get_db().execute(
        """
        SELECT
            bwe.*,
            a.starts_at,
            a.appointment_type,
            a.service_label_snapshot,
            p.first_name AS patient_first_name,
            p.last_name AS patient_last_name
        FROM booking_webhook_events bwe
        LEFT JOIN appointments a ON a.id = bwe.appointment_id
        LEFT JOIN users p ON p.id = bwe.patient_user_id
        ORDER BY bwe.created_at DESC, bwe.id DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()


def log_booking_event(
    event_type: str,
    appointment_id: int | None,
    patient_user_id: int | None,
    payload: dict | None = None,
    *,
    delivery_status: str = "pending",
) -> None:
    get_db().execute(
        """
        INSERT INTO booking_webhook_events (
            event_type,
            appointment_id,
            patient_user_id,
            payload_json,
            delivery_status,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            event_type,
            appointment_id,
            patient_user_id,
            json.dumps(payload or {}, separators=(",", ":")),
            delivery_status,
            iso_now(),
        ),
    )


def get_patient_appointments(patient_user_id: int):
    return get_db().execute(
        """
        SELECT
            a.*,
            l.name AS location_name,
            c.first_name AS clinician_first_name,
            c.last_name AS clinician_last_name,
            s.service_key,
            s.label AS service_label,
            s.description AS service_description,
            s.duration_minutes AS service_duration_minutes,
            s.buffer_before_minutes AS service_buffer_before_minutes,
            s.buffer_after_minutes AS service_buffer_after_minutes,
            s.requires_payment AS service_requires_payment,
            s.price_amount AS service_price_amount,
            s.currency AS service_currency,
            s.min_notice_minutes AS service_min_notice_minutes,
            s.max_bookings_per_day AS service_max_bookings_per_day,
            s.routing_mode AS service_routing_mode,
            asn.id AS soap_note_id,
            asn.updated_at AS soap_note_updated_at
        FROM appointments a
        LEFT JOIN locations l ON l.id = a.location_id
        LEFT JOIN users c ON c.id = a.clinician_user_id
        LEFT JOIN appointment_services s ON s.id = a.service_id
        LEFT JOIN appointment_soap_notes asn ON asn.appointment_id = a.id
        WHERE a.patient_user_id = ?
        ORDER BY a.starts_at ASC
        """,
        (patient_user_id,),
    ).fetchall()


def get_patient_appointment(patient_user_id: int, appointment_id: int):
    return get_db().execute(
        """
        SELECT *
        FROM appointments
        WHERE id = ? AND patient_user_id = ?
        """,
        (appointment_id, patient_user_id),
    ).fetchone()


def get_appointment_with_people(appointment_id: int):
    return get_db().execute(
        """
        SELECT
            a.*,
            p.first_name AS patient_first_name,
            p.last_name AS patient_last_name,
            p.email AS patient_email,
            l.name AS location_name,
            c.first_name AS clinician_first_name,
            c.last_name AS clinician_last_name,
            s.service_key,
            s.label AS service_label,
            s.description AS service_description,
            s.duration_minutes AS service_duration_minutes,
            s.buffer_before_minutes AS service_buffer_before_minutes,
            s.buffer_after_minutes AS service_buffer_after_minutes,
            s.requires_payment AS service_requires_payment,
            s.price_amount AS service_price_amount,
            s.currency AS service_currency,
            s.min_notice_minutes AS service_min_notice_minutes,
            s.max_bookings_per_day AS service_max_bookings_per_day,
            s.routing_mode AS service_routing_mode,
            asn.id AS soap_note_id,
            asn.updated_at AS soap_note_updated_at
        FROM appointments a
        JOIN users p ON p.id = a.patient_user_id
        LEFT JOIN locations l ON l.id = a.location_id
        LEFT JOIN users c ON c.id = a.clinician_user_id
        LEFT JOIN appointment_services s ON s.id = a.service_id
        LEFT JOIN appointment_soap_notes asn ON asn.appointment_id = a.id
        WHERE a.id = ?
        """,
        (appointment_id,),
    ).fetchone()


def get_all_appointments():
    return get_db().execute(
        """
        SELECT
            a.*,
            p.first_name AS patient_first_name,
            p.last_name AS patient_last_name,
            p.email AS patient_email,
            l.name AS location_name,
            c.first_name AS clinician_first_name,
            c.last_name AS clinician_last_name,
            s.service_key,
            s.label AS service_label,
            s.description AS service_description,
            s.duration_minutes AS service_duration_minutes,
            s.buffer_before_minutes AS service_buffer_before_minutes,
            s.buffer_after_minutes AS service_buffer_after_minutes,
            s.requires_payment AS service_requires_payment,
            s.price_amount AS service_price_amount,
            s.currency AS service_currency,
            s.min_notice_minutes AS service_min_notice_minutes,
            s.max_bookings_per_day AS service_max_bookings_per_day,
            s.routing_mode AS service_routing_mode,
            asn.id AS soap_note_id,
            asn.updated_at AS soap_note_updated_at
        FROM appointments a
        JOIN users p ON p.id = a.patient_user_id
        LEFT JOIN locations l ON l.id = a.location_id
        LEFT JOIN users c ON c.id = a.clinician_user_id
        LEFT JOIN appointment_services s ON s.id = a.service_id
        LEFT JOIN appointment_soap_notes asn ON asn.appointment_id = a.id
        ORDER BY a.starts_at ASC
        """
    ).fetchall()


def get_clinician_appointments(clinician_user_id: int):
    return get_db().execute(
        """
        SELECT
            a.*,
            p.first_name AS patient_first_name,
            p.last_name AS patient_last_name,
            p.email AS patient_email,
            l.name AS location_name,
            c.first_name AS clinician_first_name,
            c.last_name AS clinician_last_name,
            s.service_key,
            s.label AS service_label,
            s.description AS service_description,
            s.duration_minutes AS service_duration_minutes,
            s.buffer_before_minutes AS service_buffer_before_minutes,
            s.buffer_after_minutes AS service_buffer_after_minutes,
            s.requires_payment AS service_requires_payment,
            s.price_amount AS service_price_amount,
            s.currency AS service_currency,
            s.min_notice_minutes AS service_min_notice_minutes,
            s.max_bookings_per_day AS service_max_bookings_per_day,
            s.routing_mode AS service_routing_mode,
            asn.id AS soap_note_id,
            asn.updated_at AS soap_note_updated_at
        FROM appointments a
        JOIN users p ON p.id = a.patient_user_id
        LEFT JOIN locations l ON l.id = a.location_id
        LEFT JOIN users c ON c.id = a.clinician_user_id
        LEFT JOIN appointment_services s ON s.id = a.service_id
        LEFT JOIN appointment_soap_notes asn ON asn.appointment_id = a.id
        WHERE a.clinician_user_id = ?
        ORDER BY a.starts_at ASC, a.id ASC
        """,
        (clinician_user_id,),
    ).fetchall()


def get_appointment_soap_note(appointment_id: int):
    return get_db().execute(
        """
        SELECT *
        FROM appointment_soap_notes
        WHERE appointment_id = ?
        """,
        (appointment_id,),
    ).fetchone()


def get_active_care_plan(patient_user_id: int):
    return get_db().execute(
        """
        SELECT
            cp.*,
            s.label AS service_label,
            s.description AS service_description,
            s.duration_minutes AS service_duration_minutes,
            s.price_amount AS service_price_amount,
            s.currency AS service_currency
        FROM care_plans cp
        LEFT JOIN appointment_services s ON s.id = cp.service_id
        WHERE cp.patient_user_id = ?
          AND cp.status = 'active'
        ORDER BY cp.id DESC
        LIMIT 1
        """,
        (patient_user_id,),
    ).fetchone()


def get_care_plan_visits(care_plan_id: int):
    return get_db().execute(
        """
        SELECT *
        FROM care_plan_visits
        WHERE care_plan_id = ?
        ORDER BY visit_number ASC, id ASC
        """,
        (care_plan_id,),
    ).fetchall()


def get_care_plan_visit(visit_id: int):
    return get_db().execute(
        """
        SELECT
            cpv.*,
            cp.patient_user_id,
            cp.clinician_user_id AS plan_clinician_user_id,
            cp.location_id AS plan_location_id,
            cp.service_id AS plan_service_id,
            cp.booking_mode AS plan_booking_mode,
            cp.status AS plan_status
        FROM care_plan_visits cpv
        JOIN care_plans cp ON cp.id = cpv.care_plan_id
        WHERE cpv.id = ?
        LIMIT 1
        """,
        (visit_id,),
    ).fetchone()


def archive_active_care_plans(patient_user_id: int) -> int:
    db = get_db()
    active_ids = [
        row["id"]
        for row in db.execute(
            """
            SELECT id
            FROM care_plans
            WHERE patient_user_id = ?
              AND status = 'active'
            """,
            (patient_user_id,),
        ).fetchall()
    ]
    if not active_ids:
        return 0
    now = iso_now()
    db.execute(
        """
        UPDATE care_plans
        SET status = 'archived',
            updated_at = ?
        WHERE patient_user_id = ?
          AND status = 'active'
        """,
        (now, patient_user_id),
    )
    return len(active_ids)


def normalize_care_plan_frequency(value: str | None) -> int | None:
    parsed = int_or_none(value)
    if isinstance(parsed, int) and parsed in {option["value"] for option in CARE_PLAN_FREQUENCY_OPTIONS}:
        return parsed
    return None


def normalize_care_plan_weeks(value: str | None) -> int | None:
    parsed = int_or_none(value)
    if isinstance(parsed, int) and parsed in CARE_PLAN_WEEK_OPTIONS:
        return parsed
    return None


def normalize_care_plan_booking_mode(value: str | None) -> str | None:
    raw_value = (value or "").strip().lower()
    if raw_value in CARE_PLAN_BOOKING_MODE_META:
        return raw_value
    return None


def care_plan_title_default(duration_weeks: int, frequency_per_week: int) -> str:
    weekly_label = "Twice weekly" if frequency_per_week == 2 else "Weekly"
    return f"{duration_weeks}-week {weekly_label.lower()} care plan"


def care_plan_visit_label(visit_number: int, visit_kind: str) -> str:
    meta = care_plan_visit_meta(visit_kind)
    if visit_kind == "follow_up":
        return f"Visit {visit_number}"
    return f"Visit {visit_number} - {meta['label']}"


def move_care_plan_start_off_weekend(starts_at: datetime) -> datetime:
    current = starts_at
    while current.weekday() >= 5:
        current += timedelta(days=1)
    return current


def next_care_plan_visit_start(current_start: datetime, frequency_per_week: int) -> datetime:
    safe_start = move_care_plan_start_off_weekend(current_start)
    if frequency_per_week == 1:
        return move_care_plan_start_off_weekend(safe_start + timedelta(days=7))
    if safe_start.weekday() <= 2:
        return move_care_plan_start_off_weekend(safe_start + timedelta(days=3))
    return move_care_plan_start_off_weekend(safe_start + timedelta(days=7 - safe_start.weekday()))


def generate_care_plan_schedule(
    *,
    frequency_per_week: int,
    duration_weeks: int,
    starts_at: datetime,
    follow_up_duration_minutes: int,
    patient_details: str,
    note: str,
    fee_amount: float | None,
) -> dict:
    total_visits = frequency_per_week * duration_weeks
    midpoint_visit_number = (total_visits + 1) // 2
    current_start = move_care_plan_start_off_weekend(starts_at)
    review_duration_minutes = max(30, follow_up_duration_minutes)
    visits = []
    for visit_number in range(1, total_visits + 1):
        visit_kind = "follow_up"
        duration_minutes = follow_up_duration_minutes
        if visit_number == midpoint_visit_number:
            visit_kind = "progress_check"
            duration_minutes = review_duration_minutes
        if visit_number == total_visits:
            visit_kind = "reassessment"
            duration_minutes = review_duration_minutes
        visits.append(
            {
                "visit_number": visit_number,
                "visit_kind": visit_kind,
                "label": care_plan_visit_label(visit_number, visit_kind),
                "suggested_date": current_start.date().isoformat(),
                "suggested_starts_at": format_datetime_local(current_start),
                "duration_minutes": duration_minutes,
                "fee_amount": fee_amount,
                "patient_details": patient_details,
                "note": note,
            }
        )
        current_start = next_care_plan_visit_start(current_start, frequency_per_week)
    return {
        "total_visits": total_visits,
        "midpoint_visit_number": midpoint_visit_number,
        "visits": visits,
    }


def care_plan_visit_policy(base_policy: dict, visit_seed: dict) -> dict:
    visit_kind = visit_seed["visit_kind"]
    if visit_kind == "follow_up":
        return dict(base_policy)
    return {
        **base_policy,
        "service_id": None,
        "service_key": None,
        "service_label": care_plan_visit_meta(visit_kind)["label"],
        "duration_minutes": visit_seed["duration_minutes"],
    }


def find_care_plan_slot(
    preferred_start: datetime,
    clinician_user_id: int | None,
    location_id: int | None,
    booking_policy: dict,
    *,
    slot_increment_minutes: int = DEFAULT_SLOT_INCREMENT_MINUTES,
):
    exact_assignment = resolve_slot_assignment(
        preferred_start,
        clinician_user_id,
        location_id,
        booking_policy,
        slot_increment_minutes=slot_increment_minutes,
    )
    if exact_assignment is not None:
        return exact_assignment

    availability = build_schedule_availability(
        preferred_start.date().isoformat(),
        clinician_user_id,
        location_id,
        booking_policy["duration_minutes"],
        booking_policy=booking_policy,
        slot_increment_minutes=slot_increment_minutes,
    )
    if not availability["available_slots"]:
        return None

    preferred_clock = preferred_start.strftime("%H:%M")
    later_slots = [
        item for item in availability["available_slots"]
        if item["value"][11:16] >= preferred_clock
    ]
    if later_slots:
        return later_slots[0]
    return availability["available_slots"][0]


def refresh_care_plan_status(care_plan_id: int) -> None:
    rows = get_db().execute(
        """
        SELECT status
        FROM care_plan_visits
        WHERE care_plan_id = ?
        """,
        (care_plan_id,),
    ).fetchall()
    if not rows:
        return
    statuses = {row["status"] for row in rows}
    next_status = "active"
    if statuses.issubset({"completed", "cancelled"}):
        next_status = "completed"
    get_db().execute(
        """
        UPDATE care_plans
        SET status = ?,
            updated_at = ?
        WHERE id = ?
        """,
        (next_status, iso_now(), care_plan_id),
    )


def sync_care_plan_visit_for_appointment(appointment_id: int) -> None:
    row = get_db().execute(
        """
        SELECT cpv.id, cpv.care_plan_id, a.status, a.starts_at, a.patient_details, a.note
        FROM care_plan_visits cpv
        JOIN appointments a ON a.id = cpv.appointment_id
        WHERE cpv.appointment_id = ?
        LIMIT 1
        """,
        (appointment_id,),
    ).fetchone()
    if row is None:
        return
    visit_status = "scheduled"
    if row["status"] == "completed":
        visit_status = "completed"
    elif row["status"] == "cancelled":
        visit_status = "cancelled"
    get_db().execute(
        """
        UPDATE care_plan_visits
        SET status = ?,
            booked = 1,
            suggested_date = ?,
            suggested_starts_at = ?,
            patient_details = ?,
            note = ?,
            updated_at = ?
        WHERE id = ?
        """,
        (
            visit_status,
            row["starts_at"][:10],
            row["starts_at"],
            row["patient_details"] or "",
            row["note"] or "",
            iso_now(),
            row["id"],
        ),
    )
    refresh_care_plan_status(row["care_plan_id"])


def get_clinician_users():
    clinicians = get_db().execute(
        """
        SELECT id, first_name, last_name, email, role, COALESCE(is_active, 1) AS is_active
        FROM users
        WHERE role = 'clinician'
          AND COALESCE(is_active, 1) = 1
        ORDER BY first_name ASC, last_name ASC, email ASC
        """
    ).fetchall()
    if clinicians:
        return clinicians
    return get_db().execute(
        """
        SELECT id, first_name, last_name, email, role, COALESCE(is_active, 1) AS is_active
        FROM users
        WHERE role IN ('clinician', 'admin')
          AND COALESCE(is_active, 1) = 1
        ORDER BY first_name ASC, last_name ASC, email ASC
        """
    ).fetchall()


def get_location_options() -> list[dict]:
    return [
        {
            "value": row["id"],
            "label": row["name"],
            "address": row["address"],
            "phone": row["phone"],
            "timezone": row["timezone"],
        }
        for row in get_locations()
    ]


def get_schedule_windows():
    return get_db().execute(
        """
        SELECT
            sw.*,
            l.name AS location_name,
            u.first_name AS clinician_first_name,
            u.last_name AS clinician_last_name
        FROM schedule_windows sw
        LEFT JOIN locations l ON l.id = sw.location_id
        LEFT JOIN users u ON u.id = sw.clinician_user_id
        ORDER BY sw.weekday ASC, COALESCE(l.name, ''), sw.starts_time ASC, sw.ends_time ASC, sw.id ASC
        """
    ).fetchall()


def get_schedule_window(window_id: int):
    return get_db().execute("SELECT * FROM schedule_windows WHERE id = ?", (window_id,)).fetchone()


def get_schedule_windows_for_day(weekday: int, clinician_user_id: int | None, location_id: int | None):
    params: list = [weekday]
    query = """
        SELECT *
        FROM schedule_windows
        WHERE weekday = ?
    """
    if clinician_user_id is None:
        query += " AND clinician_user_id IS NULL"
    else:
        query += " AND (clinician_user_id IS NULL OR clinician_user_id = ?)"
        params.append(clinician_user_id)
    if location_id is None:
        query += " AND location_id IS NOT NULL"
    else:
        query += " AND location_id = ?"
        params.append(location_id)
    query += " ORDER BY starts_time ASC, ends_time ASC, id ASC"
    return get_db().execute(query, tuple(params)).fetchall()


def get_clinician_appointments_for_date(
    target_date: str,
    clinician_user_id: int | None,
    *,
    exclude_appointment_id: int | None = None,
):
    if clinician_user_id is None:
        return []

    params = [clinician_user_id, target_date]
    query = """
        SELECT
            a.*,
            p.first_name AS patient_first_name,
            p.last_name AS patient_last_name,
            p.email AS patient_email,
            c.first_name AS clinician_first_name,
            c.last_name AS clinician_last_name,
            s.service_key,
            s.label AS service_label,
            s.duration_minutes AS service_duration_minutes,
            s.buffer_before_minutes AS service_buffer_before_minutes,
            s.buffer_after_minutes AS service_buffer_after_minutes,
            s.min_notice_minutes AS service_min_notice_minutes,
            s.max_bookings_per_day AS service_max_bookings_per_day,
            s.routing_mode AS service_routing_mode
        FROM appointments a
        JOIN users p ON p.id = a.patient_user_id
        LEFT JOIN users c ON c.id = a.clinician_user_id
        LEFT JOIN appointment_services s ON s.id = a.service_id
        WHERE a.clinician_user_id = ?
          AND a.status = 'scheduled'
          AND substr(a.starts_at, 1, 10) = ?
    """
    if exclude_appointment_id is not None:
        query += " AND a.id != ?"
        params.append(exclude_appointment_id)
    query += " ORDER BY a.starts_at ASC"
    return get_db().execute(query, tuple(params)).fetchall()


def get_clinician_booking_count_by_date(target_date: str) -> dict[int, int]:
    rows = get_db().execute(
        """
        SELECT clinician_user_id, COUNT(*) AS booking_count
        FROM appointments
        WHERE status = 'scheduled'
          AND clinician_user_id IS NOT NULL
          AND substr(starts_at, 1, 10) = ?
        GROUP BY clinician_user_id
        """,
        (target_date,),
    ).fetchall()
    return {row["clinician_user_id"]: row["booking_count"] for row in rows}


def get_recent_appointment_reminders(limit: int = 30):
    return get_db().execute(
        """
        SELECT
            ar.*,
            a.appointment_type,
            a.starts_at,
            p.first_name AS patient_first_name,
            p.last_name AS patient_last_name
        FROM appointment_reminders ar
        JOIN appointments a ON a.id = ar.appointment_id
        JOIN users p ON p.id = ar.patient_user_id
        ORDER BY COALESCE(ar.sent_at, ar.created_at) DESC, ar.id DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()


def month_start_from_value(value: str | None) -> date:
    if value:
        try:
            parsed = datetime.strptime(value, "%Y-%m")
            return date(parsed.year, parsed.month, 1)
        except ValueError:
            pass
    today = date.today()
    return date(today.year, today.month, 1)


def shift_month(month_start: date, offset: int) -> date:
    year = month_start.year + ((month_start.month - 1 + offset) // 12)
    month = ((month_start.month - 1 + offset) % 12) + 1
    return date(year, month, 1)


def appointment_type_meta(appointment_type: str) -> dict:
    return APPOINTMENT_TYPE_META.get(
        appointment_type,
        {
            "label": appointment_type.replace("_", " ").title(),
            "short_label": appointment_type.replace("_", " ").title(),
            "tone": "sky",
        },
    )


def appointment_status_meta(status: str) -> dict:
    return APPOINTMENT_STATUS_META.get(
        status,
        {
            "label": status.replace("_", " ").title(),
            "tone": "sky",
        },
    )


def appointment_type_options() -> list[dict]:
    return [{"value": value, **meta} for value, meta in APPOINTMENT_TYPE_META.items()]


def appointment_status_options() -> list[dict]:
    return [{"value": value, **meta} for value, meta in APPOINTMENT_STATUS_META.items()]


def booking_routing_mode_meta(routing_mode: str) -> dict:
    if not routing_mode:
        routing_mode = "specific_clinician"
    return BOOKING_ROUTING_MODE_META.get(
        routing_mode,
        {"label": routing_mode.replace("_", " ").title()},
    )


def care_plan_visit_meta(visit_kind: str) -> dict:
    return CARE_PLAN_VISIT_META.get(
        visit_kind,
        {
            "label": visit_kind.replace("_", " ").title(),
            "tone": "sky",
            "icon": "..",
        },
    )


def care_plan_booking_mode_meta(booking_mode: str) -> dict:
    return CARE_PLAN_BOOKING_MODE_META.get(
        booking_mode,
        {
            "label": booking_mode.replace("_", " ").title(),
            "description": "",
        },
    )


def care_plan_frequency_options() -> list[dict]:
    return CARE_PLAN_FREQUENCY_OPTIONS


def care_plan_booking_mode_options() -> list[dict]:
    return [{"value": value, **meta} for value, meta in CARE_PLAN_BOOKING_MODE_META.items()]


def care_plan_week_options() -> list[int]:
    return CARE_PLAN_WEEK_OPTIONS


def build_appointment_service_item(row) -> dict:
    price_amount = row["price_amount"] if "price_amount" in row.keys() else None
    requires_payment = bool(row["requires_payment"]) if "requires_payment" in row.keys() else False
    routing_mode = row["routing_mode"] if "routing_mode" in row.keys() else "specific_clinician"
    appointment_type = row["appointment_type"] if "appointment_type" in row.keys() else "care_plan"
    return {
        "id": row["id"],
        "service_key": row["service_key"],
        "label": row["label"],
        "description": row["description"] if "description" in row.keys() else "",
        "appointment_type": appointment_type,
        "appointment_type_label": appointment_type_meta(appointment_type)["label"],
        "duration_minutes": row["duration_minutes"] if "duration_minutes" in row.keys() else 30,
        "buffer_before_minutes": row["buffer_before_minutes"] if "buffer_before_minutes" in row.keys() else 0,
        "buffer_after_minutes": row["buffer_after_minutes"] if "buffer_after_minutes" in row.keys() else 0,
        "requires_payment": requires_payment,
        "price_amount": price_amount,
        "currency": row["currency"] if "currency" in row.keys() else "GBP",
        "min_notice_minutes": row["min_notice_minutes"] if "min_notice_minutes" in row.keys() else 0,
        "max_bookings_per_day": row["max_bookings_per_day"] if "max_bookings_per_day" in row.keys() else None,
        "routing_mode": routing_mode,
        "routing_mode_label": booking_routing_mode_meta(routing_mode)["label"],
        "active": bool(row["active"]) if "active" in row.keys() else True,
        "display_order": row["display_order"] if "display_order" in row.keys() else 0,
        "price_label": f"{price_amount:.2f}" if isinstance(price_amount, (int, float)) else None,
    }


def appointment_service_options(active_only: bool = True) -> list[dict]:
    return [build_appointment_service_item(row) for row in get_appointment_services(active_only=active_only)]


def selected_appointment_service(
    value: str | None = None,
    *,
    active_only: bool = True,
    fallback_to_default: bool = True,
):
    selected_id = int_or_none(value)
    services = appointment_service_options(active_only=active_only)
    if isinstance(selected_id, int):
        for service in services:
            if service["id"] == selected_id:
                return service
    return services[0] if services and fallback_to_default else None


def default_service_for_appointment_type(appointment_type: str):
    for service in appointment_service_options(active_only=True):
        if service["appointment_type"] == appointment_type:
            return service
    return None


def resolve_booking_policy(
    service: dict | None,
    appointment_type: str | None,
    duration_minutes: int | None,
) -> dict:
    if service is not None:
        return {
            "service_id": service["id"],
            "service_key": service["service_key"],
            "service_label": service["label"],
            "appointment_type": service["appointment_type"],
            "duration_minutes": service["duration_minutes"],
            "buffer_before_minutes": service["buffer_before_minutes"],
            "buffer_after_minutes": service["buffer_after_minutes"],
            "requires_payment": service["requires_payment"],
            "price_amount": service["price_amount"],
            "currency": service["currency"],
            "min_notice_minutes": service["min_notice_minutes"],
            "max_bookings_per_day": service["max_bookings_per_day"],
            "routing_mode": service["routing_mode"],
            "routing_mode_label": service["routing_mode_label"],
        }

    safe_type = appointment_type if appointment_type in APPOINTMENT_TYPE_META else "care_plan"
    safe_duration = duration_minutes if isinstance(duration_minutes, int) and duration_is_supported(duration_minutes) else default_duration_for_type(safe_type)
    return {
        "service_id": None,
        "service_key": None,
        "service_label": appointment_type_meta(safe_type)["label"],
        "appointment_type": safe_type,
        "duration_minutes": safe_duration,
        "buffer_before_minutes": 0,
        "buffer_after_minutes": 0,
        "requires_payment": False,
        "price_amount": None,
        "currency": "GBP",
        "min_notice_minutes": 0,
        "max_bookings_per_day": None,
        "routing_mode": "specific_clinician",
        "routing_mode_label": booking_routing_mode_meta("specific_clinician")["label"],
    }


def billing_status_meta(status: str) -> dict:
    return BILLING_STATUS_META.get(
        status,
        {
            "label": status.replace("_", " ").title(),
            "tone": "sky",
        },
    )


def billing_status_options() -> list[dict]:
    return [{"value": value, **meta} for value, meta in BILLING_STATUS_META.items()]


def appointment_duration_options() -> list[dict]:
    return APPOINTMENT_DURATION_OPTIONS


def message_topic_options() -> list[dict]:
    return [{"value": value, **meta} for value, meta in MESSAGE_TOPIC_META.items()]


def message_topic_meta(topic: str) -> dict:
    return MESSAGE_TOPIC_META.get(
        topic,
        {
            "label": topic.replace("_", " ").title(),
            "tone": "sky",
        },
    )


def default_duration_for_type(appointment_type: str) -> int:
    return APPOINTMENT_DURATION_DEFAULTS.get(appointment_type, 30)


def duration_is_supported(duration_minutes: int) -> bool:
    return any(option["value"] == duration_minutes for option in APPOINTMENT_DURATION_OPTIONS)


def slot_increment_options() -> list[dict]:
    return [{"value": minutes, "label": f"{minutes} minutes"} for minutes in SLOT_INCREMENT_OPTIONS]


def selected_slot_increment_minutes(value: str | None) -> int:
    parsed = int_or_none(value)
    if isinstance(parsed, int) and parsed in SLOT_INCREMENT_OPTIONS:
        return parsed
    setting_value = int_or_none(get_app_setting("calendar_slot_increment_minutes", str(DEFAULT_SLOT_INCREMENT_MINUTES)))
    if isinstance(setting_value, int) and setting_value in SLOT_INCREMENT_OPTIONS:
        return setting_value
    return DEFAULT_SLOT_INCREMENT_MINUTES


def weekday_options() -> list[dict]:
    return WEEKDAY_OPTIONS


def schedule_window_type_options() -> list[dict]:
    return [{"value": value, **meta} for value, meta in SCHEDULE_WINDOW_TYPE_META.items()]


def schedule_window_type_meta(window_type: str) -> dict:
    return SCHEDULE_WINDOW_TYPE_META.get(
        window_type,
        {
            "label": window_type.replace("_", " ").title(),
            "tone": "sky",
        },
    )


def time_from_value(value: str | None) -> time | None:
    if not value:
        return None
    try:
        return datetime.strptime(value, "%H:%M").time()
    except ValueError:
        return None


def date_from_value(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


def combine_date_time(target_date: date, time_value: str) -> datetime | None:
    parsed_time = time_from_value(time_value)
    if parsed_time is None:
        return None
    return datetime.combine(target_date, parsed_time)


def clinician_display_name(row) -> str:
    return f"{row['first_name']} {row['last_name']}".strip()


def clinician_options() -> list[dict]:
    return [
        {
            "value": row["id"],
            "label": clinician_display_name(row),
            "email": row["email"],
        }
        for row in get_clinician_users()
    ]


def location_options() -> list[dict]:
    return get_location_options()


def default_location_id() -> int | None:
    options = location_options()
    return options[0]["value"] if options else None


def selected_location_id(value: str | None = None) -> int | None:
    candidate = int_or_none(value)
    location_ids = {option["value"] for option in location_options()}
    if isinstance(candidate, int) and candidate in location_ids:
        return candidate
    return default_location_id()


def selected_clinician_user_id(value: str | None = None) -> int | None:
    candidate = int_or_none(value)
    clinician_ids = {option["value"] for option in clinician_options()}
    if isinstance(candidate, int) and candidate in clinician_ids:
        return candidate
    if g.user is not None and g.user["role"] == "clinician" and g.user["id"] in clinician_ids:
        return g.user["id"]
    options = clinician_options()
    return options[0]["value"] if options else None


def requested_clinician_user_id(value: str | None = None, *, allow_any: bool = False) -> int | None:
    raw = (value or "").strip().lower()
    if allow_any and raw in {"", "any", "team"}:
        return None
    return selected_clinician_user_id(value)


def weekday_label(weekday: int) -> str:
    for option in WEEKDAY_OPTIONS:
        if option["value"] == weekday:
            return option["label"]
    return str(weekday)


def build_schedule_window_item(row) -> dict:
    meta = schedule_window_type_meta(row["window_type"])
    clinician_name = None
    if "clinician_first_name" in row.keys() and row["clinician_first_name"]:
        clinician_name = f"{row['clinician_first_name']} {row['clinician_last_name']}".strip()
    return {
        "id": row["id"],
        "weekday": row["weekday"],
        "weekday_label": weekday_label(row["weekday"]),
        "window_type": row["window_type"],
        "window_type_label": meta["label"],
        "window_tone": meta["tone"],
        "starts_time": row["starts_time"],
        "ends_time": row["ends_time"],
        "time_label": format_time_range(time_from_value(row["starts_time"]), time_from_value(row["ends_time"])),
        "label": row["label"] or meta["label"],
        "location_id": row["location_id"] if "location_id" in row.keys() else None,
        "location_name": row["location_name"] if "location_name" in row.keys() else None,
        "clinician_user_id": row["clinician_user_id"] if "clinician_user_id" in row.keys() else None,
        "clinician_name": clinician_name,
    }


def build_weekly_schedule_context() -> list[dict]:
    grouped = {item["value"]: {"label": item["label"], "windows": []} for item in weekday_options()}
    for row in get_schedule_windows():
        grouped[row["weekday"]]["windows"].append(build_schedule_window_item(row))
    return [
        {
            "weekday": weekday,
            "label": grouped[weekday]["label"],
            "windows": grouped[weekday]["windows"],
        }
        for weekday in grouped
    ]


def next_booking_date(
    clinician_user_id: int | None = None,
    location_id: int | None = None,
    booking_policy: dict | None = None,
    slot_increment_minutes: int = DEFAULT_SLOT_INCREMENT_MINUTES,
) -> str:
    policy = booking_policy or resolve_booking_policy(None, "care_plan", 30)
    today = date.today()
    for offset in range(0, current_booking_search_window_days()):
        candidate = today + timedelta(days=offset)
        availability = build_schedule_availability(
            candidate.isoformat(),
            clinician_user_id,
            location_id,
            policy["duration_minutes"],
            booking_policy=policy,
            slot_increment_minutes=slot_increment_minutes,
        )
        if availability["available_slots"]:
            return candidate.isoformat()
    return today.isoformat()


def overlaps(start_a: datetime, end_a: datetime, start_b: datetime, end_b: datetime) -> bool:
    return start_a < end_b and start_b < end_a


def build_schedule_availability_for_clinician(
    target_date: date,
    clinician_user_id: int,
    location_id: int | None,
    booking_policy: dict,
    *,
    slot_increment_minutes: int = DEFAULT_SLOT_INCREMENT_MINUTES,
    exclude_appointment_id: int | None = None,
) -> dict:
    duration_minutes = booking_policy["duration_minutes"]
    duration = timedelta(minutes=duration_minutes)
    buffer_before = timedelta(minutes=max(int(booking_policy["buffer_before_minutes"] or 0), 0))
    buffer_after = timedelta(minutes=max(int(booking_policy["buffer_after_minutes"] or 0), 0))
    min_notice = timedelta(minutes=max(int(booking_policy["min_notice_minutes"] or 0), 0))
    max_bookings_per_day = booking_policy["max_bookings_per_day"]
    if not isinstance(max_bookings_per_day, int):
        max_bookings_per_day = None

    clinician_name = None
    for option in clinician_options():
        if option["value"] == clinician_user_id:
            clinician_name = option["label"]
            break

    window_rows = get_schedule_windows_for_day(target_date.weekday(), clinician_user_id, location_id)
    shift_windows = []
    downtime_windows = []
    for row in window_rows:
        start_at = combine_date_time(target_date, row["starts_time"])
        end_at = combine_date_time(target_date, row["ends_time"])
        if start_at is None or end_at is None or end_at <= start_at:
            continue
        item = {
            "id": row["id"],
            "window_type": row["window_type"],
            "window_type_label": schedule_window_type_meta(row["window_type"])["label"],
            "window_tone": schedule_window_type_meta(row["window_type"])["tone"],
            "label": row["label"] or schedule_window_type_meta(row["window_type"])["label"],
            "starts_time": row["starts_time"],
            "ends_time": row["ends_time"],
            "time_label": format_time_range(start_at, end_at),
            "location_id": row["location_id"],
            "starts_at": start_at,
            "ends_at": end_at,
            "clinician_user_id": clinician_user_id,
            "clinician_name": clinician_name,
        }
        if row["window_type"] == "shift":
            shift_windows.append(item)
        else:
            downtime_windows.append(item)

    booked_windows = []
    for row in get_clinician_appointments_for_date(
        target_date.isoformat(),
        clinician_user_id,
        exclude_appointment_id=exclude_appointment_id,
    ):
        starts_at = parse_iso(row["starts_at"])
        default_minutes = row["service_duration_minutes"] or default_duration_for_type(row["appointment_type"])
        ends_at = parse_iso(row["ends_at"]) or (starts_at + timedelta(minutes=default_minutes) if starts_at else None)
        if starts_at is None or ends_at is None:
            continue

        existing_buffer_before = timedelta(minutes=max(int(row["service_buffer_before_minutes"] or 0), 0))
        existing_buffer_after = timedelta(minutes=max(int(row["service_buffer_after_minutes"] or 0), 0))
        blocked_start = starts_at - existing_buffer_before
        blocked_end = ends_at + existing_buffer_after
        booked_windows.append(
            {
                "id": row["id"],
                "label": row["service_label"] or appointment_type_meta(row["appointment_type"])["label"],
                "time_label": format_time_range(starts_at, ends_at),
                "starts_at": starts_at,
                "ends_at": ends_at,
                "blocked_starts_at": blocked_start,
                "blocked_ends_at": blocked_end,
                "clinician_user_id": clinician_user_id,
                "clinician_name": clinician_name,
            }
        )

    daily_booking_count = len(booked_windows)
    if max_bookings_per_day is not None and daily_booking_count >= max_bookings_per_day:
        return {
            "available_slots": [],
            "shift_windows": shift_windows,
            "downtime_windows": downtime_windows,
            "booked_windows": booked_windows,
            "daily_booking_count": daily_booking_count,
            "max_bookings_per_day": max_bookings_per_day,
            "clinician_user_id": clinician_user_id,
            "clinician_name": clinician_name,
        }

    available_slots = []
    seen_values = set()
    now = datetime.now()
    slot_increment = timedelta(minutes=slot_increment_minutes)
    for shift_window in shift_windows:
        slot_start = shift_window["starts_at"]
        last_start = shift_window["ends_at"] - duration
        while slot_start <= last_start:
            slot_end = slot_start + duration
            blocked_start = slot_start - buffer_before
            blocked_end = slot_end + buffer_after
            slot_value = format_datetime_local(slot_start)

            if slot_start <= now + min_notice:
                slot_start += slot_increment
                continue
            if blocked_start < shift_window["starts_at"] or blocked_end > shift_window["ends_at"]:
                slot_start += slot_increment
                continue
            if any(overlaps(blocked_start, blocked_end, item["starts_at"], item["ends_at"]) for item in downtime_windows):
                slot_start += slot_increment
                continue
            if any(overlaps(blocked_start, blocked_end, item["blocked_starts_at"], item["blocked_ends_at"]) for item in booked_windows):
                slot_start += slot_increment
                continue
            if slot_value not in seen_values:
                available_slots.append(
                    {
                        "value": slot_value,
                        "label": format_time_range(slot_start, slot_end),
                        "start_label": format_time_label(slot_start),
                        "end_label": format_time_label(slot_end),
                        "clinician_user_id": clinician_user_id,
                        "clinician_name": clinician_name,
                    }
                )
                seen_values.add(slot_value)
            slot_start += slot_increment

    return {
        "available_slots": available_slots,
        "shift_windows": shift_windows,
        "downtime_windows": downtime_windows,
        "booked_windows": booked_windows,
        "daily_booking_count": daily_booking_count,
        "max_bookings_per_day": max_bookings_per_day,
        "clinician_user_id": clinician_user_id,
        "clinician_name": clinician_name,
    }


def build_schedule_availability(
    target_date_value: str | None,
    clinician_user_id: int | None,
    location_id: int | None,
    duration_minutes: int,
    *,
    booking_policy: dict | None = None,
    slot_increment_minutes: int = DEFAULT_SLOT_INCREMENT_MINUTES,
    exclude_appointment_id: int | None = None,
) -> dict:
    slot_increment_minutes = selected_slot_increment_minutes(str(slot_increment_minutes))
    policy = booking_policy or resolve_booking_policy(None, "care_plan", duration_minutes)
    target_date = date_from_value(target_date_value)
    if target_date is None:
        return {
            "date_value": target_date_value or "",
            "date_label": target_date_value or "",
            "location_id": location_id,
            "duration_minutes": policy["duration_minutes"],
            "buffer_before_minutes": policy["buffer_before_minutes"],
            "buffer_after_minutes": policy["buffer_after_minutes"],
            "min_notice_minutes": policy["min_notice_minutes"],
            "max_bookings_per_day": policy["max_bookings_per_day"],
            "routing_mode": policy["routing_mode"],
            "routing_mode_label": policy["routing_mode_label"],
            "service_id": policy["service_id"],
            "service_label": policy["service_label"],
            "appointment_type": policy["appointment_type"],
            "requires_payment": policy["requires_payment"],
            "price_amount": policy["price_amount"],
            "currency": policy["currency"],
            "slot_increment_minutes": slot_increment_minutes,
            "available_slots": [],
            "shift_windows": [],
            "downtime_windows": [],
            "booked_windows": [],
            "error": "Choose a valid date.",
        }

    today = date.today()
    latest_allowed_date = today + timedelta(days=current_booking_search_window_days())
    if target_date > latest_allowed_date:
        return {
            "date_value": target_date.isoformat(),
            "date_label": target_date.strftime("%A %d %B %Y"),
            "location_id": location_id,
            "duration_minutes": policy["duration_minutes"],
            "buffer_before_minutes": policy["buffer_before_minutes"],
            "buffer_after_minutes": policy["buffer_after_minutes"],
            "min_notice_minutes": policy["min_notice_minutes"],
            "max_bookings_per_day": policy["max_bookings_per_day"],
            "routing_mode": policy["routing_mode"],
            "routing_mode_label": policy["routing_mode_label"],
            "service_id": policy["service_id"],
            "service_label": policy["service_label"],
            "appointment_type": policy["appointment_type"],
            "requires_payment": policy["requires_payment"],
            "price_amount": policy["price_amount"],
            "currency": policy["currency"],
            "slot_increment_minutes": slot_increment_minutes,
            "available_slots": [],
            "shift_windows": [],
            "downtime_windows": [],
            "booked_windows": [],
            "error": f"Bookings are currently limited to the next {current_booking_search_window_days()} days.",
        }
    if not same_day_booking_enabled() and target_date <= today:
        return {
            "date_value": target_date.isoformat(),
            "date_label": target_date.strftime("%A %d %B %Y"),
            "location_id": location_id,
            "duration_minutes": policy["duration_minutes"],
            "buffer_before_minutes": policy["buffer_before_minutes"],
            "buffer_after_minutes": policy["buffer_after_minutes"],
            "min_notice_minutes": policy["min_notice_minutes"],
            "max_bookings_per_day": policy["max_bookings_per_day"],
            "routing_mode": policy["routing_mode"],
            "routing_mode_label": policy["routing_mode_label"],
            "service_id": policy["service_id"],
            "service_label": policy["service_label"],
            "appointment_type": policy["appointment_type"],
            "requires_payment": policy["requires_payment"],
            "price_amount": policy["price_amount"],
            "currency": policy["currency"],
            "slot_increment_minutes": slot_increment_minutes,
            "available_slots": [],
            "shift_windows": [],
            "downtime_windows": [],
            "booked_windows": [],
            "error": "Same-day bookings are disabled in clinic settings.",
        }

    routing_mode = policy["routing_mode"]
    if routing_mode == "team_round_robin" and clinician_user_id is None:
        clinician_ids = [option["value"] for option in clinician_options()]
    elif clinician_user_id is not None:
        clinician_ids = [clinician_user_id]
    else:
        fallback_clinician = selected_clinician_user_id()
        clinician_ids = [fallback_clinician] if fallback_clinician is not None else []

    per_clinician = []
    for current_clinician_id in clinician_ids:
        if current_clinician_id is None:
            continue
        per_clinician.append(
            build_schedule_availability_for_clinician(
                target_date,
                current_clinician_id,
                location_id,
                policy,
                slot_increment_minutes=slot_increment_minutes,
                exclude_appointment_id=exclude_appointment_id,
            )
        )

    available_slots = []
    shift_windows = []
    downtime_windows = []
    booked_windows = []

    if routing_mode == "team_round_robin" and len(per_clinician) > 1:
        slot_choices: dict[str, list[dict]] = {}
        booking_load = get_clinician_booking_count_by_date(target_date.isoformat())
        for availability in per_clinician:
            shift_windows.extend(availability["shift_windows"])
            downtime_windows.extend(availability["downtime_windows"])
            booked_windows.extend(availability["booked_windows"])
            for slot in availability["available_slots"]:
                slot_choices.setdefault(slot["value"], []).append(slot)

        for slot_value in sorted(slot_choices.keys()):
            candidates = slot_choices[slot_value]
            selected_slot = min(
                candidates,
                key=lambda slot_item: (
                    booking_load.get(slot_item["clinician_user_id"], 0),
                    slot_item["clinician_name"] or "",
                    slot_item["clinician_user_id"],
                ),
            )
            slot_label = selected_slot["label"]
            if selected_slot["clinician_name"]:
                slot_label = f"{slot_label} · {selected_slot['clinician_name']}"
            available_slots.append(
                {
                    **selected_slot,
                    "label": slot_label,
                }
            )
    else:
        for availability in per_clinician:
            shift_windows.extend(availability["shift_windows"])
            downtime_windows.extend(availability["downtime_windows"])
            booked_windows.extend(availability["booked_windows"])
            available_slots.extend(availability["available_slots"])
        available_slots.sort(key=lambda item: (item["value"], item.get("clinician_name") or ""))

    error = None
    if not clinician_ids:
        error = "No chiropractor accounts are available for booking."
    elif not per_clinician:
        error = "No chiropractor availability could be loaded."

    return {
        "date_value": target_date.isoformat(),
        "date_label": target_date.strftime("%A %d %B %Y"),
        "location_id": location_id,
        "duration_minutes": policy["duration_minutes"],
        "buffer_before_minutes": policy["buffer_before_minutes"],
        "buffer_after_minutes": policy["buffer_after_minutes"],
        "min_notice_minutes": policy["min_notice_minutes"],
        "max_bookings_per_day": policy["max_bookings_per_day"],
        "routing_mode": policy["routing_mode"],
        "routing_mode_label": policy["routing_mode_label"],
        "service_id": policy["service_id"],
        "service_label": policy["service_label"],
        "appointment_type": policy["appointment_type"],
        "requires_payment": policy["requires_payment"],
        "price_amount": policy["price_amount"],
        "currency": policy["currency"],
        "slot_increment_minutes": slot_increment_minutes,
        "available_slots": available_slots,
        "shift_windows": shift_windows,
        "downtime_windows": downtime_windows,
        "booked_windows": booked_windows,
        "error": error,
    }


def serialize_schedule_availability(availability: dict) -> dict:
    return {
        "date_value": availability["date_value"],
        "date_label": availability["date_label"],
        "location_id": availability["location_id"],
        "error": availability["error"],
        "duration_minutes": availability["duration_minutes"],
        "slot_increment_minutes": availability["slot_increment_minutes"],
        "buffer_before_minutes": availability["buffer_before_minutes"],
        "buffer_after_minutes": availability["buffer_after_minutes"],
        "min_notice_minutes": availability["min_notice_minutes"],
        "max_bookings_per_day": availability["max_bookings_per_day"],
        "routing_mode": availability["routing_mode"],
        "routing_mode_label": availability["routing_mode_label"],
        "service_id": availability["service_id"],
        "service_label": availability["service_label"],
        "appointment_type": availability["appointment_type"],
        "requires_payment": availability["requires_payment"],
        "price_amount": availability["price_amount"],
        "currency": availability["currency"],
        "available_slots": [
            {
                "value": item["value"],
                "label": item["label"],
                "start_label": item["start_label"],
                "end_label": item["end_label"],
                "clinician_user_id": item.get("clinician_user_id"),
                "clinician_name": item.get("clinician_name"),
            }
            for item in availability["available_slots"]
        ],
        "shift_windows": [
            {
                "id": item["id"],
                "label": item["label"],
                "time_label": item["time_label"],
                "window_type": item["window_type"],
                "window_type_label": item["window_type_label"],
                "window_tone": item["window_tone"],
                "clinician_user_id": item.get("clinician_user_id"),
                "clinician_name": item.get("clinician_name"),
            }
            for item in availability["shift_windows"]
        ],
        "downtime_windows": [
            {
                "id": item["id"],
                "label": item["label"],
                "time_label": item["time_label"],
                "window_type": item["window_type"],
                "window_type_label": item["window_type_label"],
                "window_tone": item["window_tone"],
                "clinician_user_id": item.get("clinician_user_id"),
                "clinician_name": item.get("clinician_name"),
            }
            for item in availability["downtime_windows"]
        ],
        "booked_windows": [
            {
                "id": item["id"],
                "label": item["label"],
                "time_label": item["time_label"],
                "clinician_user_id": item.get("clinician_user_id"),
                "clinician_name": item.get("clinician_name"),
            }
            for item in availability["booked_windows"]
        ],
    }


def resolve_slot_assignment(
    starts_at: datetime,
    clinician_user_id: int | None,
    location_id: int | None,
    booking_policy: dict,
    *,
    slot_increment_minutes: int = DEFAULT_SLOT_INCREMENT_MINUTES,
    exclude_appointment_id: int | None = None,
):
    availability = build_schedule_availability(
        starts_at.date().isoformat(),
        clinician_user_id,
        location_id,
        booking_policy["duration_minutes"],
        booking_policy=booking_policy,
        slot_increment_minutes=slot_increment_minutes,
        exclude_appointment_id=exclude_appointment_id,
    )
    slot_value = format_datetime_local(starts_at)
    for slot in availability["available_slots"]:
        if slot["value"] == slot_value:
            return slot
    return None


def slot_is_available(
    starts_at: datetime,
    clinician_user_id: int | None,
    location_id: int | None,
    duration_minutes: int,
    *,
    booking_policy: dict | None = None,
    slot_increment_minutes: int = DEFAULT_SLOT_INCREMENT_MINUTES,
    exclude_appointment_id: int | None = None,
) -> bool:
    policy = booking_policy or resolve_booking_policy(None, "care_plan", duration_minutes)
    return resolve_slot_assignment(
        starts_at,
        clinician_user_id,
        location_id,
        policy,
        slot_increment_minutes=slot_increment_minutes,
        exclude_appointment_id=exclude_appointment_id,
    ) is not None


def reminder_channel_meta(channel: str) -> dict:
    return REMINDER_CHANNEL_META.get(
        channel,
        {
            "label": channel.upper(),
            "tone": "sky",
        },
    )


def reminder_delivery_status_meta(status: str) -> dict:
    return REMINDER_DELIVERY_STATUS_META.get(
        status,
        {
            "label": status.replace("_", " ").title(),
            "tone": "sky",
        },
    )


def get_patient_contact_details(patient_user_id: int) -> dict:
    patient = get_client_user(patient_user_id)
    submission = get_submission_for_user(patient_user_id)
    phone = ""
    if submission is not None:
        try:
            payload = json.loads(submission["payload_json"])
        except (TypeError, ValueError, json.JSONDecodeError):
            payload = {}
        phone = str(payload.get("patient", {}).get("phone") or "").strip()

    return {
        "patient_email": patient["email"] if patient is not None else "",
        "patient_phone": phone,
    }


def decorate_appointment_contacts(appointment: dict) -> dict:
    contact = get_patient_contact_details(appointment["patient_user_id"])
    appointment["patient_email"] = appointment.get("patient_email") or contact["patient_email"]
    appointment["patient_phone"] = contact["patient_phone"]
    appointment["can_email"] = bool(appointment["patient_email"]) and reminder_channel_enabled("email")
    appointment["can_sms"] = bool(appointment["patient_phone"]) and reminder_channel_enabled("sms")
    return appointment


def build_reminder_delivery_item(row) -> dict:
    channel_meta = reminder_channel_meta(row["channel"])
    status_meta = reminder_delivery_status_meta(row["status"])
    payload = {
        "channel": row["channel"],
        "recipient": row["recipient"],
        "subject": row["subject"],
        "message": row["message"],
    }
    return {
        "id": row["id"],
        "appointment_id": row["appointment_id"],
        "patient_user_id": row["patient_user_id"],
        "patient_name": f"{row['patient_first_name']} {row['patient_last_name']}".strip(),
        "appointment_type_label": appointment_type_meta(row["appointment_type"])["label"],
        "starts_label": format_schedule(row["starts_at"]) or row["starts_at"],
        "channel": row["channel"],
        "channel_label": channel_meta["label"],
        "channel_tone": channel_meta["tone"],
        "status": row["status"],
        "status_label": status_meta["label"],
        "status_tone": status_meta["tone"],
        "delivery_mode": row["delivery_mode"],
        "recipient": row["recipient"],
        "subject": row["subject"],
        "message": row["message"],
        "error_message": row["error_message"],
        "created_at": row["created_at"],
        "sent_at": row["sent_at"],
        "launch_link": build_delivery_launch_link(payload),
    }


def build_booking_event_item(row) -> dict:
    event_type = row["event_type"]
    payload_json = row["payload_json"] or "{}"
    try:
        payload = json.loads(payload_json)
    except (TypeError, ValueError, json.JSONDecodeError):
        payload = {}
    return {
        "id": row["id"],
        "event_type": event_type,
        "event_label": event_type.replace("_", " ").title(),
        "appointment_id": row["appointment_id"],
        "appointment_type": row["appointment_type"],
        "appointment_type_label": appointment_type_meta(row["appointment_type"])["label"] if row["appointment_type"] else "Unknown",
        "service_label": row["service_label_snapshot"] or payload.get("service_label") or "Unspecified service",
        "patient_user_id": row["patient_user_id"],
        "patient_name": f"{row['patient_first_name']} {row['patient_last_name']}".strip() if row["patient_first_name"] else "Unknown patient",
        "starts_at": row["starts_at"],
        "starts_label": format_schedule(row["starts_at"]) if row["starts_at"] else None,
        "created_at": row["created_at"],
        "created_label": format_schedule(row["created_at"]) or row["created_at"],
        "delivery_status": row["delivery_status"],
        "payload": payload,
    }


def log_appointment_reminder(
    appointment: dict,
    channel: str,
    payload: dict,
    *,
    status: str,
    delivery_mode: str,
    error_message: str = "",
) -> None:
    now = iso_now()
    sent_at = now if status in {"logged", "sent"} else None
    get_db().execute(
        """
        INSERT INTO appointment_reminders (
            appointment_id,
            patient_user_id,
            clinician_user_id,
            channel,
            delivery_mode,
            reminder_bucket,
            status,
            recipient,
            subject,
            message,
            error_message,
            created_at,
            sent_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            appointment["id"],
            appointment["patient_user_id"],
            g.user["id"],
            channel,
            delivery_mode,
            appointment["reminder_bucket"] or "manual",
            status,
            payload["recipient"],
            payload.get("subject", ""),
            payload["message"],
            error_message,
            now,
            sent_at,
        ),
    )


def existing_appointment_reminder(appointment_id: int, channel: str, reminder_bucket: str):
    return get_db().execute(
        """
        SELECT *
        FROM appointment_reminders
        WHERE appointment_id = ? AND channel = ? AND reminder_bucket = ? AND status IN ('logged', 'sent')
        ORDER BY COALESCE(sent_at, created_at) DESC, id DESC
        LIMIT 1
        """,
        (appointment_id, channel, reminder_bucket),
    ).fetchone()


def build_appointment_item(row) -> dict:
    starts_at = row["starts_at"]
    ends_at = row["ends_at"] if "ends_at" in row.keys() else None
    starts_parsed = parse_iso(starts_at)
    ends_parsed = parse_iso(ends_at)
    now = datetime.now()
    type_meta = appointment_type_meta(row["appointment_type"])
    status_meta = appointment_status_meta(row["status"])
    billing_meta = billing_status_meta(row["billing_status"]) if "billing_status" in row.keys() else billing_status_meta("pending")
    service_id = row["service_id"] if "service_id" in row.keys() else None
    service_key = row["service_key"] if "service_key" in row.keys() else None
    service_label = (
        (row["service_label"] if "service_label" in row.keys() else None)
        or (row["service_label_snapshot"] if "service_label_snapshot" in row.keys() else "")
        or type_meta["label"]
    )
    service_duration_minutes = (row["service_duration_minutes"] if "service_duration_minutes" in row.keys() else None) or None
    service_buffer_before_minutes = (row["service_buffer_before_minutes"] if "service_buffer_before_minutes" in row.keys() else 0) or 0
    service_buffer_after_minutes = (row["service_buffer_after_minutes"] if "service_buffer_after_minutes" in row.keys() else 0) or 0
    service_min_notice_minutes = (row["service_min_notice_minutes"] if "service_min_notice_minutes" in row.keys() else 0) or 0
    service_max_bookings_per_day = (row["service_max_bookings_per_day"] if "service_max_bookings_per_day" in row.keys() else None) or None
    service_routing_mode = (row["service_routing_mode"] if "service_routing_mode" in row.keys() else "specific_clinician") or "specific_clinician"
    service_currency = (row["service_currency"] if "service_currency" in row.keys() else "GBP") or "GBP"
    service_price_amount = row["service_price_amount"] if "service_price_amount" in row.keys() else None
    requires_payment = bool(row["requires_payment"]) if "requires_payment" in row.keys() else bool(row["service_requires_payment"] if "service_requires_payment" in row.keys() else 0)
    payment_status = row["payment_status"] if "payment_status" in row.keys() else ("pending" if requires_payment else "not_required")
    payment_amount = row["payment_amount"] if "payment_amount" in row.keys() else service_price_amount
    policy_snapshot = {}
    if "policy_snapshot_json" in row.keys() and row["policy_snapshot_json"]:
        try:
            policy_snapshot = json.loads(row["policy_snapshot_json"])
        except (TypeError, ValueError, json.JSONDecodeError):
            policy_snapshot = {}
    min_notice_value = policy_snapshot.get("min_notice_minutes", service_min_notice_minutes)
    policy_min_notice_minutes = int(min_notice_value) if isinstance(min_notice_value, int) else 0
    policy_min_notice_minutes = max(policy_min_notice_minutes, current_cancellation_window_minutes())
    cancellation_cutoff = starts_parsed - timedelta(minutes=policy_min_notice_minutes) if starts_parsed else None
    can_self_cancel = bool(
        starts_parsed
        and row["status"] == "scheduled"
        and cancellation_cutoff is not None
        and datetime.now() <= cancellation_cutoff
    )
    patient_name = None
    patient_first_name = None
    patient_last_name = None
    if "patient_first_name" in row.keys():
        patient_first_name = row["patient_first_name"]
        patient_last_name = row["patient_last_name"]
        patient_name = f"{row['patient_first_name']} {row['patient_last_name']}".strip()
    clinician_name = None
    if "clinician_first_name" in row.keys() and row["clinician_first_name"]:
        clinician_name = f"{row['clinician_first_name']} {row['clinician_last_name']}".strip()
    reminder_label = None
    reminder_tone = None
    reminder_bucket = None
    if starts_parsed and row["status"] == "scheduled":
        delta = starts_parsed - now
        if timedelta(0) <= delta <= timedelta(hours=24):
            reminder_label = "Within 24 hours"
            reminder_tone = "rose"
            reminder_bucket = "urgent"
        elif timedelta(hours=24) < delta <= timedelta(hours=72):
            reminder_label = "Reminder due soon"
            reminder_tone = "warm"
            reminder_bucket = "soon"
        elif timedelta(hours=72) < delta <= timedelta(days=7):
            reminder_label = "Coming up this week"
            reminder_tone = "sky"
            reminder_bucket = "week"
    soap_note_exists = "soap_note_id" in row.keys() and row["soap_note_id"] is not None
    soap_note_updated_at = row["soap_note_updated_at"] if "soap_note_updated_at" in row.keys() else None
    return {
        "id": row["id"],
        "patient_user_id": row["patient_user_id"],
        "clinician_user_id": row["clinician_user_id"] if "clinician_user_id" in row.keys() else None,
        "type": row["appointment_type"],
        "type_label": type_meta["label"],
        "type_short_label": type_meta["short_label"],
        "type_tone": type_meta["tone"],
        "status": row["status"],
        "status_label": status_meta["label"],
        "status_tone": status_meta["tone"],
        "starts_at": starts_at,
        "ends_at": ends_at,
        "starts_label": format_schedule(starts_at) or starts_at,
        "date_label": starts_parsed.strftime("%d %b %Y") if starts_parsed else starts_at[:10],
        "time_label": format_time_label(starts_parsed) if starts_parsed else "",
        "end_time_label": format_time_label(ends_parsed) if ends_parsed else None,
        "starts_input": format_datetime_local(starts_parsed),
        "ends_input": format_datetime_local(ends_parsed),
        "day_key": starts_parsed.date().isoformat() if starts_parsed else starts_at[:10],
        "month_key": starts_parsed.strftime("%Y-%m") if starts_parsed else starts_at[:7],
        "location_id": row["location_id"] if "location_id" in row.keys() else None,
        "location_name": row["location_name"] if "location_name" in row.keys() else None,
        "service_id": service_id,
        "service_key": service_key,
        "service_label": service_label,
        "service_description": row["service_description"] if "service_description" in row.keys() else "",
        "service_duration_minutes": service_duration_minutes,
        "service_buffer_before_minutes": service_buffer_before_minutes,
        "service_buffer_after_minutes": service_buffer_after_minutes,
        "service_min_notice_minutes": service_min_notice_minutes,
        "service_max_bookings_per_day": service_max_bookings_per_day,
        "service_routing_mode": service_routing_mode,
        "service_routing_mode_label": booking_routing_mode_meta(service_routing_mode)["label"],
        "service_currency": service_currency,
        "service_price_amount": service_price_amount,
        "policy_snapshot": policy_snapshot,
        "policy_min_notice_minutes": policy_min_notice_minutes,
        "cancellation_cutoff_at": format_datetime_local(cancellation_cutoff),
        "can_self_cancel": can_self_cancel,
        "cancellation_policy_label": f"Changes allowed until {format_schedule(format_datetime_local(cancellation_cutoff))}" if cancellation_cutoff else None,
        "note": row["note"] or "",
        "patient_details": row["patient_details"] if "patient_details" in row.keys() else "",
        "clinical_note": row["clinical_note"] if "clinical_note" in row.keys() else "",
        "billing_status": row["billing_status"] if "billing_status" in row.keys() else "pending",
        "billing_status_label": billing_meta["label"],
        "billing_status_tone": billing_meta["tone"],
        "billing_code": row["billing_code"] if "billing_code" in row.keys() else "",
        "billing_amount": row["billing_amount"] if "billing_amount" in row.keys() else None,
        "requires_payment": requires_payment,
        "payment_status": payment_status,
        "payment_amount": payment_amount,
        "booking_channel": row["booking_channel"] if "booking_channel" in row.keys() else "portal",
        "booking_source": row["booking_source"] if "booking_source" in row.keys() else "staff_portal",
        "is_upcoming": bool(starts_parsed and row["status"] == "scheduled" and starts_parsed >= now),
        "patient_name": patient_name,
        "patient_first_name": patient_first_name,
        "patient_last_name": patient_last_name,
        "patient_email": row["patient_email"] if "patient_email" in row.keys() else None,
        "patient_phone": None,
        "clinician_name": clinician_name,
        "reminder_label": reminder_label,
        "reminder_tone": reminder_tone,
        "reminder_bucket": reminder_bucket,
        "has_soap_note": soap_note_exists,
        "soap_note_updated_at": soap_note_updated_at,
        "soap_note_updated_label": format_schedule(soap_note_updated_at) if soap_note_updated_at else None,
        "soap_note_action_label": "Edit SOAP note" if soap_note_exists else "Add SOAP note",
        "can_email": False,
        "can_sms": False,
    }


def appointment_needs_soap(appointment: dict) -> bool:
    if appointment.get("has_soap_note") or appointment["status"] == "cancelled":
        return False
    starts_at = parse_iso(appointment["starts_at"])
    if starts_at is None:
        return False
    return appointment["status"] == "completed" or starts_at <= datetime.now()


def serialize_appointment_for_api(item: dict, *, include_internal: bool = False) -> dict:
    data = {
        "id": item["id"],
        "patient_user_id": item["patient_user_id"],
        "clinician_user_id": item["clinician_user_id"],
        "location_id": item["location_id"],
        "location_name": item["location_name"],
        "service_id": item["service_id"],
        "service_key": item["service_key"],
        "service_label": item["service_label"],
        "service_duration_minutes": item["service_duration_minutes"],
        "service_buffer_before_minutes": item["service_buffer_before_minutes"],
        "service_buffer_after_minutes": item["service_buffer_after_minutes"],
        "service_routing_mode": item["service_routing_mode"],
        "service_routing_mode_label": item["service_routing_mode_label"],
        "appointment_type": item["type"],
        "appointment_type_label": item["type_label"],
        "status": item["status"],
        "status_label": item["status_label"],
        "starts_at": item["starts_at"],
        "ends_at": item["ends_at"],
        "starts_label": item["starts_label"],
        "date_label": item["date_label"],
        "time_label": item["time_label"],
        "end_time_label": item["end_time_label"],
        "note": item["note"],
        "patient_details": item["patient_details"],
        "booking_source": item["booking_source"],
        "clinician_name": item["clinician_name"],
        "billing_status": item["billing_status"],
        "billing_status_label": item["billing_status_label"],
        "billing_code": item["billing_code"],
        "billing_amount": item["billing_amount"],
        "requires_payment": item["requires_payment"],
        "payment_status": item["payment_status"],
        "payment_amount": item["payment_amount"],
        "booking_channel": item["booking_channel"],
        "can_self_cancel": item["can_self_cancel"],
        "cancellation_cutoff_at": item["cancellation_cutoff_at"],
    }
    if include_internal:
        data["clinical_note"] = item["clinical_note"]
        data["patient_email"] = item["patient_email"]
        data["patient_phone"] = item["patient_phone"]
    return data


def build_calendar_grid(appointments: list[dict], month_start: date) -> dict:
    appointments_by_day: dict[str, list[dict]] = {}
    for item in appointments:
        appointments_by_day.setdefault(item["day_key"], []).append(item)
    weeks = []
    for week in month_calendar.Calendar(firstweekday=0).monthdatescalendar(month_start.year, month_start.month):
        week_cells = []
        for day in week:
            week_cells.append(
                {
                    "iso": day.isoformat(),
                    "day": day.day,
                    "in_month": day.month == month_start.month,
                    "is_today": day == date.today(),
                    "appointments": appointments_by_day.get(day.isoformat(), []),
                }
            )
        weeks.append(week_cells)
    return {
        "month_label": month_start.strftime("%B %Y"),
        "month_value": month_start.strftime("%Y-%m"),
        "previous_month": shift_month(month_start, -1).strftime("%Y-%m"),
        "next_month": shift_month(month_start, 1).strftime("%Y-%m"),
        "weeks": weeks,
    }


def build_patient_schedule_context(patient_user_id: int, month_value: str | None = None) -> dict:
    month_start = month_start_from_value(month_value)
    appointments = [build_appointment_item(row) for row in get_patient_appointments(patient_user_id)]
    month_key = month_start.strftime("%Y-%m")
    upcoming = [item for item in appointments if item["is_upcoming"]]
    history = [item for item in appointments if not item["is_upcoming"]]
    history.sort(key=lambda item: item["starts_at"], reverse=True)
    month_items = [item for item in appointments if item["month_key"] == month_key]
    counts = {
        appointment_type: sum(1 for item in upcoming if item["type"] == appointment_type)
        for appointment_type in APPOINTMENT_TYPE_META
    }
    reminders = [
        item
        for item in upcoming
        if item["reminder_bucket"] in {"urgent", "soon", "week"}
    ]
    return {
        "all": appointments,
        "upcoming": upcoming,
        "history": history,
        "next_appointment": upcoming[0] if upcoming else None,
        "calendar": build_calendar_grid(month_items, month_start),
        "counts": counts,
        "reminders": reminders,
    }


def build_staff_calendar_context(month_value: str | None = None) -> dict:
    month_start = month_start_from_value(month_value)
    appointments = [build_appointment_item(row) for row in get_all_appointments()]
    month_key = month_start.strftime("%Y-%m")
    upcoming = [item for item in appointments if item["is_upcoming"]]
    month_items = [item for item in appointments if item["month_key"] == month_key]
    counts = {
        appointment_type: sum(1 for item in upcoming if item["type"] == appointment_type)
        for appointment_type in APPOINTMENT_TYPE_META
    }
    reminders = [
        item
        for item in upcoming
        if item["type"] in {"report_of_findings", "care_plan"} and item["reminder_bucket"] in {"urgent", "soon", "week"}
    ]
    reminders = [decorate_appointment_contacts(item) for item in reminders[:12]]
    service_inventory = appointment_service_options(active_only=False)
    service_counts: dict[int, int] = {}
    for item in upcoming:
        service_id = item.get("service_id")
        if isinstance(service_id, int):
            service_counts[service_id] = service_counts.get(service_id, 0) + 1
    for service in service_inventory:
        service["upcoming_count"] = service_counts.get(service["id"], 0)
    booking_events = [build_booking_event_item(row) for row in get_recent_booking_events(limit=40)]
    event_counts = {
        "pending": sum(1 for item in booking_events if item["delivery_status"] == "pending"),
        "delivered": sum(1 for item in booking_events if item["delivery_status"] == "delivered"),
        "failed": sum(1 for item in booking_events if item["delivery_status"] == "failed"),
    }
    return {
        "appointments": appointments,
        "upcoming": upcoming[:12],
        "calendar": build_calendar_grid(month_items, month_start),
        "counts": counts,
        "reminders": reminders,
        "locations": [dict(row) for row in get_locations(active_only=False)],
        "schedule_templates": build_weekly_schedule_context(),
        "service_inventory": service_inventory,
        "booking_events": booking_events[:12],
        "booking_event_counts": event_counts,
    }


def get_chiropractor_roster() -> list[dict]:
    rows = get_db().execute(
        """
        SELECT
            u.id,
            u.first_name,
            u.last_name,
            u.email,
            u.created_at,
            COALESCE(u.is_active, 1) AS is_active,
            (
                SELECT COUNT(*)
                FROM appointments a
                WHERE a.clinician_user_id = u.id
                  AND a.status = 'scheduled'
                  AND a.starts_at >= ?
            ) AS upcoming_appointment_count,
            (
                SELECT COUNT(*)
                FROM schedule_windows sw
                WHERE sw.clinician_user_id = u.id
            ) AS availability_template_count
        FROM users u
        WHERE u.role = 'clinician'
        ORDER BY COALESCE(u.is_active, 1) DESC, u.first_name ASC, u.last_name ASC, u.email ASC
        """,
        (current_local_timestamp(),),
    ).fetchall()
    roster = []
    for row in rows:
        full_name = f"{row['first_name']} {row['last_name']}".strip()
        roster.append(
            {
                "id": row["id"],
                "full_name": full_name,
                "email": row["email"],
                "created_label": format_schedule(row["created_at"]) or row["created_at"],
                "is_active": bool(row["is_active"]),
                "status_label": "Active" if row["is_active"] else "Inactive",
                "upcoming_appointment_count": row["upcoming_appointment_count"],
                "availability_template_count": row["availability_template_count"],
            }
        )
    return roster


def build_database_summary() -> dict:
    db_path = Path(current_app.config["DATABASE"])
    db = get_db()
    table_rows = db.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table' AND name NOT LIKE 'sqlite_%'
        ORDER BY name ASC
        """
    ).fetchall()
    counts = {
        "users": db.execute("SELECT COUNT(*) AS count FROM users").fetchone()["count"],
        "appointments": db.execute("SELECT COUNT(*) AS count FROM appointments").fetchone()["count"],
        "messages": db.execute("SELECT COUNT(*) AS count FROM patient_messages").fetchone()["count"],
        "journal_entries": db.execute("SELECT COUNT(*) AS count FROM practitioner_journal_entries").fetchone()["count"],
        "locations": db.execute("SELECT COUNT(*) AS count FROM locations").fetchone()["count"],
        "services": db.execute("SELECT COUNT(*) AS count FROM appointment_services").fetchone()["count"],
    }
    return {
        "path": str(db_path),
        "filename": db_path.name,
        "exists": db_path.exists(),
        "size_label": format_file_size(db_path.stat().st_size) if db_path.exists() else "Missing",
        "table_count": len(table_rows),
        "tables": [row["name"] for row in table_rows],
        "counts": counts,
        "engine": "SQLite",
    }


def build_staff_settings_context() -> dict:
    chiropractors = get_chiropractor_roster()
    active_chiropractor_count = sum(1 for item in chiropractors if item["is_active"])
    max_active_chiropractors = current_max_active_chiropractors()
    booking_events = [build_booking_event_item(row) for row in get_recent_booking_events(limit=12)]
    return {
        "app_settings": get_app_settings(),
        "time_format_options": TIME_FORMAT_OPTIONS,
        "slot_increment_options": slot_increment_options(),
        "booking_search_window_days": current_booking_search_window_days(),
        "max_active_chiropractors": max_active_chiropractors,
        "active_chiropractor_count": active_chiropractor_count,
        "remaining_chiropractor_capacity": max(max_active_chiropractors - active_chiropractor_count, 0),
        "chiropractors": chiropractors,
        "locations": [dict(row) for row in get_locations(active_only=False)],
        "schedule_templates": build_weekly_schedule_context(),
        "service_inventory": appointment_service_options(active_only=False),
        "database_summary": build_database_summary(),
        "booking_link": url_for("main.appointments", _external=True),
        "booking_events": booking_events,
        "booking_event_counts": {
            "pending": sum(1 for item in booking_events if item["delivery_status"] == "pending"),
            "delivered": sum(1 for item in booking_events if item["delivery_status"] == "delivered"),
            "failed": sum(1 for item in booking_events if item["delivery_status"] == "failed"),
        },
        "settings_lists": {
            "clinic_open_days": setting_list("clinic_open_days", ["Mon", "Tue", "Wed", "Thu", "Fri"]),
            "clinical_outcome_measures": setting_list("clinical_outcome_measures", ["NDI", "ODI"]),
            "billing_payment_methods": setting_list("billing_payment_methods", ["Card"]),
        },
    }


def settings_redirect_url() -> str:
    if (request.form.get("return_to") or "").strip() == "settings":
        return url_for("main.staff_settings", section=request.form.get("section") or None)
    return url_for("main.staff_calendar", month=request.form.get("month") or None)


def build_staff_reminders_context() -> dict:
    calendar_context = build_staff_calendar_context()
    deliveries = [build_reminder_delivery_item(row) for row in get_recent_appointment_reminders()]
    counts = {
        "logged": sum(1 for item in deliveries if item["status"] == "logged"),
        "sent": sum(1 for item in deliveries if item["status"] == "sent"),
        "failed": sum(1 for item in deliveries if item["status"] == "failed"),
    }
    return {
        "due_reminders": calendar_context["reminders"],
        "recent_deliveries": deliveries,
        "delivery_counts": counts,
        "email_mode": current_app.config.get("REMINDER_EMAIL_MODE", "outbox"),
        "sms_mode": current_app.config.get("REMINDER_SMS_MODE", "outbox"),
    }


def booking_selection_context(source: str = "client") -> dict:
    service_options = appointment_service_options(active_only=True)
    selected_service = selected_appointment_service(request.args.get("service_id"), active_only=True, fallback_to_default=True)
    selected_appointment_type = request.args.get("appointment_type", "").strip()
    if selected_service is not None and not selected_appointment_type:
        selected_appointment_type = selected_service["appointment_type"]
    if selected_appointment_type not in APPOINTMENT_TYPE_META:
        selected_appointment_type = "care_plan"
    selected_location = selected_location_id(request.args.get("location_id"))
    selected_duration = int_or_none(
        request.args.get(
            "duration_minutes",
            str(selected_service["duration_minutes"] if selected_service else default_duration_for_type(selected_appointment_type)),
        )
    )
    if not isinstance(selected_duration, int) or not duration_is_supported(selected_duration):
        selected_duration = selected_service["duration_minutes"] if selected_service else default_duration_for_type(selected_appointment_type)
    booking_policy = resolve_booking_policy(selected_service, selected_appointment_type, selected_duration)

    raw_clinician_value = request.args.get("clinician_user_id")
    selected_clinician = requested_clinician_user_id(
        raw_clinician_value,
        allow_any=booking_policy["routing_mode"] == "team_round_robin",
    )
    if booking_policy["routing_mode"] == "team_round_robin" and (raw_clinician_value or "").strip().lower() in {"", "any", "team"}:
        selected_clinician = None
        selected_clinician_choice = "any"
    else:
        selected_clinician_choice = str(selected_clinician) if selected_clinician is not None else ""

    booking_date = request.args.get("appointment_date") or next_booking_date(selected_clinician, selected_location, booking_policy)
    availability = build_schedule_availability(
        booking_date,
        selected_clinician,
        selected_location,
        booking_policy["duration_minutes"],
        booking_policy=booking_policy,
    )
    return {
        "location_options": location_options(),
        "clinician_options": clinician_options(),
        "service_options": service_options,
        "duration_options": appointment_duration_options(),
        "selected_location_id": selected_location,
        "selected_clinician_id": selected_clinician,
        "selected_clinician_choice": selected_clinician_choice,
        "selected_duration_minutes": booking_policy["duration_minutes"],
        "selected_appointment_type": selected_appointment_type,
        "selected_service_id": selected_service["id"] if selected_service else None,
        "booking_policy": booking_policy,
        "allow_any_clinician": booking_policy["routing_mode"] == "team_round_robin",
        "booking_date": booking_date,
        "booking_availability": availability,
        "booking_source": source,
    }


def create_patient_appointment(
    patient_user_id: int,
    clinician_user_id: int | None,
    location_id: int | None,
    appointment_type: str,
    starts_at: str,
    *,
    service_id: int | None = None,
    ends_at: str | None = None,
    note: str = "",
    patient_details: str = "",
    clinical_note: str = "",
    billing_status: str = "pending",
    billing_code: str = "",
    billing_amount: float | None = None,
    requires_payment: bool = False,
    payment_status: str | None = None,
    payment_amount: float | None = None,
    booking_channel: str = "portal",
    service_label_snapshot: str = "",
    policy_snapshot: dict | None = None,
    booking_source: str = "staff_portal",
    status: str = "scheduled",
    source_invitation_id: int | None = None,
) -> int:
    now = iso_now()
    resolved_payment_status = payment_status or ("pending" if requires_payment else "not_required")
    resolved_service_label = service_label_snapshot or appointment_type_meta(appointment_type)["label"]
    policy_snapshot_json = json.dumps(policy_snapshot or {}, separators=(",", ":"))
    cursor = get_db().execute(
        """
        INSERT INTO appointments (
            patient_user_id,
            clinician_user_id,
            location_id,
            service_id,
            appointment_type,
            status,
            starts_at,
            ends_at,
            source_invitation_id,
            note,
            patient_details,
            clinical_note,
            billing_status,
            billing_code,
            billing_amount,
            requires_payment,
            payment_status,
            payment_amount,
            booking_channel,
            service_label_snapshot,
            policy_snapshot_json,
            booking_source,
            created_at,
            updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            patient_user_id,
            clinician_user_id,
            location_id,
            service_id,
            appointment_type,
            status,
            starts_at,
            ends_at,
            source_invitation_id,
            note,
            patient_details,
            clinical_note,
            billing_status,
            billing_code,
            billing_amount,
            int(bool(requires_payment)),
            resolved_payment_status,
            payment_amount,
            booking_channel,
            resolved_service_label,
            policy_snapshot_json,
            booking_source,
            now,
            now,
        ),
    )
    return cursor.lastrowid


def ensure_patient_appointment(
    patient_user_id: int,
    clinician_user_id: int | None,
    location_id: int | None,
    appointment_type: str,
    starts_at: str | None,
    *,
    note: str = "",
    source_invitation_id: int | None = None,
) -> int | None:
    if not starts_at:
        return None

    db = get_db()
    existing = None
    if source_invitation_id is not None:
        existing = db.execute(
            "SELECT id FROM appointments WHERE source_invitation_id = ?",
            (source_invitation_id,),
        ).fetchone()
    if existing is None:
        existing = db.execute(
            """
            SELECT id
            FROM appointments
            WHERE patient_user_id = ?
              AND appointment_type = ?
              AND starts_at = ?
            LIMIT 1
            """,
            (patient_user_id, appointment_type, starts_at),
        ).fetchone()
    if existing is not None:
        return existing["id"]

    service = default_service_for_appointment_type(appointment_type)
    booking_policy = resolve_booking_policy(service, appointment_type, None)
    return create_patient_appointment(
        patient_user_id,
        clinician_user_id,
        location_id,
        appointment_type,
        starts_at,
        service_id=booking_policy["service_id"],
        requires_payment=booking_policy["requires_payment"],
        payment_status="pending" if booking_policy["requires_payment"] else "not_required",
        payment_amount=booking_policy["price_amount"],
        service_label_snapshot=booking_policy["service_label"],
        policy_snapshot=booking_policy,
        note=note,
        source_invitation_id=source_invitation_id,
    )


def complete_initial_consult_appointment(patient_user_id: int, clinician_user_id: int | None, visit_date: str) -> None:
    if not visit_date:
        return

    db = get_db()
    now = iso_now()
    visit_day = visit_date[:10]
    existing = db.execute(
        """
        SELECT id
        FROM appointments
        WHERE patient_user_id = ?
          AND appointment_type = 'initial_consult'
          AND substr(starts_at, 1, 10) = ?
        ORDER BY starts_at ASC
        LIMIT 1
        """,
        (patient_user_id, visit_day),
    ).fetchone()
    if existing is not None:
        db.execute(
            """
            UPDATE appointments
            SET clinician_user_id = COALESCE(clinician_user_id, ?),
                status = 'completed',
                updated_at = ?
            WHERE id = ?
            """,
            (clinician_user_id, now, existing["id"]),
        )
        return

    service = default_service_for_appointment_type("initial_consult")
    booking_policy = resolve_booking_policy(service, "initial_consult", None)
    create_patient_appointment(
        patient_user_id,
        clinician_user_id,
        default_location_id(),
        "initial_consult",
        visit_date,
        service_id=booking_policy["service_id"],
        requires_payment=booking_policy["requires_payment"],
        payment_status="pending" if booking_policy["requires_payment"] else "not_required",
        payment_amount=booking_policy["price_amount"],
        service_label_snapshot=booking_policy["service_label"],
        policy_snapshot=booking_policy,
        status="completed",
    )


def staff_dashboard_context(month_value: str | None = None) -> dict:
    db = get_db()
    patient_rows = db.execute(
        """
        SELECT
            u.id,
            u.first_name,
            u.last_name,
            u.email,
            u.created_at,
            s.status AS intake_status,
            s.updated_at AS intake_updated_at,
            vr.report_status AS visit_report_status,
            vr.updated_at AS visit_report_updated_at,
            cn.updated_at AS note_updated_at
        FROM users u
        LEFT JOIN intake_submissions s ON s.user_id = u.id
        LEFT JOIN visit_reports vr
            ON vr.patient_user_id = u.id
           AND vr.visit_kind = 'initial_consult'
        LEFT JOIN clinician_notes cn ON cn.patient_user_id = u.id
        WHERE u.role = 'client'
        ORDER BY COALESCE(s.updated_at, u.created_at) DESC
        """
    ).fetchall()

    invitation_rows = db.execute(
        """
        SELECT i.*, u.first_name AS clinician_first_name, u.last_name AS clinician_last_name
        FROM invitations i
        LEFT JOIN users u ON u.id = i.created_by
        WHERE i.accepted_at IS NULL
        ORDER BY COALESCE(i.appointment_at, i.created_at) ASC
        """
    ).fetchall()

    active_invitations = [dict(row) for row in invitation_rows if not is_expired(row["expires_at"])]
    for invite in active_invitations:
        invite["appointment_label"] = format_schedule(invite["appointment_at"]) if invite["appointment_at"] else None

    calendar_context = build_staff_calendar_context(month_value)
    next_appointments = {}
    for item in calendar_context["appointments"]:
        if item["status"] != "scheduled" or not item["is_upcoming"]:
            continue
        next_appointments.setdefault(item["patient_user_id"], item)

    patients = []
    for row in patient_rows:
        patient = dict(row)
        patient["next_appointment"] = next_appointments.get(row["id"])
        patients.append(patient)

    return {
        "patients": patients,
        "active_invitations": active_invitations,
        "upcoming_appointments": calendar_context["upcoming"],
        "calendar": calendar_context["calendar"],
        "appointment_counts": calendar_context["counts"],
        "appointment_reminders": calendar_context["reminders"],
        "patient_count": len(patients),
        "submitted_count": sum(1 for row in patients if row["intake_status"] == "submitted"),
        "pending_invite_count": len(active_invitations),
    }


def practitioner_dashboard_context(clinician_user_id: int) -> dict:
    appointments = [decorate_appointment_contacts(build_appointment_item(row)) for row in get_clinician_appointments(clinician_user_id)]
    upcoming_appointments = [item for item in appointments if item["is_upcoming"]]
    today_key = date.today().isoformat()
    today_appointments = [
        item for item in appointments
        if item["day_key"] == today_key and item["status"] != "cancelled"
    ]
    charting_queue = [item for item in appointments if appointment_needs_soap(item)]
    recent_charted = [
        item for item in appointments
        if item["has_soap_note"]
    ]
    recent_charted.sort(
        key=lambda item: item["soap_note_updated_at"] or "",
        reverse=True,
    )

    patient_map: dict[int, dict] = {}
    for appointment in appointments:
        patient_id = appointment["patient_user_id"]
        patient = patient_map.setdefault(
            patient_id,
            {
                "id": patient_id,
                "first_name": appointment["patient_first_name"],
                "last_name": appointment["patient_last_name"],
                "full_name": appointment["patient_name"],
                "email": appointment["patient_email"],
                "phone": appointment["patient_phone"],
                "next_appointment": None,
                "last_appointment": None,
                "soap_note_count": 0,
                "pending_soap_count": 0,
                "last_soap_note_at": None,
            },
        )
        if appointment["is_upcoming"] and patient["next_appointment"] is None:
            patient["next_appointment"] = appointment
        starts_at = parse_iso(appointment["starts_at"])
        if starts_at is not None and starts_at <= datetime.now():
            patient["last_appointment"] = appointment
        if appointment["has_soap_note"]:
            patient["soap_note_count"] += 1
            if patient["last_soap_note_at"] is None or (appointment["soap_note_updated_at"] or "") > patient["last_soap_note_at"]:
                patient["last_soap_note_at"] = appointment["soap_note_updated_at"]
        if appointment_needs_soap(appointment):
            patient["pending_soap_count"] += 1

    patients = list(patient_map.values())
    patients.sort(
        key=lambda patient: (
            0 if patient["next_appointment"] else 1,
            patient["next_appointment"]["starts_at"] if patient["next_appointment"] else "9999-12-31T23:59",
            patient["last_name"] or "",
            patient["first_name"] or "",
        )
    )
    for patient in patients:
        patient["last_soap_note_label"] = format_schedule(patient["last_soap_note_at"]) if patient["last_soap_note_at"] else None

    return {
        "patients": patients,
        "today_appointments": today_appointments,
        "upcoming_appointments": upcoming_appointments[:8],
        "charting_queue": charting_queue[:8],
        "recent_charted": recent_charted[:6],
        "patient_count": len(patients),
        "upcoming_count": len(upcoming_appointments),
        "charting_queue_count": len(charting_queue),
        "charted_count": len(recent_charted),
    }


def build_care_plan_visit_item(row, appointment: dict | None = None) -> dict:
    visit_kind = row["visit_kind"] or "follow_up"
    visit_meta = care_plan_visit_meta(visit_kind)
    suggested_starts_at = row["suggested_starts_at"] or f"{row['suggested_date']}T09:00"
    suggested_parsed = parse_iso(suggested_starts_at)
    effective_date_value = appointment["day_key"] if appointment else row["suggested_date"]
    effective_label = appointment["starts_label"] if appointment else (format_schedule(suggested_starts_at) or row["suggested_date"])
    status = (row["status"] or "").strip().lower() or ("scheduled" if row["booked"] else "unbooked")
    status_map = {
        "unbooked": {"label": "Unbooked", "tone": "muted"},
        "scheduled": {"label": "Booked", "tone": "sky"},
        "completed": {"label": "Completed", "tone": "life"},
        "cancelled": {"label": "Cancelled", "tone": "rose"},
        "missed": {"label": "Missed", "tone": "rose"},
    }
    status_meta = status_map.get(status, {"label": status.replace("_", " ").title(), "tone": "sky"})
    return {
        "id": row["id"],
        "care_plan_id": row["care_plan_id"],
        "visit_number": row["visit_number"],
        "visit_kind": visit_kind,
        "visit_kind_label": visit_meta["label"],
        "visit_kind_tone": visit_meta["tone"],
        "visit_icon": visit_meta["icon"],
        "label": row["label"] or care_plan_visit_label(row["visit_number"], visit_kind),
        "suggested_date": row["suggested_date"],
        "suggested_starts_at": suggested_starts_at,
        "suggested_date_label": suggested_parsed.strftime("%a %d %b") if suggested_parsed else row["suggested_date"],
        "suggested_long_label": format_schedule(suggested_starts_at) or row["suggested_date"],
        "effective_date_value": effective_date_value,
        "effective_label": effective_label,
        "duration_minutes": row["duration_minutes"] or default_duration_for_type("care_plan"),
        "fee_amount": row["fee_amount"],
        "fee_label": f"{row['fee_amount']:.2f} GBP" if isinstance(row["fee_amount"], (int, float)) else None,
        "status": status,
        "status_label": status_meta["label"],
        "status_tone": status_meta["tone"],
        "booked": bool(row["booked"]),
        "appointment_id": row["appointment_id"],
        "patient_details": row["patient_details"] or "",
        "note": row["note"] or "",
        "appointment": appointment,
        "month_key": effective_date_value[:7],
        "is_linked": appointment is not None,
    }


def build_care_plan_calendar_months(visits: list[dict]) -> list[dict]:
    if not visits:
        return []
    visits_by_day: dict[str, list[dict]] = {}
    for visit in visits:
        visits_by_day.setdefault(visit["effective_date_value"], []).append(visit)
    month_keys = sorted({visit["month_key"] for visit in visits})
    months = []
    calendar_builder = month_calendar.Calendar(firstweekday=6)
    today_key = date.today().isoformat()
    for month_key in month_keys:
        year, month = [int(part) for part in month_key.split("-", 1)]
        month_start = date(year, month, 1)
        weeks = []
        for week in calendar_builder.monthdatescalendar(year, month):
            week_items = []
            for day in week:
                day_key = day.isoformat()
                items = visits_by_day.get(day_key, [])
                primary = items[0] if items else None
                week_items.append(
                    {
                        "date_value": day_key,
                        "day_number": day.day,
                        "in_month": day.month == month,
                        "is_today": day_key == today_key,
                        "visits": items,
                        "primary_visit": primary,
                    }
                )
            weeks.append(week_items)
        months.append(
            {
                "key": month_key,
                "label": month_start.strftime("%B %Y"),
                "weeks": weeks,
            }
        )
    return months


def build_care_plan_context(patient_user_id: int) -> dict:
    care_plan_row = get_active_care_plan(patient_user_id)
    if care_plan_row is None:
        return {
            "plan": None,
            "visits": [],
            "months": [],
            "stats": {
                "completed": 0,
                "booked": 0,
                "unbooked": 0,
                "cancelled": 0,
                "remaining": 0,
            },
            "next_unbooked": None,
        }

    visit_rows = get_care_plan_visits(care_plan_row["id"])
    appointment_map = {}
    for row in visit_rows:
        if row["appointment_id"] is None:
            continue
        appointment_row = get_appointment_with_people(row["appointment_id"])
        if appointment_row is None:
            continue
        appointment_map[row["appointment_id"]] = decorate_appointment_contacts(build_appointment_item(appointment_row))

    visit_items = [build_care_plan_visit_item(row, appointment_map.get(row["appointment_id"])) for row in visit_rows]
    stats = {
        "completed": sum(1 for item in visit_items if item["status"] == "completed"),
        "booked": sum(1 for item in visit_items if item["booked"]),
        "unbooked": sum(1 for item in visit_items if item["status"] == "unbooked"),
        "cancelled": sum(1 for item in visit_items if item["status"] == "cancelled"),
    }
    stats["remaining"] = len(visit_items) - stats["completed"] - stats["cancelled"]

    return {
        "plan": {
            "id": care_plan_row["id"],
            "title": care_plan_row["title"] or care_plan_title_default(care_plan_row["duration_weeks"], care_plan_row["frequency_per_week"]),
            "frequency_per_week": care_plan_row["frequency_per_week"],
            "frequency_label": "Twice weekly" if care_plan_row["frequency_per_week"] == 2 else "Weekly",
            "duration_weeks": care_plan_row["duration_weeks"],
            "total_visits": care_plan_row["total_visits"],
            "midpoint_visit_number": care_plan_row["midpoint_visit_number"],
            "booking_mode": care_plan_row["booking_mode"],
            "booking_mode_label": care_plan_booking_mode_meta(care_plan_row["booking_mode"])["label"],
            "status": care_plan_row["status"],
            "status_label": care_plan_row["status"].replace("_", " ").title(),
            "service_id": care_plan_row["service_id"],
            "service_label": care_plan_row["service_label"] or "Care plan visit",
            "start_date": care_plan_row["start_date"],
            "start_slot": care_plan_row["start_slot"],
            "start_label": format_schedule(care_plan_row["start_slot"]) if care_plan_row["start_slot"] else care_plan_row["start_date"],
            "note": care_plan_row["note"] or "",
            "patient_details": care_plan_row["patient_details"] or "",
        },
        "visits": visit_items,
        "months": build_care_plan_calendar_months(visit_items),
        "stats": stats,
        "next_unbooked": next((item for item in visit_items if item["status"] == "unbooked"), None),
    }


def staff_patient_context(user_id: int):
    patient = get_client_user(user_id)
    if patient is None:
        return None

    clinicians = clinician_options()
    locations = location_options()
    care_plan_context = build_care_plan_context(patient["id"])
    selected_location = selected_location_id(request.args.get("location_id"))
    service_options = appointment_service_options(active_only=True)
    selected_service = selected_appointment_service(request.args.get("service_id"), active_only=True, fallback_to_default=True)
    care_plan_service_options = [item for item in service_options if item["appointment_type"] == "care_plan"]
    selected_care_plan_visit_id = int_or_none(request.args.get("care_plan_visit_id"))
    selected_care_plan_visit_row = None
    if isinstance(selected_care_plan_visit_id, int):
        candidate_visit = get_care_plan_visit(selected_care_plan_visit_id)
        if candidate_visit is not None and candidate_visit["patient_user_id"] == patient["id"] and candidate_visit["appointment_id"] is None:
            selected_care_plan_visit_row = candidate_visit
            if not request.args.get("service_id") and isinstance(candidate_visit["plan_service_id"], int):
                selected_service = selected_appointment_service(str(candidate_visit["plan_service_id"]), active_only=True, fallback_to_default=False) or selected_service
    selected_appointment_type = request.args.get("appointment_type", "").strip()
    if selected_service is not None and not selected_appointment_type:
        selected_appointment_type = selected_service["appointment_type"]
    if selected_care_plan_visit_row is not None:
        selected_appointment_type = "care_plan"
    if not selected_appointment_type:
        selected_appointment_type = "initial_consult"
    if selected_appointment_type not in APPOINTMENT_TYPE_META:
        selected_appointment_type = "initial_consult"
    selected_duration = int_or_none(
        request.args.get(
            "duration_minutes",
            str(selected_service["duration_minutes"] if selected_service else default_duration_for_type(selected_appointment_type)),
        )
    )
    if selected_care_plan_visit_row is not None:
        selected_duration = selected_care_plan_visit_row["duration_minutes"] or default_duration_for_type("care_plan")
    if not isinstance(selected_duration, int) or not duration_is_supported(selected_duration):
        selected_duration = selected_service["duration_minutes"] if selected_service else default_duration_for_type(selected_appointment_type)
    booking_policy = resolve_booking_policy(selected_service, selected_appointment_type, selected_duration)
    if selected_care_plan_visit_row is not None:
        booking_policy = care_plan_visit_policy(
            booking_policy,
            {
                "visit_kind": selected_care_plan_visit_row["visit_kind"],
                "duration_minutes": selected_duration,
            },
        )
        booking_policy["service_label"] = selected_care_plan_visit_row["label"] or booking_policy["service_label"]
    selected_slot_increment = selected_slot_increment_minutes(request.args.get("slot_increment_minutes"))

    raw_clinician_value = request.args.get("clinician_user_id")
    selected_clinician_id = requested_clinician_user_id(
        raw_clinician_value,
        allow_any=booking_policy["routing_mode"] == "team_round_robin",
    )
    if booking_policy["routing_mode"] == "team_round_robin" and (raw_clinician_value or "").strip().lower() in {"", "any", "team"}:
        selected_clinician_id = None
        selected_clinician_choice = "any"
    else:
        selected_clinician_choice = str(selected_clinician_id) if selected_clinician_id is not None else ""
    if selected_care_plan_visit_row is not None and not request.args.get("clinician_user_id"):
        selected_clinician_id = requested_clinician_user_id(
            str(selected_care_plan_visit_row["plan_clinician_user_id"]) if selected_care_plan_visit_row["plan_clinician_user_id"] is not None else None,
            allow_any=booking_policy["routing_mode"] == "team_round_robin",
        )
        selected_clinician_choice = (
            "any"
            if selected_clinician_id is None and booking_policy["routing_mode"] == "team_round_robin"
            else str(selected_clinician_id) if selected_clinician_id is not None else ""
        )
    if selected_care_plan_visit_row is not None and not request.args.get("location_id"):
        selected_location = selected_location_id(str(selected_care_plan_visit_row["plan_location_id"]))

    booking_date = request.args.get("appointment_date")
    if not booking_date and selected_care_plan_visit_row is not None:
        booking_date = selected_care_plan_visit_row["suggested_date"]
    if not booking_date:
        booking_date = next_booking_date(selected_clinician_id, selected_location, booking_policy)
    booking_availability = build_schedule_availability(
        booking_date,
        selected_clinician_id,
        selected_location,
        booking_policy["duration_minutes"],
        booking_policy=booking_policy,
        slot_increment_minutes=selected_slot_increment,
    )

    submission = get_submission_for_user(patient["id"])
    visit_report = get_visit_report_for_patient(patient["id"])
    payload = json.loads(submission["payload_json"]) if submission else {}
    invitation = get_latest_invitation_for_user(patient["id"])
    notes = get_notes_for_patient(patient["id"])
    schedule = build_patient_schedule_context(patient["id"])
    decision_support_region = infer_decision_support_region(payload)
    for key in ("all", "upcoming", "history", "reminders"):
        for appointment in schedule[key]:
            decorate_appointment_contacts(appointment)
    if schedule["next_appointment"] is not None:
        decorate_appointment_contacts(schedule["next_appointment"])
    next_appointment = schedule["next_appointment"]
    summit_assessment = build_summit_assessment(
        dict(patient),
        payload,
        dict(visit_report) if visit_report else None,
    )
    summary = build_clinician_context(
        dict(patient),
        payload,
        submission["status"] if submission else "not_started",
        submission["updated_at"] if submission else patient["created_at"],
        appointment_at=next_appointment["starts_at"] if next_appointment else invitation["appointment_at"] if invitation else None,
        notes=dict(notes) if notes else None,
        visit_report=dict(visit_report) if visit_report else None,
    )
    return {
        "patient": patient,
        "submission": submission,
        "summary": summary,
        "notes": notes,
        "visit_report": visit_report,
        "schedule": schedule,
        "patient_contact": get_patient_contact_details(patient["id"]),
        "care_plan": care_plan_context,
        "care_plan_service_options": care_plan_service_options,
        "care_plan_frequency_options": care_plan_frequency_options(),
        "care_plan_week_options": care_plan_week_options(),
        "care_plan_booking_mode_options": care_plan_booking_mode_options(),
        "selected_care_plan_visit": build_care_plan_visit_item(selected_care_plan_visit_row) if selected_care_plan_visit_row is not None else None,
        "clinician_options": clinicians,
        "location_options": locations,
        "selected_location_id": selected_location,
        "selected_clinician_id": selected_clinician_id,
        "selected_clinician_choice": selected_clinician_choice,
        "billing_status_options": billing_status_options(),
        "duration_options": appointment_duration_options(),
        "selected_duration_minutes": booking_policy["duration_minutes"],
        "selected_appointment_type": selected_appointment_type,
        "service_options": service_options,
        "selected_service_id": selected_service["id"] if selected_service else None,
        "booking_policy": booking_policy,
        "slot_increment_options": slot_increment_options(),
        "selected_slot_increment_minutes": selected_slot_increment,
        "allow_any_clinician": booking_policy["routing_mode"] == "team_round_robin",
        "booking_date": booking_date,
        "booking_availability": booking_availability,
        "booking_prefill_patient_details": request.args.get("patient_details", "").strip() or (selected_care_plan_visit_row["patient_details"] if selected_care_plan_visit_row is not None else ""),
        "booking_prefill_note": request.args.get("note", "").strip() or (selected_care_plan_visit_row["note"] if selected_care_plan_visit_row is not None else ""),
        "appointment_type_options": appointment_type_options(),
        "appointment_status_options": appointment_status_options(),
        "summit_assessment": summit_assessment,
        "summit_rom_sections": SUMMIT_ROM_SECTIONS,
        "summit_ortho_regions": SUMMIT_ORTHO_REGIONS,
        "summit_spine_regions": SUMMIT_SPINE_REGIONS,
        "decision_support_region": decision_support_region,
        "decision_support_region_label": DECISION_SUPPORT_REGION_LABELS[decision_support_region],
        "decision_support_storage_key": decision_support_storage_key(patient["id"]),
    }


def results_page_context(user_id: int):
    patient = get_client_user(user_id)
    if patient is None:
        return None

    submission = get_submission_for_user(user_id)
    if submission is None:
        return {"patient": patient, "submission": None, "summary": None}

    payload = json.loads(submission["payload_json"])
    visit_report = get_visit_report_for_patient(user_id)
    summary = build_results_context(
        dict(patient),
        payload,
        submission["status"],
        submission["updated_at"],
        visit_report=dict(visit_report) if visit_report else None,
    )
    return {
        "patient": patient,
        "submission": submission,
        "summary": summary,
    }


def reminder_redirect_target(default_endpoint: str = "main.staff_reminders", **values) -> str:
    next_url = request.form.get("next_url", "").strip()
    if next_url.startswith("/") and not next_url.startswith("//"):
        return next_url
    return url_for(default_endpoint, **values)


@bp.before_app_request
def load_logged_in_user() -> None:
    user_id = session.get("user_id")
    if user_id is None:
        g.user = None
        return

    g.user = get_db().execute(
        "SELECT * FROM users WHERE id = ? AND COALESCE(is_active, 1) = 1",
        (user_id,),
    ).fetchone()
    if g.user is None:
        session.clear()
        return

    # Keep active staff and patient sessions aligned with the configured timeout.
    current_app.permanent_session_lifetime = timedelta(minutes=current_session_timeout_minutes())
    session.permanent = True
    session.modified = True


@bp.route("/")
def index():
    if g.user is not None:
        return redirect(dashboard_redirect_for(g.user))
    return redirect(url_for("main.login"))


@bp.route("/signup", methods=("GET", "POST"))
def signup():
    if g.user is not None:
        return redirect(dashboard_redirect_for(g.user))

    if request.method == "POST":
        first_name = request.form.get("first_name", "").strip()
        last_name = request.form.get("last_name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        error = None
        if not first_name or not last_name:
            error = "First and last name are required."
        elif not email:
            error = "Email is required."
        elif len(password) < 8:
            error = "Password must be at least 8 characters."

        db = get_db()
        if error is None:
            existing = db.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
            if existing is not None:
                error = "An account with that email already exists."

        if error is None:
            now = iso_now()
            cursor = db.execute(
                """
                INSERT INTO users (first_name, last_name, email, password_hash, role, created_at)
                VALUES (?, ?, ?, ?, 'client', ?)
                """,
                (first_name, last_name, email, generate_password_hash(password, method="pbkdf2:sha256"), now),
            )
            db.commit()
            session.clear()
            session["user_id"] = cursor.lastrowid
            flash("Account created. Your dashboard is ready.", "success")
            return redirect(url_for("main.dashboard"))

        flash(error, "error")

    return render_template("signup.html")


@bp.route("/invite/<token>", methods=("GET", "POST"))
def accept_invite(token: str):
    if g.user is not None:
        return redirect(dashboard_redirect_for(g.user))

    invitation = get_invitation_by_token(token)
    invalid = invitation is None or invitation["accepted_at"] is not None or is_expired(invitation["expires_at"])
    if invalid:
        return render_template("accept_invite.html", invitation=None, invalid=True)

    if request.method == "POST":
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")
        email = invitation["email"].strip().lower()

        error = None
        if len(password) < 8:
            error = "Password must be at least 8 characters."
        elif password != confirm_password:
            error = "Passwords do not match."
        elif get_db().execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone() is not None:
            error = "An account with that email already exists. Sign in instead."

        if error is None:
            now = iso_now()
            db = get_db()
            cursor = db.execute(
                """
                INSERT INTO users (first_name, last_name, email, password_hash, role, created_at)
                VALUES (?, ?, ?, ?, 'client', ?)
                """,
                (
                    invitation["first_name"],
                    invitation["last_name"],
                    email,
                    generate_password_hash(password, method="pbkdf2:sha256"),
                    now,
                ),
            )
            db.execute(
                """
                UPDATE invitations
                SET accepted_at = ?, accepted_user_id = ?
                WHERE id = ?
                """,
                (now, cursor.lastrowid, invitation["id"]),
            )
            ensure_patient_appointment(
                cursor.lastrowid,
                invitation["created_by"],
                default_location_id(),
                "initial_consult",
                invitation["appointment_at"],
                note=invitation["note"] or "",
                source_invitation_id=invitation["id"],
            )
            db.commit()
            session.clear()
            session["user_id"] = cursor.lastrowid
            flash("Invitation accepted. Your dashboard is ready.", "success")
            return redirect(url_for("main.dashboard"))

        flash(error, "error")

    return render_template("accept_invite.html", invitation=invitation, invalid=False)


@bp.route("/login", methods=("GET", "POST"))
def login():
    if g.user is not None:
        return redirect(dashboard_redirect_for(g.user))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = get_db().execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()

        error = None
        if user is None or not check_password_hash(user["password_hash"], password):
            error = "Incorrect email or password."
        elif not bool(user["is_active"] if "is_active" in user.keys() else 1):
            error = "That account is inactive."

        if error is None:
            session.clear()
            session["user_id"] = user["id"]
            flash("Signed in. Welcome to your dashboard.", "success")
            return redirect(dashboard_redirect_for(user))

        flash(error, "error")

    return render_template("login.html")


@bp.route("/forgot-password", methods=("GET", "POST"))
def forgot_password():
    if g.user is not None:
        return redirect(dashboard_redirect_for(g.user))

    reset_link = None
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        user = get_db().execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()

        if user is not None:
            now = iso_now()
            token = secrets.token_urlsafe(32)
            expires_at = (datetime.utcnow() + timedelta(hours=1)).replace(microsecond=0).isoformat() + "Z"
            db = get_db()
            db.execute(
                """
                INSERT INTO password_reset_tokens (user_id, token, expires_at, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (user["id"], token, expires_at, now),
            )
            db.commit()
            reset_link = url_for("main.reset_password", token=token, _external=True)

        flash("If an account exists for that email, a reset link is now available.", "success")

    return render_template("forgot_password.html", reset_link=reset_link)


@bp.route("/reset-password/<token>", methods=("GET", "POST"))
def reset_password(token: str):
    if g.user is not None:
        return redirect(dashboard_redirect_for(g.user))

    token_row = get_reset_token(token)
    invalid = token_row is None or token_row["used_at"] is not None or is_expired(token_row["expires_at"])
    if invalid:
        return render_template("reset_password.html", token_row=None, invalid=True)

    if request.method == "POST":
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        error = None
        if len(password) < 8:
            error = "Password must be at least 8 characters."
        elif password != confirm_password:
            error = "Passwords do not match."

        if error is None:
            now = iso_now()
            db = get_db()
            db.execute(
                "UPDATE users SET password_hash = ? WHERE id = ?",
                (generate_password_hash(password, method="pbkdf2:sha256"), token_row["user_id"]),
            )
            db.execute(
                "UPDATE password_reset_tokens SET used_at = ? WHERE id = ?",
                (now, token_row["id"]),
            )
            db.commit()
            flash("Password updated. You can sign in now.", "success")
            return redirect(url_for("main.login"))

        flash(error, "error")

    return render_template("reset_password.html", token_row=token_row, invalid=False)


@bp.post("/logout")
def logout():
    session.clear()
    flash("Signed out.", "success")
    return redirect(url_for("main.login"))


@bp.route("/dashboard")
@login_required
def dashboard():
    if is_admin(g.user):
        context = staff_dashboard_context(request.args.get("month"))
        return render_template("staff_dashboard.html", **context)
    if is_clinician(g.user):
        context = practitioner_dashboard_context(g.user["id"])
        return render_template("practitioner_dashboard.html", **context)
    if is_staff(g.user):
        context = staff_dashboard_context(request.args.get("month"))
        return render_template("staff_dashboard.html", **context)

    submission = get_submission_for_user(g.user["id"])
    invitation = get_latest_invitation_for_user(g.user["id"])
    visit_report = get_visit_report_for_patient(g.user["id"])
    schedule = build_patient_schedule_context(g.user["id"])
    return render_template(
        "dashboard.html",
        submission=submission,
        invitation=invitation,
        visit_report=visit_report,
        schedule=schedule,
        next_appointment=schedule["next_appointment"],
    )


@bp.route("/staff/dashboard")
@staff_required
def staff_dashboard():
    context = staff_dashboard_context(request.args.get("month"))
    return render_template("staff_dashboard.html", **context)


@bp.route("/staff/journal")
@staff_required
def staff_journal():
    entries = [dict(entry) for entry in get_practitioner_journal_entries(g.user["id"])]
    return render_template("staff_journal.html", entries=entries, today=date.today().isoformat())


@bp.post("/staff/journal")
@staff_required
def create_staff_journal_entry():
    entry_date = request.form.get("entry_date", "").strip() or date.today().isoformat()
    title = request.form.get("title", "").strip()
    reflection = request.form.get("reflection", "").strip()
    lesson_learned = request.form.get("lesson_learned", "").strip()
    next_step = request.form.get("next_step", "").strip()

    error = None
    if not (title or reflection or lesson_learned or next_step):
        error = "Write at least one section before saving your journal."
    elif parse_iso(entry_date) is None:
        error = "Choose a valid entry date."

    if error is None:
        now = iso_now()
        get_db().execute(
            """
            INSERT INTO practitioner_journal_entries (
                clinician_user_id,
                entry_date,
                title,
                reflection,
                lesson_learned,
                next_step,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                g.user["id"],
                entry_date,
                title,
                reflection,
                lesson_learned,
                next_step,
                now,
                now,
            ),
        )
        get_db().commit()
        flash("Journal entry saved.", "success")
    else:
        flash(error, "error")

    return redirect(url_for("main.staff_journal"))


@bp.post("/staff/journal/claude-chat")
@staff_required
def staff_journal_claude_chat():
    payload = request.get_json(silent=True) or {}
    message = str(payload.get("message", "")).strip()
    selected_ids = payload.get("entry_ids")
    if selected_ids is None:
        selected_ids = []
    if not isinstance(selected_ids, list):
        return jsonify({"ok": False, "error": "entry_ids must be a list."}), 400

    normalized_ids: list[int] = []
    for raw_id in selected_ids:
        try:
            value = int(raw_id)
        except (TypeError, ValueError):
            continue
        normalized_ids.append(value)

    selected_entries = _selected_journal_entries_for_user(
        g.user["id"],
        normalized_ids or None,
    )

    prompt = _build_journal_context_prompt(
        f"{g.user['first_name']} {g.user['last_name']}".strip(),
        selected_entries,
        message,
    )

    claude_text = None
    used_local = False
    if message:
        try:
            claude_text = _call_claude_api(prompt)
        except Exception:
            claude_text = None

    if not claude_text:
        claude_text = _fallback_claude_reply(message, selected_entries)
        used_local = True

    return jsonify(
        {
            "ok": True,
            "reply": claude_text,
            "used_local_model": used_local,
            "entry_count": len(selected_entries),
            "entries": [
                {"id": entry["id"], "entry_date": entry["entry_date"], "title": entry["title"]}
                for entry in selected_entries
            ],
        }
    )


@bp.get("/staff/messaging")
@staff_required
def staff_messaging():
    search = request.args.get("q", "").strip()
    threads = get_staff_message_threads(search)

    selected_patient_id = int_or_none(request.args.get("patient_id"))
    if not isinstance(selected_patient_id, int):
        selected_patient_id = threads[0]["patient_user_id"] if threads else None

    selected_patient = get_client_user(selected_patient_id) if selected_patient_id is not None else None
    if selected_patient is None and threads:
        selected_patient_id = threads[0]["patient_user_id"]
        selected_patient = get_client_user(selected_patient_id)

    messages = []
    if selected_patient is not None:
        mark_patient_messages_read_for_staff(selected_patient["id"])
        get_db().commit()
        messages = get_patient_message_thread(selected_patient["id"])

    return render_template(
        "staff_messaging.html",
        threads=threads,
        selected_patient=selected_patient,
        selected_patient_id=selected_patient["id"] if selected_patient is not None else None,
        messages=messages,
        message_topics=message_topic_options(),
        search_query=search,
    )


@bp.post("/staff/messaging/<int:patient_user_id>")
@staff_required
def send_staff_message(patient_user_id: int):
    patient = get_client_user(patient_user_id)
    if patient is None:
        abort(404)

    topic = request.form.get("topic", "").strip()
    body = request.form.get("body", "").strip()

    if topic not in MESSAGE_TOPIC_META:
        flash("Choose a valid message topic.", "error")
    elif not body:
        flash("Write a message before sending.", "error")
    else:
        insert_patient_message(patient_user_id, g.user["id"], g.user["role"], topic, body)
        get_db().commit()
        flash("Message sent to patient.", "success")
    return redirect(url_for("main.staff_messaging", patient_id=patient_user_id))


@bp.get("/messages")
@client_required
def patient_messages():
    unread_count = get_db().execute(
        """
        SELECT COUNT(*) AS count
        FROM patient_messages
        WHERE patient_user_id = ?
          AND sender_role IN ('admin', 'clinician')
          AND read_by_patient_at IS NULL
        """,
        (g.user["id"],),
    ).fetchone()["count"]
    mark_patient_messages_read_for_patient(g.user["id"])
    get_db().commit()
    messages = get_patient_message_thread(g.user["id"])

    return render_template(
        "patient_messages.html",
        messages=messages,
        message_topics=message_topic_options(),
        unread_count=unread_count,
    )


@bp.post("/messages")
@client_required
def send_patient_message():
    topic = request.form.get("topic", "").strip()
    body = request.form.get("body", "").strip()

    if topic not in MESSAGE_TOPIC_META:
        flash("Choose a valid message topic.", "error")
    elif not body:
        flash("Write a message before sending.", "error")
    else:
        insert_patient_message(g.user["id"], g.user["id"], "client", topic, body)
        get_db().commit()
        flash("Message sent to your chiropractic team.", "success")
    return redirect(url_for("main.patient_messages"))


@bp.get("/staff/learning")
@staff_required
def staff_learning():
    progress_by_topic = get_learning_progress_for_clinician(g.user["id"])
    topics_by_category: dict[str, list[dict]] = {}

    completed_topics = 0
    for topic in LEARNING_PATH_TOPICS:
        saved = progress_by_topic.get(topic["slug"])
        is_completed = bool(saved and int(saved["is_completed"]) == 1)
        if is_completed:
            completed_topics += 1

        topic_progress = {
            **topic,
            "is_completed": is_completed,
            "completed_at": saved["completed_at"] if saved else None,
            "reflection": (saved["reflection"] if saved else ""),
        }

        categories_set = topics_by_category.setdefault(topic["category"], [])
        categories_set.append(topic_progress)

    total_topics = len(LEARNING_PATH_TOPICS)
    return render_template(
        "staff_learning_portal.html",
        topics_by_category=topics_by_category,
        completed_topics=completed_topics,
        total_topics=total_topics,
        progress_pct=round((completed_topics / total_topics) * 100) if total_topics else 0,
    )


@bp.post("/staff/learning/progress")
@staff_required
def update_staff_learning_progress():
    topic_slug = request.form.get("topic_slug", "").strip()
    is_completed = request.form.get("is_completed") == "1"
    reflection = request.form.get("reflection", "").strip()

    topic_slugs = {topic["slug"] for topic in LEARNING_PATH_TOPICS}
    if topic_slug not in topic_slugs:
        flash("Invalid learning topic selected.", "error")
        return redirect(url_for("main.staff_learning"))

    now = iso_now()
    db = get_db()
    existing = db.execute(
        """
        SELECT id
        FROM practitioner_learning_progress
        WHERE clinician_user_id = ? AND topic_slug = ?
        """,
        (g.user["id"], topic_slug),
    ).fetchone()

    if existing is None:
        db.execute(
            """
            INSERT INTO practitioner_learning_progress (
                clinician_user_id,
                topic_slug,
                is_completed,
                completed_at,
                reflection,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                g.user["id"],
                topic_slug,
                1 if is_completed else 0,
                now if is_completed else None,
                reflection,
                now,
                now,
            ),
        )
    else:
        db.execute(
            """
            UPDATE practitioner_learning_progress
            SET is_completed = ?,
                completed_at = ?,
                reflection = ?,
                updated_at = ?
            WHERE clinician_user_id = ? AND topic_slug = ?
            """,
            (
                1 if is_completed else 0,
                now if is_completed else None,
                reflection,
                now,
                g.user["id"],
                topic_slug,
            ),
        )
    db.commit()
    flash("Learning progress saved.", "success")
    return redirect(url_for("main.staff_learning"))


@bp.route("/staff/invitations/new", methods=("GET", "POST"))
@staff_required
def staff_new_invitation():
    created_invitation = None

    if request.method == "POST":
        first_name = request.form.get("first_name", "").strip()
        last_name = request.form.get("last_name", "").strip()
        email = request.form.get("email", "").strip().lower()
        appointment_at = request.form.get("appointment_at", "").strip() or None
        note = request.form.get("note", "").strip()

        error = None
        if not first_name or not last_name:
            error = "Patient first and last name are required."
        elif not email:
            error = "Patient email is required."

        if error is None:
            now = iso_now()
            expires_at = (datetime.utcnow() + timedelta(days=14)).replace(microsecond=0).isoformat() + "Z"
            token = secrets.token_urlsafe(24)
            db = get_db()
            cursor = db.execute(
                """
                INSERT INTO invitations (
                    email,
                    first_name,
                    last_name,
                    appointment_at,
                    note,
                    token,
                    expires_at,
                    created_at,
                    created_by
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (email, first_name, last_name, appointment_at, note, token, expires_at, now, g.user["id"]),
            )
            db.commit()
            created_invitation = db.execute("SELECT * FROM invitations WHERE id = ?", (cursor.lastrowid,)).fetchone()
            flash("Invitation created.", "success")
        else:
            flash(error, "error")

    return render_template("invite_form.html", created_invitation=created_invitation)


@bp.route("/staff/calendar")
@staff_required
def staff_calendar():
    context = build_staff_calendar_context(request.args.get("month"))
    return render_template(
        "staff_calendar.html",
        appointment_type_options=appointment_type_options(),
        appointment_status_options=appointment_status_options(),
        booking_routing_mode_options=[{"value": key, "label": value["label"]} for key, value in BOOKING_ROUTING_MODE_META.items()],
        duration_options=appointment_duration_options(),
        clinician_options=clinician_options(),
        location_options=location_options(),
        weekday_options=weekday_options(),
        schedule_window_type_options=schedule_window_type_options(),
        **context,
    )


@bp.get("/staff/settings")
@staff_required
def staff_settings():
    return render_template(
        "staff_settings.html",
        appointment_type_options=appointment_type_options(),
        booking_routing_mode_options=[{"value": key, "label": value["label"]} for key, value in BOOKING_ROUTING_MODE_META.items()],
        duration_options=appointment_duration_options(),
        clinician_options=clinician_options(),
        location_options=location_options(),
        weekday_options=weekday_options(),
        schedule_window_type_options=schedule_window_type_options(),
        **build_staff_settings_context(),
    )


@bp.post("/staff/settings/general")
@staff_required
def update_staff_settings():
    calendar_time_format = (request.form.get("calendar_time_format") or "").strip().lower()
    calendar_slot_increment_minutes = int_or_none(request.form.get("calendar_slot_increment_minutes"))
    booking_search_window_days = int_or_none(request.form.get("booking_search_window_days"))
    max_active_chiropractors = int_or_none(request.form.get("max_active_chiropractors")) if "max_active_chiropractors" in request.form else current_max_active_chiropractors()
    booking_enable_online = request.form.get("booking_enable_online") == "on"
    booking_allow_same_day = request.form.get("booking_allow_same_day") == "on"
    booking_cancellation_hours = int_or_none(request.form.get("booking_cancellation_hours"))
    booking_no_show_fee = request.form.get("booking_no_show_fee", "").strip()

    active_chiropractor_count = sum(1 for item in get_chiropractor_roster() if item["is_active"])

    error = None
    if calendar_time_format not in {option["value"] for option in TIME_FORMAT_OPTIONS}:
        error = "Choose a valid calendar time format."
    elif not isinstance(calendar_slot_increment_minutes, int) or calendar_slot_increment_minutes not in SLOT_INCREMENT_OPTIONS:
        error = "Choose a supported slot increment."
    elif not isinstance(booking_search_window_days, int) or booking_search_window_days < 1 or booking_search_window_days > 120:
        error = "Booking search window must be between 1 and 120 days."
    elif not isinstance(booking_cancellation_hours, int) or booking_cancellation_hours < 0 or booking_cancellation_hours > 336:
        error = "Cancellation window must be between 0 and 336 hours."
    elif booking_no_show_fee and not isinstance(float_or_none(booking_no_show_fee), float):
        error = "No-show fee must be numeric."
    elif not isinstance(max_active_chiropractors, int) or max_active_chiropractors < 1 or max_active_chiropractors > 100:
        error = "Max chiropractors must be between 1 and 100."
    elif max_active_chiropractors < active_chiropractor_count:
        error = f"Cannot set the chiropractor limit below the current active count ({active_chiropractor_count})."

    if error is None:
        set_app_setting("calendar_time_format", calendar_time_format)
        set_app_setting("calendar_slot_increment_minutes", str(calendar_slot_increment_minutes))
        set_app_setting("booking_search_window_days", str(booking_search_window_days))
        set_app_setting("max_active_chiropractors", str(max_active_chiropractors))
        set_app_setting("booking_enable_online", "1" if booking_enable_online else "0")
        set_app_setting("booking_allow_same_day", "1" if booking_allow_same_day else "0")
        set_app_setting("booking_cancellation_hours", str(booking_cancellation_hours))
        set_app_setting("booking_no_show_fee", booking_no_show_fee)
        get_db().commit()
        flash("Settings updated.", "success")
    else:
        flash(error, "error")

    return redirect(url_for("main.staff_settings", section="scheduling"))


@bp.post("/staff/settings/preferences/<section_key>")
@staff_required
def update_staff_settings_section(section_key: str):
    db = get_db()
    error = None

    def save_text(setting_key: str) -> None:
        set_app_setting(setting_key, request.form.get(setting_key, "").strip())

    def save_checkbox(setting_key: str) -> None:
        set_app_setting(setting_key, "1" if request.form.get(setting_key) == "on" else "0")

    if section_key == "profile":
        for setting_key in (
            "practice_practitioner_name",
            "practice_registration_number",
            "practice_qualifications",
            "practice_clinic_name",
            "practice_email",
            "practice_phone",
            "practice_address",
            "practice_bio",
        ):
            save_text(setting_key)
    elif section_key == "clinic":
        selected_days = [item for item in request.form.getlist("clinic_open_days") if item in {"Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"}]
        open_time = request.form.get("clinic_open_time", "").strip()
        close_time = request.form.get("clinic_close_time", "").strip()
        lunch_start = request.form.get("clinic_lunch_start", "").strip()
        lunch_end = request.form.get("clinic_lunch_end", "").strip()
        clinic_rooms = int_or_none(request.form.get("clinic_rooms"))
        if not selected_days:
            error = "Choose at least one operating day."
        elif time_from_value(open_time) is None or time_from_value(close_time) is None:
            error = "Opening and closing times must be valid."
        elif lunch_start and time_from_value(lunch_start) is None:
            error = "Lunch start must be a valid time."
        elif lunch_end and time_from_value(lunch_end) is None:
            error = "Lunch end must be a valid time."
        elif not isinstance(clinic_rooms, int) or clinic_rooms < 1 or clinic_rooms > 50:
            error = "Treatment rooms must be between 1 and 50."
        if error is None:
            set_app_setting("clinic_open_days", ",".join(selected_days))
            set_app_setting("clinic_open_time", open_time)
            set_app_setting("clinic_close_time", close_time)
            set_app_setting("clinic_lunch_start", lunch_start)
            set_app_setting("clinic_lunch_end", lunch_end)
            set_app_setting("clinic_rooms", str(clinic_rooms))
            save_checkbox("clinic_multi_practitioner_mode")
    elif section_key == "notifications":
        recall_days = int_or_none(request.form.get("notifications_recall_days"))
        if not isinstance(recall_days, int) or recall_days < 7 or recall_days > 365:
            error = "Recall days must be between 7 and 365."
        if error is None:
            for setting_key in (
                "notifications_confirmation_email",
                "notifications_confirmation_sms",
                "notifications_reminder_24h",
                "notifications_reminder_1h",
                "notifications_post_visit_email",
                "notifications_recall_enabled",
            ):
                save_checkbox(setting_key)
            set_app_setting("notifications_recall_days", str(recall_days))
    elif section_key == "clinical":
        selected_measures = [item for item in request.form.getlist("clinical_outcome_measures") if item in {"NDI", "ODI", "QuickDASH", "HIT-6", "SF-36", "PSFS", "VAS Pain"}]
        reexam_interval = int_or_none(request.form.get("clinical_reexam_interval"))
        if not selected_measures:
            error = "Choose at least one default outcome measure."
        elif not isinstance(reexam_interval, int) or reexam_interval < 1 or reexam_interval > 52:
            error = "Re-examination interval must be between 1 and 52 visits."
        if error is None:
            set_app_setting("clinical_outcome_measures", ",".join(selected_measures))
            set_app_setting("clinical_reexam_interval", str(reexam_interval))
            for setting_key in (
                "clinical_use_mcid",
                "clinical_auto_assign_intake",
                "clinical_include_consent",
            ):
                save_checkbox(setting_key)
    elif section_key == "billing":
        initial_fee = request.form.get("billing_initial_fee", "").strip()
        followup_fee = request.form.get("billing_followup_fee", "").strip()
        if initial_fee and not isinstance(float_or_none(initial_fee), float):
            error = "Initial consultation fee must be numeric."
        elif followup_fee and not isinstance(float_or_none(followup_fee), float):
            error = "Follow-up fee must be numeric."
        if error is None:
            selected_methods = [item for item in request.form.getlist("billing_payment_methods") if item in {"Card", "Cash", "Bank Transfer", "Apple Pay", "Google Pay"}]
            set_app_setting("billing_initial_fee", initial_fee)
            set_app_setting("billing_followup_fee", followup_fee)
            set_app_setting("billing_payment_methods", ",".join(selected_methods))
            save_checkbox("billing_auto_invoice")
            save_checkbox("billing_email_receipts")
    elif section_key == "security":
        session_timeout = int_or_none(request.form.get("security_session_timeout"))
        max_active_chiropractors = int_or_none(request.form.get("max_active_chiropractors"))
        active_chiropractor_count = sum(1 for item in get_chiropractor_roster() if item["is_active"])
        if not isinstance(session_timeout, int) or session_timeout not in {15, 30, 60, 120}:
            error = "Choose a valid session timeout."
        elif not isinstance(max_active_chiropractors, int) or max_active_chiropractors < 1 or max_active_chiropractors > 100:
            error = "Max chiropractors must be between 1 and 100."
        elif max_active_chiropractors < active_chiropractor_count:
            error = f"Cannot set the chiropractor limit below the current active count ({active_chiropractor_count})."
        if error is None:
            set_app_setting("security_session_timeout", str(session_timeout))
            set_app_setting("max_active_chiropractors", str(max_active_chiropractors))
            save_checkbox("security_two_factor")
    elif section_key == "data":
        retention_period = request.form.get("data_retention_period", "").strip()
        if retention_period not in {"3y", "7y", "10y"}:
            error = "Choose a valid data retention period."
        if error is None:
            save_text("data_ico_reference")
            set_app_setting("data_retention_period", retention_period)
            save_checkbox("data_auto_anonymize")
            save_checkbox("data_daily_backups")
    elif section_key == "appearance":
        theme = request.form.get("appearance_theme", "").strip()
        font_style = request.form.get("appearance_font_style", "").strip()
        brand_color = request.form.get("appearance_brand_color", "").strip()
        if theme not in {"light", "dark", "auto"}:
            error = "Choose a valid appearance theme."
        elif font_style not in {"modern", "classic", "clean"}:
            error = "Choose a valid font style."
        elif not re.fullmatch(r"#[0-9A-Fa-f]{6}", brand_color):
            error = "Brand colour must be a 6-digit hex value."
        if error is None:
            set_app_setting("appearance_theme", theme)
            set_app_setting("appearance_font_style", font_style)
            set_app_setting("appearance_brand_color", brand_color)
            save_checkbox("appearance_show_portal_branding")
    elif section_key == "integrations":
        for setting_key in (
            "integration_payment_provider",
            "integration_calendar_sync",
            "integration_email_provider",
            "integration_sms_provider",
        ):
            save_text(setting_key)
    else:
        abort(404)

    if error is None:
        db.commit()
        flash("Settings updated.", "success")
    else:
        flash(error, "error")

    return redirect(url_for("main.staff_settings", section=section_key))


@bp.post("/staff/settings/chiropractors")
@staff_required
def create_staff_chiropractor():
    first_name = request.form.get("first_name", "").strip()
    last_name = request.form.get("last_name", "").strip()
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")

    error = None
    if not first_name or not last_name:
        error = "First and last name are required."
    elif not email:
        error = "Email is required."
    elif len(password) < 8:
        error = "Password must be at least 8 characters."

    db = get_db()
    existing = None
    if error is None:
        existing = db.execute(
            """
            SELECT id, role, COALESCE(is_active, 1) AS is_active
            FROM users
            WHERE email = ?
            LIMIT 1
            """,
            (email,),
        ).fetchone()

    active_chiropractor_count = sum(1 for item in get_chiropractor_roster() if item["is_active"])
    if error is None:
        projected_active_count = active_chiropractor_count
        if existing is None:
            projected_active_count += 1
        elif existing["role"] == "clinician" and not bool(existing["is_active"]):
            projected_active_count += 1
        elif existing["role"] != "clinician":
            error = "That email is already assigned to a non-chiropractor account."

        if error is None and projected_active_count > current_max_active_chiropractors():
            error = "Increase the max chiropractor count before adding another active chiropractor."

    if error is None:
        password_hash = generate_password_hash(password, method="pbkdf2:sha256")
        if existing is None:
            db.execute(
                """
                INSERT INTO users (first_name, last_name, email, password_hash, role, is_active, created_at)
                VALUES (?, ?, ?, ?, 'clinician', 1, ?)
                """,
                (first_name, last_name, email, password_hash, iso_now()),
            )
            flash("Chiropractor account created.", "success")
        else:
            db.execute(
                """
                UPDATE users
                SET first_name = ?,
                    last_name = ?,
                    password_hash = ?,
                    role = 'clinician',
                    is_active = 1
                WHERE id = ?
                """,
                (first_name, last_name, password_hash, existing["id"]),
            )
            flash("Chiropractor account updated and reactivated.", "success")
        db.commit()
    else:
        flash(error, "error")

    return redirect(url_for("main.staff_settings", section="security"))


@bp.post("/staff/settings/chiropractors/<int:user_id>/status")
@staff_required
def update_staff_chiropractor_status(user_id: int):
    clinician = get_db().execute(
        """
        SELECT id, first_name, last_name, COALESCE(is_active, 1) AS is_active
        FROM users
        WHERE id = ? AND role = 'clinician'
        LIMIT 1
        """,
        (user_id,),
    ).fetchone()
    if clinician is None:
        abort(404)

    is_active = request.form.get("is_active") == "1"
    current_state = bool(clinician["is_active"])

    error = None
    if clinician["id"] == g.user["id"] and not is_active:
        error = "You cannot deactivate the account you are currently using."
    elif is_active and not current_state:
        active_chiropractor_count = sum(1 for item in get_chiropractor_roster() if item["is_active"])
        if active_chiropractor_count >= current_max_active_chiropractors():
            error = "Increase the max chiropractor count before activating another chiropractor."

    if error is None and current_state != is_active:
        get_db().execute(
            "UPDATE users SET is_active = ? WHERE id = ?",
            (1 if is_active else 0, clinician["id"]),
        )
        get_db().commit()
        flash(
            f"{clinician['first_name']} {clinician['last_name']} is now {'active' if is_active else 'inactive'}.",
            "success",
        )
    elif error is not None:
        flash(error, "error")

    return redirect(url_for("main.staff_settings", section="security"))


@bp.get("/staff/settings/database-backup")
@staff_required
def download_staff_database_backup():
    db_path = Path(current_app.config["DATABASE"])
    if not db_path.exists():
        abort(404)
    return send_file(
        db_path,
        mimetype="application/x-sqlite3",
        as_attachment=True,
        download_name=f"life-chiro-backup-{datetime.now().strftime('%Y%m%d-%H%M%S')}.sqlite3",
        max_age=0,
    )


@bp.get("/staff/availability")
@staff_required
def staff_schedule_availability():
    selected_service = selected_appointment_service(request.args.get("service_id"), active_only=True, fallback_to_default=False)
    appointment_type = request.args.get("appointment_type", "").strip()
    duration_minutes = int_or_none(request.args.get("duration_minutes", "30"))
    booking_policy = resolve_booking_policy(selected_service, appointment_type, duration_minutes if isinstance(duration_minutes, int) else None)
    clinician_user_id = requested_clinician_user_id(
        request.args.get("clinician_user_id"),
        allow_any=booking_policy["routing_mode"] == "team_round_robin",
    )
    if booking_policy["routing_mode"] == "team_round_robin" and (request.args.get("clinician_user_id", "").strip().lower() in {"", "any", "team"}):
        clinician_user_id = None
    location_id = selected_location_id(request.args.get("location_id"))
    availability = build_schedule_availability(
        request.args.get("date"),
        clinician_user_id,
        location_id,
        booking_policy["duration_minutes"],
        booking_policy=booking_policy,
        slot_increment_minutes=selected_slot_increment_minutes(request.args.get("slot_increment_minutes")),
    )
    return jsonify(serialize_schedule_availability(availability))


@bp.post("/staff/schedule-windows")
@staff_required
def create_staff_schedule_window():
    clinician_user_id = int_or_none(request.form.get("clinician_user_id"))
    location_id = selected_location_id(request.form.get("location_id"))
    weekday = int_or_none(request.form.get("weekday"))
    window_type = request.form.get("window_type", "").strip()
    starts_time = request.form.get("starts_time", "").strip()
    ends_time = request.form.get("ends_time", "").strip()
    label = request.form.get("label", "").strip()

    error = None
    clinician_ids = {option["value"] for option in clinician_options()}
    location_ids = {option["value"] for option in location_options()}
    if clinician_user_id in ("", None):
        clinician_user_id = None
    elif not isinstance(clinician_user_id, int) or clinician_user_id not in clinician_ids:
        error = "Choose a valid chiropractor for the schedule template."
    if error is None and (not isinstance(location_id, int) or location_id not in location_ids):
        error = "Choose a valid location."
    if error is None and (not isinstance(weekday, int) or weekday < 0 or weekday > 6):
        error = "Choose a valid weekday."
    elif error is None and window_type not in SCHEDULE_WINDOW_TYPE_META:
        error = "Choose a valid schedule type."
    elif error is None:
        start_time = time_from_value(starts_time)
        end_time = time_from_value(ends_time)
        if start_time is None or end_time is None:
            error = "Shift times must use valid hour and minute values."
        elif datetime.combine(date.today(), end_time) <= datetime.combine(date.today(), start_time):
            error = "Shift end time must be after the start time."

    if error is None:
        now = iso_now()
        get_db().execute(
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
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (clinician_user_id, location_id, weekday, window_type, starts_time, ends_time, label, now, now),
        )
        get_db().commit()
        flash("Schedule template saved.", "success")
    else:
        flash(error, "error")

    return redirect(settings_redirect_url())


@bp.post("/staff/schedule-windows/<int:window_id>/delete")
@staff_required
def delete_staff_schedule_window(window_id: int):
    window = get_schedule_window(window_id)
    if window is None:
        abort(404)
    get_db().execute("DELETE FROM schedule_windows WHERE id = ?", (window_id,))
    get_db().commit()
    flash("Schedule template removed.", "success")
    return redirect(settings_redirect_url())


@bp.post("/staff/locations")
@staff_required
def create_staff_location():
    name = request.form.get("name", "").strip()
    slug = request.form.get("slug", "").strip().lower()
    address = request.form.get("address", "").strip()
    phone = request.form.get("phone", "").strip()
    timezone = request.form.get("timezone", "").strip() or "Europe/London"

    error = None
    if not name:
        error = "Location name is required."
    elif not slug:
        error = "Location slug is required."
    elif get_db().execute("SELECT id FROM locations WHERE slug = ?", (slug,)).fetchone() is not None:
        error = "A location with that slug already exists."

    if error is None:
        now = iso_now()
        get_db().execute(
            """
            INSERT INTO locations (name, slug, address, phone, timezone, active, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, 1, ?, ?)
            """,
            (name, slug, address, phone, timezone, now, now),
        )
        get_db().commit()
        flash("Location added.", "success")
    else:
        flash(error, "error")

    return redirect(settings_redirect_url())


@bp.post("/staff/booking-services")
@staff_required
def create_or_update_staff_booking_service():
    service_id = int_or_none(request.form.get("service_id"))
    label = request.form.get("label", "").strip()
    service_key = slugify_service_key(request.form.get("service_key", "").strip() or label)
    description = request.form.get("description", "").strip()
    appointment_type = request.form.get("appointment_type", "").strip()
    duration_minutes = int_or_none(request.form.get("duration_minutes"))
    buffer_before_minutes = int_or_none(request.form.get("buffer_before_minutes", "0"))
    buffer_after_minutes = int_or_none(request.form.get("buffer_after_minutes", "0"))
    min_notice_minutes = int_or_none(request.form.get("min_notice_minutes", "0"))
    max_bookings_per_day = int_or_none(request.form.get("max_bookings_per_day", ""))
    routing_mode = request.form.get("routing_mode", "").strip() or "specific_clinician"
    requires_payment = request.form.get("requires_payment") == "on"
    price_amount = float_or_none(request.form.get("price_amount"))
    currency = (request.form.get("currency", "").strip() or "GBP").upper()
    display_order = int_or_none(request.form.get("display_order", "0"))
    active = 0 if request.form.get("active") == "0" else 1

    error = None
    if not label:
        error = "Service label is required."
    elif not service_key:
        error = "Service key is required."
    elif appointment_type not in APPOINTMENT_TYPE_META:
        error = "Choose a valid appointment type."
    elif not isinstance(duration_minutes, int) or not duration_is_supported(duration_minutes):
        error = "Choose a supported appointment length."
    elif not isinstance(buffer_before_minutes, int) or buffer_before_minutes < 0 or buffer_before_minutes > 120:
        error = "Buffer before must be between 0 and 120 minutes."
    elif not isinstance(buffer_after_minutes, int) or buffer_after_minutes < 0 or buffer_after_minutes > 120:
        error = "Buffer after must be between 0 and 120 minutes."
    elif not isinstance(min_notice_minutes, int) or min_notice_minutes < 0 or min_notice_minutes > 20160:
        error = "Minimum notice must be between 0 and 20,160 minutes."
    elif max_bookings_per_day not in (None, "") and (not isinstance(max_bookings_per_day, int) or max_bookings_per_day < 1 or max_bookings_per_day > 60):
        error = "Max bookings/day must be between 1 and 60."
    elif routing_mode not in BOOKING_ROUTING_MODE_META:
        error = "Choose a valid routing mode."
    elif requires_payment and not isinstance(price_amount, float):
        error = "Enter a numeric price when payment is required."
    elif not re.fullmatch(r"[A-Z]{3}", currency):
        error = "Currency must be a 3-letter code."
    elif not isinstance(display_order, int) or display_order < 0 or display_order > 1000:
        error = "Display order must be between 0 and 1000."

    db = get_db()
    existing = get_appointment_service(service_id) if isinstance(service_id, int) else None
    if error is None:
        duplicate = db.execute(
            "SELECT id FROM appointment_services WHERE service_key = ? LIMIT 1",
            (service_key,),
        ).fetchone()
        if duplicate is not None and (existing is None or duplicate["id"] != existing["id"]):
            error = "That service key already exists."

    if error is None:
        now = iso_now()
        if existing is None:
            db.execute(
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
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    service_key,
                    label,
                    description,
                    appointment_type,
                    duration_minutes,
                    buffer_before_minutes,
                    buffer_after_minutes,
                    int(requires_payment),
                    price_amount if isinstance(price_amount, float) else None,
                    currency,
                    min_notice_minutes,
                    max_bookings_per_day if isinstance(max_bookings_per_day, int) else None,
                    routing_mode,
                    active,
                    display_order,
                    now,
                    now,
                ),
            )
            flash("Booking service added.", "success")
        else:
            db.execute(
                """
                UPDATE appointment_services
                SET service_key = ?,
                    label = ?,
                    description = ?,
                    appointment_type = ?,
                    duration_minutes = ?,
                    buffer_before_minutes = ?,
                    buffer_after_minutes = ?,
                    requires_payment = ?,
                    price_amount = ?,
                    currency = ?,
                    min_notice_minutes = ?,
                    max_bookings_per_day = ?,
                    routing_mode = ?,
                    active = ?,
                    display_order = ?,
                    updated_at = ?
                WHERE id = ?
                """,
                (
                    service_key,
                    label,
                    description,
                    appointment_type,
                    duration_minutes,
                    buffer_before_minutes,
                    buffer_after_minutes,
                    int(requires_payment),
                    price_amount if isinstance(price_amount, float) else None,
                    currency,
                    min_notice_minutes,
                    max_bookings_per_day if isinstance(max_bookings_per_day, int) else None,
                    routing_mode,
                    active,
                    display_order,
                    now,
                    existing["id"],
                ),
            )
            flash("Booking service updated.", "success")
        db.commit()
    else:
        flash(error, "error")

    return redirect(settings_redirect_url())


@bp.route("/staff/reminders")
@staff_required
def staff_reminders():
    context = build_staff_reminders_context()
    return render_template("staff_reminders.html", **context)


@bp.post("/staff/appointments/<int:appointment_id>/send-reminder")
@staff_required
def send_staff_appointment_reminder(appointment_id: int):
    appointment_row = get_appointment_with_people(appointment_id)
    if appointment_row is None:
        abort(404)

    appointment = build_appointment_item(appointment_row)
    appointment = decorate_appointment_contacts(appointment)
    if not appointment["is_upcoming"]:
        flash("Only future scheduled appointments can receive reminders.", "error")
        return redirect(reminder_redirect_target())

    requested_channel = request.form.get("channel", "").strip().lower()
    channels = ["email", "sms"] if requested_channel == "both" else [requested_channel]
    valid_channels = [channel for channel in channels if channel in REMINDER_CHANNEL_META]
    if not valid_channels:
        flash("Choose a valid reminder channel.", "error")
        return redirect(reminder_redirect_target())
    for channel in valid_channels:
        if not reminder_channel_enabled(channel):
            flash(f"{reminder_channel_meta(channel)['label']} reminders are disabled in settings.", "error")
            return redirect(reminder_redirect_target())

    allow_resend = request.form.get("allow_resend", "").strip() == "1"
    outcomes = {"logged": 0, "sent": 0, "failed": 0, "skipped": 0}
    skipped_labels: list[str] = []
    db = get_db()

    for channel in valid_channels:
        payload = reminder_preview_payload(appointment, channel)
        if not payload["recipient"]:
            outcomes["skipped"] += 1
            skipped_labels.append(f"{reminder_channel_meta(channel)['label']} missing contact details")
            continue

        bucket = appointment["reminder_bucket"] or "manual"
        if not allow_resend and existing_appointment_reminder(appointment_id, channel, bucket) is not None:
            outcomes["skipped"] += 1
            skipped_labels.append(f"{reminder_channel_meta(channel)['label']} already sent for this reminder window")
            continue

        try:
            status, delivery_mode, error_message = deliver_reminder(current_app.config, payload)
        except Exception as exc:  # pragma: no cover - only hit on transport errors
            status = "failed"
            delivery_mode = current_app.config.get(
                "REMINDER_EMAIL_MODE" if channel == "email" else "REMINDER_SMS_MODE",
                "outbox",
            )
            error_message = str(exc)

        log_appointment_reminder(
            appointment,
            channel,
            payload,
            status=status,
            delivery_mode=delivery_mode,
            error_message=error_message,
        )
        outcomes[status] += 1

    db.commit()

    messages = []
    if outcomes["sent"]:
        messages.append(f"{outcomes['sent']} sent")
    if outcomes["logged"]:
        messages.append(f"{outcomes['logged']} logged to outbox")
    if outcomes["failed"]:
        messages.append(f"{outcomes['failed']} failed")
    if outcomes["skipped"]:
        messages.append(f"{outcomes['skipped']} skipped")

    if outcomes["sent"] or outcomes["logged"]:
        flash(f"Reminder processing complete: {', '.join(messages)}.", "success")
    elif outcomes["failed"]:
        flash(f"Reminder processing failed: {', '.join(messages)}.", "error")
    else:
        flash(", ".join(skipped_labels) or "No reminders were processed.", "error")

    return redirect(reminder_redirect_target())


@bp.post("/staff/patients/<int:user_id>/care-plan")
@staff_required
def create_staff_patient_care_plan(user_id: int):
    patient = get_client_user(user_id)
    if patient is None:
        abort(404)

    raw_service_value = request.form.get("service_id")
    selected_service = selected_appointment_service(raw_service_value, active_only=True, fallback_to_default=False)
    if selected_service is None or selected_service["appointment_type"] != "care_plan":
        selected_service = default_service_for_appointment_type("care_plan")
    booking_policy = resolve_booking_policy(
        selected_service,
        "care_plan",
        selected_service["duration_minutes"] if selected_service else default_duration_for_type("care_plan"),
    )
    raw_clinician_value = request.form.get("clinician_user_id")
    clinician_user_id = requested_clinician_user_id(
        raw_clinician_value,
        allow_any=booking_policy["routing_mode"] == "team_round_robin",
    )
    if booking_policy["routing_mode"] == "team_round_robin" and (raw_clinician_value or "").strip().lower() in {"", "any", "team"}:
        clinician_user_id = None
    location_id = selected_location_id(request.form.get("location_id"))
    slot_start = request.form.get("slot_start", "").strip()
    slot_increment_minutes = selected_slot_increment_minutes(request.form.get("slot_increment_minutes"))
    frequency_per_week = normalize_care_plan_frequency(request.form.get("frequency_per_week"))
    duration_weeks = normalize_care_plan_weeks(request.form.get("duration_weeks"))
    booking_mode = normalize_care_plan_booking_mode(request.form.get("care_plan_booking_mode"))
    title = request.form.get("care_plan_title", "").strip()
    patient_details = request.form.get("patient_details", "").strip()
    note = request.form.get("note", "").strip()

    error = None
    if raw_service_value and (selected_service is None or selected_service["appointment_type"] != "care_plan"):
        error = "Choose a care-plan service before creating a care plan."
    elif selected_service is None:
        error = "Choose a care-plan service before creating a care plan."
    elif location_id is None:
        error = "Choose a valid location."
    elif booking_policy["routing_mode"] != "team_round_robin" and clinician_user_id is None:
        error = "Choose a valid chiropractor."
    elif frequency_per_week is None:
        error = "Choose a valid care-plan frequency."
    elif duration_weeks is None:
        error = "Choose a valid care-plan duration."
    elif booking_mode is None:
        error = "Choose a valid care-plan booking mode."
    elif not slot_start:
        error = "Choose the first visit slot from the live diary before creating a care plan."
    else:
        starts_parsed = parse_iso(slot_start)
        if starts_parsed is None:
            error = "Choose a valid first visit slot."
        elif resolve_slot_assignment(
            starts_parsed,
            clinician_user_id,
            location_id,
            booking_policy,
            slot_increment_minutes=slot_increment_minutes,
        ) is None:
            error = "The selected first visit slot is no longer available."

    if error is not None:
        flash(error, "error")
        return redirect(
            url_for(
                "main.staff_patient_detail",
                user_id=user_id,
                location_id=location_id,
                clinician_user_id="any" if clinician_user_id is None and booking_policy["routing_mode"] == "team_round_robin" else clinician_user_id,
                service_id=booking_policy["service_id"],
                appointment_type="care_plan",
                duration_minutes=booking_policy["duration_minutes"],
                appointment_date=slot_start[:10] if slot_start else None,
            )
        )

    starts_parsed = parse_iso(slot_start)
    generated = generate_care_plan_schedule(
        frequency_per_week=frequency_per_week,
        duration_weeks=duration_weeks,
        starts_at=starts_parsed,
        follow_up_duration_minutes=booking_policy["duration_minutes"],
        patient_details=patient_details,
        note=note,
        fee_amount=booking_policy["price_amount"] if isinstance(booking_policy["price_amount"], (int, float)) else None,
    )
    resolved_title = title or care_plan_title_default(duration_weeks, frequency_per_week)
    db = get_db()
    archived_count = archive_active_care_plans(user_id)
    now = iso_now()
    cursor = db.execute(
        """
        INSERT INTO care_plans (
            patient_user_id,
            clinician_user_id,
            location_id,
            service_id,
            title,
            frequency_per_week,
            duration_weeks,
            total_visits,
            midpoint_visit_number,
            booking_mode,
            start_date,
            start_slot,
            status,
            patient_details,
            note,
            created_at,
            updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'active', ?, ?, ?, ?)
        """,
        (
            user_id,
            clinician_user_id,
            location_id,
            booking_policy["service_id"],
            resolved_title,
            frequency_per_week,
            duration_weeks,
            generated["total_visits"],
            generated["midpoint_visit_number"],
            booking_mode,
            starts_parsed.date().isoformat(),
            slot_start,
            patient_details,
            note,
            now,
            now,
        ),
    )
    care_plan_id = cursor.lastrowid
    booked_count = 0
    unbooked_count = 0

    for visit_seed in generated["visits"]:
        visit_policy = care_plan_visit_policy(booking_policy, visit_seed)
        appointment_id = None
        booked = 0
        visit_status = "unbooked"
        booked_start_value = visit_seed["suggested_starts_at"]
        should_attempt_booking = booking_mode == "all" or visit_seed["visit_number"] == 1
        if should_attempt_booking:
            preferred_start = parse_iso(visit_seed["suggested_starts_at"])
            selected_slot = find_care_plan_slot(
                preferred_start,
                clinician_user_id,
                location_id,
                visit_policy,
                slot_increment_minutes=slot_increment_minutes,
            )
            if selected_slot is not None:
                actual_start = parse_iso(selected_slot["value"])
                actual_end = actual_start + timedelta(minutes=visit_policy["duration_minutes"])
                assigned_clinician_id = selected_slot.get("clinician_user_id") or clinician_user_id
                appointment_id = create_patient_appointment(
                    user_id,
                    assigned_clinician_id,
                    location_id,
                    "care_plan",
                    format_datetime_local(actual_start),
                    service_id=visit_policy["service_id"],
                    ends_at=format_datetime_local(actual_end),
                    note=visit_seed["note"],
                    patient_details=visit_seed["patient_details"],
                    requires_payment=visit_policy["requires_payment"],
                    payment_status="pending" if visit_policy["requires_payment"] else "not_required",
                    payment_amount=visit_policy["price_amount"],
                    booking_channel="staff",
                    service_label_snapshot=visit_seed["label"],
                    policy_snapshot=visit_policy,
                    booking_source="care_plan_sync",
                )
                log_booking_event(
                    "booking_created",
                    appointment_id,
                    user_id,
                    {
                        "source": "care_plan_sync",
                        "care_plan_id": care_plan_id,
                        "care_plan_visit_number": visit_seed["visit_number"],
                        "care_plan_visit_kind": visit_seed["visit_kind"],
                        "service_id": visit_policy["service_id"],
                        "service_label": visit_seed["label"],
                        "location_id": location_id,
                        "clinician_user_id": assigned_clinician_id,
                    },
                )
                booked = 1
                visit_status = "scheduled"
                booked_start_value = format_datetime_local(actual_start)
                booked_count += 1
            else:
                unbooked_count += 1
        else:
            unbooked_count += 1

        db.execute(
            """
            INSERT INTO care_plan_visits (
                care_plan_id,
                visit_number,
                visit_kind,
                label,
                suggested_date,
                suggested_starts_at,
                duration_minutes,
                fee_amount,
                status,
                booked,
                appointment_id,
                patient_details,
                note,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                care_plan_id,
                visit_seed["visit_number"],
                visit_seed["visit_kind"],
                visit_seed["label"],
                booked_start_value[:10],
                booked_start_value,
                visit_seed["duration_minutes"],
                visit_seed["fee_amount"],
                visit_status,
                booked,
                appointment_id,
                visit_seed["patient_details"],
                visit_seed["note"],
                now,
                now,
            ),
        )

    refresh_care_plan_status(care_plan_id)
    db.commit()

    message = f"Care plan created: {booked_count} of {generated['total_visits']} visits synced to the live calendar."
    if archived_count:
        message = f"{message} Archived {archived_count} previous active care plan."
    if unbooked_count:
        message = f"{message} {unbooked_count} visit(s) still need manual booking."
    flash(message, "success")
    return redirect(url_for("main.staff_patient_detail", user_id=user_id))


@bp.post("/staff/patients/<int:user_id>/appointments")
@staff_required
def create_staff_patient_appointment(user_id: int):
    patient = get_client_user(user_id)
    if patient is None:
        abort(404)

    selected_service = selected_appointment_service(request.form.get("service_id"), active_only=True, fallback_to_default=False)
    appointment_type = request.form.get("appointment_type", "").strip()
    if selected_service is not None and not appointment_type:
        appointment_type = selected_service["appointment_type"]
    duration_minutes = int_or_none(
        request.form.get(
            "duration_minutes",
            str(selected_service["duration_minutes"] if selected_service else default_duration_for_type(appointment_type or "care_plan")),
        )
    )
    booking_policy = resolve_booking_policy(selected_service, appointment_type, duration_minutes if isinstance(duration_minutes, int) else None)

    raw_clinician_value = request.form.get("clinician_user_id")
    clinician_user_id = requested_clinician_user_id(
        raw_clinician_value,
        allow_any=booking_policy["routing_mode"] == "team_round_robin",
    )
    if booking_policy["routing_mode"] == "team_round_robin" and (raw_clinician_value or "").strip().lower() in {"", "any", "team"}:
        clinician_user_id = None
    location_id = selected_location_id(request.form.get("location_id"))
    appointment_date = request.form.get("appointment_date", "").strip()
    slot_start = request.form.get("slot_start", "").strip()
    starts_at = request.form.get("starts_at", "").strip()
    ends_at = request.form.get("ends_at", "").strip() or None
    note = request.form.get("note", "").strip()
    patient_details = request.form.get("patient_details", "").strip() or note
    repeat_count = int_or_none(request.form.get("repeat_count", "1"))
    repeat_every_days = int_or_none(request.form.get("repeat_every_days", "7"))
    care_plan_visit_id = int_or_none(request.form.get("care_plan_visit_id"))
    care_plan_visit = get_care_plan_visit(care_plan_visit_id) if isinstance(care_plan_visit_id, int) else None
    if care_plan_visit is not None:
        booking_policy = care_plan_visit_policy(
            booking_policy,
            {
                "visit_kind": care_plan_visit["visit_kind"],
                "duration_minutes": care_plan_visit["duration_minutes"] or booking_policy["duration_minutes"],
            },
        )
        booking_policy["service_label"] = care_plan_visit["label"] or booking_policy["service_label"]

    error = None
    if appointment_type not in APPOINTMENT_TYPE_META:
        error = "Choose a valid appointment type."
    elif care_plan_visit is not None and appointment_type != "care_plan":
        error = "Care-plan visits must be booked as care-plan appointments."
    elif location_id is None:
        error = "Choose a valid location."
    elif booking_policy["routing_mode"] != "team_round_robin" and clinician_user_id is None:
        error = "Choose a valid chiropractor."
    elif isinstance(care_plan_visit_id, int) and (care_plan_visit is None or care_plan_visit["patient_user_id"] != user_id):
        error = "Choose a valid care-plan visit before booking it."
    elif care_plan_visit is not None and care_plan_visit["appointment_id"] is not None:
        error = "This care-plan visit is already booked."
    elif not isinstance(repeat_count, int) or repeat_count < 1 or repeat_count > 24:
        error = "Repeat count must be between 1 and 24."
    elif not isinstance(repeat_every_days, int) or repeat_every_days < 1 or repeat_every_days > 30:
        error = "Repeat interval must be between 1 and 30 days."
    elif care_plan_visit is not None and repeat_count != 1:
        error = "Use repeat count 1 when booking a specific care-plan visit."
    elif slot_start:
        starts_parsed = parse_iso(slot_start)
        if starts_parsed is None:
            error = "Choose a valid available time slot."
        elif appointment_date and starts_parsed.date().isoformat() != appointment_date:
            error = "Selected time slot does not match the chosen date."
        elif resolve_slot_assignment(starts_parsed, clinician_user_id, location_id, booking_policy) is None:
            error = "Selected time slot is no longer available within the clinic schedule at this location."
    elif not starts_at:
        error = "Appointment start time is required."
    else:
        starts_parsed = parse_iso(starts_at)
        ends_parsed = parse_iso(ends_at)
        if starts_parsed is None:
            error = "Appointment start time is invalid."
        elif ends_at and ends_parsed is None:
            error = "Appointment end time is invalid."
        elif ends_parsed and starts_parsed and ends_parsed <= starts_parsed:
            error = "Appointment end time must be after the start time."
        elif booking_policy["routing_mode"] == "team_round_robin" and clinician_user_id is None:
            error = "Choose a chiropractor when manually entering a start time for team-routed services."

    if error is None:
        created_slots: list[tuple[str, str | None, int | None]] = []
        if slot_start:
            base_start = parse_iso(slot_start)
            duration = timedelta(minutes=booking_policy["duration_minutes"])
            for index in range(repeat_count):
                item_start = base_start + timedelta(days=repeat_every_days * index)
                assignment = resolve_slot_assignment(item_start, clinician_user_id, location_id, booking_policy)
                if assignment is None:
                    error = (
                        f"{item_start.strftime('%d %b %Y %H:%M')} is outside shift hours, "
                        "falls in downtime, violates service policy, or is already booked."
                    )
                    break
                assigned_clinician_id = assignment.get("clinician_user_id") or clinician_user_id
                item_end = item_start + duration
                created_slots.append((format_datetime_local(item_start), format_datetime_local(item_end), assigned_clinician_id))
        else:
            duration = None
            if ends_at:
                duration = parse_iso(ends_at) - parse_iso(starts_at)
            assigned_clinician_id = clinician_user_id
            for index in range(repeat_count):
                item_start = parse_iso(starts_at) + timedelta(days=repeat_every_days * index)
                item_end = item_start + duration if duration is not None else None
                created_slots.append(
                    (
                        format_datetime_local(item_start),
                        format_datetime_local(item_end) if item_end else None,
                        assigned_clinician_id,
                    )
                )

    if error is None:
        created = 0
        created_appointment_ids: list[int] = []
        for item_start, item_end, item_clinician_id in created_slots:
            appointment_id = create_patient_appointment(
                user_id,
                item_clinician_id,
                location_id,
                appointment_type,
                item_start,
                service_id=booking_policy["service_id"],
                ends_at=item_end,
                note=note,
                patient_details=patient_details,
                requires_payment=booking_policy["requires_payment"],
                payment_status="pending" if booking_policy["requires_payment"] else "not_required",
                payment_amount=booking_policy["price_amount"],
                booking_channel="staff",
                service_label_snapshot=booking_policy["service_label"],
                policy_snapshot=booking_policy,
                booking_source="care_plan_sync" if care_plan_visit is not None else "staff_portal",
            )
            log_booking_event(
                "booking_created",
                appointment_id,
                user_id,
                {
                    "source": "care_plan_sync" if care_plan_visit is not None else "staff_portal",
                    "service_id": booking_policy["service_id"],
                    "service_label": booking_policy["service_label"],
                    "location_id": location_id,
                    "clinician_user_id": item_clinician_id,
                },
            )
            created_appointment_ids.append(appointment_id)
            created += 1
        if care_plan_visit is not None and created_appointment_ids:
            linked_appointment_id = created_appointment_ids[0]
            linked_start = created_slots[0][0]
            get_db().execute(
                """
                UPDATE care_plan_visits
                SET appointment_id = ?,
                    booked = 1,
                    status = 'scheduled',
                    suggested_date = ?,
                    suggested_starts_at = ?,
                    duration_minutes = ?,
                    patient_details = ?,
                    note = ?,
                    updated_at = ?
                WHERE id = ?
                """,
                (
                    linked_appointment_id,
                    linked_start[:10],
                    linked_start,
                    booking_policy["duration_minutes"],
                    patient_details,
                    note,
                    iso_now(),
                    care_plan_visit["id"],
                ),
            )
            refresh_care_plan_status(care_plan_visit["care_plan_id"])
        get_db().commit()
        label = booking_policy["service_label"] or appointment_type_meta(appointment_type)["label"]
        if care_plan_visit is not None:
            generic_label = appointment_type_meta("care_plan")["label"]
            visit_label = care_plan_visit["label"] or label
            label = generic_label if visit_label == generic_label else f"{generic_label} ({visit_label})"
        if created == 1:
            flash(f"{label} scheduled.", "success")
        else:
            flash(f"{created} {label} appointments scheduled.", "success")
    else:
        flash(error, "error")

    return redirect(
        url_for(
            "main.staff_patient_detail",
            user_id=user_id,
            location_id=location_id,
            clinician_user_id="any" if clinician_user_id is None and booking_policy["routing_mode"] == "team_round_robin" else clinician_user_id,
            service_id=booking_policy["service_id"],
            appointment_type=appointment_type,
            duration_minutes=booking_policy["duration_minutes"],
            appointment_date=appointment_date or (slot_start[:10] if slot_start else None),
            care_plan_visit_id=care_plan_visit["id"] if care_plan_visit is not None and error is not None else None,
        )
    )


@bp.post("/staff/patients/<int:user_id>/appointments/<int:appointment_id>")
@staff_required
def update_staff_patient_appointment(user_id: int, appointment_id: int):
    patient = get_client_user(user_id)
    appointment = get_patient_appointment(user_id, appointment_id)
    if patient is None or appointment is None:
        abort(404)

    action = request.form.get("action", "save").strip().lower()
    appointment_type = request.form.get("appointment_type", "").strip()
    clinician_user_id = selected_clinician_user_id(request.form.get("clinician_user_id")) or appointment["clinician_user_id"]
    location_id = selected_location_id(request.form.get("location_id")) or appointment["location_id"]
    starts_at = request.form.get("starts_at", "").strip()
    ends_at = request.form.get("ends_at", "").strip() or None
    note = request.form.get("note", "").strip()
    patient_details = request.form.get("patient_details", "").strip()
    clinical_note = request.form.get("clinical_note", "").strip()
    billing_status = request.form.get("billing_status", appointment["billing_status"]).strip().lower()
    billing_code = request.form.get("billing_code", "").strip()
    billing_amount = float_or_none(request.form.get("billing_amount"))

    status = appointment["status"]
    if action == "complete":
        status = "completed"
    elif action == "cancel":
        status = "cancelled"
    elif action == "reopen":
        status = "scheduled"
    else:
        status = request.form.get("status", appointment["status"]).strip().lower()

    error = None
    if appointment_type not in APPOINTMENT_TYPE_META:
        error = "Choose a valid appointment type."
    elif location_id is None:
        error = "Choose a valid location."
    elif clinician_user_id is None:
        error = "Choose a valid chiropractor."
    elif status not in APPOINTMENT_STATUS_META:
        error = "Choose a valid appointment status."
    elif billing_status not in BILLING_STATUS_META:
        error = "Choose a valid billing status."
    elif not starts_at:
        error = "Appointment start time is required."
    else:
        starts_parsed = parse_iso(starts_at)
        ends_parsed = parse_iso(ends_at)
        if starts_parsed is None:
            error = "Appointment start time is invalid."
        elif ends_at and ends_parsed is None:
            error = "Appointment end time is invalid."
        elif ends_parsed and starts_parsed and ends_parsed <= starts_parsed:
            error = "Appointment end time must be after the start time."
        elif billing_amount not in (None, "") and not isinstance(billing_amount, float):
            error = "Billing amount must be numeric."

    if error is None:
        get_db().execute(
            """
            UPDATE appointments
            SET clinician_user_id = ?,
                location_id = ?,
                appointment_type = ?,
                status = ?,
                starts_at = ?,
                ends_at = ?,
                note = ?,
                patient_details = ?,
                clinical_note = ?,
                billing_status = ?,
                billing_code = ?,
                billing_amount = ?,
                updated_at = ?
            WHERE id = ? AND patient_user_id = ?
            """,
            (
                clinician_user_id,
                location_id,
                appointment_type,
                status,
                starts_at,
                ends_at,
                note,
                patient_details,
                clinical_note,
                billing_status,
                billing_code,
                billing_amount if isinstance(billing_amount, float) else None,
                iso_now(),
                appointment_id,
                user_id,
            ),
        )
        event_type = "booking_updated"
        if action == "cancel":
            event_type = "booking_cancelled"
        elif action == "reopen":
            event_type = "booking_reopened"
        elif starts_at != appointment["starts_at"]:
            event_type = "booking_rescheduled"
        elif action == "complete":
            event_type = "booking_completed"
        log_booking_event(
            event_type,
            appointment_id,
            user_id,
            {
                "source": "staff_portal",
                "appointment_type": appointment_type,
                "status": status,
                "starts_at": starts_at,
                "ends_at": ends_at,
            },
        )
        sync_care_plan_visit_for_appointment(appointment_id)
        get_db().commit()
        if action == "complete":
            flash("Appointment marked completed.", "success")
        elif action == "cancel":
            flash("Appointment cancelled.", "success")
        elif action == "reopen":
            flash("Appointment reopened.", "success")
        else:
            flash("Appointment updated.", "success")
    else:
        flash(error, "error")

    return redirect(url_for("main.staff_patient_detail", user_id=user_id))


@bp.route("/appointments")
@client_required
def appointments():
    schedule = build_patient_schedule_context(g.user["id"], request.args.get("month"))
    booking = booking_selection_context("patient_portal")
    booking_disabled_reason = None
    if not online_booking_enabled():
        booking_disabled_reason = "Online booking is disabled in clinic settings. Contact the clinic to schedule a visit."
    return render_template("appointments.html", schedule=schedule, booking_disabled_reason=booking_disabled_reason, **booking)


@bp.post("/appointments/self-book")
@client_required
def self_book_appointment():
    if not online_booking_enabled():
        flash("Online booking is disabled in clinic settings.", "error")
        return redirect(url_for("main.appointments"))

    selected_service = selected_appointment_service(request.form.get("service_id"), active_only=True, fallback_to_default=False)
    appointment_type = request.form.get("appointment_type", "").strip()
    if selected_service is not None and not appointment_type:
        appointment_type = selected_service["appointment_type"]
    duration_minutes = int_or_none(
        request.form.get(
            "duration_minutes",
            str(selected_service["duration_minutes"] if selected_service else default_duration_for_type(appointment_type or "care_plan")),
        )
    )
    booking_policy = resolve_booking_policy(selected_service, appointment_type, duration_minutes if isinstance(duration_minutes, int) else None)
    raw_clinician_value = request.form.get("clinician_user_id")
    clinician_user_id = requested_clinician_user_id(
        raw_clinician_value,
        allow_any=booking_policy["routing_mode"] == "team_round_robin",
    )
    if booking_policy["routing_mode"] == "team_round_robin" and (raw_clinician_value or "").strip().lower() in {"", "any", "team"}:
        clinician_user_id = None
    location_id = selected_location_id(request.form.get("location_id"))
    appointment_date = request.form.get("appointment_date", "").strip()
    slot_start = request.form.get("slot_start", "").strip()
    patient_details = request.form.get("patient_details", "").strip()

    error = None
    if appointment_type not in APPOINTMENT_TYPE_META:
        error = "Choose a valid appointment type."
    elif location_id is None:
        error = "Choose a valid clinic location."
    elif booking_policy["routing_mode"] != "team_round_robin" and clinician_user_id is None:
        error = "Choose a valid chiropractor."
    elif not slot_start:
        error = "Choose an available time slot."
    else:
        starts_parsed = parse_iso(slot_start)
        if starts_parsed is None:
            error = "Choose a valid available time slot."
        elif appointment_date and starts_parsed.date().isoformat() != appointment_date:
            error = "Selected slot does not match the chosen date."
        elif resolve_slot_assignment(starts_parsed, clinician_user_id, location_id, booking_policy) is None:
            error = "Selected slot is no longer available."

    if error is None:
        starts_parsed = parse_iso(slot_start)
        assignment = resolve_slot_assignment(starts_parsed, clinician_user_id, location_id, booking_policy)
        assigned_clinician_id = assignment.get("clinician_user_id") if assignment else clinician_user_id
        ends_parsed = starts_parsed + timedelta(minutes=booking_policy["duration_minutes"])
        appointment_id = create_patient_appointment(
            g.user["id"],
            assigned_clinician_id,
            location_id,
            appointment_type,
            format_datetime_local(starts_parsed),
            service_id=booking_policy["service_id"],
            ends_at=format_datetime_local(ends_parsed),
            note=patient_details,
            patient_details=patient_details,
            requires_payment=booking_policy["requires_payment"],
            payment_status="pending" if booking_policy["requires_payment"] else "not_required",
            payment_amount=booking_policy["price_amount"],
            booking_channel="portal_link",
            service_label_snapshot=booking_policy["service_label"],
            policy_snapshot=booking_policy,
            booking_source="patient_portal",
        )
        log_booking_event(
            "booking_created",
            appointment_id,
            g.user["id"],
            {
                "source": "patient_portal",
                "service_id": booking_policy["service_id"],
                "service_label": booking_policy["service_label"],
                "location_id": location_id,
                "clinician_user_id": assigned_clinician_id,
            },
        )
        get_db().commit()
        if booking_policy["requires_payment"] and isinstance(booking_policy["price_amount"], (int, float)):
            flash(
                f"Appointment booked. Payment of {booking_policy['price_amount']:.2f} {booking_policy['currency']} is marked pending.",
                "success",
            )
        else:
            flash("Appointment booked from your portal.", "success")
    else:
        flash(error, "error")

    return redirect(
        url_for(
            "main.appointments",
            location_id=location_id,
            clinician_user_id="any" if clinician_user_id is None and booking_policy["routing_mode"] == "team_round_robin" else clinician_user_id,
            service_id=booking_policy["service_id"],
            appointment_type=appointment_type or None,
            duration_minutes=booking_policy["duration_minutes"],
            appointment_date=appointment_date or (slot_start[:10] if slot_start else None),
        )
    )


@bp.post("/appointments/<int:appointment_id>/cancel")
@client_required
def cancel_self_booked_appointment(appointment_id: int):
    appointment_row = get_appointment_with_people(appointment_id)
    if appointment_row is None or appointment_row["patient_user_id"] != g.user["id"]:
        abort(404)

    appointment = build_appointment_item(appointment_row)
    if appointment["status"] != "scheduled":
        flash("Only scheduled appointments can be cancelled.", "error")
        return redirect(url_for("main.appointments"))
    if not appointment["can_self_cancel"]:
        flash("This appointment is inside the minimum notice window and can no longer be cancelled online.", "error")
        return redirect(url_for("main.appointments"))

    get_db().execute(
        """
        UPDATE appointments
        SET status = 'cancelled',
            updated_at = ?
        WHERE id = ? AND patient_user_id = ?
        """,
        (iso_now(), appointment_id, g.user["id"]),
    )
    log_booking_event(
        "booking_cancelled",
        appointment_id,
        g.user["id"],
        {
            "source": "patient_portal",
            "self_service": True,
        },
    )
    sync_care_plan_visit_for_appointment(appointment_id)
    get_db().commit()
    flash("Appointment cancelled. You can book a new slot anytime.", "success")
    return redirect(url_for("main.appointments"))


@bp.route("/staff/patients/<int:user_id>")
@staff_required
def staff_patient_detail(user_id: int):
    context = staff_patient_context(user_id)
    if context is None:
        abort(404)
    return render_template("staff_patient.html", active_staff_tab="overview", **context)


@bp.route("/staff/patients/<int:user_id>/summit-assessment")
@staff_required
def staff_patient_assessment(user_id: int):
    context = staff_patient_context(user_id)
    if context is None:
        abort(404)
    return render_template("staff_assessment.html", active_staff_tab="assessment", **context)


@bp.route("/staff/patients/<int:user_id>/decision-support")
@staff_required
def staff_patient_decision_support(user_id: int):
    context = staff_patient_context(user_id)
    if context is None:
        abort(404)
    return render_template("staff_decision_support.html", active_staff_tab="decision_support", **context)


@bp.get("/staff/tools/claude-ddx-tool.jsx")
@staff_required
def staff_claude_ddx_tool():
    source = build_claude_artifact_source()
    if source is None:
        abort(404)
    return current_app.response_class(
        source,
        mimetype="text/babel",
        headers={"Cache-Control": "no-store"},
    )


@bp.route("/practitioner/appointments/<int:appointment_id>/soap", methods=("GET", "POST"))
@staff_required
def practitioner_appointment_soap_note(appointment_id: int):
    appointment_row = get_appointment_with_people(appointment_id)
    if appointment_row is None:
        abort(404)
    if not can_access_staff_appointment(g.user, appointment_row):
        abort(403)

    patient = get_client_user(appointment_row["patient_user_id"])
    if patient is None:
        abort(404)

    existing_note = get_appointment_soap_note(appointment_id)
    if request.method == "POST":
        subjective = request.form.get("subjective", "").strip()
        objective = request.form.get("objective", "").strip()
        assessment = request.form.get("assessment", "").strip()
        plan = request.form.get("plan", "").strip()
        spine_findings = normalize_spine_findings(request.form.get("spine_findings_json"))
        spine_findings_json = json.dumps(spine_findings, separators=(",", ":"))
        has_spine_findings = bool(spine_findings["left"] or spine_findings["right"])

        error = None
        if not any((subjective, objective, assessment, plan)) and not has_spine_findings:
            error = "Add at least one SOAP section or spine dysfunction level before saving the appointment note."

        if error is None:
            now = iso_now()
            db = get_db()
            if existing_note is None:
                db.execute(
                    """
                    INSERT INTO appointment_soap_notes (
                        appointment_id,
                        patient_user_id,
                        clinician_user_id,
                        subjective,
                        objective,
                        assessment,
                        plan,
                        spine_findings_json,
                        created_at,
                        updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        appointment_id,
                        appointment_row["patient_user_id"],
                        g.user["id"],
                        subjective,
                        objective,
                        assessment,
                        plan,
                        spine_findings_json,
                        now,
                        now,
                    ),
                )
            else:
                db.execute(
                    """
                    UPDATE appointment_soap_notes
                    SET clinician_user_id = ?,
                        subjective = ?,
                        objective = ?,
                        assessment = ?,
                        plan = ?,
                        spine_findings_json = ?,
                        updated_at = ?
                    WHERE appointment_id = ?
                    """,
                    (g.user["id"], subjective, objective, assessment, plan, spine_findings_json, now, appointment_id),
                )
            db.commit()
            flash("SOAP note saved for this appointment.", "success")
            return redirect(url_for("main.practitioner_appointment_soap_note", appointment_id=appointment_id))

        flash(error, "error")

    appointment = decorate_appointment_contacts(build_appointment_item(get_appointment_with_people(appointment_id)))
    soap_note = get_appointment_soap_note(appointment_id)
    spine_findings = {"left": [], "right": []}
    if soap_note is not None and "spine_findings_json" in soap_note.keys():
        spine_findings = normalize_spine_findings(soap_note["spine_findings_json"])
    return render_template(
        "practitioner_soap_note.html",
        appointment=appointment,
        patient=patient,
        soap_note=soap_note,
        spine_segments=SPINE_SEGMENT_ORDER,
        spine_findings=spine_findings,
    )


@bp.post("/staff/patients/<int:user_id>/notes")
@staff_required
def save_staff_patient_notes(user_id: int):
    patient = get_client_user(user_id)
    if patient is None:
        abort(404)

    exam_findings = request.form.get("exam_findings", "").strip()
    assessment = request.form.get("assessment", "").strip()
    care_plan = request.form.get("care_plan", "").strip()
    internal_notes = request.form.get("internal_notes", "").strip()
    next_visit_at = request.form.get("next_visit_at", "").strip() or None
    now = iso_now()

    db = get_db()
    existing = get_notes_for_patient(user_id)
    if existing is None:
        db.execute(
            """
            INSERT INTO clinician_notes (
                patient_user_id,
                clinician_user_id,
                exam_findings,
                assessment,
                care_plan,
                internal_notes,
                next_visit_at,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (user_id, g.user["id"], exam_findings, assessment, care_plan, internal_notes, next_visit_at, now, now),
        )
    else:
        db.execute(
            """
            UPDATE clinician_notes
            SET clinician_user_id = ?,
                exam_findings = ?,
                assessment = ?,
                care_plan = ?,
                internal_notes = ?,
                next_visit_at = ?,
                updated_at = ?
            WHERE patient_user_id = ?
            """,
            (g.user["id"], exam_findings, assessment, care_plan, internal_notes, next_visit_at, now, user_id),
        )
    db.commit()
    flash("Clinician notes saved.", "success")
    return redirect(url_for("main.staff_patient_detail", user_id=user_id))


@bp.post("/staff/patients/<int:user_id>/initial-consult")
@staff_required
def save_initial_consult_report(user_id: int):
    patient = get_client_user(user_id)
    if patient is None:
        abort(404)

    redirect_to = request.form.get("redirect_to", "").strip().lower()

    def redirect_target():
        endpoint = "main.staff_patient_assessment" if redirect_to == "assessment" else "main.staff_patient_detail"
        return redirect(url_for(endpoint, user_id=user_id))

    action = request.form.get("action", "draft").strip().lower()
    if action not in {"draft", "published"}:
        flash("Invalid report action.", "error")
        return redirect_target()

    submission = get_submission_for_user(user_id)
    intake_payload = json.loads(submission["payload_json"]) if submission else {}
    existing = get_visit_report_for_patient(user_id)
    existing_data = dict(existing) if existing else None
    base_assessment = build_summit_assessment(dict(patient), intake_payload, existing_data)

    visit_date = request.form.get("visit_date", (existing_data or {}).get("visit_date", "")).strip()
    assessment_date = request.form.get("assessment_date", base_assessment["assessment_date"]).strip()
    if not assessment_date and visit_date:
        assessment_date = visit_date[:10]

    patient_goals = split_lines(request.form.get("patient_goals", base_assessment["patient_goals_text"]))
    if not patient_goals:
        patient_goals = base_assessment["patient"]["goals"]

    summit_assessment = {
        "patient": {
            "full_name": base_assessment["patient"]["full_name"],
            "dob": base_assessment["patient"]["dob"],
            "sex": base_assessment["patient"]["sex"],
            "age": base_assessment["patient"]["age"],
            "referring_provider": request.form.get(
                "referring_provider",
                base_assessment["patient"]["referring_provider"],
            ).strip(),
            "goals": patient_goals,
        },
        "assessment_date": assessment_date or base_assessment["assessment_date"],
        "history": {
            "chief_complaint": request.form.get(
                "history_chief_complaint",
                base_assessment["history"]["chief_complaint"],
            ).strip(),
            "duration_years": float_or_none(
                request.form.get(
                    "history_duration_years",
                    base_assessment["history"]["duration_years"],
                )
            ),
            "occupation": request.form.get(
                "history_occupation",
                base_assessment["history"]["occupation"],
            ).strip(),
            "work_hours": request.form.get(
                "history_work_hours",
                base_assessment["history"]["work_hours"],
            ).strip(),
            "pain_level": int_or_none(
                request.form.get(
                    "history_pain_level",
                    base_assessment["history"]["pain_level"],
                )
            ),
            "frequency": int_or_none(
                request.form.get(
                    "history_frequency",
                    base_assessment["history"]["frequency"],
                )
            ),
            "notes": request.form.get(
                "history_notes",
                base_assessment["history"]["notes"],
            ).strip(),
        },
        "health_indicators": {
            "grip_strength": {
                "left_kg": float_or_none(request.form.get("grip_left_kg", "")),
                "right_kg": float_or_none(request.form.get("grip_right_kg", "")),
            },
            "balance": {
                "left_sec": int_or_none(request.form.get("balance_left_sec", "")),
                "right_sec": int_or_none(request.form.get("balance_right_sec", "")),
            },
            "chair_stand": {
                "reps_30s": int_or_none(request.form.get("chair_stand_reps_30s", "")),
            },
            "gait_speed": {
                "time_10m": float_or_none(request.form.get("gait_speed_time_10m", "")),
            },
            "sitting_rising": {
                "sit_score": float_or_none(request.form.get("srt_sit_score", "")),
                "rise_score": float_or_none(request.form.get("srt_rise_score", "")),
            },
            "resting_heart_rate": {
                "bpm": int_or_none(request.form.get("resting_hr_bpm", "")),
            },
            "vo2_max": {
                "age": int_or_none(
                    request.form.get(
                        "vo2_age",
                        base_assessment["health_indicators"]["vo2_max"]["age"],
                    )
                ),
                "resting_hr": int_or_none(request.form.get("vo2_resting_hr", "")),
            },
            "fingertip_to_floor": {
                "distance_cm": float_or_none(request.form.get("fingertip_floor_cm", "")),
            },
        },
        "functional_tests": {
            "marching_test": {
                "deviation_cm": float_or_none(request.form.get("marching_deviation_cm", "")),
                "direction": request.form.get("marching_direction", "").strip(),
            },
            "heel_toe_walk": {
                "steady_steps": int_or_none(request.form.get("heel_toe_steps", "")),
            },
            "weight_distribution": {
                "left_kg": float_or_none(request.form.get("weight_left_kg", "")),
                "right_kg": float_or_none(request.form.get("weight_right_kg", "")),
            },
        },
        "range_of_motion": {},
        "orthopedic_tests": {},
        "spine_assessment": {"left": {}, "right": {}},
        "leg_length": {
            "left_cm": float_or_none(request.form.get("leg_left_cm", "")),
            "right_cm": float_or_none(request.form.get("leg_right_cm", "")),
        },
    }

    for section in SUMMIT_ROM_SECTIONS:
        summit_assessment["range_of_motion"][section["key"]] = {}
        for item in section["items"]:
            field_name = f"rom_{section['key']}_{item['key']}"
            summit_assessment["range_of_motion"][section["key"]][item["key"]] = float_or_none(
                request.form.get(field_name, "")
            )

    positive_orthopedic_lines = []
    for region in SUMMIT_ORTHO_REGIONS:
        summit_assessment["orthopedic_tests"][region["key"]] = []
        for index, test in enumerate(region["tests"]):
            result = request.form.get(f"ortho_{region['key']}_{index}_result", "").strip()
            side = request.form.get(f"ortho_{region['key']}_{index}_side", "B").strip() or "B"
            measure = float_or_none(request.form.get(f"ortho_{region['key']}_{index}_measure", ""))
            notes = request.form.get(f"ortho_{region['key']}_{index}_notes", "").strip()
            summit_assessment["orthopedic_tests"][region["key"]].append(
                {
                    "test": test["name"],
                    "result": result,
                    "side": side,
                    "measure": measure,
                    "notes": notes,
                }
            )
            if result == "+":
                line = test["name"]
                if side and side != "B":
                    line += f" ({side})"
                if measure is not None:
                    line += f" {measure:g}"
                    if test.get("measure_unit"):
                        line += test["measure_unit"]
                if notes:
                    line += f" — {notes}"
                positive_orthopedic_lines.append(line)

    for side in ("left", "right"):
        for region in SUMMIT_SPINE_REGIONS:
            for level in region["levels"]:
                field_name = f"spine_{side}_{level}"
                summit_assessment["spine_assessment"][side][level] = max(
                    0,
                    min(5, int_or_none(request.form.get(field_name, "0")) or 0),
                )

    rom_summary_lines = []
    for section in SUMMIT_ROM_SECTIONS:
        summary_items = []
        for item in section["items"]:
            measured = summit_assessment["range_of_motion"][section["key"]][item["key"]]
            if measured is not None:
                summary_items.append(f"{item['label']} {measured:g}/{item['max_norm']}°")
        if summary_items:
            rom_summary_lines.append(f"{section['label']}: {', '.join(summary_items)}")

    marching_summary = ""
    marching = summit_assessment["functional_tests"]["marching_test"]
    if marching["deviation_cm"] is not None:
        marching_summary = f"{marching['deviation_cm']:g} cm"
        if marching["direction"]:
            marching_summary += f" {marching['direction']}"

    heel_toe_summary = ""
    heel_toe_steps = summit_assessment["functional_tests"]["heel_toe_walk"]["steady_steps"]
    if heel_toe_steps is not None:
        heel_toe_summary = f"{heel_toe_steps} steady steps"

    duration_years = summit_assessment["history"]["duration_years"]
    complaint_duration = f"{duration_years:g} years" if duration_years is not None else ""
    frequency = summit_assessment["history"]["frequency"]
    complaint_frequency = f"{frequency}/10 days" if frequency is not None else ""
    subjective_summary = summit_assessment["history"]["notes"] or summit_assessment["history"]["chief_complaint"]

    report = {
        "visit_date": visit_date,
        "assessment_payload_json": json.dumps(summit_assessment),
        "rapport_notes": request.form.get("rapport_notes", (existing_data or {}).get("rapport_notes", "")).strip(),
        "subjective_summary": subjective_summary,
        "complaint_duration": complaint_duration,
        "first_notice": request.form.get("first_notice", (existing_data or {}).get("first_notice", "")).strip(),
        "complaint_frequency": complaint_frequency,
        "pain_worst": summit_assessment["history"]["pain_level"],
        "pain_quality": request.form.get("pain_quality", (existing_data or {}).get("pain_quality", "")).strip(),
        "radiates": 1
        if request.form.get("radiates", "on" if (existing_data or {}).get("radiates") else "") == "on"
        else 0,
        "radiation_start": request.form.get("radiation_start", (existing_data or {}).get("radiation_start", "")).strip(),
        "radiation_end": request.form.get("radiation_end", (existing_data or {}).get("radiation_end", "")).strip(),
        "accident_history": request.form.get("accident_history", (existing_data or {}).get("accident_history", "")).strip(),
        "microtrauma_history": request.form.get("microtrauma_history", (existing_data or {}).get("microtrauma_history", "")).strip(),
        "prior_treatment_history": request.form.get("prior_treatment_history", (existing_data or {}).get("prior_treatment_history", "")).strip(),
        "symptom_trend": request.form.get("symptom_trend", (existing_data or {}).get("symptom_trend", "")).strip(),
        "adl_impacts": request.form.get("adl_impacts", (existing_data or {}).get("adl_impacts", "")).strip(),
        "medical_family_history_review": request.form.get(
            "medical_family_history_review",
            (existing_data or {}).get("medical_family_history_review", ""),
        ).strip(),
        "commitment_score": int_or_none(
            request.form.get("commitment_score", (existing_data or {}).get("commitment_score", ""))
        ),
        "obstacles_to_care": request.form.get(
            "obstacles_to_care",
            (existing_data or {}).get("obstacles_to_care", ""),
        ).strip(),
        "education_summary": request.form.get(
            "education_summary",
            (existing_data or {}).get("education_summary", ""),
        ).strip(),
        "posture_findings": request.form.get("posture_findings", (existing_data or {}).get("posture_findings", "")).strip(),
        "forward_head_inches": float_or_none(
            request.form.get("forward_head_inches", (existing_data or {}).get("forward_head_inches", ""))
        ),
        "shoulders_level": request.form.get("shoulders_level", (existing_data or {}).get("shoulders_level", "")).strip(),
        "hips_level": request.form.get("hips_level", (existing_data or {}).get("hips_level", "")).strip(),
        "range_of_motion": "\n".join(rom_summary_lines),
        "single_leg_balance_left_seconds": summit_assessment["health_indicators"]["balance"]["left_sec"],
        "single_leg_balance_right_seconds": summit_assessment["health_indicators"]["balance"]["right_sec"],
        "heel_to_toe_walk": heel_toe_summary,
        "marching_test": marching_summary,
        "orthopedic_findings": "\n".join(positive_orthopedic_lines),
        "neuro_findings": request.form.get("neuro_findings", (existing_data or {}).get("neuro_findings", "")).strip(),
        "palpation_findings": request.form.get(
            "palpation_findings",
            (existing_data or {}).get("palpation_findings", ""),
        ).strip(),
        "xray_recommended": 1 if request.form.get("xray_recommended") == "on" else 0,
        "xray_status": request.form.get("xray_status", (existing_data or {}).get("xray_status", "")).strip(),
        "xray_regions": request.form.get("xray_regions", (existing_data or {}).get("xray_regions", "")).strip(),
        "imaging_review": request.form.get("imaging_review", (existing_data or {}).get("imaging_review", "")).strip(),
        "assessment": request.form.get("assessment", "").strip(),
        "diagnosis": request.form.get("diagnosis", "").strip(),
        "care_plan": request.form.get("care_plan", "").strip(),
        "home_care": request.form.get("home_care", "").strip(),
        "follow_up_plan": request.form.get("follow_up_plan", "").strip(),
        "wrap_up_notes": request.form.get("wrap_up_notes", "").strip(),
        "triangle_handoff": request.form.get("triangle_handoff", "").strip(),
        "patient_summary": request.form.get("patient_summary", "").strip(),
        "patient_key_findings": request.form.get("patient_key_findings", "").strip(),
        "patient_recommendations": request.form.get("patient_recommendations", "").strip(),
    }
    errors = validate_visit_report(report, publish=action == "published")
    if errors:
        for error in errors:
            flash(error, "error")
        return redirect_target()

    now = iso_now()
    db = get_db()
    report_columns = list(report.keys())
    if existing is None:
        insert_columns = [
            "patient_user_id",
            "clinician_user_id",
            "visit_kind",
            "report_status",
            *report_columns,
            "created_at",
            "updated_at",
        ]
        placeholders = ", ".join("?" for _ in insert_columns)
        values = [
            user_id,
            g.user["id"],
            "initial_consult",
            action,
            *[report[column] for column in report_columns],
            now,
            now,
        ]
        db.execute(
            f"INSERT INTO visit_reports ({', '.join(insert_columns)}) VALUES ({placeholders})",
            values,
        )
    else:
        assignments = ", ".join(f"{column} = ?" for column in report_columns)
        values = [
            g.user["id"],
            action,
            *[report[column] for column in report_columns],
            now,
            user_id,
        ]
        db.execute(
            f"""
            UPDATE visit_reports
            SET clinician_user_id = ?,
                report_status = ?,
                {assignments},
                updated_at = ?
            WHERE patient_user_id = ? AND visit_kind = 'initial_consult'
            """,
            values,
        )
    complete_initial_consult_appointment(user_id, g.user["id"], visit_date)
    db.commit()
    flash("Initial consultation saved as draft." if action == "draft" else "Initial consultation published to the patient portal.", "success")
    return redirect_target()


@bp.route("/intake")
@client_required
def intake():
    submission = get_submission_for_user(g.user["id"])
    payload = json.loads(submission["payload_json"]) if submission else {}
    seed_payload = build_seed_payload(dict(g.user), payload)
    return render_template(
        "intake.html",
        intake_payload=seed_payload,
        submission_status=submission["status"] if submission else "draft",
    )


@bp.get("/api/intake")
@client_required
def intake_json():
    submission = get_submission_for_user(g.user["id"])
    payload = json.loads(submission["payload_json"]) if submission else {}
    return jsonify(
        {
            "ok": True,
            "status": submission["status"] if submission else "draft",
            "payload": build_seed_payload(dict(g.user), payload),
        }
    )


@bp.post("/api/intake")
@client_required
def save_intake():
    incoming = request.get_json(silent=True) or {}
    payload = incoming.get("payload")
    status = incoming.get("status", "draft")

    if status not in {"draft", "submitted"}:
        return jsonify({"ok": False, "errors": ["Invalid save status."]}), 400

    errors = validate_submission(payload, status)
    if errors:
        return jsonify({"ok": False, "errors": errors}), 400

    payload = build_seed_payload(dict(g.user), payload)
    payload["submittedAt"] = payload.get("submittedAt") or iso_now()
    now = iso_now()

    db = get_db()
    existing = get_submission_for_user(g.user["id"])
    payload_json = json.dumps(payload)

    if existing is None:
        db.execute(
            """
            INSERT INTO intake_submissions (user_id, status, payload_json, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (g.user["id"], status, payload_json, now, now),
        )
    else:
        db.execute(
            """
            UPDATE intake_submissions
            SET status = ?, payload_json = ?, updated_at = ?
            WHERE user_id = ?
            """,
            (status, payload_json, now, g.user["id"]),
        )
    persist_intake_questionnaire_scores(db, g.user["id"], payload, now)
    db.commit()

    return jsonify(
        {
            "ok": True,
            "status": status,
            "updatedAt": now,
            "redirect": url_for("main.results") if status == "submitted" else None,
        }
    )


@bp.get("/api/locations")
@login_required
def api_locations():
    return jsonify(
        {
            "ok": True,
            "locations": [dict(row) for row in get_locations()],
        }
    )


@bp.get("/api/booking-services")
@login_required
def api_booking_services():
    return jsonify(
        {
            "ok": True,
            "services": appointment_service_options(active_only=not is_staff(g.user)),
        }
    )


@bp.get("/api/availability")
@login_required
def api_availability():
    selected_service = selected_appointment_service(request.args.get("service_id"), active_only=True, fallback_to_default=False)
    appointment_type = request.args.get("appointment_type", "").strip()
    duration_minutes = int_or_none(request.args.get("duration_minutes", "30"))
    booking_policy = resolve_booking_policy(selected_service, appointment_type, duration_minutes if isinstance(duration_minutes, int) else None)
    clinician_user_id = requested_clinician_user_id(
        request.args.get("clinician_user_id"),
        allow_any=booking_policy["routing_mode"] == "team_round_robin",
    )
    if booking_policy["routing_mode"] == "team_round_robin" and (request.args.get("clinician_user_id", "").strip().lower() in {"", "any", "team"}):
        clinician_user_id = None
    location_id = selected_location_id(request.args.get("location_id"))
    availability = build_schedule_availability(
        request.args.get("date"),
        clinician_user_id,
        location_id,
        booking_policy["duration_minutes"],
        booking_policy=booking_policy,
    )
    return jsonify({"ok": True, "availability": serialize_schedule_availability(availability)})


@bp.route("/api/appointments", methods=("GET", "POST"))
@login_required
def api_appointments():
    if request.method == "GET":
        include_internal = is_staff(g.user)
        if include_internal:
            patient_user_id = int_or_none(request.args.get("patient_user_id"))
            if isinstance(patient_user_id, int):
                rows = get_patient_appointments(patient_user_id)
            else:
                rows = get_all_appointments()
        else:
            rows = get_patient_appointments(g.user["id"])
        appointments_payload = [serialize_appointment_for_api(build_appointment_item(row), include_internal=include_internal) for row in rows]
        return jsonify({"ok": True, "appointments": appointments_payload})

    incoming = request.get_json(silent=True) or {}
    incoming_service_id = incoming.get("service_id")
    selected_service = selected_appointment_service(
        "" if incoming_service_id is None else str(incoming_service_id),
        active_only=True,
        fallback_to_default=False,
    )
    appointment_type = str(incoming.get("appointment_type", "")).strip()
    if selected_service is not None and not appointment_type:
        appointment_type = selected_service["appointment_type"]
    duration_minutes = int_or_none(
        str(
            incoming.get(
                "duration_minutes",
                selected_service["duration_minutes"] if selected_service else default_duration_for_type(appointment_type or "care_plan"),
            )
        )
    )
    booking_policy = resolve_booking_policy(selected_service, appointment_type, duration_minutes if isinstance(duration_minutes, int) else None)
    incoming_clinician_value = incoming.get("clinician_user_id")
    raw_clinician_value = "" if incoming_clinician_value is None else str(incoming_clinician_value).strip()
    clinician_user_id = requested_clinician_user_id(
        raw_clinician_value,
        allow_any=booking_policy["routing_mode"] == "team_round_robin",
    )
    if booking_policy["routing_mode"] == "team_round_robin" and raw_clinician_value.lower() in {"", "any", "team"}:
        clinician_user_id = None
    location_id = selected_location_id(str(incoming.get("location_id", "")))
    slot_start = str(incoming.get("slot_start", "")).strip()
    patient_details = str(incoming.get("patient_details", "")).strip()

    if is_staff(g.user):
        patient_user_id = int_or_none(str(incoming.get("patient_user_id", "")))
        if not isinstance(patient_user_id, int) or get_client_user(patient_user_id) is None:
            return jsonify({"ok": False, "errors": ["A valid patient_user_id is required for staff bookings."]}), 400
        booking_source = "api_staff"
    else:
        patient_user_id = g.user["id"]
        booking_source = "api_client"

    errors = []
    if appointment_type not in APPOINTMENT_TYPE_META:
        errors.append("Choose a valid appointment type.")
    if location_id is None:
        errors.append("Choose a valid location.")
    if booking_policy["routing_mode"] != "team_round_robin" and clinician_user_id is None:
        errors.append("Choose a valid chiropractor.")
    starts_parsed = parse_iso(slot_start)
    slot_assignment = None
    if starts_parsed is None:
        errors.append("Choose a valid available time slot.")
    else:
        slot_assignment = resolve_slot_assignment(starts_parsed, clinician_user_id, location_id, booking_policy)
    if starts_parsed is not None and slot_assignment is None:
        errors.append("Selected slot is no longer available.")

    if errors:
        return jsonify({"ok": False, "errors": errors}), 400

    assigned_clinician_id = slot_assignment.get("clinician_user_id") if slot_assignment else clinician_user_id
    ends_parsed = starts_parsed + timedelta(minutes=booking_policy["duration_minutes"])
    appointment_id = create_patient_appointment(
        patient_user_id,
        assigned_clinician_id,
        location_id,
        appointment_type,
        format_datetime_local(starts_parsed),
        service_id=booking_policy["service_id"],
        ends_at=format_datetime_local(ends_parsed),
        note=patient_details,
        patient_details=patient_details,
        requires_payment=booking_policy["requires_payment"],
        payment_status="pending" if booking_policy["requires_payment"] else "not_required",
        payment_amount=booking_policy["price_amount"],
        booking_channel="api",
        service_label_snapshot=booking_policy["service_label"],
        policy_snapshot=booking_policy,
        booking_source=booking_source,
    )
    log_booking_event(
        "booking_created",
        appointment_id,
        patient_user_id,
        {
            "source": booking_source,
            "service_id": booking_policy["service_id"],
            "service_label": booking_policy["service_label"],
            "location_id": location_id,
            "clinician_user_id": assigned_clinician_id,
        },
    )
    get_db().commit()
    appointment = build_appointment_item(get_appointment_with_people(appointment_id))
    return jsonify({"ok": True, "appointment": serialize_appointment_for_api(appointment, include_internal=is_staff(g.user))}), 201


@bp.route("/results")
@client_required
def results():
    context = results_page_context(g.user["id"])
    if context is None or context["submission"] is None:
        flash("Complete your intake before viewing results.", "error")
        return redirect(url_for("main.intake"))

    return render_template(
        "results.html",
        summary=context["summary"],
        preview_mode=False,
        home_url=url_for("main.dashboard"),
        home_label="Dashboard",
        secondary_url=url_for("main.intake"),
        secondary_label="Edit intake",
    )


@bp.route("/staff/patients/<int:user_id>/results-preview")
@staff_required
def staff_patient_results_preview(user_id: int):
    context = results_page_context(user_id)
    if context is None:
        abort(404)
    if context["submission"] is None:
        flash("This patient has not completed intake yet.", "error")
        return redirect(url_for("main.staff_patient_detail", user_id=user_id))

    return render_template(
        "results.html",
        summary=context["summary"],
        preview_mode=True,
        home_url=url_for("main.staff_patient_detail", user_id=user_id),
        home_label="Back to chart",
        secondary_url=url_for("main.staff_patient_assessment", user_id=user_id),
        secondary_label="Back to assessment",
    )
