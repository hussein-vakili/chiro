from __future__ import annotations

import json
import secrets
from datetime import datetime, timedelta
from functools import wraps

from flask import (
    Blueprint,
    abort,
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
    iso_now,
    split_lines,
    validate_submission,
    validate_visit_report,
)


bp = Blueprint("main", __name__)


def is_staff(user) -> bool:
    return bool(user and user["role"] in {"clinician", "admin"})


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


def dashboard_redirect_for(user) -> str:
    return url_for("main.dashboard") if user else url_for("main.login")


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


def staff_dashboard_context() -> dict:
    db = get_db()
    patients = db.execute(
        """
        SELECT
            u.id,
            u.first_name,
            u.last_name,
            u.email,
            u.created_at,
            s.status AS intake_status,
            s.updated_at AS intake_updated_at,
            (
                SELECT appointment_at
                FROM invitations i
                WHERE i.accepted_user_id = u.id
                ORDER BY COALESCE(i.accepted_at, i.created_at) DESC
                LIMIT 1
            ) AS appointment_at,
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
        ORDER BY COALESCE(appointment_at, s.updated_at, u.created_at) DESC
        """
    ).fetchall()

    invitations = db.execute(
        """
        SELECT i.*, u.first_name AS clinician_first_name, u.last_name AS clinician_last_name
        FROM invitations i
        LEFT JOIN users u ON u.id = i.created_by
        WHERE i.accepted_at IS NULL
        ORDER BY COALESCE(i.appointment_at, i.created_at) ASC
        """
    ).fetchall()

    active_invitations = [row for row in invitations if not is_expired(row["expires_at"])]

    return {
        "patients": patients,
        "active_invitations": active_invitations,
        "patient_count": len(patients),
        "submitted_count": sum(1 for row in patients if row["intake_status"] == "submitted"),
        "pending_invite_count": len(active_invitations),
    }


def staff_patient_context(user_id: int):
    patient = get_client_user(user_id)
    if patient is None:
        return None

    submission = get_submission_for_user(patient["id"])
    visit_report = get_visit_report_for_patient(patient["id"])
    payload = json.loads(submission["payload_json"]) if submission else {}
    invitation = get_latest_invitation_for_user(patient["id"])
    notes = get_notes_for_patient(patient["id"])
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
        appointment_at=invitation["appointment_at"] if invitation else None,
        notes=dict(notes) if notes else None,
        visit_report=dict(visit_report) if visit_report else None,
    )
    return {
        "patient": patient,
        "submission": submission,
        "summary": summary,
        "notes": notes,
        "visit_report": visit_report,
        "summit_assessment": summit_assessment,
        "summit_rom_sections": SUMMIT_ROM_SECTIONS,
        "summit_ortho_regions": SUMMIT_ORTHO_REGIONS,
        "summit_spine_regions": SUMMIT_SPINE_REGIONS,
    }


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
            flash("Account created. You can start your intake now.", "success")
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
            db.commit()
            session.clear()
            session["user_id"] = cursor.lastrowid
            flash("Invitation accepted. Your account is ready.", "success")
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
            flash("Signed in.", "success")
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
    if is_staff(g.user):
        context = staff_dashboard_context()
        return render_template("staff_dashboard.html", **context)

    submission = get_submission_for_user(g.user["id"])
    invitation = get_latest_invitation_for_user(g.user["id"])
    visit_report = get_visit_report_for_patient(g.user["id"])
    return render_template("dashboard.html", submission=submission, invitation=invitation, visit_report=visit_report)


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


@bp.route("/results")
@client_required
def results():
    submission = get_submission_for_user(g.user["id"])
    if submission is None:
        flash("Complete your intake before viewing results.", "error")
        return redirect(url_for("main.intake"))

    payload = json.loads(submission["payload_json"])
    visit_report = get_visit_report_for_patient(g.user["id"])
    context = build_results_context(
        dict(g.user),
        payload,
        submission["status"],
        submission["updated_at"],
        visit_report=dict(visit_report) if visit_report else None,
    )
    return render_template("results.html", summary=context)
