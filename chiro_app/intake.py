from __future__ import annotations

import json
from datetime import date, datetime


def iso_now() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def format_long_date(value: str | None) -> str | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).strftime("%d %b %Y")
    except ValueError:
        try:
            return datetime.strptime(value, "%Y-%m-%d").strftime("%d %b %Y")
        except ValueError:
            return value


def format_schedule(value: str | None) -> str | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).strftime("%d %b %Y · %H:%M")
    except ValueError:
        return format_long_date(value)


def calculate_age(dob: str | None) -> int | None:
    if not dob:
        return None
    try:
        born = datetime.strptime(dob, "%Y-%m-%d").date()
    except ValueError:
        return None
    today = date.today()
    return today.year - born.year - ((today.month, today.day) < (born.month, born.day))


def split_lines(value: str | None) -> list[str]:
    if not value:
        return []
    raw = value.replace("\r\n", "\n")
    items = []
    for part in raw.split("\n"):
        cleaned = part.strip().lstrip("-").strip()
        if cleaned:
            items.append(cleaned)
    return items


SUMMIT_ROM_SECTIONS = [
    {
        "key": "cervical",
        "label": "Cervical",
        "items": [
            {"key": "flexion", "label": "Flexion", "max_norm": 90},
            {"key": "extension", "label": "Extension", "max_norm": 80},
            {"key": "left_rotation", "label": "Left rotation", "max_norm": 90},
            {"key": "right_rotation", "label": "Right rotation", "max_norm": 90},
            {"key": "left_lateral_flexion", "label": "Left lateral flexion", "max_norm": 50},
            {"key": "right_lateral_flexion", "label": "Right lateral flexion", "max_norm": 50},
        ],
    },
    {
        "key": "lumbar",
        "label": "Lumbar",
        "items": [
            {"key": "flexion", "label": "Flexion", "max_norm": 90},
            {"key": "extension", "label": "Extension", "max_norm": 80},
            {"key": "left_rotation", "label": "Left rotation", "max_norm": 90},
            {"key": "right_rotation", "label": "Right rotation", "max_norm": 90},
            {"key": "left_lateral_flexion", "label": "Left lateral flexion", "max_norm": 50},
            {"key": "right_lateral_flexion", "label": "Right lateral flexion", "max_norm": 50},
            {"key": "sit_and_reach", "label": "Sit and reach", "max_norm": 70},
        ],
    },
]

SUMMIT_SPINE_REGIONS = [
    {"label": "Cervical", "levels": ["C1", "C2", "C3", "C4", "C5", "C6", "C7"]},
    {"label": "Thoracic", "levels": [f"T{index}" for index in range(1, 13)]},
    {"label": "Lumbar", "levels": [f"L{index}" for index in range(1, 6)]},
    {"label": "Sacral", "levels": ["S1", "S2"]},
]

SUMMIT_ORTHO_REGIONS = [
    {
        "key": "cervical",
        "label": "Cervical Spine (C1-C7)",
        "tests": [
            {
                "name": "Spurling's Test",
                "target": "Cervical radiculopathy / nerve root compression",
                "detail": "Extend, rotate, laterally flex, then apply axial compression.",
                "evidence": "Sensitivity 50-95% · Specificity 89-94%",
                "has_side": True,
                "has_measure": False,
            },
            {
                "name": "Cervical Distraction",
                "target": "Nerve root compression relief",
                "detail": "Gentle axial traction in supine.",
                "evidence": "Sensitivity 40-50% · Specificity 90-100%",
                "has_side": True,
                "has_measure": False,
            },
            {
                "name": "Shoulder Abduction (Bakody's)",
                "target": "C4-C5 nerve root involvement",
                "detail": "Hand placed on top of the head to check symptom relief.",
                "evidence": "Sensitivity 17-78% · Specificity 75-92%",
                "has_side": True,
                "has_measure": False,
            },
            {
                "name": "Valsalva Manoeuvre",
                "target": "Space-occupying lesion / disc involvement",
                "detail": "Bear down to provoke spinal or radiating pain.",
                "evidence": "High specificity, low sensitivity",
                "has_side": False,
                "has_measure": False,
            },
            {
                "name": "Vertebral Artery Test (DeKleyn's)",
                "target": "Vertebrobasilar insufficiency screen",
                "detail": "Extend and rotate head, monitoring for dizziness or nystagmus.",
                "evidence": "Pre-manipulation safety screen",
                "has_side": True,
                "has_measure": False,
            },
            {
                "name": "Upper Limb Tension Test (ULTT)",
                "target": "Neural tension",
                "detail": "Median / radial / ulnar nerve bias sequence.",
                "evidence": "Sensitivity 72-97% · Specificity 11-33%",
                "has_side": True,
                "has_measure": False,
            },
            {
                "name": "Jackson's Compression",
                "target": "Facet syndrome / foraminal encroachment",
                "detail": "Laterally flex head and apply axial compression.",
                "evidence": "Differentiates facet from nerve-root pain",
                "has_side": True,
                "has_measure": False,
            },
        ],
    },
    {
        "key": "thoracic",
        "label": "Thoracic Spine (T1-T12)",
        "tests": [
            {
                "name": "Adam's Forward Bend",
                "target": "Structural vs functional scoliosis",
                "detail": "Observe for rib hump or persistent asymmetry.",
                "evidence": "Standard scoliosis screen",
                "has_side": False,
                "has_measure": False,
            },
            {
                "name": "Schepelmann's Test",
                "target": "Intercostal neuralgia vs pleuritic pain",
                "detail": "Laterally flex trunk to compare concave vs convex pain.",
                "evidence": "Differentiates MSK from pleural pain",
                "has_side": True,
                "has_measure": False,
            },
            {
                "name": "Soto-Hall Test",
                "target": "Thoracic vertebral fracture / ligament injury",
                "detail": "Passive cervical flexion while fixing the sternum.",
                "evidence": "Screens for fracture",
                "has_side": False,
                "has_measure": False,
            },
            {
                "name": "Passive Neck Flexion (Brudzinski)",
                "target": "Meningeal irritation / UMN pattern",
                "detail": "Passive neck flexion monitoring hip and knee response.",
                "evidence": "Red-flag meningitis / cord screen",
                "has_side": False,
                "has_measure": False,
            },
            {
                "name": "Chest Expansion Test",
                "target": "Costovertebral restriction / ankylosing spondylitis",
                "detail": "Measure thoracic circumference change from expiration to inspiration.",
                "evidence": "Normal >= 5 cm · restricted < 2.5 cm",
                "has_side": False,
                "has_measure": True,
                "measure_unit": "cm",
            },
        ],
    },
    {
        "key": "lumbar",
        "label": "Lumbar Spine (L1-L5)",
        "tests": [
            {
                "name": "Straight Leg Raise (Lasegue's)",
                "target": "Lumbar disc herniation / sciatic nerve",
                "detail": "Supine straight-leg raise looking for radiating pain between 30 and 70 degrees.",
                "evidence": "Sensitivity 72-97% · Specificity 11-66%",
                "has_side": True,
                "has_measure": True,
                "measure_unit": "deg",
            },
            {
                "name": "Crossed SLR (Well Leg Raise)",
                "target": "Large disc herniation / central stenosis",
                "detail": "Raise the unaffected leg and note opposite-leg pain.",
                "evidence": "Sensitivity 29% · Specificity 88%",
                "has_side": True,
                "has_measure": False,
            },
            {
                "name": "Kemp's Test",
                "target": "Facet syndrome / foraminal encroachment",
                "detail": "Extension, lateral flexion, and rotation toward the affected side.",
                "evidence": "Differentiates facet from disc-driven pain",
                "has_side": True,
                "has_measure": False,
            },
            {
                "name": "Prone Knee Bend (Femoral Stretch)",
                "target": "Upper lumbar disc / L2-L4 nerve root",
                "detail": "Flex knee toward buttock and note anterior thigh pain.",
                "evidence": "Tests L2-L4 (femoral nerve)",
                "has_side": True,
                "has_measure": False,
            },
            {
                "name": "Slump Test",
                "target": "Neural tension / dural irritation",
                "detail": "Slump, flex neck, extend knee, dorsiflex foot.",
                "evidence": "Sensitivity 84% · Specificity 83%",
                "has_side": True,
                "has_measure": False,
            },
            {
                "name": "Milgram's Test",
                "target": "Intrathecal pathology / disc lesion",
                "detail": "Hold both legs 6 inches off the table for 30 seconds.",
                "evidence": "Increases intrathecal and intradiskal pressure",
                "has_side": False,
                "has_measure": False,
            },
            {
                "name": "Stork Test (Single Leg Extension)",
                "target": "Spondylolysis / spondylolisthesis",
                "detail": "Single-leg stance with lumbar extension.",
                "evidence": "Screens for pars fracture",
                "has_side": True,
                "has_measure": False,
            },
        ],
    },
    {
        "key": "si",
        "label": "Sacroiliac / Pelvis",
        "tests": [
            {
                "name": "FABER / Patrick's Test",
                "target": "SI joint dysfunction / hip pathology",
                "detail": "Flex, abduct, externally rotate and press the knee down.",
                "evidence": "Sensitivity 57-77% · Specificity 71-100%",
                "has_side": True,
                "has_measure": False,
            },
            {
                "name": "Gaenslen's Test",
                "target": "SI joint inflammation",
                "detail": "Flex one hip to chest while extending the other off the table.",
                "evidence": "Stresses anterior SI ligaments",
                "has_side": True,
                "has_measure": False,
            },
            {
                "name": "SI Compression Test",
                "target": "SI joint sprain / inflammation",
                "detail": "Side-lying downward pressure on the iliac crest.",
                "evidence": "Part of SI provocation cluster",
                "has_side": True,
                "has_measure": False,
            },
            {
                "name": "Gillet's Test (Stork / March)",
                "target": "SI joint hypomobility",
                "detail": "Track PSIS drop during hip flexion.",
                "evidence": "Assesses SI joint motion",
                "has_side": True,
                "has_measure": False,
            },
            {
                "name": "Thomas Test",
                "target": "Hip flexion contracture / iliopsoas",
                "detail": "Flex one knee to chest and observe opposite thigh lift.",
                "evidence": "Standard hip flexor assessment",
                "has_side": True,
                "has_measure": False,
            },
        ],
    },
]

