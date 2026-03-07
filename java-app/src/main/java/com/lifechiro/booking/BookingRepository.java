package com.lifechiro.booking;

import java.sql.PreparedStatement;
import java.sql.Statement;
import java.time.LocalDate;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.core.RowMapper;
import org.springframework.jdbc.support.GeneratedKeyHolder;
import org.springframework.jdbc.support.KeyHolder;
import org.springframework.stereotype.Repository;

@Repository
public class BookingRepository {
    private static final RowMapper<LocationRow> LOCATION_ROW_MAPPER = (rs, rowNum) -> new LocationRow(
        rs.getLong("id"),
        rs.getString("name"),
        rs.getString("slug"),
        rs.getString("address"),
        rs.getString("phone"),
        rs.getString("timezone"),
        rs.getInt("active") != 0
    );

    private static final RowMapper<ServiceRow> SERVICE_ROW_MAPPER = (rs, rowNum) -> new ServiceRow(
        rs.getLong("id"),
        rs.getString("service_key"),
        rs.getString("label"),
        rs.getString("description"),
        rs.getString("appointment_type"),
        rs.getInt("duration_minutes"),
        rs.getInt("buffer_before_minutes"),
        rs.getInt("buffer_after_minutes"),
        rs.getInt("requires_payment") != 0,
        rs.getObject("price_amount") == null ? null : rs.getDouble("price_amount"),
        rs.getString("currency"),
        rs.getInt("min_notice_minutes"),
        rs.getObject("max_bookings_per_day") == null ? null : rs.getInt("max_bookings_per_day"),
        rs.getString("routing_mode"),
        rs.getInt("active") != 0,
        rs.getInt("display_order")
    );

    private static final RowMapper<ClinicianRow> CLINICIAN_ROW_MAPPER = (rs, rowNum) -> new ClinicianRow(
        rs.getLong("id"),
        rs.getString("first_name"),
        rs.getString("last_name"),
        rs.getString("email"),
        rs.getString("role")
    );

    private static final RowMapper<ScheduleWindowRow> SCHEDULE_WINDOW_ROW_MAPPER = (rs, rowNum) -> new ScheduleWindowRow(
        rs.getLong("id"),
        rs.getObject("clinician_user_id") == null ? null : rs.getLong("clinician_user_id"),
        rs.getObject("location_id") == null ? null : rs.getLong("location_id"),
        rs.getInt("weekday"),
        rs.getString("window_type"),
        rs.getString("starts_time"),
        rs.getString("ends_time"),
        rs.getString("label")
    );

    private static final RowMapper<BusyBlockRow> BUSY_BLOCK_ROW_MAPPER = (rs, rowNum) -> new BusyBlockRow(
        rs.getString("id"),
        rs.getString("appointment_type"),
        rs.getString("starts_at"),
        rs.getString("ends_at"),
        rs.getString("service_label"),
        rs.getObject("service_duration_minutes") == null ? null : rs.getInt("service_duration_minutes"),
        rs.getObject("service_buffer_before_minutes") == null ? null : rs.getInt("service_buffer_before_minutes"),
        rs.getObject("service_buffer_after_minutes") == null ? null : rs.getInt("service_buffer_after_minutes"),
        rs.getString("expires_at")
    );

    private final JdbcTemplate jdbcTemplate;

    public BookingRepository(JdbcTemplate jdbcTemplate) {
        this.jdbcTemplate = jdbcTemplate;
    }

    public List<LocationRow> findActiveLocations() {
        return jdbcTemplate.query(
            """
            SELECT id, name, slug, address, phone, timezone, active
            FROM locations
            WHERE active = 1
            ORDER BY name ASC, id ASC
            """,
            LOCATION_ROW_MAPPER
        );
    }

    public Optional<LocationRow> findLocationById(long locationId) {
        return jdbcTemplate.query(
            """
            SELECT id, name, slug, address, phone, timezone, active
            FROM locations
            WHERE id = ?
            LIMIT 1
            """,
            LOCATION_ROW_MAPPER,
            locationId
        ).stream().findFirst();
    }

    public List<ServiceRow> findActiveServices() {
        return jdbcTemplate.query(
            """
            SELECT id, service_key, label, description, appointment_type, duration_minutes,
                   buffer_before_minutes, buffer_after_minutes, requires_payment, price_amount,
                   currency, min_notice_minutes, max_bookings_per_day, routing_mode, active, display_order
            FROM appointment_services
            WHERE active = 1
            ORDER BY display_order ASC, label ASC, id ASC
            """,
            SERVICE_ROW_MAPPER
        );
    }

    public Optional<ServiceRow> findServiceById(long serviceId) {
        return jdbcTemplate.query(
            """
            SELECT id, service_key, label, description, appointment_type, duration_minutes,
                   buffer_before_minutes, buffer_after_minutes, requires_payment, price_amount,
                   currency, min_notice_minutes, max_bookings_per_day, routing_mode, active, display_order
            FROM appointment_services
            WHERE id = ?
            LIMIT 1
            """,
            SERVICE_ROW_MAPPER,
            serviceId
        ).stream().findFirst();
    }

