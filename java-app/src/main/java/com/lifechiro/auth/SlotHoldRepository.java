package com.lifechiro.auth;

import com.lifechiro.auth.model.SlotHoldRecord;
import java.util.Optional;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.core.RowMapper;
import org.springframework.stereotype.Repository;

@Repository
public class SlotHoldRepository {
    private static final RowMapper<SlotHoldRecord> SLOT_HOLD_ROW_MAPPER = (resultSet, rowNum) -> new SlotHoldRecord(
        resultSet.getLong("id"),
        resultSet.getObject("invitation_id") == null ? null : resultSet.getLong("invitation_id"),
        resultSet.getObject("lead_id") == null ? null : resultSet.getLong("lead_id"),
        resultSet.getLong("clinician_user_id"),
        resultSet.getObject("location_id") == null ? null : resultSet.getLong("location_id"),
        resultSet.getObject("service_id") == null ? null : resultSet.getLong("service_id"),
        resultSet.getString("appointment_type"),
        resultSet.getString("starts_at"),
        resultSet.getString("ends_at"),
        resultSet.getString("status"),
        resultSet.getString("expires_at"),
        resultSet.getObject("consumed_appointment_id") == null ? null : resultSet.getLong("consumed_appointment_id"),
        resultSet.getString("created_at"),
        resultSet.getString("updated_at"),
        resultSet.getString("service_label"),
        resultSet.getString("location_name"),
        resultSet.getString("clinician_name")
    );

    private final JdbcTemplate jdbcTemplate;

    public SlotHoldRepository(JdbcTemplate jdbcTemplate) {
        this.jdbcTemplate = jdbcTemplate;
    }

    public Optional<SlotHoldRecord> findByInvitationId(long invitationId) {
        return jdbcTemplate.query(
            """
            SELECT
                sh.*,
                s.label AS service_label,
                loc.name AS location_name,
                TRIM(COALESCE(c.first_name, '') || ' ' || COALESCE(c.last_name, '')) AS clinician_name
            FROM appointment_slot_holds sh
            LEFT JOIN appointment_services s ON s.id = sh.service_id
            LEFT JOIN locations loc ON loc.id = sh.location_id
            LEFT JOIN users c ON c.id = sh.clinician_user_id
            WHERE sh.invitation_id = ?
            LIMIT 1
            """,
            SLOT_HOLD_ROW_MAPPER,
            invitationId
        ).stream().findFirst();
    }

    public void markConsumed(long slotHoldId, long appointmentId, String updatedAt) {
        jdbcTemplate.update(
            """
            UPDATE appointment_slot_holds
            SET status = 'consumed',
                consumed_appointment_id = ?,
                updated_at = ?
            WHERE id = ?
            """,
            appointmentId,
            updatedAt,
            slotHoldId
        );
    }
}