SUMMIT_SPINE_SEVERITY = {
    0: "None",
    1: "Mild",
    2: "Moderate",
    3: "Significant",
    4: "Severe",
    5: "Critical",
}


def format_number(value):
    if value in (None, ""):
        return None
    if isinstance(value, float):
        if value.is_integer():
            return str(int(value))
        return f"{value:.1f}".rstrip("0").rstrip(".")
    return str(value)


def _safe_json_dict(value: str | None) -> dict:
    if not value:
        return {}
    try:
        parsed = json.loads(value)
    except (TypeError, ValueError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _status_meta(status: str) -> tuple[str, str]:
    labels = {
        "healthy": "Healthy",
        "warning": "Attention",
        "concern": "Concern",
        "pending": "Not tested",
    }
    tones = {
        "healthy": "life",
        "warning": "amber",
        "concern": "rose",
        "pending": "sky",
    }
    return labels.get(status, "Not tested"), tones.get(status, "sky")


def _int_or_none(value):
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _float_or_none(value):
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _normalize_goals(values: list[str]) -> list[str]:
    seen = set()
    goals = []
    for value in values:
        cleaned = (value or "").strip()
        if cleaned and cleaned not in seen:
            goals.append(cleaned)
            seen.add(cleaned)
    return goals


def build_summit_assessment(user: dict, payload: dict, report: dict | None = None) -> dict:
    payload = build_seed_payload(user, payload)
    stored = _safe_json_dict((report or {}).get("assessment_payload_json"))
    patient = payload.get("patient") or {}
    reason = payload.get("reasonForVisit") or {}
    pain = payload.get("pain") or {}
    lifestyle = payload.get("lifestyle") or {}
    goals = payload.get("goals") or {}
    stored_patient = stored.get("patient") or {}
    stored_history = stored.get("history") or {}
    stored_health = stored.get("health_indicators") or {}
    stored_functional = stored.get("functional_tests") or {}
    stored_rom = stored.get("range_of_motion") or {}
    stored_ortho = stored.get("orthopedic_tests") or {}
    stored_spine = stored.get("spine_assessment") or {}
    stored_leg = stored.get("leg_length") or {}

    derived_goals = list(goals.get("goals") or [])
    if goals.get("activityGoal"):
        derived_goals.append(goals["activityGoal"])
    patient_goals = _normalize_goals(stored_patient.get("goals") or derived_goals)

    assessment = {
        "patient": {
            "full_name": stored_patient.get("full_name")
            or f"{patient.get('firstName', user['first_name'])} {patient.get('lastName', user['last_name'])}".strip(),
            "dob": stored_patient.get("dob") or patient.get("dob", ""),
            "sex": stored_patient.get("sex") or patient.get("sex", ""),
            "age": _int_or_none(stored_patient.get("age")) or calculate_age(patient.get("dob")),
            "referring_provider": stored_patient.get("referring_provider")
            or patient.get("referringProvider")
            or "",
            "goals": patient_goals,
        },
        "assessment_date": stored.get("assessment_date")
        or ((report or {}).get("visit_date", "") or "")[:10]
        or date.today().isoformat(),
        "history": {
            "chief_complaint": stored_history.get("chief_complaint")
            or reason.get("chiefComplaint")
            or "",
            "duration_years": _float_or_none(stored_history.get("duration_years")),
            "occupation": stored_history.get("occupation") or lifestyle.get("occupation", ""),
            "work_hours": stored_history.get("work_hours") or lifestyle.get("workHours", ""),
            "pain_level": _int_or_none(stored_history.get("pain_level"))
            or _int_or_none((report or {}).get("pain_worst"))
            or _int_or_none(pain.get("worstLevel")),
            "frequency": _int_or_none(stored_history.get("frequency")),
            "notes": stored_history.get("notes") or "",
        },
        "health_indicators": {
            "grip_strength": {
                "left_kg": _float_or_none((stored_health.get("grip_strength") or {}).get("left_kg")),
                "right_kg": _float_or_none((stored_health.get("grip_strength") or {}).get("right_kg")),
            },
            "balance": {
                "left_sec": _int_or_none((stored_health.get("balance") or {}).get("left_sec"))
                or _int_or_none((report or {}).get("single_leg_balance_left_seconds")),
                "right_sec": _int_or_none((stored_health.get("balance") or {}).get("right_sec"))
                or _int_or_none((report or {}).get("single_leg_balance_right_seconds")),
            },
            "chair_stand": {
                "reps_30s": _int_or_none((stored_health.get("chair_stand") or {}).get("reps_30s")),
            },
            "gait_speed": {
                "time_10m": _float_or_none((stored_health.get("gait_speed") or {}).get("time_10m")),
            },
            "sitting_rising": {
                "sit_score": _float_or_none((stored_health.get("sitting_rising") or {}).get("sit_score")),
                "rise_score": _float_or_none((stored_health.get("sitting_rising") or {}).get("rise_score")),
            },
            "resting_heart_rate": {
                "bpm": _int_or_none((stored_health.get("resting_heart_rate") or {}).get("bpm")),
            },
            "vo2_max": {
                "age": _int_or_none((stored_health.get("vo2_max") or {}).get("age"))
                or calculate_age(patient.get("dob")),
                "resting_hr": _int_or_none((stored_health.get("vo2_max") or {}).get("resting_hr")),
            },
            "fingertip_to_floor": {
                "distance_cm": _float_or_none((stored_health.get("fingertip_to_floor") or {}).get("distance_cm")),
            },
        },
        "functional_tests": {
            "marching_test": {
                "deviation_cm": _float_or_none((stored_functional.get("marching_test") or {}).get("deviation_cm")),
                "direction": (stored_functional.get("marching_test") or {}).get("direction") or "",
            },
            "heel_toe_walk": {
                "steady_steps": _int_or_none((stored_functional.get("heel_toe_walk") or {}).get("steady_steps")),
            },
            "weight_distribution": {
                "left_kg": _float_or_none((stored_functional.get("weight_distribution") or {}).get("left_kg")),
                "right_kg": _float_or_none((stored_functional.get("weight_distribution") or {}).get("right_kg")),
            },
        },
        "range_of_motion": {},
        "orthopedic_tests": {},
        "spine_assessment": {"left": {}, "right": {}},
        "leg_length": {
            "left_cm": _float_or_none(stored_leg.get("left_cm")),
            "right_cm": _float_or_none(stored_leg.get("right_cm")),
        },
    }

    for section in SUMMIT_ROM_SECTIONS:
        stored_section = stored_rom.get(section["key"]) or {}
        assessment["range_of_motion"][section["key"]] = {}
        for item in section["items"]:
            assessment["range_of_motion"][section["key"]][item["key"]] = _float_or_none(stored_section.get(item["key"]))

    for region in SUMMIT_ORTHO_REGIONS:
        stored_tests = stored_ortho.get(region["key"]) or []
        normalized_tests = []
        for index, test in enumerate(region["tests"]):
            stored_test = {}
            if index < len(stored_tests) and isinstance(stored_tests[index], dict):
                stored_test = stored_tests[index]
            else:
                for candidate in stored_tests:
                    if isinstance(candidate, dict) and candidate.get("test") == test["name"]:
                        stored_test = candidate
                        break
            normalized_tests.append(
                {
                    "test": test["name"],
                    "result": stored_test.get("result") or "",
                    "side": stored_test.get("side") or "B",
                    "measure": _float_or_none(stored_test.get("measure")),
                    "notes": stored_test.get("notes") or "",
                }
            )
        assessment["orthopedic_tests"][region["key"]] = normalized_tests

    for side in ("left", "right"):
        stored_side = stored_spine.get(side) or {}
        for region in SUMMIT_SPINE_REGIONS:
            for level in region["levels"]:
                value = _int_or_none(stored_side.get(level)) or 0
                assessment["spine_assessment"][side][level] = max(0, min(5, value))

    assessment["patient_goals_text"] = "\n".join(assessment["patient"]["goals"])
    return assessment


def _health_indicator_card(name: str, value: str, status: str, detail: str, supporting: str | None = None) -> dict:
    status_label, tone = _status_meta(status)
    return {
        "name": name,
        "value": value,
        "status": status,
        "status_label": status_label,
        "tone": tone,
        "detail": detail,
        "supporting": supporting or "",
    }


def build_summit_health_indicator_cards(assessment: dict) -> tuple[list[dict], dict]:
    patient_sex = (assessment.get("patient", {}).get("sex") or "").strip().lower()
    is_male = patient_sex in {"m", "male"}
    age = _int_or_none(assessment.get("patient", {}).get("age")) or 40
    health = assessment.get("health_indicators") or {}
    cards = []

    grip = health.get("grip_strength") or {}
    left_grip = _float_or_none(grip.get("left_kg"))
    right_grip = _float_or_none(grip.get("right_kg"))
    if left_grip is None and right_grip is None:
        cards.append(_health_indicator_card("Grip Strength", "Not tested", "pending", "Record best left / right grip in kg."))
    else:
        best_grip = max(left_grip or 0, right_grip or 0)
        thresholds = [54, 44, 35] if is_male else [34, 28, 22]
        if best_grip >= thresholds[0]:
            status = "healthy"
            detail = "Excellent"
        elif best_grip >= thresholds[1]:
            status = "healthy"
            detail = "Good"
        elif best_grip >= thresholds[2]:
            status = "warning"
            detail = "Below average"
        else:
            status = "concern"
            detail = "Low grip strength"
        cards.append(
            _health_indicator_card(
                "Grip Strength",
                f"{format_number(best_grip)} kg",
                status,
                detail,
                f"L {format_number(left_grip) or '—'} · R {format_number(right_grip) or '—'}",
            )
        )

    balance = health.get("balance") or {}
    left_balance = _int_or_none(balance.get("left_sec"))
    right_balance = _int_or_none(balance.get("right_sec"))
    if left_balance is None and right_balance is None:
        cards.append(_health_indicator_card("10-Second Balance", "Not tested", "pending", "Record left and right hold time."))
    else:
        weakest = min(value for value in [left_balance, right_balance] if value is not None)
        threshold = 20 if age < 40 else 10 if age < 60 else 5 if age < 80 else 3
        if weakest >= threshold:
            status = "healthy"
            detail = "Healthy balance"
        elif weakest >= max(1, threshold / 2):
            status = "warning"
            detail = "Below average balance"
        else:
            status = "concern"
            detail = "Balance deficit"
        cards.append(
            _health_indicator_card(
                "10-Second Balance",
                f"{format_number(weakest)} s",
                status,
                detail,
                f"L {left_balance if left_balance is not None else '—'} · R {right_balance if right_balance is not None else '—'}",
            )
        )

    chair_stand = _int_or_none((health.get("chair_stand") or {}).get("reps_30s"))
    if chair_stand is None:
        cards.append(_health_indicator_card("30-Second Chair Stand", "Not tested", "pending", "Count total reps in 30 seconds."))
    else:
        if chair_stand >= 15:
            status = "healthy"
            detail = "Excellent"
        elif chair_stand >= 12:
            status = "healthy"
            detail = "Good"
        elif chair_stand >= 8:
            status = "warning"
            detail = "Below average"
        else:
            status = "concern"
            detail = "Fall-risk range"
        cards.append(_health_indicator_card("30-Second Chair Stand", f"{chair_stand} reps", status, detail))

    gait_time = _float_or_none((health.get("gait_speed") or {}).get("time_10m"))
    if gait_time is None or gait_time <= 0:
        cards.append(_health_indicator_card("Gait Speed (10 m)", "Not tested", "pending", "Enter the time for 10 meters."))
    else:
        gait_speed = 10 / gait_time
        if gait_speed >= 1.2:
            status = "healthy"
            detail = "Excellent gait speed"
        elif gait_speed >= 1.0:
            status = "healthy"
            detail = "Normal gait speed"
        elif gait_speed >= 0.8:
            status = "warning"
            detail = "Below average gait speed"
        else:
            status = "concern"
            detail = "Slow gait speed"
        cards.append(
            _health_indicator_card(
                "Gait Speed (10 m)",
                f"{gait_speed:.2f} m/s",
                status,
                detail,
                f"10 m in {format_number(gait_time)} s",
            )
        )

    srt = health.get("sitting_rising") or {}
    sit_score = _float_or_none(srt.get("sit_score"))
    rise_score = _float_or_none(srt.get("rise_score"))
    if sit_score is None and rise_score is None:
        cards.append(_health_indicator_card("Sitting-Rising Test", "Not tested", "pending", "Record sit and rise score out of 5."))
    else:
        total_score = (sit_score or 0) + (rise_score or 0)
        if total_score >= 8:
            status = "healthy"
            detail = "Excellent"
        elif total_score >= 6:
            status = "healthy"
            detail = "Good"
        elif total_score >= 3.5:
            status = "warning"
            detail = "Below average"
        else:
            status = "concern"
            detail = "High-risk pattern"
        cards.append(
            _health_indicator_card(
                "Sitting-Rising Test",
                f"{format_number(total_score)}/10",
                status,
                detail,
                f"Sit {format_number(sit_score) or '0'} · Rise {format_number(rise_score) or '0'}",
            )
        )

    resting_hr = _int_or_none((health.get("resting_heart_rate") or {}).get("bpm"))
    if resting_hr is None:
        cards.append(_health_indicator_card("Resting Heart Rate", "Not tested", "pending", "Enter resting heart rate in bpm."))
    else:
        if resting_hr < 60:
            status = "healthy"
            detail = "Athletic"
        elif resting_hr <= 70:
            status = "healthy"
            detail = "Good"
        elif resting_hr <= 80:
            status = "warning"
            detail = "Average"
        else:
            status = "concern"
            detail = "Elevated CV risk"
        cards.append(_health_indicator_card("Resting Heart Rate", f"{resting_hr} bpm", status, detail))

    vo2 = health.get("vo2_max") or {}
    vo2_age = _int_or_none(vo2.get("age"))
    vo2_rhr = _int_or_none(vo2.get("resting_hr"))
    if vo2_age is None or vo2_rhr is None or vo2_rhr <= 0:
        cards.append(_health_indicator_card("VO2 Max Estimate", "Not tested", "pending", "Needs age and resting heart rate."))
    else:
        max_hr = 208 - (0.7 * vo2_age)
        vo2_value = 15.3 * (max_hr / vo2_rhr)
        if vo2_value >= 46:
            status = "healthy"
            detail = "Excellent fitness"
        elif vo2_value >= 38:
            status = "healthy"
            detail = "Good fitness"
        elif vo2_value >= 30:
            status = "warning"
            detail = "Average fitness"
        else:
            status = "concern"
            detail = "Low fitness"
        cards.append(
            _health_indicator_card(
                "VO2 Max Estimate",
                f"{vo2_value:.1f}",
                status,
                detail,
                f"Age {vo2_age} · RHR {vo2_rhr} bpm",
            )
        )

    fingertip = _float_or_none((health.get("fingertip_to_floor") or {}).get("distance_cm"))
    if fingertip is None:
        cards.append(_health_indicator_card("Fingertip-to-Floor", "Not tested", "pending", "Measure fingertip distance from the floor."))
    else:
        if fingertip <= 0:
            status = "healthy"
            detail = "Excellent"
        elif fingertip <= 5:
            status = "healthy"
            detail = "Normal"
        elif fingertip <= 15:
            status = "warning"
            detail = "Below average"
        else:
            status = "concern"
            detail = "Restricted"
        cards.append(_health_indicator_card("Fingertip-to-Floor", f"{format_number(fingertip)} cm", status, detail))

    tested_cards = [card for card in cards if card["status"] != "pending"]
    summary = {
        "tested_count": len(tested_cards),
        "healthy_count": sum(1 for card in tested_cards if card["status"] == "healthy"),
        "total_count": len(cards),
    }
    return cards, summary


def build_summit_functional_cards(assessment: dict) -> list[dict]:
    functional = assessment.get("functional_tests") or {}
    cards = []

    marching = functional.get("marching_test") or {}
    deviation = _float_or_none(marching.get("deviation_cm"))
    direction = marching.get("direction") or ""
    if deviation is None:
        cards.append(_health_indicator_card("Marching Test", "Not tested", "pending", "Record deviation from the T in cm."))
    else:
        status = "healthy" if deviation <= 10 else "concern"
        detail = "On the T / within range" if status == "healthy" else "Deviation noted"
        cards.append(
            _health_indicator_card(
                "Marching Test",
                f"{format_number(deviation)} cm{f' {direction}' if direction else ''}",
                status,
                detail,
            )
        )

    heel_toe = _int_or_none((functional.get("heel_toe_walk") or {}).get("steady_steps"))
    if heel_toe is None:
        cards.append(_health_indicator_card("Heel-to-Toe Walk", "Not tested", "pending", "Record the number of steady steps."))
    else:
        status = "healthy" if heel_toe >= 10 else "concern"
        detail = "Steady gait pattern" if status == "healthy" else "Reduced stability"
        cards.append(_health_indicator_card("Heel-to-Toe Walk", f"{heel_toe} steps", status, detail))

    weight = functional.get("weight_distribution") or {}
    left_weight = _float_or_none(weight.get("left_kg"))
    right_weight = _float_or_none(weight.get("right_kg"))
    if left_weight is None and right_weight is None:
        cards.append(_health_indicator_card("Weight Distribution", "Not tested", "pending", "Record left and right standing weight."))
    else:
        difference = abs((left_weight or 0) - (right_weight or 0))
        status = "healthy" if difference < 2 else "concern"
        detail = "Balanced load" if status == "healthy" else "Asymmetrical load"
        cards.append(
            _health_indicator_card(
                "Weight Distribution",
                f"Δ {format_number(difference)} kg",
                status,
                detail,
                f"L {format_number(left_weight) or '—'} · R {format_number(right_weight) or '—'}",
            )
        )

    return cards


def build_summit_rom_sections(assessment: dict) -> tuple[list[dict], int | None]:
    stored_rom = assessment.get("range_of_motion") or {}
    sections = []
    percent_values = []

    for section in SUMMIT_ROM_SECTIONS:
        items = []
        for item in section["items"]:
            measured = _float_or_none((stored_rom.get(section["key"]) or {}).get(item["key"]))
            if measured is None:
                items.append(
                    {
                        "key": item["key"],
                        "label": item["label"],
                        "max_norm": item["max_norm"],
                        "measured": None,
                        "percent": None,
                        "status": "pending",
                        "status_label": "Not tested",
                        "tone": "sky",
                    }
                )
                continue

            percent = round((measured / item["max_norm"]) * 100)
            percent_values.append(percent)
            if percent >= 85:
                status = "healthy"
            elif percent >= 65:
                status = "warning"
            else:
                status = "concern"
            status_label, tone = _status_meta(status)
            items.append(
                {
                    "key": item["key"],
                    "label": item["label"],
                    "max_norm": item["max_norm"],
                    "measured": measured,
                    "percent": percent,
                    "status": status,
                    "status_label": status_label,
                    "tone": tone,
                }
            )
        sections.append({"key": section["key"], "label": section["label"], "items": items})

    average = round(sum(percent_values) / len(percent_values)) if percent_values else None
    return sections, average


def build_summit_orthopedic_summary(assessment: dict) -> tuple[list[dict], list[dict], int]:
    stored = assessment.get("orthopedic_tests") or {}
    positives = []
    regions = []
    tested_count = 0

    for region in SUMMIT_ORTHO_REGIONS:
        saved_tests = stored.get(region["key"]) or []
        region_entries = []
        for index, test in enumerate(region["tests"]):
            saved_test = saved_tests[index] if index < len(saved_tests) else {}
            result = saved_test.get("result") or ""
            if result:
                tested_count += 1
            entry = {
                "name": test["name"],
                "target": test["target"],
                "result": result,
                "side": saved_test.get("side") or "B",
                "measure": _float_or_none(saved_test.get("measure")),
                "notes": saved_test.get("notes") or "",
            }
            region_entries.append(entry)
            if result == "+":
                positives.append(
                    {
                        "region": region["label"],
                        "name": test["name"],
                        "target": test["target"],
                        "side": entry["side"],
                        "measure": entry["measure"],
                        "notes": entry["notes"],
                    }
                )
        regions.append(
            {
                "key": region["key"],
                "label": region["label"],
                "entries": region_entries,
                "tested_count": sum(1 for entry in region_entries if entry["result"]),
                "positive_count": sum(1 for entry in region_entries if entry["result"] == "+"),
            }
        )

    return regions, positives, tested_count


def build_summit_spine_summary(assessment: dict) -> dict:
    stored = assessment.get("spine_assessment") or {}
    rows = []
    flagged_count = 0
    highest_level = 0

    for region in SUMMIT_SPINE_REGIONS:
        for level in region["levels"]:
            left_value = _int_or_none((stored.get("left") or {}).get(level)) or 0
            right_value = _int_or_none((stored.get("right") or {}).get(level)) or 0
            highest_level = max(highest_level, left_value, right_value)
            if left_value or right_value:
                flagged_count += 1
            rows.append(
                {
                    "region": region["label"],
                    "level": level,
                    "left": left_value,
                    "right": right_value,
                    "left_label": SUMMIT_SPINE_SEVERITY.get(left_value, "None"),
                    "right_label": SUMMIT_SPINE_SEVERITY.get(right_value, "None"),
                    "flagged": bool(left_value or right_value),
                }
            )

    highlighted = [row for row in rows if row["flagged"]]
    highlighted.sort(key=lambda row: max(row["left"], row["right"]), reverse=True)

    return {
        "rows": rows,
        "highlighted_rows": highlighted[:12],
        "flagged_count": flagged_count,
        "highest_level": highest_level,
        "highest_label": SUMMIT_SPINE_SEVERITY.get(highest_level, "None"),
    }


def build_summit_leg_length_summary(assessment: dict) -> dict:
    leg_length = assessment.get("leg_length") or {}
    left_cm = _float_or_none(leg_length.get("left_cm"))
    right_cm = _float_or_none(leg_length.get("right_cm"))
    if left_cm is None or right_cm is None:
        return {
            "left_cm": left_cm,
            "right_cm": right_cm,
            "difference_cm": None,
            "summary": "Not tested",
        }

    difference = abs(left_cm - right_cm)
    if difference == 0:
        summary = "Leg lengths equal"
    elif left_cm > right_cm:
        summary = "Left leg longer"
    else:
        summary = "Right leg longer"

    return {
        "left_cm": left_cm,
        "right_cm": right_cm,
        "difference_cm": difference,
        "summary": summary,
    }


def build_seed_payload(user: dict, payload: dict | None = None) -> dict:
    payload = payload or {}
    payload.setdefault("_app", "Life Chiropractic Intake")
    payload.setdefault("_version", "1.0")
    payload.setdefault("submittedAt", iso_now())

    patient = payload.setdefault("patient", {})
    patient.setdefault("firstName", user["first_name"])
    patient.setdefault("lastName", user["last_name"])
    patient["email"] = user["email"]
    patient.setdefault("phone", "")
    patient.setdefault("dob", "")
    patient.setdefault("sex", "")
    patient.setdefault("pronoun", "")
    patient.setdefault("heightFt", None)
    patient.setdefault("heightIn", None)
    patient.setdefault("weight", "")
    patient.setdefault("address", "")
    emergency = patient.setdefault("emergencyContact", {})
    emergency.setdefault("name", "")
    emergency.setdefault("relationship", "")
    emergency.setdefault("phone", "")
    patient.setdefault("referralSource", [])
    patient.setdefault("referringProvider", "")

    payload.setdefault(
        "reasonForVisit",
        {
            "reasons": [],
            "chiefComplaint": "",
            "onset": "",
            "onsetType": "",
            "cause": [],
            "causeDetail": "",
        },
    )
    payload.setdefault(
        "pain",
        {
            "areas": [],
            "currentLevel": 5,
            "worstLevel": 7,
            "type": [],
            "frequency": [],
            "aggravating": [],
            "relieving": [],
        },
    )
    payload.setdefault(
        "medicalHistory",
        {
            "conditions": [],
            "conditionsOther": "",
            "surgeries": None,
            "fractures": None,
            "previousInjuries": None,
            "medications": None,
            "allergies": None,
            "priorChiropractic": [],
            "priorTreatments": "",
            "imaging": [],
        },
    )
    payload.setdefault(
        "lifestyle",
        {
            "occupation": "",
            "workType": "",
            "workHours": "",
            "dailyImpact": [],
            "exerciseFrequency": "",
            "exerciseType": "",
            "sleepHours": "",
            "sleepQuality": "",
            "sleepPosition": [],
            "stressLevel": 5,
            "habits": {
                "smoker": False,
                "alcohol": False,
                "highCaffeine": False,
                "prolongedSitting": False,
                "highScreenTime": False,
            },
        },
    )
    payload.setdefault(
        "functionalOutcomeMeasures",
        {
            "routing": {"selectedComplaints": [], "questionnairesShown": []},
            "questionnaires": [],
            "archived": [],
        },
    )
    payload.setdefault(
        "goals",
        {
            "goals": [],
            "activityGoal": "",
            "commitmentLevel": None,
            "additionalNotes": "",
        },
    )
    consent = payload.setdefault(
        "consent",
        {
            "chiropracticCare": False,
            "privacyNotice": False,
            "accuracyConfirmation": False,
            "signature": "",
            "signatureDate": date.today().isoformat(),
        },
    )
    consent.setdefault("signatureDate", date.today().isoformat())
    return payload


def validate_submission(payload: dict | None, status: str) -> list[str]:
    if not isinstance(payload, dict):
        return ["Invalid intake payload."]

    if status == "draft":
        return []

    patient = payload.get("patient") or {}
    reason = payload.get("reasonForVisit") or {}
    pain = payload.get("pain") or {}
    consent = payload.get("consent") or {}

    required = {
        "First name": patient.get("firstName"),
        "Last name": patient.get("lastName"),
        "Email": patient.get("email"),
        "Phone": patient.get("phone"),
        "Date of birth": patient.get("dob"),
        "Sex": patient.get("sex"),
        "Chief complaint": reason.get("chiefComplaint"),
    }

    errors = [f"{label} is required." for label, value in required.items() if not value]

    current_level = pain.get("currentLevel")
    worst_level = pain.get("worstLevel")
    if current_level in (None, ""):
        errors.append("Current pain level is required.")
    if worst_level in (None, ""):
        errors.append("Worst pain level is required.")

    if not consent.get("chiropracticCare"):
        errors.append("Chiropractic care consent must be accepted.")
    if not consent.get("privacyNotice"):
        errors.append("Privacy notice consent must be accepted.")
    if not consent.get("accuracyConfirmation"):
        errors.append("Accuracy confirmation must be accepted.")
    if not consent.get("signature"):
        errors.append("Digital signature is required.")
    if not consent.get("signatureDate"):
        errors.append("Signature date is required.")

    return errors


def questionnaire_display(questionnaire: dict) -> dict:
    raw_score = questionnaire.get("rawScore")
    percent = questionnaire.get("percent") or 0
    label = questionnaire.get("displayName") or questionnaire.get("questionnaireId") or "Outcome score"
    interpretation = questionnaire.get("interpretation") or "Incomplete"

    if questionnaire.get("questionnaireId") == "hit6" and raw_score is not None:
        display_value = f"{raw_score}/78"
        ring_percent = max(0, min(100, percent))
    else:
        display_value = f"{percent}%"
        ring_percent = max(0, min(100, percent))

    if "Severe" in interpretation or "Complete" in interpretation or "Crippling" in interpretation:
        tone = "rose"
    elif "Moderate" in interpretation or "Some" in interpretation or "Substantial" in interpretation:
        tone = "amber"
    else:
        tone = "life"

    circumference = 264
    offset = circumference - round(circumference * ring_percent / 100)

    return {
        "label": label,
        "interpretation": interpretation,
        "display_value": display_value,
        "ring_percent": ring_percent,
        "stroke_offset": offset,
        "tone": tone,
    }


def build_visit_report_context(report: dict | None, user: dict | None = None, payload: dict | None = None) -> dict | None:
    if not report:
        return None

    summit_assessment = build_summit_assessment(
        user or {"first_name": "", "last_name": "", "email": ""},
        payload or {},
        report,
    )
    health_indicator_cards, health_indicator_summary = build_summit_health_indicator_cards(summit_assessment)
    functional_cards = build_summit_functional_cards(summit_assessment)
    rom_sections, rom_average = build_summit_rom_sections(summit_assessment)
    orthopedic_regions, positive_orthopedic_tests, orthopedic_tested_count = build_summit_orthopedic_summary(summit_assessment)
    spine_summary = build_summit_spine_summary(summit_assessment)
    leg_length = build_summit_leg_length_summary(summit_assessment)

    pain_level = summit_assessment["history"].get("pain_level")
    duration_years = summit_assessment["history"].get("duration_years")
    history_frequency = summit_assessment["history"].get("frequency")
    marching = summit_assessment["functional_tests"]["marching_test"]
    heel_toe_steps = summit_assessment["functional_tests"]["heel_toe_walk"].get("steady_steps")
    weight_distribution = summit_assessment["functional_tests"]["weight_distribution"]
    gait_card = next((card for card in health_indicator_cards if card["name"] == "Gait Speed (10 m)"), None)

    objective_metrics = []
    if pain_level is not None:
        objective_metrics.append(
            {
                "label": "Pain level",
                "value": f"{pain_level}/10",
                "tone": "rose" if pain_level >= 7 else "amber" if pain_level >= 4 else "life",
            }
        )
    if health_indicator_summary["tested_count"]:
        objective_metrics.append(
            {
                "label": "Vital indicators passed",
                "value": f"{health_indicator_summary['healthy_count']}/{health_indicator_summary['tested_count']}",
                "tone": "life"
                if health_indicator_summary["healthy_count"] == health_indicator_summary["tested_count"]
                else "amber",
            }
        )
    if gait_card and gait_card["status"] != "pending":
        objective_metrics.append(
            {
                "label": gait_card["name"],
                "value": gait_card["value"],
                "tone": gait_card["tone"],
            }
        )
    if rom_average is not None:
        objective_metrics.append(
            {
                "label": "Average ROM",
                "value": f"{rom_average}%",
                "tone": "life" if rom_average >= 80 else "amber" if rom_average >= 60 else "rose",
            }
        )
    if leg_length["difference_cm"] is not None:
        objective_metrics.append(
            {
                "label": "Leg length difference",
                "value": f"{format_number(leg_length['difference_cm'])} cm",
                "tone": "amber" if leg_length["difference_cm"] < 1 else "rose",
            }
        )
    left_weight = weight_distribution.get("left_kg")
    right_weight = weight_distribution.get("right_kg")
    if left_weight is not None or right_weight is not None:
        difference = abs((left_weight or 0) - (right_weight or 0))
        objective_metrics.append(
            {
                "label": "Weight distribution delta",
                "value": f"{format_number(difference)} kg",
                "tone": "life" if difference < 2 else "rose",
            }
        )
    if positive_orthopedic_tests:
        objective_metrics.append(
            {
                "label": "Positive orthopedic tests",
                "value": str(len(positive_orthopedic_tests)),
                "tone": "amber" if len(positive_orthopedic_tests) < 3 else "rose",
            }
        )
    if report.get("forward_head_inches") not in (None, ""):
        objective_metrics.append(
            {
                "label": "Forward head posture",
                "value": f"{report.get('forward_head_inches')} in",
                "tone": "amber",
            }
        )
    if report.get("shoulders_level"):
        objective_metrics.append(
            {
                "label": "Shoulder level",
                "value": report.get("shoulders_level"),
                "tone": "life",
            }
        )
    if report.get("hips_level"):
        objective_metrics.append(
            {
                "label": "Hip level",
                "value": report.get("hips_level"),
                "tone": "life",
            }
        )
    if report.get("single_leg_balance_left_seconds") not in (None, "") or report.get("single_leg_balance_right_seconds") not in (None, ""):
        left = report.get("single_leg_balance_left_seconds")
        right = report.get("single_leg_balance_right_seconds")
        objective_metrics.append(
            {
                "label": "Single-leg balance",
                "value": f"L {left or '—'}s · R {right or '—'}s",
                "tone": "sky",
            }
        )
    if report.get("heel_to_toe_walk"):
        objective_metrics.append(
            {
                "label": "Heel-to-toe walk",
                "value": report.get("heel_to_toe_walk"),
                "tone": "life",
            }
        )
    if report.get("marching_test"):
        objective_metrics.append(
            {
                "label": "Marching test",
                "value": report.get("marching_test"),
                "tone": "plum",
            }
        )
    if report.get("pain_worst") not in (None, ""):
        objective_metrics.append(
            {
                "label": "Worst pain reported",
                "value": f"{report.get('pain_worst')}/10",
                "tone": "rose",
            }
        )

    sections = [
        {"title": "Rapport Building", "body": report.get("rapport_notes")},
        {"title": "Chief Complaint Summary", "body": report.get("subjective_summary")},
        {"title": "Accidents and Injuries", "body": report.get("accident_history")},
        {"title": "Microtrauma / Repetitive Strain", "body": report.get("microtrauma_history")},
        {"title": "Past or Current Treatment Sought", "body": report.get("prior_treatment_history")},
        {"title": "ADL Impact", "body": report.get("adl_impacts")},
        {"title": "Medical and Family History Review", "body": report.get("medical_family_history_review")},
        {"title": "Education Given", "body": report.get("education_summary")},
        {"title": "Posture", "body": report.get("posture_findings")},
        {"title": "Range of Motion", "body": report.get("range_of_motion")},
        {"title": "Orthopedic Testing", "body": report.get("orthopedic_findings")},
        {"title": "Neurological Findings", "body": report.get("neuro_findings")},
        {"title": "Palpation", "body": report.get("palpation_findings")},
        {"title": "Imaging Review", "body": report.get("imaging_review")},
        {"title": "Wrap Up", "body": report.get("wrap_up_notes")},
        {"title": "Triangle / Handoff", "body": report.get("triangle_handoff")},
    ]

    rom_summary_lines = []
    for section in rom_sections:
        measured_items = [item for item in section["items"] if item["measured"] is not None]
        if measured_items:
            summary = ", ".join(
                f"{item['label']} {format_number(item['measured'])}/{item['max_norm']}°"
                for item in measured_items
            )
            rom_summary_lines.append(f"{section['label']}: {summary}")

    orthopedic_summary_lines = []
    for item in positive_orthopedic_tests:
        line = item["name"]
        if item["side"] and item["side"] != "B":
            line += f" ({item['side']})"
        if item["measure"] is not None:
            line += f" {format_number(item['measure'])}"
        orthopedic_summary_lines.append(line)

    marching_summary = report.get("marching_test", "")
    if not marching_summary and marching.get("deviation_cm") is not None:
        marching_summary = f"{format_number(marching['deviation_cm'])} cm"
        if marching.get("direction"):
            marching_summary += f" {marching['direction']}"

    heel_toe_summary = report.get("heel_to_toe_walk", "")
    if not heel_toe_summary and heel_toe_steps is not None:
        heel_toe_summary = f"{heel_toe_steps} steady steps"

    complaint_duration = report.get("complaint_duration", "")
    if not complaint_duration and duration_years is not None:
        complaint_duration = f"{format_number(duration_years)} years"

    complaint_frequency = report.get("complaint_frequency", "")
    if not complaint_frequency and history_frequency is not None:
        complaint_frequency = f"{history_frequency}/10 days"

    return {
        "status": report.get("report_status", "draft"),
        "visit_kind": report.get("visit_kind", "initial_consult"),
        "visit_date": format_schedule(report.get("visit_date")) or report.get("visit_date"),
        "assessment_date": format_long_date(summit_assessment.get("assessment_date")) or summit_assessment.get("assessment_date"),
        "rapport_notes": report.get("rapport_notes", ""),
        "subjective_summary": report.get("subjective_summary", "")
        or summit_assessment["history"].get("notes", "")
        or summit_assessment["history"].get("chief_complaint", ""),
        "complaint_duration": complaint_duration,
        "first_notice": report.get("first_notice", ""),
        "complaint_frequency": complaint_frequency,
        "pain_worst": report.get("pain_worst") if report.get("pain_worst") is not None else pain_level,
        "pain_quality": report.get("pain_quality", ""),
        "radiates": bool(report.get("radiates")),
        "radiation_start": report.get("radiation_start", ""),
        "radiation_end": report.get("radiation_end", ""),
        "accident_history": report.get("accident_history", ""),
        "microtrauma_history": report.get("microtrauma_history", ""),
        "prior_treatment_history": report.get("prior_treatment_history", ""),
        "symptom_trend": report.get("symptom_trend", ""),
        "adl_impacts": report.get("adl_impacts", ""),
        "medical_family_history_review": report.get("medical_family_history_review", ""),
        "commitment_score": report.get("commitment_score"),
        "obstacles_to_care": report.get("obstacles_to_care", ""),
        "education_summary": report.get("education_summary", ""),
        "forward_head_inches": report.get("forward_head_inches"),
        "shoulders_level": report.get("shoulders_level", ""),
        "hips_level": report.get("hips_level", ""),
        "single_leg_balance_left_seconds": report.get("single_leg_balance_left_seconds")
        if report.get("single_leg_balance_left_seconds") is not None
        else summit_assessment["health_indicators"]["balance"].get("left_sec"),
        "single_leg_balance_right_seconds": report.get("single_leg_balance_right_seconds")
        if report.get("single_leg_balance_right_seconds") is not None
        else summit_assessment["health_indicators"]["balance"].get("right_sec"),
        "heel_to_toe_walk": heel_toe_summary,
        "marching_test": marching_summary,
        "xray_recommended": bool(report.get("xray_recommended")),
        "xray_status": report.get("xray_status", ""),
        "xray_regions": report.get("xray_regions", ""),
        "assessment": report.get("assessment", ""),
        "diagnosis": report.get("diagnosis", ""),
        "diagnosis_items": split_lines(report.get("diagnosis")),
        "care_plan": report.get("care_plan", ""),
        "home_care": report.get("home_care", ""),
        "follow_up_plan": report.get("follow_up_plan", ""),
        "wrap_up_notes": report.get("wrap_up_notes", ""),
        "triangle_handoff": report.get("triangle_handoff", ""),
        "patient_summary": report.get("patient_summary", ""),
        "patient_key_findings": split_lines(report.get("patient_key_findings")),
        "patient_recommendations": split_lines(report.get("patient_recommendations")),
        "exam_sections": [section for section in sections if section["body"]],
        "objective_metrics": objective_metrics,
        "summit_assessment": summit_assessment,
        "health_indicator_cards": health_indicator_cards,
        "health_indicator_summary": health_indicator_summary,
        "functional_cards": functional_cards,
        "rom_sections": rom_sections,
        "rom_average": rom_average,
        "range_of_motion": report.get("range_of_motion", "") or "\n".join(rom_summary_lines),
        "orthopedic_findings": report.get("orthopedic_findings", "") or "\n".join(orthopedic_summary_lines),
        "orthopedic_regions": orthopedic_regions,
        "positive_orthopedic_tests": positive_orthopedic_tests,
        "orthopedic_tested_count": orthopedic_tested_count,
        "spine_summary": spine_summary,
        "leg_length": leg_length,
    }


def validate_visit_report(report: dict, publish: bool) -> list[str]:
    errors = []
    if not report.get("visit_date"):
        errors.append("Visit date is required.")
    commitment_score = report.get("commitment_score")
    if commitment_score not in (None, ""):
        try:
            score = int(commitment_score)
        except (TypeError, ValueError):
            errors.append("Commitment score must be a whole number.")
        else:
            if score < 0 or score > 10:
                errors.append("Commitment score must be between 0 and 10.")
    pain_worst = report.get("pain_worst")
    if pain_worst not in (None, ""):
        try:
            score = int(pain_worst)
        except (TypeError, ValueError):
            errors.append("Worst pain must be a whole number.")
        else:
            if score < 0 or score > 10:
                errors.append("Worst pain must be between 0 and 10.")
    if publish and not report.get("patient_summary"):
        errors.append("Patient-facing summary is required before publishing.")
    if publish and not report.get("care_plan"):
        errors.append("Care plan is required before publishing.")
    if publish and not report.get("patient_recommendations"):
        errors.append("Patient recommendations are required before publishing.")
    return errors


def build_flag_list(payload: dict) -> list[str]:
    payload = payload or {}
    pain = payload.get("pain") or {}
    medical = payload.get("medicalHistory") or {}
    functional = payload.get("functionalOutcomeMeasures") or {}
    conditions = medical.get("conditions") or []

    flags = []
    if "Osteoporosis" in conditions:
        flags.append("Osteoporosis history noted.")
    if "Cancer" in conditions:
        flags.append("Cancer history requires contraindication review.")
    if "Stroke" in conditions:
        flags.append("Stroke history requires vascular screening.")
    if "Currently pregnant" in conditions:
        flags.append("Pregnancy noted for positioning and treatment modifications.")
    if pain.get("currentLevel") is not None and pain.get("currentLevel", 0) >= 8:
        flags.append(f"High current pain level ({pain.get('currentLevel')}/10).")
    previous = medical.get("previousInjuries") or {}
    recovery = previous.get("recoveryStatus") or []
    if "Never fully recovered" in recovery:
        flags.append("Previous injury never fully recovered.")

    for questionnaire in functional.get("questionnaires", []):
        interpretation = questionnaire.get("interpretation") or ""
        if any(label in interpretation for label in ("Severe", "Complete", "Crippling")):
            flags.append(
                f"{questionnaire.get('displayName', questionnaire.get('questionnaireId', 'Outcome score'))}: {interpretation}."
            )

    return flags


def build_clinician_context(
    user: dict,
    payload: dict,
    submission_status: str,
    updated_at: str,
    appointment_at: str | None = None,
    notes: dict | None = None,
    visit_report: dict | None = None,
) -> dict:
    payload = build_seed_payload(user, payload)
    patient = payload["patient"]
    reason = payload["reasonForVisit"]
    pain = payload["pain"]
    medical = payload["medicalHistory"]
    lifestyle = payload["lifestyle"]
    goals = payload["goals"]
    functional = payload["functionalOutcomeMeasures"]

    questionnaires = [questionnaire_display(item) for item in functional.get("questionnaires", [])]
    flags = build_flag_list(payload)

    habits = []
    habit_map = [
        ("smoker", "Uses tobacco"),
        ("alcohol", "Drinks alcohol regularly"),
        ("highCaffeine", "High caffeine intake"),
        ("prolongedSitting", "Prolonged sitting"),
        ("highScreenTime", "High screen time"),
    ]
    for key, label in habit_map:
        if lifestyle.get("habits", {}).get(key):
            habits.append(label)

    return {
        "status": submission_status,
        "updated_at": format_long_date(updated_at),
        "appointment_at": format_schedule(appointment_at),
        "full_name": f"{patient.get('firstName', '')} {patient.get('lastName', '')}".strip() or f"{user['first_name']} {user['last_name']}",
        "initials": (
            (patient.get("firstName", user["first_name"])[:1] + patient.get("lastName", user["last_name"])[:1]).upper()
        ),
        "age": calculate_age(patient.get("dob")),
        "patient": patient,
        "reason": reason,
        "pain": pain,
        "medical": medical,
        "lifestyle": lifestyle,
        "goals": goals,
        "questionnaires": questionnaires,
        "flags": flags,
        "notes": notes or {},
        "habits": habits,
        "visit_report": build_visit_report_context(visit_report, user=user, payload=payload),
    }


def build_results_context(
    user: dict,
    payload: dict,
    submission_status: str,
    updated_at: str,
    visit_report: dict | None = None,
) -> dict:
    payload = build_seed_payload(user, payload)
    patient = payload["patient"]
    reason = payload["reasonForVisit"]
    pain = payload["pain"]
    lifestyle = payload["lifestyle"]
    goals = payload["goals"]
    consent = payload["consent"]
    functional = payload["functionalOutcomeMeasures"]
    questionnaires = [questionnaire_display(item) for item in functional.get("questionnaires", [])]

    habits = []
    habit_map = [
        ("smoker", "Uses tobacco"),
        ("alcohol", "Drinks alcohol regularly"),
        ("highCaffeine", "High caffeine intake"),
        ("prolongedSitting", "Prolonged sitting"),
        ("highScreenTime", "High screen time"),
    ]
    for key, label in habit_map:
        if lifestyle.get("habits", {}).get(key):
            habits.append(label)

    visit_context = build_visit_report_context(visit_report, user=user, payload=payload)
    if visit_context and visit_context["status"] == "published":
        next_steps = [
            "Your chiropractor has published the results from your initial consultation and physical exam.",
            "Use the care plan section to review the recommendations and the next visit plan.",
            "Return to this portal after future visits as more clinical updates are added.",
        ]
    else:
        next_steps = [
            "Your intake has been saved to your secure client portal.",
            "A clinician can review your baseline questionnaire scores before the first visit.",
            "After the initial consultation, the clinic can publish physical findings and your treatment plan here.",
        ]

    return {
        "status": submission_status,
        "updated_at": format_long_date(updated_at),
        "submitted_at": format_long_date(payload.get("submittedAt")),
        "full_name": f"{patient.get('firstName', '')} {patient.get('lastName', '')}".strip() or f"{user['first_name']} {user['last_name']}",
        "initials": (
            (patient.get("firstName", user["first_name"])[:1] + patient.get("lastName", user["last_name"])[:1]).upper()
        ),
        "age": calculate_age(patient.get("dob")),
        "patient": patient,
        "reason": reason,
        "pain": pain,
        "lifestyle": lifestyle,
        "goals": goals,
        "consent": consent,
        "questionnaires": questionnaires,
        "pain_areas": pain.get("areas", []),
        "reason_tags": reason.get("reasons", []),
        "goal_tags": goals.get("goals", []),
        "habits": habits,
        "next_steps": next_steps,
        "visit_report": visit_context if visit_context and visit_context["status"] == "published" else None,
    }
