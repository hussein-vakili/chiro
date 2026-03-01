from __future__ import annotations

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
        self.assertIn("Clinic onboarding operations", response.get_data(as_text=True))

    def test_invited_patient_and_password_reset_flow(self) -> None:
        self.create_staff_user()
        self.login_staff()

        response = self.client.post(
            "/staff/invitations/new",
            data={
                "first_name": "Sarah",
                "last_name": "Mitchell",
                "email": "sarah@example.com",
                "appointment_at": "2026-03-10T09:30",
                "note": "Please arrive 10 minutes early.",
            },
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("Invitation created", response.get_data(as_text=True))

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
        self.assertIn("Appointment scheduled", response.get_data(as_text=True))

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
                "signatureDate": "2026-03-01",
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

        response = self.client.get(f"/staff/patients/{patient['id']}/summit-assessment")
        self.assertEqual(response.status_code, 200)
        assessment_html = response.get_data(as_text=True)
        self.assertIn("Summit complete assessment (2)", assessment_html)
        self.assertIn("Dedicated chiropractor assessment workspace", assessment_html)

        response = self.client.post(
            f"/staff/patients/{patient['id']}/initial-consult",
            data={
                "action": "published",
                "redirect_to": "assessment",
                "visit_date": "2026-03-10T09:30",
                "assessment_date": "2026-03-10",
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
        self.assertIn("Summit complete assessment (2)", assessment_html)

        response = self.client.post(
            f"/staff/patients/{patient['id']}/notes",
            data={
                "exam_findings": "Restricted cervical rotation and upper trap guarding.",
                "assessment": "Mechanical neck pain with headache referral pattern.",
                "care_plan": "6-visit trial with gentle adjustments and mobility work.",
                "next_visit_at": "2026-03-12T09:30",
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


if __name__ == "__main__":
    unittest.main()
