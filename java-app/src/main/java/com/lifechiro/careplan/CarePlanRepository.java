package com.lifechiro.careplan;

import java.util.List;
import java.util.Map;
import java.util.Optional;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Repository;

@Repository
public class CarePlanRepository {
    private final JdbcTemplate jdbcTemplate;

    public CarePlanRepository(JdbcTemplate jdbcTemplate) {
        this.jdbcTemplate = jdbcTemplate;
    }

    public Optional<Map<String, Object>> findActivePlanForPatient(long patientUserId) {
        return jdbcTemplate.queryForList(
            planSelectSql() + " WHERE cp.patient_user_id = ? AND cp.status = 'active' ORDER BY cp.updated_at DESC, cp.id DESC LIMIT 1",
            patientUserId
        ).stream().findFirst();
    }

    public List<Map<String, Object>> findVisitsForPlan(long carePlanId) {
        return jdbcTemplate.queryForList(
            visitSelectSql() + " WHERE cpv.care_plan_id = ? ORDER BY cpv.visit_number ASC, cpv.id ASC",
            carePlanId
        );
    }

    public Optional<Map<String, Object>> findVisitForPatient(long visitId, long patientUserId) {
        return jdbcTemplate.queryForList(
            visitSelectSql() + " WHERE cpv.id = ? AND cp.patient_user_id = ? LIMIT 1",
            visitId,
            patientUserId
        ).stream().findFirst();
    }

    public Optional<Map<String, Object>> findVisitByAppointmentId(long appointmentId) {
        return jdbcTemplate.queryForList(
            visitSelectSql() + " WHERE cpv.appointment_id = ? LIMIT 1",
            appointmentId
        ).stream().findFirst();
    }

    public void linkAppointmentToVisit(long visitId, long appointmentId, String patientDetails, String note, String updatedAt) {
        jdbcTemplate.update(
            """
            UPDATE care_plan_visits
            SET appointment_id = ?,
                booked = 1,
                status = 'scheduled',
                patient_details = ?,
                note = ?,
                updated_at = ?
            WHERE id = ?
            """,
            appointmentId,
            patientDetails,
            note,
            updatedAt,
            visitId
        );
    }

    public void reopenVisitFromAppointment(long appointmentId, String startsAt, String patientDetails, String note, String updatedAt) {
        jdbcTemplate.update(
            """
            UPDATE care_plan_visits
            SET status = 'unbooked',
                booked = 0,
                appointment_id = NULL,
                suggested_date = substr(?, 1, 10),
                suggested_starts_at = ?,
                patient_details = ?,
                note = ?,
                updated_at = ?
            WHERE appointment_id = ?
            """,
            startsAt,
            startsAt,
            patientDetails,
            note,
            updatedAt,
            appointmentId
        );
    }

    public void refreshPlanStatus(long carePlanId, String updatedAt) {
        List<String> statuses = jdbcTemplate.query(
            "SELECT status FROM care_plan_visits WHERE care_plan_id = ?",
            (rs, rowNum) -> rs.getString("status"),
            carePlanId
        );
        if (statuses.isEmpty()) {
            return;
        }
        boolean completed = statuses.stream().allMatch(status -> "completed".equals(status) || "cancelled".equals(status));
        jdbcTemplate.update(
            """
            UPDATE care_plans
            SET status = ?,
                updated_at = ?
            WHERE id = ?
            """,
            completed ? "completed" : "active",
            updatedAt,
            carePlanId
        );
    }

    private String planSelectSql() {
        return """
            SELECT
                cp.*, 
                l.name AS location_name,
                c.first_name AS clinician_first_name,
                c.last_name AS clinician_last_name,
                s.label AS service_label
            FROM care_plans cp
            LEFT JOIN locations l ON l.id = cp.location_id
            LEFT JOIN users c ON c.id = cp.clinician_user_id
            LEFT JOIN appointment_services s ON s.id = cp.service_id
            """;
    }

    private String visitSelectSql() {
        return """
            SELECT
                cpv.*, 
                cp.patient_user_id,
                cp.clinician_user_id AS plan_clinician_user_id,
                cp.location_id AS plan_location_id,
                cp.service_id AS plan_service_id,
                cp.booking_mode AS plan_booking_mode,
                cp.status AS plan_status,
                a.status AS appointment_status,
                a.starts_at AS appointment_starts_at,
                a.ends_at AS appointment_ends_at,
                a.note AS appointment_note,
                a.patient_details AS appointment_patient_details,
                l.name AS appointment_location_name,
                c.first_name AS appointment_clinician_first_name,
                c.last_name AS appointment_clinician_last_name
            FROM care_plan_visits cpv
            JOIN care_plans cp ON cp.id = cpv.care_plan_id
            LEFT JOIN appointments a ON a.id = cpv.appointment_id
            LEFT JOIN locations l ON l.id = a.location_id
            LEFT JOIN users c ON c.id = a.clinician_user_id
            """;
    }
}