    public List<ClinicianRow> findBookableClinicians() {
        List<ClinicianRow> clinicians = jdbcTemplate.query(
            """
            SELECT id, first_name, last_name, email, role
            FROM users
            WHERE role = 'clinician'
              AND COALESCE(is_active, 1) = 1
            ORDER BY first_name ASC, last_name ASC, email ASC
            """,
            CLINICIAN_ROW_MAPPER
        );
        if (!clinicians.isEmpty()) {
            return clinicians;
        }
        return jdbcTemplate.query(
            """
            SELECT id, first_name, last_name, email, role
            FROM users
            WHERE role IN ('clinician', 'admin')
              AND COALESCE(is_active, 1) = 1
            ORDER BY first_name ASC, last_name ASC, email ASC
            """,
            CLINICIAN_ROW_MAPPER
        );
    }

    public List<ScheduleWindowRow> findScheduleWindowsForDay(int weekday, long clinicianUserId, long locationId) {
        return jdbcTemplate.query(
            """
            SELECT id, clinician_user_id, location_id, weekday, window_type, starts_time, ends_time, label
            FROM schedule_windows
            WHERE weekday = ?
              AND (clinician_user_id IS NULL OR clinician_user_id = ?)
              AND location_id = ?
            ORDER BY starts_time ASC, ends_time ASC, id ASC
            """,
            SCHEDULE_WINDOW_ROW_MAPPER,
            weekday,
            clinicianUserId,
            locationId
        );
    }

    public List<BusyBlockRow> findAppointmentsForDate(LocalDate targetDate, long clinicianUserId) {
        return jdbcTemplate.query(
            """
            SELECT CAST(a.id AS TEXT) AS id,
                   a.appointment_type,
                   a.starts_at,
                   a.ends_at,
                   s.label AS service_label,
                   s.duration_minutes AS service_duration_minutes,
                   s.buffer_before_minutes AS service_buffer_before_minutes,
                   s.buffer_after_minutes AS service_buffer_after_minutes,
                   NULL AS expires_at
            FROM appointments a
            LEFT JOIN appointment_services s ON s.id = a.service_id
            WHERE a.clinician_user_id = ?
              AND a.status = 'scheduled'
              AND substr(a.starts_at, 1, 10) = ?
            ORDER BY a.starts_at ASC, a.id ASC
            """,
            BUSY_BLOCK_ROW_MAPPER,
            clinicianUserId,
            targetDate.toString()
        );
    }

    public List<BusyBlockRow> findActiveSlotHoldsForDate(LocalDate targetDate, long clinicianUserId) {
        return jdbcTemplate.query(
            """
            SELECT 'hold-' || sh.id AS id,
                   sh.appointment_type,
                   sh.starts_at,
                   sh.ends_at,
                   s.label AS service_label,
                   s.duration_minutes AS service_duration_minutes,
                   s.buffer_before_minutes AS service_buffer_before_minutes,
                   s.buffer_after_minutes AS service_buffer_after_minutes,
                   sh.expires_at
            FROM appointment_slot_holds sh
            LEFT JOIN appointment_services s ON s.id = sh.service_id
            WHERE sh.clinician_user_id = ?
              AND sh.status = 'active'
              AND substr(sh.starts_at, 1, 10) = ?
            ORDER BY sh.starts_at ASC, sh.id ASC
            """,
            BUSY_BLOCK_ROW_MAPPER,
            clinicianUserId,
            targetDate.toString()
        );
    }

    public String findAppSetting(String key) {
        return jdbcTemplate.query(
            """
            SELECT setting_value
            FROM app_settings
            WHERE setting_key = ?
            LIMIT 1
            """,
            (rs, rowNum) -> rs.getString("setting_value"),
            key
        ).stream().findFirst().orElse(null);
    }

    public List<Map<String, Object>> findPatientAppointments(long patientUserId) {
        return jdbcTemplate.queryForList(appointmentsSelectSql() + " WHERE a.patient_user_id = ? ORDER BY a.starts_at ASC", patientUserId);
    }

    public List<Map<String, Object>> findAllAppointments() {
        return jdbcTemplate.queryForList(appointmentsSelectSql() + " ORDER BY a.starts_at ASC, a.id ASC");
    }

    public Optional<Map<String, Object>> findPatientAppointmentById(long appointmentId, long patientUserId) {
        return jdbcTemplate.queryForList(
            appointmentsSelectSql() + " WHERE a.id = ? AND a.patient_user_id = ? LIMIT 1",
            appointmentId,
            patientUserId
        ).stream().findFirst();
    }

