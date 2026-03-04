from __future__ import annotations

import calendar as month_calendar
import json
import secrets
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
    format_schedule,
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
    {"value": 20, "label": "20 minutes"},
    {"value": 30, "label": "30 minutes"},
    {"value": 45, "label": "45 minutes"},
    {"value": 60, "label": "60 minutes"},
]

APPOINTMENT_DURATION_DEFAULTS = {
    "initial_consult": 60,
    "report_of_findings": 30,
    "care_plan": 20,
}

SLOT_INCREMENT_MINUTES = 15
CLAUDE_DDX_ARTIFACT_PATH = Path(__file__).resolve().parent.parent / "life-chiro-ddx-tx (1).jsx"

DECISION_SUPPORT_REGION_LABELS = {
    "neck": "Neck Pain",
    "low_back": "Low Back Pain",
    "shoulder": "Shoulder",
    "headache": "Headache",
}


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


def is_expired(value: str | None) -> bool:
    parsed = parse_iso(value)
    if parsed is None:
        return True
    return parsed <= datetime.now(parsed.tzinfo)


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


def get_patient_appointments(patient_user_id: int):
    return get_db().execute(
        """
        SELECT
            a.*,
            l.name AS location_name,
            c.first_name AS clinician_first_name,
            c.last_name AS clinician_last_name,
            asn.id AS soap_note_id,
            asn.updated_at AS soap_note_updated_at
        FROM appointments a
        LEFT JOIN locations l ON l.id = a.location_id
        LEFT JOIN users c ON c.id = a.clinician_user_id
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
            asn.id AS soap_note_id,
            asn.updated_at AS soap_note_updated_at
        FROM appointments a
        JOIN users p ON p.id = a.patient_user_id
        LEFT JOIN locations l ON l.id = a.location_id
        LEFT JOIN users c ON c.id = a.clinician_user_id
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
            asn.id AS soap_note_id,
            asn.updated_at AS soap_note_updated_at
        FROM appointments a
        JOIN users p ON p.id = a.patient_user_id
        LEFT JOIN locations l ON l.id = a.location_id
        LEFT JOIN users c ON c.id = a.clinician_user_id
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
            asn.id AS soap_note_id,
            asn.updated_at AS soap_note_updated_at
        FROM appointments a
        JOIN users p ON p.id = a.patient_user_id
        LEFT JOIN locations l ON l.id = a.location_id
        LEFT JOIN users c ON c.id = a.clinician_user_id
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


def get_clinician_users():
    clinicians = get_db().execute(
        """
        SELECT id, first_name, last_name, email, role
        FROM users
        WHERE role = 'clinician'
        ORDER BY first_name ASC, last_name ASC, email ASC
        """
    ).fetchall()
    if clinicians:
        return clinicians
    return get_db().execute(
        """
        SELECT id, first_name, last_name, email, role
        FROM users
        WHERE role IN ('clinician', 'admin')
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
            c.last_name AS clinician_last_name
        FROM appointments a
        JOIN users p ON p.id = a.patient_user_id
        LEFT JOIN users c ON c.id = a.clinician_user_id
        WHERE a.clinician_user_id = ?
          AND a.status = 'scheduled'
          AND substr(a.starts_at, 1, 10) = ?
    """
    if exclude_appointment_id is not None:
        query += " AND a.id != ?"
        params.append(exclude_appointment_id)
    query += " ORDER BY a.starts_at ASC"
    return get_db().execute(query, tuple(params)).fetchall()


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


def default_duration_for_type(appointment_type: str) -> int:
    return APPOINTMENT_DURATION_DEFAULTS.get(appointment_type, 30)


def duration_is_supported(duration_minutes: int) -> bool:
    return any(option["value"] == duration_minutes for option in APPOINTMENT_DURATION_OPTIONS)


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
        "time_label": f"{row['starts_time']} - {row['ends_time']}",
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


def next_booking_date(clinician_user_id: int | None = None, location_id: int | None = None) -> str:
    today = date.today()
    for offset in range(0, 14):
        candidate = today + timedelta(days=offset)
        if build_schedule_availability(candidate.isoformat(), clinician_user_id, location_id, 30)["shift_windows"]:
            return candidate.isoformat()
    return today.isoformat()


def overlaps(start_a: datetime, end_a: datetime, start_b: datetime, end_b: datetime) -> bool:
    return start_a < end_b and start_b < end_a


def build_schedule_availability(
    target_date_value: str | None,
    clinician_user_id: int | None,
    location_id: int | None,
    duration_minutes: int,
    *,
    exclude_appointment_id: int | None = None,
) -> dict:
    target_date = date_from_value(target_date_value)
    if target_date is None:
        return {
            "date_value": target_date_value or "",
            "date_label": target_date_value or "",
            "location_id": location_id,
            "available_slots": [],
            "shift_windows": [],
            "downtime_windows": [],
            "booked_windows": [],
            "error": "Choose a valid date.",
        }

    duration = timedelta(minutes=duration_minutes)
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
            "time_label": f"{row['starts_time']} - {row['ends_time']}",
            "location_id": row["location_id"],
            "starts_at": start_at,
            "ends_at": end_at,
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
        ends_at = parse_iso(row["ends_at"]) or (starts_at + duration if starts_at else None)
        if starts_at is None or ends_at is None:
            continue
        booked_windows.append(
            {
                "id": row["id"],
                "label": appointment_type_meta(row["appointment_type"])["label"],
                "time_label": f"{starts_at.strftime('%H:%M')} - {ends_at.strftime('%H:%M')}",
                "starts_at": starts_at,
                "ends_at": ends_at,
            }
        )

    available_slots = []
    seen_values = set()
    now = datetime.now()
    for shift_window in shift_windows:
        slot_start = shift_window["starts_at"]
        last_start = shift_window["ends_at"] - duration
        while slot_start <= last_start:
            slot_end = slot_start + duration
            slot_value = format_datetime_local(slot_start)
            if slot_start.date() == now.date() and slot_start <= now:
                slot_start += timedelta(minutes=SLOT_INCREMENT_MINUTES)
                continue
            if any(overlaps(slot_start, slot_end, item["starts_at"], item["ends_at"]) for item in downtime_windows):
                slot_start += timedelta(minutes=SLOT_INCREMENT_MINUTES)
                continue
            if any(overlaps(slot_start, slot_end, item["starts_at"], item["ends_at"]) for item in booked_windows):
                slot_start += timedelta(minutes=SLOT_INCREMENT_MINUTES)
                continue
            if slot_value not in seen_values:
                available_slots.append(
                    {
                        "value": slot_value,
                        "label": f"{slot_start.strftime('%H:%M')} - {slot_end.strftime('%H:%M')}",
                        "start_label": slot_start.strftime("%H:%M"),
                        "end_label": slot_end.strftime("%H:%M"),
                    }
                )
                seen_values.add(slot_value)
            slot_start += timedelta(minutes=SLOT_INCREMENT_MINUTES)

    return {
        "date_value": target_date.isoformat(),
        "date_label": target_date.strftime("%A %d %B %Y"),
        "location_id": location_id,
        "available_slots": available_slots,
        "shift_windows": shift_windows,
        "downtime_windows": downtime_windows,
        "booked_windows": booked_windows,
        "error": None,
    }


def serialize_schedule_availability(availability: dict) -> dict:
    return {
        "date_value": availability["date_value"],
        "date_label": availability["date_label"],
        "location_id": availability["location_id"],
        "error": availability["error"],
        "available_slots": availability["available_slots"],
        "shift_windows": [
            {
                "id": item["id"],
                "label": item["label"],
                "time_label": item["time_label"],
                "window_type": item["window_type"],
                "window_type_label": item["window_type_label"],
                "window_tone": item["window_tone"],
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
            }
            for item in availability["downtime_windows"]
        ],
        "booked_windows": [
            {
                "id": item["id"],
                "label": item["label"],
                "time_label": item["time_label"],
            }
            for item in availability["booked_windows"]
        ],
    }


def slot_is_available(
    starts_at: datetime,
    clinician_user_id: int | None,
    location_id: int | None,
    duration_minutes: int,
    *,
    exclude_appointment_id: int | None = None,
) -> bool:
    availability = build_schedule_availability(
        starts_at.date().isoformat(),
        clinician_user_id,
        location_id,
        duration_minutes,
        exclude_appointment_id=exclude_appointment_id,
    )
    slot_value = format_datetime_local(starts_at)
    return slot_value in {item["value"] for item in availability["available_slots"]}


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
    appointment["can_email"] = bool(appointment["patient_email"])
    appointment["can_sms"] = bool(appointment["patient_phone"])
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
        "time_label": starts_parsed.strftime("%H:%M") if starts_parsed else "",
        "end_time_label": ends_parsed.strftime("%H:%M") if ends_parsed else None,
        "starts_input": format_datetime_local(starts_parsed),
        "ends_input": format_datetime_local(ends_parsed),
        "day_key": starts_parsed.date().isoformat() if starts_parsed else starts_at[:10],
        "month_key": starts_parsed.strftime("%Y-%m") if starts_parsed else starts_at[:7],
        "location_id": row["location_id"] if "location_id" in row.keys() else None,
        "location_name": row["location_name"] if "location_name" in row.keys() else None,
        "note": row["note"] or "",
        "patient_details": row["patient_details"] if "patient_details" in row.keys() else "",
        "clinical_note": row["clinical_note"] if "clinical_note" in row.keys() else "",
        "billing_status": row["billing_status"] if "billing_status" in row.keys() else "pending",
        "billing_status_label": billing_meta["label"],
        "billing_status_tone": billing_meta["tone"],
        "billing_code": row["billing_code"] if "billing_code" in row.keys() else "",
        "billing_amount": row["billing_amount"] if "billing_amount" in row.keys() else None,
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
    return {
        "appointments": appointments,
        "upcoming": upcoming[:12],
        "calendar": build_calendar_grid(month_items, month_start),
        "counts": counts,
        "reminders": reminders,
        "locations": [dict(row) for row in get_locations(active_only=False)],
        "schedule_templates": build_weekly_schedule_context(),
    }


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
    selected_appointment_type = request.args.get("appointment_type", "care_plan").strip() or "care_plan"
    if selected_appointment_type not in APPOINTMENT_TYPE_META:
        selected_appointment_type = "care_plan"
    selected_location = selected_location_id(request.args.get("location_id"))
    selected_clinician = selected_clinician_user_id(request.args.get("clinician_user_id"))
    selected_duration = int_or_none(
        request.args.get("duration_minutes", str(default_duration_for_type(selected_appointment_type)))
    )
    if not isinstance(selected_duration, int) or not duration_is_supported(selected_duration):
        selected_duration = default_duration_for_type(selected_appointment_type)
    booking_date = request.args.get("appointment_date") or next_booking_date(selected_clinician, selected_location)
    availability = build_schedule_availability(booking_date, selected_clinician, selected_location, selected_duration)
    return {
        "location_options": location_options(),
        "clinician_options": clinician_options(),
        "duration_options": appointment_duration_options(),
        "selected_location_id": selected_location,
        "selected_clinician_id": selected_clinician,
        "selected_duration_minutes": selected_duration,
        "selected_appointment_type": selected_appointment_type,
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
    ends_at: str | None = None,
    note: str = "",
    patient_details: str = "",
    clinical_note: str = "",
    billing_status: str = "pending",
    billing_code: str = "",
    billing_amount: float | None = None,
    booking_source: str = "staff_portal",
    status: str = "scheduled",
    source_invitation_id: int | None = None,
) -> int:
    now = iso_now()
    cursor = get_db().execute(
        """
        INSERT INTO appointments (
            patient_user_id,
            clinician_user_id,
            location_id,
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
            booking_source,
            created_at,
            updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            patient_user_id,
            clinician_user_id,
            location_id,
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

    return create_patient_appointment(
        patient_user_id,
        clinician_user_id,
        location_id,
        appointment_type,
        starts_at,
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

    create_patient_appointment(
        patient_user_id,
        clinician_user_id,
        default_location_id(),
        "initial_consult",
        visit_date,
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


def staff_patient_context(user_id: int):
    patient = get_client_user(user_id)
    if patient is None:
        return None

    clinicians = clinician_options()
    locations = location_options()
    selected_clinician_id = selected_clinician_user_id(request.args.get("clinician_user_id"))
    selected_location = selected_location_id(request.args.get("location_id"))
    selected_appointment_type = request.args.get("appointment_type", "initial_consult").strip() or "initial_consult"
    if selected_appointment_type not in APPOINTMENT_TYPE_META:
        selected_appointment_type = "initial_consult"
    selected_duration = int_or_none(request.args.get("duration_minutes", str(default_duration_for_type(selected_appointment_type))))
    if not isinstance(selected_duration, int) or not duration_is_supported(selected_duration):
        selected_duration = default_duration_for_type(selected_appointment_type)
    booking_date = request.args.get("appointment_date") or next_booking_date(selected_clinician_id, selected_location)
    booking_availability = build_schedule_availability(booking_date, selected_clinician_id, selected_location, selected_duration)

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
        "clinician_options": clinicians,
        "location_options": locations,
        "selected_location_id": selected_location,
        "selected_clinician_id": selected_clinician_id,
        "billing_status_options": billing_status_options(),
        "duration_options": appointment_duration_options(),
        "selected_duration_minutes": selected_duration,
        "selected_appointment_type": selected_appointment_type,
        "booking_date": booking_date,
        "booking_availability": booking_availability,
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

    g.user = get_db().execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()


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
        clinician_options=clinician_options(),
        location_options=location_options(),
        weekday_options=weekday_options(),
        schedule_window_type_options=schedule_window_type_options(),
        **context,
    )


@bp.get("/staff/availability")
@staff_required
def staff_schedule_availability():
    clinician_user_id = selected_clinician_user_id(request.args.get("clinician_user_id"))
    location_id = selected_location_id(request.args.get("location_id"))
    duration_minutes = int_or_none(request.args.get("duration_minutes", "30"))
    if not isinstance(duration_minutes, int):
        duration_minutes = 30
    availability = build_schedule_availability(
        request.args.get("date"),
        clinician_user_id,
        location_id,
        duration_minutes,
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

    return redirect(url_for("main.staff_calendar", month=request.form.get("month") or None))


@bp.post("/staff/schedule-windows/<int:window_id>/delete")
@staff_required
def delete_staff_schedule_window(window_id: int):
    window = get_schedule_window(window_id)
    if window is None:
        abort(404)
    get_db().execute("DELETE FROM schedule_windows WHERE id = ?", (window_id,))
    get_db().commit()
    flash("Schedule template removed.", "success")
    return redirect(url_for("main.staff_calendar", month=request.form.get("month") or None))


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

    return redirect(url_for("main.staff_calendar", month=request.form.get("month") or None))


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


@bp.post("/staff/patients/<int:user_id>/appointments")
@staff_required
def create_staff_patient_appointment(user_id: int):
    patient = get_client_user(user_id)
    if patient is None:
        abort(404)

    appointment_type = request.form.get("appointment_type", "").strip()
    clinician_user_id = selected_clinician_user_id(request.form.get("clinician_user_id"))
    location_id = selected_location_id(request.form.get("location_id"))
    appointment_date = request.form.get("appointment_date", "").strip()
    slot_start = request.form.get("slot_start", "").strip()
    duration_minutes = int_or_none(request.form.get("duration_minutes", str(default_duration_for_type(appointment_type))))
    starts_at = request.form.get("starts_at", "").strip()
    ends_at = request.form.get("ends_at", "").strip() or None
    note = request.form.get("note", "").strip()
    patient_details = request.form.get("patient_details", "").strip() or note
    repeat_count = int_or_none(request.form.get("repeat_count", "1"))
    repeat_every_days = int_or_none(request.form.get("repeat_every_days", "7"))

    error = None
    if appointment_type not in APPOINTMENT_TYPE_META:
        error = "Choose a valid appointment type."
    elif location_id is None:
        error = "Choose a valid location."
    elif clinician_user_id is None:
        error = "Choose a valid chiropractor."
    elif not isinstance(repeat_count, int) or repeat_count < 1 or repeat_count > 24:
        error = "Repeat count must be between 1 and 24."
    elif not isinstance(repeat_every_days, int) or repeat_every_days < 1 or repeat_every_days > 30:
        error = "Repeat interval must be between 1 and 30 days."
    elif slot_start:
        if not isinstance(duration_minutes, int) or not duration_is_supported(duration_minutes):
            error = "Choose a supported appointment length."
        else:
            starts_parsed = parse_iso(slot_start)
            if starts_parsed is None:
                error = "Choose a valid available time slot."
            elif appointment_date and starts_parsed.date().isoformat() != appointment_date:
                error = "Selected time slot does not match the chosen date."
            elif not slot_is_available(starts_parsed, clinician_user_id, location_id, duration_minutes):
                error = "Selected time slot is no longer available within the chiropractor schedule at this location."
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

    if error is None:
        created_slots = []
        if slot_start:
            base_start = parse_iso(slot_start)
            duration = timedelta(minutes=duration_minutes)
            for index in range(repeat_count):
                item_start = base_start + timedelta(days=repeat_every_days * index)
                item_end = item_start + duration
                if not slot_is_available(item_start, clinician_user_id, location_id, duration_minutes):
                    error = (
                        f"{item_start.strftime('%d %b %Y %H:%M')} is outside chiropractor shift hours, "
                        "falls in downtime, or is already booked for this location."
                    )
                    break
                created_slots.append((format_datetime_local(item_start), format_datetime_local(item_end)))
        else:
            duration = None
            if ends_at:
                duration = parse_iso(ends_at) - parse_iso(starts_at)
            for index in range(repeat_count):
                item_start = parse_iso(starts_at) + timedelta(days=repeat_every_days * index)
                item_end = item_start + duration if duration is not None else None
                created_slots.append(
                    (
                        format_datetime_local(item_start),
                        format_datetime_local(item_end) if item_end else None,
                    )
                )

    if error is None:
        created = 0
        for item_start, item_end in created_slots:
            create_patient_appointment(
                user_id,
                clinician_user_id,
                location_id,
                appointment_type,
                item_start,
                ends_at=item_end,
                note=note,
                patient_details=patient_details,
                booking_source="staff_portal",
            )
            created += 1
        get_db().commit()
        label = appointment_type_meta(appointment_type)["label"]
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
            clinician_user_id=clinician_user_id,
            appointment_type=appointment_type,
            duration_minutes=duration_minutes if isinstance(duration_minutes, int) else None,
            appointment_date=appointment_date or (slot_start[:10] if slot_start else None),
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
    return render_template("appointments.html", schedule=schedule, **booking)


@bp.post("/appointments/self-book")
@client_required
def self_book_appointment():
    appointment_type = request.form.get("appointment_type", "").strip()
    clinician_user_id = selected_clinician_user_id(request.form.get("clinician_user_id"))
    location_id = selected_location_id(request.form.get("location_id"))
    appointment_date = request.form.get("appointment_date", "").strip()
    slot_start = request.form.get("slot_start", "").strip()
    duration_minutes = int_or_none(request.form.get("duration_minutes", str(default_duration_for_type(appointment_type))))
    patient_details = request.form.get("patient_details", "").strip()

    error = None
    if appointment_type not in APPOINTMENT_TYPE_META:
        error = "Choose a valid appointment type."
    elif location_id is None:
        error = "Choose a valid clinic location."
    elif clinician_user_id is None:
        error = "Choose a valid chiropractor."
    elif not isinstance(duration_minutes, int) or not duration_is_supported(duration_minutes):
        error = "Choose a supported appointment length."
    elif not slot_start:
        error = "Choose an available time slot."
    else:
        starts_parsed = parse_iso(slot_start)
        if starts_parsed is None:
            error = "Choose a valid available time slot."
        elif appointment_date and starts_parsed.date().isoformat() != appointment_date:
            error = "Selected slot does not match the chosen date."
        elif not slot_is_available(starts_parsed, clinician_user_id, location_id, duration_minutes):
            error = "Selected slot is no longer available."

    if error is None:
        starts_parsed = parse_iso(slot_start)
        ends_parsed = starts_parsed + timedelta(minutes=duration_minutes)
        create_patient_appointment(
            g.user["id"],
            clinician_user_id,
            location_id,
            appointment_type,
            format_datetime_local(starts_parsed),
            ends_at=format_datetime_local(ends_parsed),
            note=patient_details,
            patient_details=patient_details,
            booking_source="patient_portal",
        )
        get_db().commit()
        flash("Appointment booked from your portal.", "success")
    else:
        flash(error, "error")

    return redirect(
        url_for(
            "main.appointments",
            location_id=location_id,
            clinician_user_id=clinician_user_id,
            appointment_type=appointment_type or None,
            duration_minutes=duration_minutes if isinstance(duration_minutes, int) else None,
            appointment_date=appointment_date or (slot_start[:10] if slot_start else None),
        )
    )


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

        error = None
        if not any((subjective, objective, assessment, plan)):
            error = "Add at least one SOAP section before saving the appointment note."

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
                        created_at,
                        updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        appointment_id,
                        appointment_row["patient_user_id"],
                        g.user["id"],
                        subjective,
                        objective,
                        assessment,
                        plan,
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
                        updated_at = ?
                    WHERE appointment_id = ?
                    """,
                    (g.user["id"], subjective, objective, assessment, plan, now, appointment_id),
                )
            db.commit()
            flash("SOAP note saved for this appointment.", "success")
            return redirect(url_for("main.practitioner_appointment_soap_note", appointment_id=appointment_id))

        flash(error, "error")

    appointment = decorate_appointment_contacts(build_appointment_item(get_appointment_with_people(appointment_id)))
    soap_note = get_appointment_soap_note(appointment_id)
    return render_template(
        "practitioner_soap_note.html",
        appointment=appointment,
        patient=patient,
        soap_note=soap_note,
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


@bp.get("/api/availability")
@login_required
def api_availability():
    clinician_user_id = selected_clinician_user_id(request.args.get("clinician_user_id"))
    location_id = selected_location_id(request.args.get("location_id"))
    duration_minutes = int_or_none(request.args.get("duration_minutes", "30"))
    if not isinstance(duration_minutes, int):
        duration_minutes = 30
    availability = build_schedule_availability(
        request.args.get("date"),
        clinician_user_id,
        location_id,
        duration_minutes,
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
    appointment_type = str(incoming.get("appointment_type", "")).strip()
    clinician_user_id = selected_clinician_user_id(str(incoming.get("clinician_user_id", "")))
    location_id = selected_location_id(str(incoming.get("location_id", "")))
    slot_start = str(incoming.get("slot_start", "")).strip()
    duration_minutes = int_or_none(str(incoming.get("duration_minutes", default_duration_for_type(appointment_type))))
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
    if clinician_user_id is None:
        errors.append("Choose a valid chiropractor.")
    if not isinstance(duration_minutes, int) or not duration_is_supported(duration_minutes):
        errors.append("Choose a supported appointment length.")
    starts_parsed = parse_iso(slot_start)
    if starts_parsed is None:
        errors.append("Choose a valid available time slot.")
    elif not slot_is_available(starts_parsed, clinician_user_id, location_id, duration_minutes):
        errors.append("Selected slot is no longer available.")

    if errors:
        return jsonify({"ok": False, "errors": errors}), 400

    ends_parsed = starts_parsed + timedelta(minutes=duration_minutes)
    appointment_id = create_patient_appointment(
        patient_user_id,
        clinician_user_id,
        location_id,
        appointment_type,
        format_datetime_local(starts_parsed),
        ends_at=format_datetime_local(ends_parsed),
        note=patient_details,
        patient_details=patient_details,
        booking_source=booking_source,
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
