package com.lifechiro.auth;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.lifechiro.auth.model.InvitationRecord;
import com.lifechiro.auth.model.SlotHoldRecord;
import java.sql.PreparedStatement;
import java.sql.Statement;
import java.time.LocalDateTime;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Optional;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.support.GeneratedKeyHolder;
import org.springframework.jdbc.support.KeyHolder;
import org.springframework.stereotype.Repository;

@Repository
public class AppointmentRepository {
    private final JdbcTemplate jdbcTemplate;
    private final ObjectMapper objectMapper;

    public AppointmentRepository(JdbcTemplate jdbcTemplate, ObjectMapper objectMapper) {
        this.jdbcTemplate = jdbcTemplate;
        this.objectMapper = objectMapper;
    }

    public long ensurePatientAppointment(long patientUserId, InvitationRecord invitation, SlotHoldRecord slotHold, String createdAt) {
        String startsAt = slotHold != null && slotHold.startsAt() != null ? slotHold.startsAt() : invitation.appointmentAt();
        if (startsAt == null || startsAt.isBlank()) {
            return -1L;
        }
        String appointmentType = slotHold != null && slotHold.appointmentType() != null ? slotHold.appointmentType() : "initial_consult";
        Long serviceId = slotHold != null ? slotHold.serviceId() : null;
        ServiceSnapshot service = findServiceSnapshot(serviceId).orElse(null);
        Optional<Long> existing = jdbcTemplate.query(
            """
            SELECT id
            FROM appointments
            WHERE source_invitation_id = ?
               OR (patient_user_id = ? AND appointment_type = ? AND starts_at = ?)
            LIMIT 1
            """,
            (resultSet, rowNum) -> resultSet.getLong("id"),
            invitation.id(),
            patientUserId,
            appointmentType,
            startsAt
        ).stream().findFirst();
        if (existing.isPresent()) {
            return existing.get();
        }
        String bookingNote = invitation.note() == null ? "" : invitation.note();
        String endsAt = resolveEndsAt(startsAt, slotHold, service);
        String billingStatus = service != null && service.requiresPayment() ? "pending" : "not_required";
        String paymentStatus = billingStatus;
        Double paymentAmount = service != null ? service.priceAmount() : null;
        String serviceLabelSnapshot = service != null && service.label() != null ? service.label() : appointmentTypeLabel(appointmentType);
        String policySnapshotJson = toJson(buildPolicySnapshot(service, appointmentType, endsAt));

        KeyHolder keyHolder = new GeneratedKeyHolder();
        jdbcTemplate.update(connection -> {
            PreparedStatement statement = connection.prepareStatement(
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
                VALUES (?, ?, ?, ?, ?, 'scheduled', ?, ?, ?, ?, ?, ?, '', NULL, ?, ?, ?, 'portal_link', ?, ?, 'invite_acceptance', ?, ?)
                """,
                Statement.RETURN_GENERATED_KEYS
            );
            statement.setLong(1, patientUserId);
            if (slotHold != null) {
                statement.setLong(2, slotHold.clinicianUserId());
            } else if (invitation.createdBy() != null) {
                statement.setLong(2, invitation.createdBy());
            } else {
                statement.setObject(2, null);
            }
            if (slotHold != null && slotHold.locationId() != null) {
                statement.setLong(3, slotHold.locationId());
            } else {
                statement.setObject(3, null);
            }
            if (slotHold != null && slotHold.serviceId() != null) {
                statement.setLong(4, slotHold.serviceId());
            } else {
                statement.setObject(4, null);
            }
            statement.setString(5, appointmentType);
            statement.setString(6, startsAt);
            statement.setString(7, endsAt);
            statement.setLong(8, invitation.id());
            statement.setString(9, bookingNote);
            statement.setString(10, bookingNote);
            statement.setString(11, billingStatus);
            statement.setInt(12, service != null && service.requiresPayment() ? 1 : 0);
            statement.setString(13, paymentStatus);
            if (paymentAmount == null) {
                statement.setObject(14, null);
            } else {
                statement.setDouble(14, paymentAmount);
            }
            statement.setString(15, serviceLabelSnapshot);
            statement.setString(16, policySnapshotJson);
            statement.setString(17, createdAt);
            statement.setString(18, createdAt);
            return statement;
        }, keyHolder);
        Number key = keyHolder.getKey();
        if (key == null) {
            throw new IllegalStateException("Failed to create invitation appointment");
        }
        return key.longValue();
    }

    public long countUpcomingAppointments() {
        Long count = jdbcTemplate.queryForObject(
            "SELECT COUNT(*) FROM appointments WHERE status = 'scheduled'",
            Long.class
        );
        return count == null ? 0L : count;
    }

    public String findNextAppointmentLabelForPatient(long patientUserId) {
        return jdbcTemplate.query(
            """
            SELECT starts_at
            FROM appointments
            WHERE patient_user_id = ?
              AND status = 'scheduled'
            ORDER BY starts_at ASC, id ASC
            LIMIT 1
            """,
            (resultSet, rowNum) -> resultSet.getString("starts_at"),
            patientUserId
        ).stream().findFirst().orElse(null);
    }

    private Optional<ServiceSnapshot> findServiceSnapshot(Long serviceId) {
        if (serviceId == null) {
            return Optional.empty();
        }
        return jdbcTemplate.query(
            """
            SELECT id, label, appointment_type, duration_minutes, buffer_before_minutes, buffer_after_minutes,
                   requires_payment, price_amount, currency, min_notice_minutes, max_bookings_per_day, routing_mode
            FROM appointment_services
            WHERE id = ?
            LIMIT 1
            """,
            (rs, rowNum) -> new ServiceSnapshot(
                rs.getLong("id"),
                rs.getString("label"),
                rs.getString("appointment_type"),
                rs.getInt("duration_minutes"),
                rs.getInt("buffer_before_minutes"),
                rs.getInt("buffer_after_minutes"),
                rs.getInt("requires_payment") != 0,
                rs.getObject("price_amount") == null ? null : rs.getDouble("price_amount"),
                rs.getString("currency"),
                rs.getInt("min_notice_minutes"),
                rs.getObject("max_bookings_per_day") == null ? null : rs.getInt("max_bookings_per_day"),
                rs.getString("routing_mode")
            ),
            serviceId
        ).stream().findFirst();
    }

    private String resolveEndsAt(String startsAt, SlotHoldRecord slotHold, ServiceSnapshot service) {
        if (slotHold != null && slotHold.endsAt() != null && !slotHold.endsAt().isBlank()) {
            return slotHold.endsAt();
        }
        if (service == null || startsAt == null || startsAt.isBlank()) {
            return null;
        }
        try {
            return LocalDateTime.parse(startsAt).plusMinutes(service.durationMinutes()).toString();
        } catch (Exception ignored) {
            return null;
        }
    }

    private String appointmentTypeLabel(String appointmentType) {
        return switch (appointmentType) {
            case "initial_consult" -> "Initial Consultation";
            case "report_of_findings" -> "Report of Findings";
            case "care_plan" -> "Care Plan Visit";
            default -> appointmentType == null ? "" : appointmentType.replace('_', ' ');
        };
    }

    private Map<String, Object> buildPolicySnapshot(ServiceSnapshot service, String appointmentType, String endsAt) {
        Map<String, Object> snapshot = new LinkedHashMap<>();
        if (service != null) {
            snapshot.put("service_id", service.id());
            snapshot.put("service_label", service.label());
            snapshot.put("appointment_type", service.appointmentType());
            snapshot.put("duration_minutes", service.durationMinutes());
            snapshot.put("buffer_before_minutes", service.bufferBeforeMinutes());
            snapshot.put("buffer_after_minutes", service.bufferAfterMinutes());
            snapshot.put("requires_payment", service.requiresPayment());
            snapshot.put("price_amount", service.priceAmount());
            snapshot.put("currency", service.currency());
            snapshot.put("min_notice_minutes", service.minNoticeMinutes());
            snapshot.put("max_bookings_per_day", service.maxBookingsPerDay());
            snapshot.put("routing_mode", service.routingMode());
        } else {
            snapshot.put("appointment_type", appointmentType);
        }
        if (endsAt != null) {
            snapshot.put("ends_at", endsAt);
        }
        return snapshot;
    }

    private String toJson(Object value) {
        try {
            return objectMapper.writeValueAsString(value);
        } catch (JsonProcessingException exception) {
            throw new IllegalStateException("Failed to serialize invitation appointment snapshot", exception);
        }
    }

    private record ServiceSnapshot(
        long id,
        String label,
        String appointmentType,
        int durationMinutes,
        int bufferBeforeMinutes,
        int bufferAfterMinutes,
        boolean requiresPayment,
        Double priceAmount,
        String currency,
        int minNoticeMinutes,
        Integer maxBookingsPerDay,
        String routingMode
    ) {
    }
}
