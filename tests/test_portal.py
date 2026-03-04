from __future__ import annotations

from datetime import date, datetime, timedelta
import os
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

    def login_staff(self) -> None:
        response = self.client.post(
            "/login",
            data={"email": "staff@example.com", "password": "staffpass123"},
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("Practitioner dashboard", response.get_data(as_text=True))
        self.assertIn("My patients", response.get_data(as_text=True))

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

        response = self.client.post(
            f"/practitioner/appointments/{rof_appointment['id']}/soap",
            data={
                "subjective": "Headaches eased for two days after the initial treatment, but neck stiffness returned after a long shift.",
                "objective": "Cervical rotation improved slightly left and right. Upper trapezius tension still present on palpation.",
                "assessment": "Progressing, but prolonged nursing shifts continue to irritate the cervical region.",
                "plan": "Continue with the scheduled care plan, reinforce hourly posture resets, and re-check cervical rotation next visit.",
            },
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)
        soap_html = response.get_data(as_text=True)
        self.assertIn("SOAP note saved for this appointment", soap_html)
        self.assertIn("Headaches eased for two days", soap_html)
        self.assertIn("Continue with the scheduled care plan", soap_html)

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


if __name__ == "__main__":
    unittest.main()
