from __future__ import annotations

from datetime import date, datetime, timedelta
import json
import os
import re
import tempfile
import unittest

from werkzeug.security import generate_password_hash

from chiro_app import create_app
from chiro_app.db import get_db, init_db
from chiro_app.intake import build_seed_payload, iso_now


class PortalFlowTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.app = create_app()
        self.app.config.update(TESTING=True, DATABASE=os.path.join(self.tempdir.name, "test.sqlite3"))
        self.base_now = datetime.now().replace(second=0, microsecond=0)
        with self.app.app_context():
            init_db()
        self.client = self.app.test_client()

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def create_staff_user(self) -> int:
        with self.app.app_context():
            db = get_db()
            cursor = db.execute(
                """
                INSERT INTO users (first_name, last_name, email, password_hash, role, created_at)
                VALUES (?, ?, ?, ?, 'clinician', ?)
                """,
                ("Dr", "Stone", "staff@example.com", generate_password_hash("staffpass123", method="pbkdf2:sha256"), iso_now()),
            )
            db.commit()
            return cursor.lastrowid

    def create_client_user(
        self,
        *,
        first_name: str = "Patient",
        last_name: str = "One",
        email: str = "patient.one@example.com",
        password: str = "patientpass123",
    ) -> int:
        with self.app.app_context():
            db = get_db()
            cursor = db.execute(
                """
                INSERT INTO users (first_name, last_name, email, password_hash, role, created_at)
                VALUES (?, ?, ?, ?, 'client', ?)
                """,
                (
                    first_name,
                    last_name,
                    email,
                    generate_password_hash(password, method="pbkdf2:sha256"),
                    iso_now(),
                ),
            )
            db.commit()
            return cursor.lastrowid

    def login_staff(self) -> None:
        response = self.client.post(
            "/login",
            data={"email": "staff@example.com", "password": "staffpass123"},
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("Practitioner dashboard", response.get_data(as_text=True))
        self.assertIn("My patients", response.get_data(as_text=True))

    def login_client(self, email: str = "patient.one@example.com", password: str = "patientpass123") -> None:
        response = self.client.post(
            "/login",
            data={"email": email, "password": password},
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("your onboarding is ready", response.get_data(as_text=True))

    def appointment_slot(self, days_from_now: int, hour: int, minute: int, duration_minutes: int = 30) -> tuple[str, str]:
        start = (self.base_now + timedelta(days=days_from_now)).replace(hour=hour, minute=minute)
        if start <= self.base_now:
            start += timedelta(days=1)
        end = start + timedelta(minutes=duration_minutes)
        return (
            start.strftime("%Y-%m-%dT%H:%M"),
            end.strftime("%Y-%m-%dT%H:%M"),
        )

    def test_invited_patient_and_password_reset_flow(self) -> None:
        staff_id = self.create_staff_user()
        self.login_staff()
        with self.app.app_context():
            main_location_id = get_db().execute(
                "SELECT id FROM locations WHERE slug = 'main-clinic'"
            ).fetchone()["id"]
        initial_consult_start, _ = self.appointment_slot(days_from_now=1, hour=9, minute=30)
        rof_start, rof_end = self.appointment_slot(days_from_now=2, hour=9, minute=30)
        rof_updated_start, rof_updated_end = self.appointment_slot(days_from_now=2, hour=10, minute=0)
        care_plan_start, care_plan_end = self.appointment_slot(days_from_now=5, hour=9, minute=0, duration_minutes=20)

        response = self.client.post(
            "/staff/invitations/new",
            data={
                "first_name": "Sarah",
                "last_name": "Mitchell",
                "email": "sarah@example.com",
                "appointment_at": initial_consult_start,
                "note": "Please arrive 10 minutes early.",
            },
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("Invitation created", response.get_data(as_text=True))

        response = self.client.post(
            "/staff/locations",
            data={
                "name": "North Branch",
                "slug": "north-branch",
                "address": "88 High Street",
                "phone": "555-0222",
                "timezone": "Europe/London",
            },
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("Location added", response.get_data(as_text=True))

        with self.app.app_context():
            db = get_db()
            invitation = db.execute("SELECT * FROM invitations WHERE email = ?", ("sarah@example.com",)).fetchone()

        self.client.post("/logout", follow_redirects=True)

        response = self.client.post(
            f"/invite/{invitation['token']}",
            data={"password": "patientpass123", "confirm_password": "patientpass123"},
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)
        accepted_html = response.get_data(as_text=True)
        self.assertIn("Invitation accepted", accepted_html)
        self.assertIn("Initial Consultation", accepted_html)

        with self.app.app_context():
            user = dict(get_db().execute("SELECT * FROM users WHERE email = ?", ("sarah@example.com",)).fetchone())

        payload = build_seed_payload(user)
        payload["patient"].update({"dob": "1989-01-02", "sex": "Female", "phone": "555-0100"})
        payload["reasonForVisit"].update(
            {
                "chiefComplaint": "Headaches and neck pain after long shifts",
                "reasons": ["Pain / discomfort"],
                "onset": "4 months",
                "onsetType": "Gradually over time",
            }
        )
        payload["pain"].update({"areas": ["Neck", "Head"], "currentLevel": 6, "worstLevel": 8})
        payload["functionalOutcomeMeasures"].update(
            {
                "schemaVersion": "2026-03-odi-slider",
                "questionnaireSchemas": {
                    "odi": {
                        "responseModel": "continuous_0_to_10",
                        "scaleMin": 0,
                        "scaleMax": 10,
                        "optionalSectionTitles": ["Sex Life"],
                        "version": "2.2",
                    }
                },
                "questionnaires": [
                    {
                        "questionnaireId": "odi",
                        "displayName": "Oswestry Disability Index (ODI)",
                        "version": "2.2",
                        "completedAt": iso_now(),
                        "rawScore": 36.5,
                        "percent": 36.5,
                        "interpretation": "Moderate Disability",
                        "responseModel": "continuous_0_to_10",
                        "responses": [
                            {
                                "questionId": "odi_q0",
                                "prompt": "Pain Intensity",
                                "responseType": "slider",
                                "scaleMin": 0,
                                "scaleMax": 10,
                                "selectedValue": 3.5,
                                "selectedLabel": "Fairly severe pain",
                            },
                            {
                                "questionId": "odi_q7",
                                "prompt": "Sex Life",
                                "subtitle": "if applicable",
                                "responseType": "slider",
                                "scaleMin": 0,
                                "scaleMax": 10,
                                "selectedValue": None,
                                "selectedLabel": None,
                                "skipped": True,
                            },
                        ],
                    }
                ],
            }
        )
        payload["consent"].update(
            {
                "chiropracticCare": True,
                "privacyNotice": True,
                "accuracyConfirmation": True,
                "signature": "Sarah Mitchell",
                "signatureDate": date.today().isoformat(),
            }
        )

        response = self.client.post("/api/intake", json={"status": "submitted", "payload": payload})
        self.assertEqual(response.status_code, 200)
        self.assertIn("/results", response.get_data(as_text=True))

        with self.app.app_context():
            stored_row = get_db().execute(
                "SELECT payload_json FROM intake_submissions WHERE user_id = ?",
                (user["id"],),
            ).fetchone()
            self.assertIsNotNone(stored_row)
            stored_payload = json.loads(stored_row["payload_json"])
            functional_schema = stored_payload.get("functionalOutcomeMeasures", {})
            self.assertEqual(functional_schema.get("schemaVersion"), "2026-03-odi-slider")
            self.assertIn("odi", (functional_schema.get("questionnaireSchemas") or {}))

            questionnaire_row = get_db().execute(
                """
                SELECT questionnaire_id, response_model, percent_score, interpretation
                FROM intake_questionnaire_scores
                WHERE user_id = ? AND questionnaire_id = 'odi'
                """,
                (user["id"],),
            ).fetchone()
            self.assertIsNotNone(questionnaire_row)
            self.assertEqual(questionnaire_row["questionnaire_id"], "odi")
            self.assertEqual(questionnaire_row["response_model"], "continuous_0_to_10")
            self.assertAlmostEqual(questionnaire_row["percent_score"], 36.5)
            self.assertEqual(questionnaire_row["interpretation"], "Moderate Disability")

        self.client.post("/logout", follow_redirects=True)
        self.login_staff()

        with self.app.app_context():
            db = get_db()
            patient = db.execute("SELECT * FROM users WHERE email = ?", ("sarah@example.com",)).fetchone()

        response = self.client.get(f"/staff/patients/{patient['id']}")
        self.assertEqual(response.status_code, 200)
        overview_html = response.get_data(as_text=True)
        self.assertIn("Headaches and neck pain after long shifts", overview_html)
        self.assertIn("Open Summit Assessment", overview_html)
        self.assertIn("Initial Consultation", overview_html)
        self.assertIn("Available time slot", overview_html)
        self.assertIn("Chiropractor", overview_html)

        response = self.client.get(f"/staff/patients/{patient['id']}/summit-assessment")
        self.assertEqual(response.status_code, 200)
        assessment_html = response.get_data(as_text=True)
        self.assertIn("Summit complete assessment", assessment_html)
        self.assertIn("Dedicated chiropractor assessment workspace", assessment_html)
        self.assertIn("DDx + Tx Tool", assessment_html)
        self.assertIn("ddxImportBanner", assessment_html)

        response = self.client.get(f"/staff/patients/{patient['id']}/decision-support")
        self.assertEqual(response.status_code, 200)
        decision_support_html = response.get_data(as_text=True)
        self.assertIn("Bayesian DDx + treatment planner", decision_support_html)
        self.assertIn("Loading the Claude decision-support artifact", decision_support_html)
        self.assertIn("/staff/tools/claude-ddx-tool.jsx", decision_support_html)
        self.assertIn("/static/vendor/react.production.min.js", decision_support_html)
        self.assertIn("/static/vendor/react-dom.production.min.js", decision_support_html)
        self.assertIn("/static/vendor/babel.min.js", decision_support_html)
        self.assertIn("storageKey", decision_support_html)

        response = self.client.get("/staff/tools/claude-ddx-tool.jsx")
        self.assertEqual(response.status_code, 200)
        artifact_source = response.get_data(as_text=True)
        self.assertIn("const { useState, useMemo } = React;", artifact_source)
        self.assertIn('ReactDOM.createRoot(document.getElementById("claude-artifact-root"))', artifact_source)
        self.assertIn("window.localStorage.setItem", artifact_source)
        self.assertIn("Send to Summit Assessment", artifact_source)

        response = self.client.post(
            f"/staff/patients/{patient['id']}/initial-consult",
            data={
                "action": "published",
                "redirect_to": "assessment",
                "visit_date": initial_consult_start,
                "assessment_date": initial_consult_start[:10],
                "referring_provider": "Dr. Walsh",
                "patient_goals": "Reduce headaches\nReturn to regular gym sessions",
                "history_chief_complaint": "Headaches and neck pain after long shifts",
                "history_duration_years": "2.0",
                "history_occupation": "Nurse",
                "history_work_hours": "12-hour shifts",
                "history_pain_level": "8",
                "history_frequency": "4",
                "history_notes": "Pain builds during long nursing shifts and eases slightly with rest.",
                "first_notice": "Intermittently over the last 2 years",
                "pain_quality": "Sharp and throbbing at the end of a long shift",
                "radiates": "on",
                "radiation_start": "Base of neck",
                "radiation_end": "Left temple",
                "accident_history": "Rear-end collision in 2021 with no fracture but ongoing neck stiffness afterward.",
                "microtrauma_history": "Twelve-hour nursing shifts with repeated patient transfers and computer charting.",
                "prior_treatment_history": "Tried massage, ibuprofen, and stretching with only short-term relief.",
                "symptom_trend": "Getting worse in both intensity and frequency.",
                "adl_impacts": "Headaches reduce concentration during charting and limit gym training after work.",
                "medical_family_history_review": "No red flags. Mother also has chronic neck tension and forward-head posture.",
                "commitment_score": "9",
                "obstacles_to_care": "Shift schedule is the main barrier to regular appointments.",
                "education_summary": "Reviewed posture, spinal alignment, and how nerve irritation can contribute to headache patterns.",
                "grip_left_kg": "29.5",
                "grip_right_kg": "31.0",
                "balance_left_sec": "18",
                "balance_right_sec": "24",
                "chair_stand_reps_30s": "11",
                "gait_speed_time_10m": "8.5",
                "srt_sit_score": "4.0",
                "srt_rise_score": "3.5",
                "resting_hr_bpm": "74",
                "vo2_age": "37",
                "vo2_resting_hr": "74",
                "fingertip_floor_cm": "9.0",
                "marching_deviation_cm": "12",
                "marching_direction": "R",
                "heel_toe_steps": "8",
                "weight_left_kg": "31.5",
                "weight_right_kg": "35.0",
                "leg_left_cm": "39.9",
                "leg_right_cm": "40.7",
                "rom_cervical_flexion": "70",
                "rom_cervical_extension": "60",
                "rom_cervical_left_rotation": "62",
                "rom_cervical_right_rotation": "72",
                "rom_cervical_left_lateral_flexion": "28",
                "rom_cervical_right_lateral_flexion": "34",
                "rom_lumbar_flexion": "78",
                "rom_lumbar_extension": "32",
                "rom_lumbar_left_rotation": "68",
                "rom_lumbar_right_rotation": "71",
                "rom_lumbar_left_lateral_flexion": "36",
                "rom_lumbar_right_lateral_flexion": "39",
                "rom_lumbar_sit_and_reach": "54",
                "ortho_cervical_0_result": "+",
                "ortho_cervical_0_side": "L",
                "ortho_cervical_0_notes": "Reproduced familiar neck pain with headache referral.",
                "ortho_lumbar_0_result": "+",
                "ortho_lumbar_0_side": "L",
                "ortho_lumbar_0_measure": "48",
                "ortho_si_0_result": "−",
                "ortho_si_0_side": "B",
                "spine_left_C5": "3",
                "spine_right_C5": "2",
                "spine_left_L4": "1",
                "spine_right_L4": "4",
                "posture_findings": "Forward head carriage and guarded upper thoracic posture.",
                "forward_head_inches": "2.5",
                "shoulders_level": "Right high",
                "hips_level": "Level",
                "neuro_findings": "Strength and sensation intact bilaterally.",
                "palpation_findings": "Hypertonicity in upper trapezius and levator scapulae.",
                "xray_recommended": "on",
                "xray_status": "Booked",
                "xray_regions": "Cervical AP/lateral",
                "imaging_review": "Cervical imaging booked to review alignment and rule out structural contributors.",
                "assessment": "Mechanical cervical dysfunction with associated cervicogenic headache pattern.",
                "diagnosis": "Mechanical neck pain\nCervicogenic headaches",
                "care_plan": "Twice weekly for two weeks, then reassess range of motion and headache frequency.",
                "home_care": "Gentle chin-tuck drills, hourly posture resets, and hydration target of 2L daily.",
                "follow_up_plan": "Re-test cervical rotation and headache frequency at visit 5.",
                "wrap_up_notes": "We will review the exam findings and imaging at the Report of Findings visit.",
                "triangle_handoff": "Front desk confirmed the next appointment and consent review.",
                "patient_summary": "Your exam suggests that restricted neck movement and muscle tension are contributing to both your neck pain and your headaches.",
                "patient_key_findings": "Your neck is not moving as freely to the left.\nMuscle tension is contributing to your headaches.",
                "patient_recommendations": "Do your posture reset every hour.\nKeep walking daily even on sore days.",
            },
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)
        assessment_html = response.get_data(as_text=True)
        self.assertIn("published to the patient portal", assessment_html)
        self.assertIn("Summit complete assessment", assessment_html)

        response = self.client.get(
            f"/staff/availability?date={rof_start[:10]}&clinician_user_id={staff_id}&location_id={main_location_id}&duration_minutes=30"
        )
        self.assertEqual(response.status_code, 200)
        availability_payload = response.get_json()
        self.assertTrue(any(item["value"] == rof_start for item in availability_payload["available_slots"]))
        self.assertTrue(any(item["time_label"] == "12:00 - 13:00" for item in availability_payload["downtime_windows"]))
        self.assertFalse(any(item["value"].endswith("T12:00") for item in availability_payload["available_slots"]))

        response = self.client.post(
            f"/staff/patients/{patient['id']}/appointments",
            data={
                "appointment_type": "report_of_findings",
                "clinician_user_id": str(staff_id),
                "location_id": str(main_location_id),
                "appointment_date": rof_start[:10],
                "duration_minutes": "30",
                "slot_start": rof_start,
                "patient_details": "Review report of findings, answer questions, and confirm the first treatment plan.",
                "note": "Review findings, deliver results, and perform first treatment.",
            },
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("Report of Findings scheduled", response.get_data(as_text=True))

        response = self.client.get(
            f"/staff/availability?date={rof_start[:10]}&clinician_user_id={staff_id}&location_id={main_location_id}&duration_minutes=30"
        )
        self.assertEqual(response.status_code, 200)
        availability_payload = response.get_json()
        self.assertFalse(any(item["value"] == rof_start for item in availability_payload["available_slots"]))

        response = self.client.post(
            f"/staff/patients/{patient['id']}/appointments",
            data={
                "appointment_type": "care_plan",
                "clinician_user_id": str(staff_id),
                "location_id": str(main_location_id),
                "appointment_date": care_plan_start[:10],
                "duration_minutes": "20",
                "slot_start": care_plan_start,
                "patient_details": "Adjustment visit booked from the care plan cadence.",
                "note": "Care plan visit to continue the adjustment schedule.",
                "repeat_count": "3",
                "repeat_every_days": "7",
            },
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("3 Care Plan Visit appointments scheduled", response.get_data(as_text=True))

        with self.app.app_context():
            db = get_db()
            rof_appointment = db.execute(
                """
                SELECT *
                FROM appointments
                WHERE patient_user_id = ? AND appointment_type = 'report_of_findings'
                ORDER BY starts_at ASC
                LIMIT 1
                """,
                (patient["id"],),
            ).fetchone()
            care_plan_appointments = db.execute(
                """
                SELECT *
                FROM appointments
                WHERE patient_user_id = ? AND appointment_type = 'care_plan'
                ORDER BY starts_at ASC
                """,
                (patient["id"],),
            ).fetchall()

        self.assertEqual(len(care_plan_appointments), 3)

        response = self.client.post(
            f"/staff/patients/{patient['id']}/appointments/{rof_appointment['id']}",
            data={
                "action": "save",
                "appointment_type": "report_of_findings",
                "status": "scheduled",
                "starts_at": rof_updated_start,
                "ends_at": rof_updated_end,
                "note": "Review findings, deliver results, first treatment, and answer questions.",
            },
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("Appointment updated", response.get_data(as_text=True))

        response = self.client.post(
            f"/staff/patients/{patient['id']}/appointments/{care_plan_appointments[1]['id']}",
            data={
                "action": "complete",
                "appointment_type": "care_plan",
                "status": "scheduled",
                "starts_at": care_plan_appointments[1]["starts_at"],
                "ends_at": care_plan_appointments[1]["ends_at"] or "",
                "note": care_plan_appointments[1]["note"],
            },
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("Appointment marked completed", response.get_data(as_text=True))

        response = self.client.post(
            f"/staff/patients/{patient['id']}/appointments/{care_plan_appointments[2]['id']}",
            data={
                "action": "cancel",
                "appointment_type": "care_plan",
                "status": "scheduled",
                "starts_at": care_plan_appointments[2]["starts_at"],
                "ends_at": care_plan_appointments[2]["ends_at"] or "",
                "note": care_plan_appointments[2]["note"],
            },
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("Appointment cancelled", response.get_data(as_text=True))

        response = self.client.get("/staff/calendar")
        self.assertEqual(response.status_code, 200)
        staff_calendar_html = response.get_data(as_text=True)
        self.assertIn("Appointment schedule", staff_calendar_html)
        self.assertIn("Report of Findings", staff_calendar_html)
        self.assertIn("Care Plan Visit", staff_calendar_html)
        self.assertIn("Sarah Mitchell", staff_calendar_html)
        self.assertIn("Reminder queue", staff_calendar_html)
        self.assertIn("Reminder due soon", staff_calendar_html)
        self.assertIn("Coming up this week", staff_calendar_html)
        self.assertIn("Send email", staff_calendar_html)
        self.assertIn("Send SMS", staff_calendar_html)
        self.assertIn("Weekly availability templates", staff_calendar_html)
        self.assertIn("Lunch downtime", staff_calendar_html)
        self.assertIn("North Branch", staff_calendar_html)
        self.assertIn("Clinic locations", staff_calendar_html)

        response = self.client.get("/dashboard")
        self.assertEqual(response.status_code, 200)
        practitioner_dashboard_html = response.get_data(as_text=True)
        self.assertIn("Practitioner dashboard", practitioner_dashboard_html)
        self.assertIn("My patients", practitioner_dashboard_html)
        self.assertIn("Sarah Mitchell", practitioner_dashboard_html)
        self.assertIn("SOAP charting queue", practitioner_dashboard_html)
        self.assertIn("Add SOAP note", practitioner_dashboard_html)

        response = self.client.get("/staff/dashboard")
        self.assertEqual(response.status_code, 200)
        staff_dashboard_html = response.get_data(as_text=True)
        self.assertIn("Reminder queue", staff_dashboard_html)
        self.assertIn("Reminder due soon", staff_dashboard_html)
        self.assertIn("Coming up this week", staff_dashboard_html)
        self.assertIn("Open reminder center", staff_dashboard_html)

        response = self.client.get(f"/staff/patients/{patient['id']}")
        self.assertEqual(response.status_code, 200)
        patient_detail_html = response.get_data(as_text=True)
        self.assertIn("Repeat count", patient_detail_html)
        self.assertIn("Reminder queue", patient_detail_html)
        self.assertIn("Review findings, deliver results, first treatment, and answer questions.", patient_detail_html)
        self.assertIn("Completed", patient_detail_html)
        self.assertIn("Cancelled", patient_detail_html)
        self.assertIn("Send email", patient_detail_html)
        self.assertIn("Send SMS", patient_detail_html)
        self.assertIn("Billing status", patient_detail_html)
        self.assertIn("Location", patient_detail_html)
        self.assertIn("Add SOAP note", patient_detail_html)

        response = self.client.get(f"/practitioner/appointments/{rof_appointment['id']}/soap")
        self.assertEqual(response.status_code, 200)
        soap_html = response.get_data(as_text=True)
        self.assertIn("Appointment SOAP note", soap_html)
        self.assertIn("Report of Findings", soap_html)
        self.assertIn("Sarah Mitchell", soap_html)
        self.assertIn("Spine dysfunction map", soap_html)
        self.assertIn(">C1<", soap_html)
        self.assertIn(">S5<", soap_html)

        response = self.client.post(
            f"/practitioner/appointments/{rof_appointment['id']}/soap",
            data={
                "subjective": "Headaches eased for two days after the initial treatment, but neck stiffness returned after a long shift.",
                "objective": "Cervical rotation improved slightly left and right. Upper trapezius tension still present on palpation.",
                "assessment": "Progressing, but prolonged nursing shifts continue to irritate the cervical region.",
                "plan": "Continue with the scheduled care plan, reinforce hourly posture resets, and re-check cervical rotation next visit.",
                "spine_findings_json": "{\"left\":[\"C5\",\"T2\"],\"right\":[\"L4\",\"S1\"]}",
            },
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)
        soap_html = response.get_data(as_text=True)
        self.assertIn("SOAP note saved for this appointment", soap_html)
        self.assertIn("Headaches eased for two days", soap_html)
        self.assertIn("Continue with the scheduled care plan", soap_html)

        with self.app.app_context():
            soap_row = get_db().execute(
                "SELECT spine_findings_json FROM appointment_soap_notes WHERE appointment_id = ?",
                (rof_appointment["id"],),
            ).fetchone()
            self.assertIsNotNone(soap_row)
            spine_payload = json.loads(soap_row["spine_findings_json"])
            self.assertEqual(spine_payload["left"], ["C5", "T2"])
            self.assertEqual(spine_payload["right"], ["L4", "S1"])

        response = self.client.post(
            f"/staff/appointments/{rof_appointment['id']}/send-reminder",
            data={"channel": "email", "next_url": "/staff/reminders"},
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)
        reminder_center_html = response.get_data(as_text=True)
        self.assertIn("Reminder processing complete", reminder_center_html)
        self.assertIn("Reminder center", reminder_center_html)
        self.assertIn("Recent delivery history", reminder_center_html)
        self.assertIn("sarah@example.com", reminder_center_html)
        self.assertIn("logged to outbox", reminder_center_html)

        response = self.client.post(
            f"/staff/appointments/{care_plan_appointments[0]['id']}/send-reminder",
            data={"channel": "sms", "next_url": "/staff/reminders"},
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)
        reminder_center_html = response.get_data(as_text=True)
        self.assertIn("Reminder center", reminder_center_html)
        self.assertIn("555-0100", reminder_center_html)
        self.assertIn("Open in device app", reminder_center_html)

        response = self.client.post(
            f"/staff/appointments/{rof_appointment['id']}/send-reminder",
            data={"channel": "email", "next_url": "/staff/reminders"},
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("already sent for this reminder window", response.get_data(as_text=True))

        with self.app.app_context():
            reminder_rows = get_db().execute(
                """
                SELECT channel, status, delivery_mode, recipient
                FROM appointment_reminders
                ORDER BY id ASC
                """
            ).fetchall()

        self.assertEqual(len(reminder_rows), 2)
        self.assertEqual(reminder_rows[0]["channel"], "email")
        self.assertEqual(reminder_rows[0]["status"], "logged")
        self.assertEqual(reminder_rows[0]["delivery_mode"], "outbox")
        self.assertEqual(reminder_rows[0]["recipient"], "sarah@example.com")
        self.assertEqual(reminder_rows[1]["channel"], "sms")
        self.assertEqual(reminder_rows[1]["status"], "logged")
        self.assertEqual(reminder_rows[1]["recipient"], "555-0100")

        response = self.client.get(f"/api/appointments?patient_user_id={patient['id']}")
        self.assertEqual(response.status_code, 200)
        staff_api_payload = response.get_json()
        self.assertTrue(staff_api_payload["ok"])
        self.assertTrue(any(item["location_name"] == "Main Clinic" for item in staff_api_payload["appointments"]))

        response = self.client.get(f"/staff/patients/{patient['id']}/results-preview")
        self.assertEqual(response.status_code, 200)
        preview_html = response.get_data(as_text=True)
        self.assertIn("Patient Portal Preview", preview_html)
        self.assertIn("Print report", preview_html)
        self.assertIn("Back to assessment", preview_html)
        self.assertIn("restricted neck movement and muscle tension", preview_html)

        response = self.client.post(
            f"/staff/patients/{patient['id']}/notes",
            data={
                "exam_findings": "Restricted cervical rotation and upper trap guarding.",
                "assessment": "Mechanical neck pain with headache referral pattern.",
                "care_plan": "6-visit trial with gentle adjustments and mobility work.",
                "next_visit_at": rof_updated_start,
                "internal_notes": "Prefers low-force techniques.",
            },
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("Clinician notes saved", response.get_data(as_text=True))

        self.client.post("/logout", follow_redirects=True)
        response = self.client.post(
            "/login",
            data={"email": "sarah@example.com", "password": "patientpass123"},
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)
        response = self.client.get("/results")
        self.assertEqual(response.status_code, 200)
        results_html = response.get_data(as_text=True)
        self.assertIn("Summit Complete Assessment", results_html)
        self.assertIn("restricted neck movement and muscle tension", results_html)
        self.assertIn("Twice weekly for two weeks", results_html)
        self.assertIn("Vital Health Indicators", results_html)
        self.assertIn("Grip Strength", results_html)
        self.assertIn("Spurling", results_html)
        self.assertIn("Cervical AP/lateral", results_html)

        response = self.client.get("/appointments")
        self.assertEqual(response.status_code, 200)
        appointments_html = response.get_data(as_text=True)
        self.assertIn("Your visit calendar", appointments_html)
        self.assertIn("Self-service booking", appointments_html)
        self.assertIn("Book available appointments 24/7", appointments_html)
        self.assertIn("Initial Consultation", appointments_html)
        self.assertIn("Report of Findings", appointments_html)
        self.assertIn("Care Plan Visit", appointments_html)
        self.assertIn("Review findings, deliver results, first treatment, and answer questions.", appointments_html)
        self.assertIn("Reminders due soon", appointments_html)
        self.assertIn("Reminder due soon", appointments_html)
        self.assertIn("Coming up this week", appointments_html)
        self.assertIn("Completed", appointments_html)
        self.assertIn("Cancelled", appointments_html)
        self.assertIn("Main Clinic", appointments_html)

        self_book_start, _ = self.appointment_slot(days_from_now=9, hour=10, minute=0, duration_minutes=20)
        response = self.client.get(
            f"/api/availability?date={self_book_start[:10]}&clinician_user_id={staff_id}&location_id={main_location_id}&duration_minutes=20"
        )
        self.assertEqual(response.status_code, 200)
        client_availability_payload = response.get_json()
        self.assertTrue(client_availability_payload["ok"])
        self.assertTrue(any(item["value"] == self_book_start for item in client_availability_payload["availability"]["available_slots"]))

        response = self.client.post(
            "/appointments/self-book",
            data={
                "appointment_type": "care_plan",
                "location_id": str(main_location_id),
                "clinician_user_id": str(staff_id),
                "appointment_date": self_book_start[:10],
                "duration_minutes": "20",
                "slot_start": self_book_start,
                "patient_details": "Booking from the portal for another care-plan visit.",
            },
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("Appointment booked from your portal", response.get_data(as_text=True))
        self.assertIn("Booking from the portal for another care-plan visit.", response.get_data(as_text=True))

        response = self.client.get("/api/appointments")
        self.assertEqual(response.status_code, 200)
        client_api_payload = response.get_json()
        self.assertTrue(client_api_payload["ok"])
        self.assertTrue(any(item["booking_source"] == "patient_portal" for item in client_api_payload["appointments"]))
        self.assertTrue(any(item["location_name"] == "Main Clinic" for item in client_api_payload["appointments"]))

        response = self.client.get("/api/locations")
        self.assertEqual(response.status_code, 200)
        locations_payload = response.get_json()
        self.assertTrue(locations_payload["ok"])
        self.assertTrue(any(item["slug"] == "north-branch" for item in locations_payload["locations"]))

        self.client.post("/logout", follow_redirects=True)
        response = self.client.post("/forgot-password", data={"email": "sarah@example.com"}, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn("One-time reset link", response.get_data(as_text=True))

        with self.app.app_context():
            token = get_db().execute(
                "SELECT token FROM password_reset_tokens ORDER BY id DESC LIMIT 1"
            ).fetchone()["token"]

        response = self.client.post(
            f"/reset-password/{token}",
            data={"password": "newpatientpass123", "confirm_password": "newpatientpass123"},
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("Password updated", response.get_data(as_text=True))

        response = self.client.post(
            "/login",
            data={"email": "sarah@example.com", "password": "newpatientpass123"},
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("your onboarding is ready", response.get_data(as_text=True))
        self.assertIn("Your dashboard is the home screen", response.get_data(as_text=True))
        self.assertIn("Open calendar", response.get_data(as_text=True))

    def test_public_consultation_request_creates_lead_and_invite_flow(self) -> None:
        staff_id = self.create_staff_user()
        with self.app.app_context():
            db = get_db()
            main_location_id = db.execute(
                "SELECT id FROM locations WHERE slug = 'main-clinic'"
            ).fetchone()["id"]

        preferred_start, _ = self.appointment_slot(days_from_now=5, hour=9, minute=15, duration_minutes=30)
        response = self.client.get(
            f"/api/public-availability?date={preferred_start[:10]}&clinician_user_id={staff_id}&location_id={main_location_id}"
        )
        self.assertEqual(response.status_code, 200)
        availability_payload = response.get_json()
        self.assertTrue(availability_payload["ok"])
        slot_value = availability_payload["availability"]["available_slots"][0]["value"]

        response = self.client.post(
            "/new-patient",
            data={
                "first_name": "Mia",
                "last_name": "Jordan",
                "email": "mia@example.com",
                "phone": "555-0200",
                "reason": "Neck pain and headaches after long desk work.",
                "source": "google",
                "location_id": str(main_location_id),
                "clinician_user_id": str(staff_id),
                "appointment_date": slot_value[:10],
                "slot_start": slot_value,
            },
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)
        invite_html = response.get_data(as_text=True)
        self.assertIn("reserved for 30 minutes", invite_html)
        self.assertIn("Finish setting up your account", invite_html)

        with self.app.app_context():
            db = get_db()
            lead = db.execute(
                "SELECT * FROM leads WHERE email = ? ORDER BY id DESC LIMIT 1",
                ("mia@example.com",),
            ).fetchone()
            invitation = db.execute(
                "SELECT * FROM invitations WHERE id = ?",
                (lead["invitation_id"],),
            ).fetchone()
            slot_hold = db.execute(
                "SELECT * FROM appointment_slot_holds WHERE invitation_id = ?",
                (lead["invitation_id"],),
            ).fetchone()
        self.assertIsNotNone(lead)
        self.assertEqual(lead["status"], "invited")
        self.assertEqual(lead["requested_starts_at"], slot_value)
        self.assertIsNotNone(invitation)
        self.assertIsNotNone(slot_hold)
        self.assertEqual(slot_hold["starts_at"], slot_value)
        self.assertEqual(slot_hold["status"], "active")

        response = self.client.get(
            f"/api/public-availability?date={preferred_start[:10]}&clinician_user_id={staff_id}&location_id={main_location_id}"
        )
        self.assertEqual(response.status_code, 200)
        availability_payload = response.get_json()
        self.assertFalse(any(item["value"] == slot_value for item in availability_payload["availability"]["available_slots"]))

        self.login_staff()
        response = self.client.get("/staff/dashboard")
        self.assertEqual(response.status_code, 200)
        staff_html = response.get_data(as_text=True)
        self.assertIn("New patient requests", staff_html)
        self.assertIn("Mia Jordan", staff_html)
        self.assertIn("Open invite", staff_html)

        self.client.post("/logout", follow_redirects=True)
        response = self.client.post(
            f"/invite/{invitation['token']}",
            data={"password": "patientpass123", "confirm_password": "patientpass123"},
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("Invitation accepted", response.get_data(as_text=True))

        with self.app.app_context():
            db = get_db()
            converted_lead = db.execute(
                "SELECT * FROM leads WHERE id = ?",
                (lead["id"],),
            ).fetchone()
            appointment = db.execute(
                "SELECT * FROM appointments WHERE source_invitation_id = ?",
                (invitation["id"],),
            ).fetchone()
            consumed_hold = db.execute(
                "SELECT * FROM appointment_slot_holds WHERE invitation_id = ?",
                (invitation["id"],),
            ).fetchone()
        self.assertEqual(converted_lead["status"], "converted")
        self.assertIsNotNone(converted_lead["converted_user_id"])
        self.assertIsNotNone(appointment)
        self.assertEqual(appointment["starts_at"], slot_value)
        self.assertEqual(consumed_hold["status"], "consumed")
        self.assertEqual(consumed_hold["consumed_appointment_id"], appointment["id"])

    def test_expired_public_slot_hold_releases_availability(self) -> None:
        staff_id = self.create_staff_user()
        with self.app.app_context():
            db = get_db()
            main_location_id = db.execute(
                "SELECT id FROM locations WHERE slug = 'main-clinic'"
            ).fetchone()["id"]

        preferred_start, _ = self.appointment_slot(days_from_now=6, hour=9, minute=30, duration_minutes=30)
        response = self.client.get(
            f"/api/public-availability?date={preferred_start[:10]}&clinician_user_id={staff_id}&location_id={main_location_id}"
        )
        self.assertEqual(response.status_code, 200)
        slot_value = response.get_json()["availability"]["available_slots"][0]["value"]

        response = self.client.post(
            "/new-patient",
            data={
                "first_name": "Ava",
                "last_name": "Reed",
                "email": "ava@example.com",
                "phone": "555-0222",
                "reason": "Low back pain after a gym strain.",
                "source": "website",
                "location_id": str(main_location_id),
                "clinician_user_id": str(staff_id),
                "appointment_date": slot_value[:10],
                "slot_start": slot_value,
            },
            follow_redirects=False,
        )
        self.assertEqual(response.status_code, 302)

        with self.app.app_context():
            db = get_db()
            invitation = db.execute(
                "SELECT * FROM invitations WHERE email = ? ORDER BY id DESC LIMIT 1",
                ("ava@example.com",),
            ).fetchone()
            db.execute(
                """
                UPDATE appointment_slot_holds
                SET expires_at = ?, updated_at = ?
                WHERE invitation_id = ?
                """,
                ("2000-01-01T00:00:00Z", iso_now(), invitation["id"]),
            )
            db.commit()

        response = self.client.get(
            f"/api/public-availability?date={preferred_start[:10]}&clinician_user_id={staff_id}&location_id={main_location_id}"
        )
        self.assertEqual(response.status_code, 200)
        availability_payload = response.get_json()
        self.assertTrue(any(item["value"] == slot_value for item in availability_payload["availability"]["available_slots"]))

        response = self.client.get(f"/invite/{invitation['token']}", follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn("Invitation unavailable", response.get_data(as_text=True))

    def test_client_dashboard_portal_summary(self) -> None:
        staff_id = self.create_staff_user()
        patient_id = self.create_client_user()
        report_visit_start, report_visit_end = self.appointment_slot(days_from_now=4, hour=11, minute=0, duration_minutes=30)

        with self.app.app_context():
            db = get_db()
            main_location_id = db.execute(
                "SELECT id FROM locations WHERE slug = 'main-clinic'"
            ).fetchone()["id"]
            now = iso_now()
            db.execute(
                """
                INSERT INTO intake_submissions (user_id, status, payload_json, created_at, updated_at)
                VALUES (?, 'submitted', ?, ?, ?)
                """,
                (
                    patient_id,
                    json.dumps({"patient": {"firstName": "Patient", "lastName": "One"}}),
                    now,
                    now,
                ),
            )
            db.execute(
                """
                INSERT INTO visit_reports (
                    patient_user_id,
                    clinician_user_id,
                    visit_kind,
                    report_status,
                    visit_date,
                    patient_summary,
                    care_plan,
                    patient_recommendations,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, 'initial_consult', 'published', ?, ?, ?, ?, ?, ?)
                """,
                (
                    patient_id,
                    staff_id,
                    report_visit_start[:10],
                    "Your neck and upper thoracic findings support a mechanical treatment plan.",
                    "Twice weekly care for three weeks, then reassess.",
                    "Keep walking daily and continue the posture reset drills.",
                    now,
                    now,
                ),
            )
            db.execute(
                """
                INSERT INTO appointments (
                    patient_user_id,
                    clinician_user_id,
                    location_id,
                    appointment_type,
                    status,
                    starts_at,
                    ends_at,
                    note,
                    patient_details,
                    booking_channel,
                    service_label_snapshot,
                    booking_source,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, 'report_of_findings', 'scheduled', ?, ?, ?, ?, 'staff', 'Report of Findings', 'staff_portal', ?, ?)
                """,
                (
                    patient_id,
                    staff_id,
                    main_location_id,
                    report_visit_start,
                    report_visit_end,
                    "Review findings and confirm the next stage of care.",
                    "Bring any questions about the plan so the clinic can answer them in person.",
                    now,
                    now,
                ),
            )
            db.execute(
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
                VALUES (?, ?, 'clinician', 'treatment', ?, ?, NULL, ?)
                """,
                (
                    patient_id,
                    staff_id,
                    "Please confirm you are comfortable with the updated care plan.",
                    now,
                    now,
                ),
            )
            db.commit()

        response = self.client.post(
            "/login",
            data={"email": "patient.one@example.com", "password": "patientpass123"},
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)

        response = self.client.get("/dashboard")
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn("Portal snapshot", html)
        self.assertIn("Care journey", html)
        self.assertIn("Read your 1 new message", html)
        self.assertIn("Recent messages", html)
        self.assertIn("Please confirm you are comfortable with the updated care plan.", html)
        self.assertIn("Published findings", html)
        self.assertIn("Upcoming visits", html)
        self.assertIn("Report of Findings", html)

        response = self.client.get("/api/client/dashboard")
        self.assertEqual(response.status_code, 200)
        dashboard_payload = response.get_json()["dashboard"]
        self.assertEqual(dashboard_payload["journey_state"], "plan_review")
        self.assertEqual(dashboard_payload["journey_summary"]["stage_label"], "Review recommendations")
        self.assertEqual(dashboard_payload["journey_summary"]["primary_action_url"], "/app/appointments")
        self.assertEqual(dashboard_payload["journey_summary"]["secondary_action_url"], "/app/results")

        response = self.client.get("/api/client/care-plan")
        self.assertEqual(response.status_code, 200)
        care_plan_payload = response.get_json()
        self.assertTrue(care_plan_payload["ok"])
        self.assertEqual(care_plan_payload["journey_state"], "plan_review")
        self.assertEqual(care_plan_payload["journey_summary"]["primary_action_label"], "Book next visit")

        response = self.client.get("/api/client/results")
        self.assertEqual(response.status_code, 200)
        results_payload = response.get_json()
        self.assertTrue(results_payload["ok"])
        self.assertEqual(results_payload["journey_state"], "plan_review")
        self.assertEqual(results_payload["journey_summary"]["secondary_action_url"], "/app/results")

    def test_client_dashboard_first_visit_journey_state(self) -> None:
        staff_id = self.create_staff_user()
        patient_id = self.create_client_user()
        initial_consult_start, initial_consult_end = self.appointment_slot(days_from_now=2, hour=9, minute=15)

        with self.app.app_context():
            db = get_db()
            main_location_id = db.execute(
                "SELECT id FROM locations WHERE slug = 'main-clinic'"
            ).fetchone()["id"]
            now = iso_now()
            db.execute(
                """
                INSERT INTO appointments (
                    patient_user_id,
                    clinician_user_id,
                    location_id,
                    appointment_type,
                    status,
                    starts_at,
                    ends_at,
                    booking_channel,
                    service_label_snapshot,
                    booking_source,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, 'initial_consult', 'scheduled', ?, ?, 'portal', 'Initial Consultation', 'patient_portal', ?, ?)
                """,
                (
                    patient_id,
                    staff_id,
                    main_location_id,
                    initial_consult_start,
                    initial_consult_end,
                    now,
                    now,
                ),
            )
            db.commit()

        self.login_client()

        response = self.client.get("/api/client/dashboard")
        self.assertEqual(response.status_code, 200)
        dashboard_payload = response.get_json()["dashboard"]
        self.assertEqual(dashboard_payload["journey_state"], "booked_first_visit")
        self.assertEqual(dashboard_payload["journey_summary"]["primary_action_url"], "/app/intake")
        self.assertEqual(dashboard_payload["journey_summary"]["secondary_action_url"], "/app/appointments")
        self.assertEqual(dashboard_payload["journey_summary"]["checklist"][0]["value"], "Initial Consultation")

        response = self.client.get("/api/client/appointments/context")
        self.assertEqual(response.status_code, 200)
        appointments_payload = response.get_json()
        self.assertTrue(appointments_payload["ok"])
        self.assertEqual(appointments_payload["journey_state"], "booked_first_visit")
        self.assertEqual(appointments_payload["journey_summary"]["primary_action_label"], "Start intake")

    def test_staff_care_plan_calendar_sync(self) -> None:
        staff_id = self.create_staff_user()
        self.login_staff()

        with self.app.app_context():
            db = get_db()
            patient_id = db.execute(
                """
                INSERT INTO users (first_name, last_name, email, password_hash, role, created_at)
                VALUES (?, ?, ?, ?, 'client', ?)
                """,
                (
                    "Mark",
                    "Hughes",
                    "mark@example.com",
                    generate_password_hash("patientpass123", method="pbkdf2:sha256"),
                    iso_now(),
                ),
            ).lastrowid
            main_location_id = db.execute(
                "SELECT id FROM locations WHERE slug = 'main-clinic'"
            ).fetchone()["id"]
            care_plan_service_id = db.execute(
                "SELECT id FROM appointment_services WHERE service_key = 'follow_up_15'"
            ).fetchone()["id"]
            db.commit()

        first_visit_start, _ = self.appointment_slot(days_from_now=4, hour=9, minute=15, duration_minutes=15)

        response = self.client.post(
            f"/staff/patients/{patient_id}/care-plan",
            data={
                "service_id": str(care_plan_service_id),
                "appointment_type": "care_plan",
                "clinician_user_id": str(staff_id),
                "location_id": str(main_location_id),
                "appointment_date": first_visit_start[:10],
                "duration_minutes": "15",
                "slot_increment_minutes": "15",
                "slot_start": first_visit_start,
                "patient_details": "Follow the 3-week reset care plan.",
                "note": "Generated from the care plan calendar.",
                "frequency_per_week": "2",
                "duration_weeks": "3",
                "care_plan_booking_mode": "as_you_go",
                "care_plan_title": "3-week reset",
            },
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn("Care plan created", html)
        self.assertIn("3-week reset", html)
        self.assertIn("Book next visit in live diary", html)
        self.assertIn("Load into diary", html)

        with self.app.app_context():
            db = get_db()
            care_plan = db.execute(
                "SELECT * FROM care_plans WHERE patient_user_id = ? ORDER BY id DESC LIMIT 1",
                (patient_id,),
            ).fetchone()
            visits = db.execute(
                "SELECT * FROM care_plan_visits WHERE care_plan_id = ? ORDER BY visit_number ASC",
                (care_plan["id"],),
            ).fetchall()
        self.assertIsNotNone(care_plan)
        self.assertEqual(care_plan["title"], "3-week reset")
        self.assertEqual(care_plan["total_visits"], 6)
        self.assertEqual(len(visits), 6)
        self.assertEqual(visits[0]["status"], "scheduled")
        self.assertEqual(visits[0]["booked"], 1)
        self.assertEqual(visits[2]["visit_kind"], "progress_check")
        self.assertEqual(visits[5]["visit_kind"], "reassessment")
        self.assertEqual(sum(1 for row in visits if row["status"] == "unbooked"), 5)

        next_visit = visits[1]
        next_visit_start = next_visit["suggested_starts_at"]
        response = self.client.post(
            f"/staff/patients/{patient_id}/appointments",
            data={
                "service_id": str(care_plan_service_id),
                "appointment_type": "care_plan",
                "clinician_user_id": str(staff_id),
                "location_id": str(main_location_id),
                "appointment_date": next_visit_start[:10],
                "duration_minutes": str(next_visit["duration_minutes"]),
                "slot_start": next_visit_start,
                "repeat_count": "1",
                "repeat_every_days": "7",
                "patient_details": next_visit["patient_details"],
                "note": next_visit["note"],
                "care_plan_visit_id": str(next_visit["id"]),
            },
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("Care Plan Visit (Visit 2) scheduled.", response.get_data(as_text=True))

        with self.app.app_context():
            db = get_db()
            linked_visit = db.execute(
                "SELECT * FROM care_plan_visits WHERE id = ?",
                (next_visit["id"],),
            ).fetchone()
            linked_appointment = db.execute(
                "SELECT * FROM appointments WHERE id = ?",
                (linked_visit["appointment_id"],),
            ).fetchone()
        self.assertEqual(linked_visit["status"], "scheduled")
        self.assertEqual(linked_visit["booked"], 1)
        self.assertIsNotNone(linked_appointment)

        response = self.client.post(
            f"/staff/patients/{patient_id}/appointments/{linked_appointment['id']}",
            data={
                "action": "complete",
                "appointment_type": "care_plan",
                "status": "scheduled",
                "location_id": str(main_location_id),
                "clinician_user_id": str(staff_id),
                "starts_at": linked_appointment["starts_at"],
                "ends_at": linked_appointment["ends_at"] or "",
                "note": linked_appointment["note"],
                "patient_details": linked_appointment["patient_details"],
                "clinical_note": linked_appointment["clinical_note"],
                "billing_status": linked_appointment["billing_status"],
                "billing_code": linked_appointment["billing_code"],
                "billing_amount": linked_appointment["billing_amount"] if linked_appointment["billing_amount"] is not None else "",
            },
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("Appointment marked completed", response.get_data(as_text=True))

        with self.app.app_context():
            synced_visit = get_db().execute(
                "SELECT status FROM care_plan_visits WHERE id = ?",
                (next_visit["id"],),
            ).fetchone()
        self.assertEqual(synced_visit["status"], "completed")

        overdue_visit = visits[2]
        overdue_date = (date.today() - timedelta(days=2)).isoformat()
        with self.app.app_context():
            db = get_db()
            db.execute(
                """
                UPDATE care_plan_visits
                SET suggested_date = ?,
                    suggested_starts_at = ?,
                    updated_at = ?
                WHERE id = ?
                """,
                (
                    overdue_date,
                    f"{overdue_date}T09:00",
                    iso_now(),
                    overdue_visit["id"],
                ),
            )
            db.commit()

        self.client.post("/logout", follow_redirects=True)
        response = self.client.post(
            "/login",
            data={"email": "mark@example.com", "password": "patientpass123"},
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)
        dashboard_html = response.get_data(as_text=True)
        self.assertIn("Client dashboard", dashboard_html)
        self.assertIn("You&#39;re due for your next visit", dashboard_html)
        self.assertIn("Book next visit", dashboard_html)

        response = self.client.get(f"/appointments?care_plan_visit_id={overdue_visit['id']}")
        self.assertEqual(response.status_code, 200)
        appointments_html = response.get_data(as_text=True)
        self.assertIn("Your next recommended care-plan visit is already loaded below.", appointments_html)
        self.assertIn("Visit 3 - Progress Check", appointments_html)
        booking_date_match = re.search(r'id="patientBookingDate" value="([^"]+)"', appointments_html)
        self.assertIsNotNone(booking_date_match)
        booking_date = booking_date_match.group(1)
        self.assertNotEqual(booking_date, overdue_date)
        self.assertGreaterEqual(booking_date, date.today().isoformat())

        response = self.client.get(
            f"/api/availability?date={booking_date}&clinician_user_id={staff_id}&location_id={main_location_id}&service_id={care_plan_service_id}&appointment_type=care_plan&duration_minutes={overdue_visit['duration_minutes']}&care_plan_visit_id={overdue_visit['id']}"
        )
        self.assertEqual(response.status_code, 200)
        availability_payload = response.get_json()
        self.assertTrue(availability_payload["ok"])
        self.assertTrue(availability_payload["availability"]["available_slots"])
        selected_slot = availability_payload["availability"]["available_slots"][0]["value"]

        response = self.client.post(
            "/appointments/self-book",
            data={
                "service_id": str(care_plan_service_id),
                "appointment_type": "care_plan",
                "clinician_user_id": str(staff_id),
                "location_id": str(main_location_id),
                "appointment_date": booking_date,
                "duration_minutes": str(overdue_visit["duration_minutes"]),
                "slot_start": selected_slot,
                "patient_details": "Booked from the portal as the next care-plan step.",
                "care_plan_visit_id": str(overdue_visit["id"]),
            },
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)
        booked_html = response.get_data(as_text=True)
        self.assertIn("Your next recommended care-plan visit is booked.", booked_html)

        with self.app.app_context():
            db = get_db()
            rebooked_visit = db.execute(
                "SELECT status, booked, appointment_id FROM care_plan_visits WHERE id = ?",
                (overdue_visit["id"],),
            ).fetchone()
            rebooked_appointment = db.execute(
                "SELECT * FROM appointments WHERE id = ?",
                (rebooked_visit["appointment_id"],),
            ).fetchone()
            first_plan_visit = db.execute(
                "SELECT status, booked, appointment_id FROM care_plan_visits WHERE id = ?",
                (visits[0]["id"],),
            ).fetchone()
            first_plan_appointment = db.execute(
                "SELECT * FROM appointments WHERE id = ?",
                (first_plan_visit["appointment_id"],),
            ).fetchone()
        self.assertEqual(rebooked_visit["status"], "scheduled")
        self.assertEqual(rebooked_visit["booked"], 1)
        self.assertIsNotNone(rebooked_appointment)
        self.assertEqual(first_plan_visit["status"], "scheduled")
        self.assertEqual(first_plan_visit["booked"], 1)
        self.assertIsNotNone(first_plan_appointment)

        response = self.client.post(
            f"/appointments/{first_plan_appointment['id']}/cancel",
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)
        cancelled_html = response.get_data(as_text=True)
        self.assertIn("Appointment cancelled. Choose a new time to stay on track with your care plan.", cancelled_html)
        self.assertIn(f'name="care_plan_visit_id" value="{visits[0]["id"]}"', cancelled_html)
        self.assertIn("Your next recommended care-plan visit is already loaded below.", cancelled_html)

        with self.app.app_context():
            reopened_visit = get_db().execute(
                "SELECT status, booked, appointment_id FROM care_plan_visits WHERE id = ?",
                (visits[0]["id"],),
            ).fetchone()
        self.assertEqual(reopened_visit["status"], "unbooked")
        self.assertEqual(reopened_visit["booked"], 0)
        self.assertIsNone(reopened_visit["appointment_id"])

        self.client.post("/logout", follow_redirects=True)
        self.login_staff()
        response = self.client.get("/staff/dashboard")
        self.assertEqual(response.status_code, 200)
        staff_dashboard_html = response.get_data(as_text=True)
        self.assertIn("Care-plan follow-up", staff_dashboard_html)
        self.assertIn("Mark Hughes", staff_dashboard_html)

    def test_react_client_portal_shell_and_session_api(self) -> None:
        self.create_client_user()
        self.login_client()

        response = self.client.get("/app")
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn("react-portal-root", html)
        self.assertIn("/api/client/session", html)
        self.assertIn("/static/react-portal/portal.js", html)

        response = self.client.get("/api/client/session")
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["user"]["email"], "patient.one@example.com")
        self.assertTrue(any(item["label"] == "Care Plan" for item in payload["nav"]))
        self.assertTrue(any(item["url"] == "/app/results" for item in payload["nav"]))
        self.assertTrue(any(item["url"] == "/app/intake" for item in payload["nav"]))

        response = self.client.get("/api/client/results")
        self.assertEqual(response.status_code, 409)
        results_payload = response.get_json()
        self.assertFalse(results_payload["ok"])
        self.assertEqual(results_payload["redirect"], "/intake")

        response = self.client.get("/app/intake")
        self.assertEqual(response.status_code, 200)
        intake_html = response.get_data(as_text=True)
        self.assertIn("/intake/embed", intake_html)

        response = self.client.get("/intake/embed")
        self.assertEqual(response.status_code, 200)
        embedded_html = response.get_data(as_text=True)
        self.assertIn('class="embed-mode"', embedded_html)

    def test_react_staff_portal_shell_and_session_api(self) -> None:
        self.create_staff_user()
        self.login_staff()

        response = self.client.get("/staff/app")
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn("react-portal-root", html)
        self.assertIn('data-portal-kind="staff"', html)
        self.assertIn("/api/staff/session", html)
        self.assertIn("/api/staff/dashboard", html)

        response = self.client.get("/api/staff/session")
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["user"]["email"], "staff@example.com")
        self.assertTrue(any(item["url"] == "/staff/app/calendar" for item in payload["nav"]))
        self.assertTrue(any(item["url"] == "/staff/app/clinic-ops" for item in payload["nav"]))

        response = self.client.get("/api/staff/dashboard")
        self.assertEqual(response.status_code, 200)
        dashboard_payload = response.get_json()
        self.assertTrue(dashboard_payload["ok"])
        self.assertEqual(dashboard_payload["view"], "practitioner")

        response = self.client.get("/staff/calendar?embed=1")
        self.assertEqual(response.status_code, 200)
        embedded_html = response.get_data(as_text=True)
        self.assertIn("embedded-frame", embedded_html)
        self.assertNotIn("app-sidebar", embedded_html)

    def test_react_staff_messaging_api_and_portal(self) -> None:
        self.create_staff_user()
        with self.app.app_context():
            db = get_db()
            db.execute(
                """
                INSERT INTO users (first_name, last_name, email, password_hash, role, created_at)
                VALUES (?, ?, ?, ?, 'client', ?)
                """,
                ("Mila", "Hart", "mila@example.com", generate_password_hash("patientpass123", method="pbkdf2:sha256"), iso_now()),
            )
            patient_user_id = db.execute(
                "SELECT id FROM users WHERE email = ?",
                ("mila@example.com",),
            ).fetchone()["id"]
            db.execute(
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
                VALUES (?, ?, 'client', 'symptoms', ?, NULL, ?, ?)
                """,
                (
                    patient_user_id,
                    patient_user_id,
                    "Morning stiffness is worse after long drives.",
                    iso_now(),
                    iso_now(),
                ),
            )
            db.commit()

        self.login_staff()

        response = self.client.get("/staff/app/messaging")
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn("react-portal-root", html)
        self.assertIn("/api/staff/messages", html)

        response = self.client.get(f"/api/staff/messages?patient_id={patient_user_id}")
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["selected_patient"]["full_name"], "Mila Hart")
        self.assertEqual(payload["unread_before_open"], 1)
        self.assertEqual(payload["threads"][0]["unread_for_staff"], 0)
        self.assertIn("Morning stiffness is worse after long drives.", payload["messages"][0]["body"])

        response = self.client.post(
            f"/api/staff/messages/{patient_user_id}",
            json={"topic": "appointment", "body": "Please book your reassessment for next week."},
        )
        self.assertEqual(response.status_code, 201)
        post_payload = response.get_json()
        self.assertTrue(post_payload["ok"])
        self.assertEqual(post_payload["message"], "Message sent to patient.")
        self.assertTrue(any(item["body"] == "Please book your reassessment for next week." for item in post_payload["messages"]))

    def test_react_staff_calendar_api_and_reminder_actions(self) -> None:
        staff_id = self.create_staff_user()
        with self.app.app_context():
            db = get_db()
            patient_id = db.execute(
                """
                INSERT INTO users (first_name, last_name, email, password_hash, role, created_at)
                VALUES (?, ?, ?, ?, 'client', ?)
                """,
                (
                    "Liam",
                    "Shore",
                    "liam@example.com",
                    generate_password_hash("patientpass123", method="pbkdf2:sha256"),
                    iso_now(),
                ),
            ).lastrowid
            main_location_id = db.execute(
                "SELECT id FROM locations WHERE slug = 'main-clinic'"
            ).fetchone()["id"]
            start_at, end_at = self.appointment_slot(days_from_now=2, hour=10, minute=0)
            appointment_id = db.execute(
                """
                INSERT INTO appointments (
                    patient_user_id,
                    clinician_user_id,
                    location_id,
                    appointment_type,
                    status,
                    starts_at,
                    ends_at,
                    note,
                    patient_details,
                    booking_channel,
                    service_label_snapshot,
                    booking_source,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, 'report_of_findings', 'scheduled', ?, ?, ?, ?, 'staff', 'Report of Findings', 'staff_portal', ?, ?)
                """,
                (
                    patient_id,
                    staff_id,
                    main_location_id,
                    start_at,
                    end_at,
                    "Discuss findings and confirm next stage of care.",
                    "Patient requested the earliest available review.",
                    iso_now(),
                    iso_now(),
                ),
            ).lastrowid
            db.commit()

        self.login_staff()

        response = self.client.get("/staff/app/calendar")
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn("react-portal-root", html)
        self.assertIn("/api/staff/calendar", html)

        response = self.client.get(f"/api/staff/calendar?month={start_at[:7]}")
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["calendar"]["month_value"], start_at[:7])
        self.assertTrue(any(item["patient_name"] == "Liam Shore" for item in payload["upcoming"]))
        self.assertTrue(any(item["id"] == appointment_id for item in payload["reminders"]))

        response = self.client.post(
            f"/api/staff/appointments/{appointment_id}/send-reminder",
            json={"channel": "email"},
        )
        self.assertEqual(response.status_code, 200)
        reminder_payload = response.get_json()
        self.assertTrue(reminder_payload["ok"])
        self.assertIn("Reminder processing complete", reminder_payload["message"])

        response = self.client.post(
            f"/api/staff/appointments/{appointment_id}/send-reminder",
            json={"channel": "email"},
        )
        self.assertEqual(response.status_code, 400)
        duplicate_payload = response.get_json()
        self.assertFalse(duplicate_payload["ok"])
        self.assertIn("already sent for this reminder window", duplicate_payload["message"])

    def test_react_staff_reminders_api_and_portal(self) -> None:
        staff_id = self.create_staff_user()
        with self.app.app_context():
            db = get_db()
            patient_id = db.execute(
                """
                INSERT INTO users (first_name, last_name, email, password_hash, role, created_at)
                VALUES (?, ?, ?, ?, 'client', ?)
                """,
                (
                    "Ava",
                    "North",
                    "ava@example.com",
                    generate_password_hash("patientpass123", method="pbkdf2:sha256"),
                    iso_now(),
                ),
            ).lastrowid
            main_location_id = db.execute(
                "SELECT id FROM locations WHERE slug = 'main-clinic'"
            ).fetchone()["id"]
            start_at, end_at = self.appointment_slot(days_from_now=1, hour=15, minute=0)
            appointment_id = db.execute(
                """
                INSERT INTO appointments (
                    patient_user_id,
                    clinician_user_id,
                    location_id,
                    appointment_type,
                    status,
                    starts_at,
                    ends_at,
                    note,
                    patient_details,
                    booking_channel,
                    service_label_snapshot,
                    booking_source,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, 'care_plan', 'scheduled', ?, ?, ?, ?, 'staff', 'Care Plan Visit', 'staff_portal', ?, ?)
                """,
                (
                    patient_id,
                    staff_id,
                    main_location_id,
                    start_at,
                    end_at,
                    "Recheck mobility and continue plan cadence.",
                    "Patient prefers afternoon slots.",
                    iso_now(),
                    iso_now(),
                ),
            ).lastrowid
            db.commit()

        self.login_staff()

        response = self.client.get("/staff/app/reminders")
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn("react-portal-root", html)
        self.assertIn("/api/staff/reminders", html)

        response = self.client.get("/api/staff/reminders")
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["reminders"]["routes"]["spa_root"], "/staff/app/reminders")
        self.assertTrue(any(item["id"] == appointment_id for item in payload["reminders"]["due_reminders"]))

        response = self.client.post(
            f"/api/staff/appointments/{appointment_id}/send-reminder",
            json={"channel": "email"},
        )
        self.assertEqual(response.status_code, 200)
        reminder_payload = response.get_json()
        self.assertTrue(reminder_payload["ok"])

        response = self.client.get("/api/staff/reminders")
        self.assertEqual(response.status_code, 200)
        refreshed_payload = response.get_json()
        self.assertTrue(
            any(item["appointment_id"] == appointment_id for item in refreshed_payload["reminders"]["recent_deliveries"])
        )
        self.assertGreaterEqual(
            refreshed_payload["reminders"]["delivery_counts"]["logged"] + refreshed_payload["reminders"]["delivery_counts"]["sent"],
            1,
        )

    def test_staff_recurring_availability_and_duration_controls_drive_patient_slots(self) -> None:
        staff_id = self.create_staff_user()
        self.login_staff()

        with self.app.app_context():
            db = get_db()
            location_id = db.execute(
                """
                INSERT INTO locations (name, slug, address, phone, timezone, active, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, 1, ?, ?)
                """,
                (
                    "Booking Test Clinic",
                    "booking-test-clinic",
                    "1 Test Street",
                    "555-0606",
                    "Europe/London",
                    iso_now(),
                    iso_now(),
                ),
            ).lastrowid
            service_id = db.execute(
                "SELECT id FROM appointment_services WHERE service_key = 'follow_up_15' LIMIT 1"
            ).fetchone()["id"]
            target_date = date.today() + timedelta(days=3)
            db.commit()

        response = self.client.post(
            "/api/staff/schedule-windows",
            json={
                "clinician_user_id": staff_id,
                "location_id": location_id,
                "weekday": target_date.weekday(),
                "window_type": "shift",
                "starts_time": "09:00",
                "ends_time": "10:00",
                "label": "Morning clinic",
            },
        )
        self.assertEqual(response.status_code, 201)
        availability_payload = response.get_json()
        self.assertTrue(availability_payload["ok"])
        self.assertEqual(availability_payload["window"]["clinician_user_id"], staff_id)

        response = self.client.get(
            f"/api/availability?date={target_date.isoformat()}&clinician_user_id={staff_id}&location_id={location_id}&service_id={service_id}"
        )
        self.assertEqual(response.status_code, 200)
        availability_before = response.get_json()["availability"]
        self.assertEqual(len(availability_before["available_slots"]), 2)

        response = self.client.post(
            f"/api/staff/booking-services/{service_id}/duration",
            json={"duration_minutes": 30},
        )
        self.assertEqual(response.status_code, 200)
        duration_payload = response.get_json()
        self.assertTrue(duration_payload["ok"])
        self.assertEqual(duration_payload["service"]["duration_minutes"], 30)

        response = self.client.get(
            f"/api/availability?date={target_date.isoformat()}&clinician_user_id={staff_id}&location_id={location_id}&service_id={service_id}"
        )
        self.assertEqual(response.status_code, 200)
        availability_after = response.get_json()["availability"]
        self.assertEqual(len(availability_after["available_slots"]), 1)

        response = self.client.post(
            f"/api/staff/schedule-windows/{availability_payload['window']['id']}/delete",
            json={},
        )
        self.assertEqual(response.status_code, 200)
        removed_payload = response.get_json()
        self.assertTrue(removed_payload["ok"])

        response = self.client.get(
            f"/api/availability?date={target_date.isoformat()}&clinician_user_id={staff_id}&location_id={location_id}&service_id={service_id}"
        )
        self.assertEqual(response.status_code, 200)
        availability_removed = response.get_json()["availability"]
        self.assertEqual(len(availability_removed["available_slots"]), 0)

    def test_react_staff_settings_api_and_return_redirect(self) -> None:
        self.create_staff_user()
        self.login_staff()

        response = self.client.get("/staff/app/settings")
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn("react-portal-root", html)
        self.assertIn("/api/staff/settings", html)

        response = self.client.get("/api/staff/settings")
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertTrue(payload["ok"])
        self.assertIn("app_settings", payload["settings"])
        self.assertEqual(payload["settings"]["routes"]["spa_root"], "/staff/app/settings")

        response = self.client.post(
            "/staff/settings/preferences/appearance",
            data={
                "return_to": "react_settings",
                "section": "appearance",
                "appearance_theme": "light",
                "appearance_brand_color": "#2f6f4f",
                "appearance_font_style": "clean",
                "appearance_show_portal_branding": "on",
            },
            follow_redirects=False,
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.headers["Location"].endswith("/staff/app/settings?section=appearance"))

        with self.app.app_context():
            stored = get_db().execute(
                "SELECT setting_value FROM app_settings WHERE setting_key = 'appearance_brand_color'"
            ).fetchone()
            self.assertEqual(stored["setting_value"], "#2f6f4f")

    def test_react_staff_invitation_api_and_portal(self) -> None:
        staff_id = self.create_staff_user()
        with self.app.app_context():
            db = get_db()
            main_location_id = db.execute(
                "SELECT id FROM locations WHERE slug = 'main-clinic'"
            ).fetchone()["id"]
            initial_service_id = db.execute(
                "SELECT id FROM appointment_services WHERE service_key = 'new_patient_30'"
            ).fetchone()["id"]
            requested_start, _requested_end = self.appointment_slot(days_from_now=3, hour=11, minute=15)
            lead_id = db.execute(
                """
                INSERT INTO leads (
                    first_name,
                    last_name,
                    email,
                    phone,
                    source,
                    preferred_service_id,
                    preferred_location_id,
                    preferred_clinician_user_id,
                    requested_starts_at,
                    reason,
                    notes,
                    status,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'new', ?, ?)
                """,
                (
                    "Eva",
                    "North",
                    "eva@example.com",
                    "555-0171",
                    "website",
                    initial_service_id,
                    main_location_id,
                    staff_id,
                    requested_start,
                    "Neck pain after commuting.",
                    "",
                    iso_now(),
                    iso_now(),
                ),
            ).lastrowid
            db.commit()

        self.login_staff()

        response = self.client.get("/staff/app/new-invite")
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn("react-portal-root", html)
        self.assertIn("/api/staff/invitations/new", html)

        response = self.client.get(f"/api/staff/invitations/new?lead_id={lead_id}")
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["linked_lead"]["full_name"], "Eva North")
        self.assertEqual(payload["invite_prefill"]["appointment_at"], requested_start)
        self.assertTrue(any(item["id"] == lead_id for item in payload["open_leads"]))

        response = self.client.post(
            "/api/staff/invitations",
            json={
                "lead_id": str(lead_id),
                "first_name": "Eva",
                "last_name": "North",
                "email": "eva@example.com",
                "appointment_at": requested_start,
                "note": "Please arrive 10 minutes early.",
            },
        )
        self.assertEqual(response.status_code, 201)
        create_payload = response.get_json()
        self.assertTrue(create_payload["ok"])
        self.assertEqual(create_payload["message"], "Invitation created from the lead request.")
        self.assertEqual(create_payload["created_invitation"]["email"], "eva@example.com")
        self.assertIn("/invite/", create_payload["created_invitation"]["accept_url"])
        self.assertIsNotNone(create_payload["created_slot_hold"])

        with self.app.app_context():
            db = get_db()
            lead_row = db.execute(
                "SELECT status, invitation_id FROM leads WHERE id = ?",
                (lead_id,),
            ).fetchone()
            self.assertEqual(lead_row["status"], "invited")
            self.assertIsNotNone(lead_row["invitation_id"])

    def test_api_appointments_books_care_plan_visit_for_react_portal(self) -> None:
        staff_id = self.create_staff_user()
        self.login_staff()

        with self.app.app_context():
            db = get_db()
            patient_id = db.execute(
                """
                INSERT INTO users (first_name, last_name, email, password_hash, role, created_at)
                VALUES (?, ?, ?, ?, 'client', ?)
                """,
                (
                    "Leah",
                    "Rowe",
                    "leah@example.com",
                    generate_password_hash("patientpass123", method="pbkdf2:sha256"),
                    iso_now(),
                ),
            ).lastrowid
            main_location_id = db.execute(
                "SELECT id FROM locations WHERE slug = 'main-clinic'"
            ).fetchone()["id"]
            care_plan_service_id = db.execute(
                "SELECT id FROM appointment_services WHERE service_key = 'follow_up_15'"
            ).fetchone()["id"]
            db.commit()

        first_visit_start, _ = self.appointment_slot(days_from_now=4, hour=10, minute=0, duration_minutes=15)

        response = self.client.post(
            f"/staff/patients/{patient_id}/care-plan",
            data={
                "service_id": str(care_plan_service_id),
                "appointment_type": "care_plan",
                "clinician_user_id": str(staff_id),
                "location_id": str(main_location_id),
                "appointment_date": first_visit_start[:10],
                "duration_minutes": "15",
                "slot_increment_minutes": "15",
                "slot_start": first_visit_start,
                "patient_details": "Follow the reset plan.",
                "note": "Generated from the care plan calendar.",
                "frequency_per_week": "2",
                "duration_weeks": "3",
                "care_plan_booking_mode": "as_you_go",
                "care_plan_title": "Reset plan",
            },
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("Care plan created", response.get_data(as_text=True))

        with self.app.app_context():
            db = get_db()
            care_plan = db.execute(
                "SELECT id FROM care_plans WHERE patient_user_id = ? ORDER BY id DESC LIMIT 1",
                (patient_id,),
            ).fetchone()
            overdue_visit = db.execute(
                """
                SELECT *
                FROM care_plan_visits
                WHERE care_plan_id = ? AND status = 'unbooked'
                ORDER BY visit_number ASC
                LIMIT 1
                """,
                (care_plan["id"],),
            ).fetchone()
            self.assertIsNotNone(overdue_visit)
            overdue_date = (date.today() - timedelta(days=1)).isoformat()
            db.execute(
                """
                UPDATE care_plan_visits
                SET suggested_date = ?,
                    suggested_starts_at = ?,
                    updated_at = ?
                WHERE id = ?
                """,
                (
                    overdue_date,
                    f"{overdue_date}T09:00",
                    iso_now(),
                    overdue_visit["id"],
                ),
            )
            db.commit()

        self.client.post("/logout", follow_redirects=True)
        self.login_client("leah@example.com", "patientpass123")

        response = self.client.get(f"/api/client/appointments/context?care_plan_visit_id={overdue_visit['id']}")
        self.assertEqual(response.status_code, 200)
        context_payload = response.get_json()
        self.assertTrue(context_payload["ok"])
        self.assertEqual(context_payload["journey_state"], "at_risk")
        self.assertEqual(context_payload["journey_summary"]["primary_action_label"], "Rebook overdue visit")
        appointments_context = context_payload["appointments"]
        self.assertEqual(appointments_context["selected_care_plan_visit"]["id"], overdue_visit["id"])
        booking_date = appointments_context["booking_date"]
        self.assertGreaterEqual(booking_date, date.today().isoformat())

        response = self.client.get(
            f"/api/availability?date={booking_date}&clinician_user_id={staff_id}&location_id={main_location_id}&service_id={care_plan_service_id}&appointment_type=care_plan&duration_minutes={overdue_visit['duration_minutes']}&care_plan_visit_id={overdue_visit['id']}"
        )
        self.assertEqual(response.status_code, 200)
        availability_payload = response.get_json()
        self.assertTrue(availability_payload["ok"])
        selected_slot = availability_payload["availability"]["available_slots"][0]["value"]

        response = self.client.post(
            "/api/appointments",
            json={
                "service_id": str(care_plan_service_id),
                "appointment_type": "care_plan",
                "clinician_user_id": str(staff_id),
                "location_id": str(main_location_id),
                "appointment_date": booking_date,
                "duration_minutes": str(overdue_visit["duration_minutes"]),
                "slot_start": selected_slot,
                "patient_details": "Booked from the React portal API.",
                "care_plan_visit_id": str(overdue_visit["id"]),
            },
        )
        self.assertEqual(response.status_code, 201)
        api_payload = response.get_json()
        self.assertTrue(api_payload["ok"])
        self.assertEqual(api_payload["care_plan_visit_id"], overdue_visit["id"])

        with self.app.app_context():
            linked_visit = get_db().execute(
                "SELECT status, booked, appointment_id FROM care_plan_visits WHERE id = ?",
                (overdue_visit["id"],),
            ).fetchone()
            linked_appointment = get_db().execute(
                "SELECT note, booking_source, appointment_type FROM appointments WHERE id = ?",
                (linked_visit["appointment_id"],),
            ).fetchone()
        self.assertEqual(linked_visit["status"], "scheduled")
        self.assertEqual(linked_visit["booked"], 1)
        self.assertIsNotNone(linked_visit["appointment_id"])
        self.assertEqual(linked_appointment["appointment_type"], "care_plan")
        self.assertEqual(linked_appointment["booking_source"], "api_client")
        self.assertEqual(linked_appointment["note"], "Booked from the React portal API.")

    def test_staff_learning_portal_progress(self) -> None:
        staff_user_id = self.create_staff_user()
        self.login_staff()

        response = self.client.get("/staff/learning")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Learning portal", response.get_data(as_text=True))

        response = self.client.post(
            "/staff/learning/progress",
            data={
                "topic_slug": "anatomy-spine-joints",
                "is_completed": "1",
                "reflection": "Reviewed spinal landmarks and segmental motion.",
            },
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("Learning progress saved", response.get_data(as_text=True))

        response = self.client.post(
            "/staff/learning/progress",
            data={
                "topic_slug": "anatomy-spine-joints",
                "reflection": "Need to revisit adjustment dosage guidance.",
            },
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("Learning progress saved", response.get_data(as_text=True))

        with self.app.app_context():
            row = get_db().execute(
                "SELECT is_completed, reflection FROM practitioner_learning_progress WHERE clinician_user_id = ? AND topic_slug = ?",
                (staff_user_id, "anatomy-spine-joints"),
            ).fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row["is_completed"], 0)
        self.assertEqual(row["reflection"], "Need to revisit adjustment dosage guidance.")

    def test_staff_settings_controls(self) -> None:
        staff_id = self.create_staff_user()
        self.login_staff()

        response = self.client.get("/staff/settings")
        self.assertEqual(response.status_code, 200)
        settings_html = response.get_data(as_text=True)
        self.assertIn("Settings workspace", settings_html)
        self.assertIn("Profile &amp; Practice", settings_html)
        self.assertIn("Subscription", settings_html)
        self.assertIn("Download SQLite backup", settings_html)

        response = self.client.post(
            "/staff/settings/general",
            data={
                "calendar_time_format": "12h",
                "calendar_slot_increment_minutes": "5",
                "booking_search_window_days": "14",
                "booking_cancellation_hours": "48",
                "max_active_chiropractors": "2",
            },
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)
        updated_html = response.get_data(as_text=True)
        self.assertIn("Settings updated.", updated_html)
        self.assertIn("9:00 AM - 5:00 PM", updated_html)

        with self.app.app_context():
            db = get_db()
            settings_rows = db.execute(
                "SELECT setting_key, setting_value FROM app_settings"
            ).fetchall()
            settings_map = {row["setting_key"]: row["setting_value"] for row in settings_rows}
            self.assertEqual(settings_map["calendar_time_format"], "12h")
            self.assertEqual(settings_map["calendar_slot_increment_minutes"], "5")
            self.assertEqual(settings_map["booking_search_window_days"], "14")
            self.assertEqual(settings_map["booking_cancellation_hours"], "48")
            self.assertEqual(settings_map["max_active_chiropractors"], "2")
            main_location_id = db.execute(
                "SELECT id FROM locations WHERE slug = 'main-clinic'"
            ).fetchone()["id"]

        availability_date = (date.today() + timedelta(days=1)).isoformat()
        response = self.client.get(
            f"/staff/availability?date={availability_date}&clinician_user_id={staff_id}&location_id={main_location_id}&duration_minutes=30"
        )
        self.assertEqual(response.status_code, 200)
        availability_payload = response.get_json()
        self.assertEqual(availability_payload["slot_increment_minutes"], 5)
        self.assertTrue(any(item["time_label"] == "12:00 PM - 1:00 PM" for item in availability_payload["downtime_windows"]))

        response = self.client.post(
            "/staff/settings/preferences/profile",
            data={
                "practice_practitioner_name": "Dr Stone",
                "practice_registration_number": "GCC-12345",
                "practice_qualifications": "DC",
                "practice_clinic_name": "Summit Chiropractic",
                "practice_email": "clinic@summit.test",
                "practice_phone": "555-1111",
                "practice_address": "1 Summit Street",
                "practice_bio": "Focused on practical chiropractic care.",
            },
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)
        profile_html = response.get_data(as_text=True)
        self.assertIn("Summit Chiropractic", profile_html)

        response = self.client.post(
            "/staff/settings/chiropractors",
            data={
                "first_name": "Maya",
                "last_name": "Blue",
                "email": "maya.blue@example.com",
                "password": "chiroPass123",
            },
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("Chiropractor account created.", response.get_data(as_text=True))

        with self.app.app_context():
            clinician_row = get_db().execute(
                """
                SELECT first_name, last_name, role, is_active
                FROM users
                WHERE email = ?
                """,
                ("maya.blue@example.com",),
            ).fetchone()
            self.assertIsNotNone(clinician_row)
            self.assertEqual(clinician_row["role"], "clinician")
            self.assertEqual(clinician_row["is_active"], 1)
            self.assertEqual(
                get_db().execute(
                    "SELECT setting_value FROM app_settings WHERE setting_key = 'practice_clinic_name'"
                ).fetchone()["setting_value"],
                "Summit Chiropractic",
            )

        response = self.client.get("/staff/settings/database-backup")
        self.assertEqual(response.status_code, 200)
        self.assertIn("attachment;", response.headers.get("Content-Disposition", ""))
        self.assertGreater(len(response.get_data()), 0)
        response.close()

    def test_staff_journal_claude_chat_fallback(self) -> None:
        staff_user_id = self.create_staff_user()
        self.login_staff()

        with self.app.app_context():
            db = get_db()
            cursor = db.execute(
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
                    staff_user_id,
                    "2026-03-01",
                    "Technique review",
                    "Need better pelvic balancing on case load.",
                    "Learned that a longer setup changed response.",
                    "Revisit setup setup checklist before first thrust.",
                    iso_now(),
                    iso_now(),
                ),
            )
            entry_id = cursor.lastrowid
            db.commit()

        response = self.client.post(
            "/staff/journal/claude-chat",
            json={"message": "Find the pattern", "entry_ids": [entry_id]},
        )
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data["ok"])
        self.assertEqual(data["entry_count"], 1)
        self.assertIn("entries", data)
        self.assertIn("id", data["entries"][0])
        self.assertIn("Reflection summary", data["reply"])

    def test_staff_messaging_workspace(self) -> None:
        self.create_staff_user()
        with self.app.app_context():
            db = get_db()
            db.execute(
                """
                INSERT INTO users (first_name, last_name, email, password_hash, role, created_at)
                VALUES (?, ?, ?, ?, 'client', ?)
                """,
                ("Patient", "One", "patient.one@example.com", generate_password_hash("patientpass123", method="pbkdf2:sha256"), iso_now()),
            )
            patient_user_id = db.execute(
                "SELECT id FROM users WHERE email = ?",
                ("patient.one@example.com",),
            ).fetchone()["id"]
            db.commit()

        self.login_staff()

        response = self.client.get("/staff/messaging")
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn("Chiropractor conversations", html)
        self.assertIn("Patient One", html)

        response = self.client.post(
            f"/staff/messaging/{patient_user_id}",
            data={
                "topic": "appointment",
                "body": "Please confirm your availability for Thursday.",
            },
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("Message sent to patient", response.get_data(as_text=True))

        self.client.post("/logout", follow_redirects=True)
        response = self.client.post(
            "/login",
            data={"email": "patient.one@example.com", "password": "patientpass123"},
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)

        response = self.client.get("/messages")
        self.assertEqual(response.status_code, 200)
        patient_html = response.get_data(as_text=True)
        self.assertIn("Your chiropractic thread", patient_html)
        self.assertIn("Please confirm your availability for Thursday.", patient_html)

        response = self.client.post(
            "/messages",
            data={
                "topic": "symptoms",
                "body": "Pain reduced after stretches, but still stiff in mornings.",
            },
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("Message sent to your chiropractic team", response.get_data(as_text=True))

        self.client.post("/logout", follow_redirects=True)
        self.login_staff()
        response = self.client.get(f"/staff/messaging?patient_id={patient_user_id}")
        self.assertEqual(response.status_code, 200)
        refreshed_html = response.get_data(as_text=True)
        self.assertIn("Pain reduced after stretches, but still stiff in mornings.", refreshed_html)


if __name__ == "__main__":
    unittest.main()