    public Optional<Map<String, Object>> findAppointmentById(long appointmentId) {
        return jdbcTemplate.queryForList(
            appointmentsSelectSql() + " WHERE a.id = ? LIMIT 1",
            appointmentId
        ).stream().findFirst();
    }

    public long createAppointment(
        long patientUserId,
        Long clinicianUserId,
        Long locationId,
        Long serviceId,
        String appointmentType,
        String status,
        String startsAt,
        String endsAt,
        String note,
        String patientDetails,
        String billingStatus,
        String billingCode,
        Double billingAmount,
        boolean requiresPayment,
        String paymentStatus,
        Double paymentAmount,
        String bookingChannel,
        String serviceLabelSnapshot,
        String policySnapshotJson,
        String bookingSource,
        String createdAt
    ) {
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
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                Statement.RETURN_GENERATED_KEYS
            );
            statement.setLong(1, patientUserId);
            if (clinicianUserId == null) {
                statement.setObject(2, null);
            } else {
                statement.setLong(2, clinicianUserId);
            }
            if (locationId == null) {
                statement.setObject(3, null);
            } else {
                statement.setLong(3, locationId);
            }
            if (serviceId == null) {
                statement.setObject(4, null);
            } else {
                statement.setLong(4, serviceId);
            }
            statement.setString(5, appointmentType);
            statement.setString(6, status);
            statement.setString(7, startsAt);
            statement.setString(8, endsAt);
            statement.setString(9, note);
            statement.setString(10, patientDetails);
            statement.setString(11, billingStatus);
            statement.setString(12, billingCode);
            if (billingAmount == null) {
                statement.setObject(13, null);
            } else {
                statement.setDouble(13, billingAmount);
            }
            statement.setInt(14, requiresPayment ? 1 : 0);
            statement.setString(15, paymentStatus);
            if (paymentAmount == null) {
                statement.setObject(16, null);
            } else {
                statement.setDouble(16, paymentAmount);
            }
            statement.setString(17, bookingChannel);
            statement.setString(18, serviceLabelSnapshot);
            statement.setString(19, policySnapshotJson);
            statement.setString(20, bookingSource);
            statement.setString(21, createdAt);
            statement.setString(22, createdAt);
            return statement;
        }, keyHolder);
        Number key = keyHolder.getKey();
        if (key == null) {
            throw new IllegalStateException("Failed to create appointment");
        }
        return key.longValue();
    }

    public void cancelPatientAppointment(long appointmentId, long patientUserId, String updatedAt) {
        jdbcTemplate.update(
            """
            UPDATE appointments
            SET status = 'cancelled',
                updated_at = ?
            WHERE id = ? AND patient_user_id = ?
            """,
            updatedAt,
            appointmentId,
            patientUserId
        );
    }

    public void logBookingEvent(String eventType, Long appointmentId, Long patientUserId, String payloadJson, String createdAt) {
        jdbcTemplate.update(
            """
            INSERT INTO booking_webhook_events (
                event_type,
                appointment_id,
                patient_user_id,
                payload_json,
                delivery_status,
                created_at
            )
            VALUES (?, ?, ?, ?, 'pending', ?)
            """,
            eventType,
            appointmentId,
            patientUserId,
            payloadJson,
            createdAt
        );
    }

    private String appointmentsSelectSql() {
        return """
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
                s.routing_mode AS service_routing_mode
            FROM appointments a
            JOIN users p ON p.id = a.patient_user_id
            LEFT JOIN locations l ON l.id = a.location_id
            LEFT JOIN users c ON c.id = a.clinician_user_id
            LEFT JOIN appointment_services s ON s.id = a.service_id
            """;
    }
}

record LocationRow(
    long id,
    String name,
    String slug,
    String address,
    String phone,
    String timezone,
    boolean active
) {
}

record ServiceRow(
    long id,
    String serviceKey,
    String label,
    String description,
    String appointmentType,
    int durationMinutes,
    int bufferBeforeMinutes,
    int bufferAfterMinutes,
    boolean requiresPayment,
    Double priceAmount,
    String currency,
    int minNoticeMinutes,
    Integer maxBookingsPerDay,
    String routingMode,
    boolean active,
    int displayOrder
) {
}

record ClinicianRow(
    long id,
    String firstName,
    String lastName,
    String email,
    String role
) {
    String displayName() {
        return (firstName + " " + lastName).trim();
    }
}

record ScheduleWindowRow(
    long id,
    Long clinicianUserId,
    Long locationId,
    int weekday,
    String windowType,
    String startsTime,
    String endsTime,
    String label
) {
}

record BusyBlockRow(
    String id,
    String appointmentType,
    String startsAt,
    String endsAt,
    String serviceLabel,
    Integer serviceDurationMinutes,
    Integer serviceBufferBeforeMinutes,
    Integer serviceBufferAfterMinutes,
    String expiresAt
) {
}
