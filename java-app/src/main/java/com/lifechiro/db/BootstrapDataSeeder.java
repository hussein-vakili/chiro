package com.lifechiro.db;

import com.lifechiro.config.AppConfig;
import com.lifechiro.shared.TimeSupport;
import java.time.ZoneOffset;
import java.time.LocalDateTime;
import org.springframework.boot.ApplicationArguments;
import org.springframework.boot.ApplicationRunner;
import org.springframework.core.annotation.Order;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Component;

@Component
@Order(1)
public class BootstrapDataSeeder implements ApplicationRunner {
    private final JdbcTemplate jdbcTemplate;
    private final PasswordEncoder passwordEncoder;
    private final AppConfig appConfig;

    public BootstrapDataSeeder(JdbcTemplate jdbcTemplate, PasswordEncoder passwordEncoder, AppConfig appConfig) {
        this.jdbcTemplate = jdbcTemplate;
        this.passwordEncoder = passwordEncoder;
        this.appConfig = appConfig;
    }

    @Override
    public void run(ApplicationArguments args) {
        long mainLocationId = ensureDefaultLocation();
        ensureDefaultAppointmentServices();
        ensureDefaultAppSettings();
        ensureDefaultScheduleWindows(mainLocationId);
        long staffId = ensureDefaultStaffUser();
        ensureDemoInvitation(staffId, mainLocationId);
    }

    private long ensureDefaultLocation() {
        return jdbcTemplate.query(
            "SELECT id FROM locations WHERE slug = 'main-clinic' LIMIT 1",
            (rs, rowNum) -> rs.getLong("id")
        ).stream().findFirst().orElseGet(() -> {
            jdbcTemplate.update(
                """
                INSERT INTO locations (name, slug, address, phone, timezone, active, created_at, updated_at)
                VALUES ('Main Clinic', 'main-clinic', '123 Wellness Way', '555-0101', 'Europe/London', 1, ?, ?)
                """,
                TimeSupport.isoNowUtc(),
                TimeSupport.isoNowUtc()
            );
            return jdbcTemplate.queryForObject(
                "SELECT id FROM locations WHERE slug = 'main-clinic' LIMIT 1",
                Long.class
            );
        });
    }

    private void ensureDefaultScheduleWindows(long locationId) {
        Integer count = jdbcTemplate.queryForObject("SELECT COUNT(*) FROM schedule_windows", Integer.class);
        if (count != null && count > 0) {
            return;
        }
        String now = TimeSupport.isoNowUtc();
        for (int weekday = 0; weekday < 7; weekday += 1) {
            jdbcTemplate.update(
                """
                INSERT INTO schedule_windows (
                    clinician_user_id, location_id, weekday, window_type, starts_time, ends_time, label, created_at, updated_at
                ) VALUES (NULL, ?, ?, 'shift', '09:00', '17:00', 'Clinic shift', ?, ?)
                """,
                locationId,
                weekday,
                now,
                now
            );
            jdbcTemplate.update(
                """
                INSERT INTO schedule_windows (
                    clinician_user_id, location_id, weekday, window_type, starts_time, ends_time, label, created_at, updated_at
                ) VALUES (NULL, ?, ?, 'downtime', '12:00', '13:00', 'Lunch downtime', ?, ?)
                """,
                locationId,
                weekday,
                now,
                now
            );
        }
    }

    private void ensureDefaultAppointmentServices() {
        String now = TimeSupport.isoNowUtc();
        insertService("new_patient_30", "New Patient Visit", "Comprehensive first appointment with exam and consultation.", "initial_consult", 30, 10, 10, 1, 95.0, "GBP", 180, 8, "specific_clinician", 1, 10, now);
        insertService("report_of_findings_30", "Report of Findings", "Review findings, explain diagnosis, and confirm care plan.", "report_of_findings", 30, 5, 10, 0, null, "GBP", 120, 10, "specific_clinician", 1, 20, now);
        insertService("follow_up_15", "Follow-up Visit", "Standard adjustment and progress check.", "care_plan", 15, 5, 5, 0, null, "GBP", 60, 16, "specific_clinician", 1, 30, now);
        insertService("team_adjustment_15", "Team Adjustment (Any Chiropractor)", "Fast follow-up visit routed to any available chiropractor.", "care_plan", 15, 5, 5, 0, null, "GBP", 60, 24, "team_round_robin", 1, 40, now);
    }

    private void insertService(
        String serviceKey,
        String label,
        String description,
        String appointmentType,
        int durationMinutes,
        int bufferBefore,
        int bufferAfter,
        int requiresPayment,
        Double priceAmount,
        String currency,
        int minNotice,
        Integer maxBookings,
        String routingMode,
        int active,
        int displayOrder,
        String now
    ) {
        Integer existing = jdbcTemplate.queryForObject(
            "SELECT COUNT(*) FROM appointment_services WHERE service_key = ?",
            Integer.class,
            serviceKey
        );
        if (existing != null && existing > 0) {
            return;
        }
        jdbcTemplate.update(
            """
            INSERT INTO appointment_services (
                service_key, label, description, appointment_type, duration_minutes, buffer_before_minutes,
                buffer_after_minutes, requires_payment, price_amount, currency, min_notice_minutes,
                max_bookings_per_day, routing_mode, active, display_order, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            serviceKey,
            label,
            description,
            appointmentType,
            durationMinutes,
            bufferBefore,
            bufferAfter,
            requiresPayment,
            priceAmount,
            currency,
            minNotice,
            maxBookings,
            routingMode,
            active,
            displayOrder,
            now,
            now
        );
    }

    private void ensureDefaultAppSettings() {
        upsertSetting("calendar_time_format", "24h");
        upsertSetting("calendar_slot_increment_minutes", "15");
        upsertSetting("booking_search_window_days", "21");
        upsertSetting("max_active_chiropractors", "3");
    }

    private void upsertSetting(String key, String value) {
        jdbcTemplate.update(
            """
            INSERT INTO app_settings (setting_key, setting_value, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(setting_key) DO UPDATE SET
                setting_value = excluded.setting_value,
                updated_at = excluded.updated_at
            """,
            key,
            value,
            TimeSupport.isoNowUtc()
        );
    }

    private long ensureDefaultStaffUser() {
        return jdbcTemplate.query(
            "SELECT id FROM users WHERE lower(email) = lower(?) LIMIT 1",
            (rs, rowNum) -> rs.getLong("id"),
            appConfig.getDefaultStaffEmail()
        ).stream().findFirst().orElseGet(() -> {
            jdbcTemplate.update(
                """
                INSERT INTO users (first_name, last_name, email, password_hash, role, is_active, created_at)
                VALUES (?, ?, ?, ?, 'clinician', 1, ?)
                """,
                appConfig.getDefaultStaffFirstName(),
                appConfig.getDefaultStaffLastName(),
                appConfig.getDefaultStaffEmail().toLowerCase(),
                passwordEncoder.encode(appConfig.getDefaultStaffPassword()),
                TimeSupport.isoNowUtc()
            );
            return jdbcTemplate.queryForObject(
                "SELECT id FROM users WHERE lower(email) = lower(?) LIMIT 1",
                Long.class,
                appConfig.getDefaultStaffEmail()
            );
        });
    }

    private void ensureDemoInvitation(long staffId, long locationId) {
        Integer invitationCount = jdbcTemplate.queryForObject("SELECT COUNT(*) FROM invitations", Integer.class);
        if (invitationCount != null && invitationCount > 0) {
            return;
        }
        String now = TimeSupport.isoNowUtc();
        String appointmentAt = TimeSupport.localDateTimeValue(LocalDateTime.now().plusDays(2).withHour(10).withMinute(0));
        String expiresAt = LocalDateTime.now()
            .plusDays(7)
            .withHour(23)
            .withMinute(59)
            .withSecond(0)
            .withNano(0)
            .atOffset(ZoneOffset.UTC)
            .toInstant()
            .toString();
        jdbcTemplate.update(
            """
            INSERT INTO invitations (
                email, first_name, last_name, appointment_at, note, token, expires_at, created_at, created_by
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            appConfig.getDemoInviteEmail().toLowerCase(),
            "New",
            "Patient",
            appointmentAt,
            "This is a seeded invitation from the Java migration slice.",
            appConfig.getDemoInviteToken(),
            expiresAt,
            now,
            staffId
        );
        Long invitationId = jdbcTemplate.queryForObject(
            "SELECT id FROM invitations WHERE token = ? LIMIT 1",
            Long.class,
            appConfig.getDemoInviteToken()
        );
        Long serviceId = jdbcTemplate.queryForObject(
            "SELECT id FROM appointment_services WHERE service_key = 'new_patient_30' LIMIT 1",
            Long.class
        );
        if (invitationId != null && serviceId != null) {
            jdbcTemplate.update(
                """
                INSERT INTO appointment_slot_holds (
                    invitation_id, clinician_user_id, location_id, service_id, appointment_type,
                    starts_at, ends_at, status, expires_at, created_at, updated_at
                ) VALUES (?, ?, ?, ?, 'initial_consult', ?, ?, 'active', ?, ?, ?)
                """,
                invitationId,
                staffId,
                locationId,
                serviceId,
                appointmentAt,
                TimeSupport.localDateTimeValue(LocalDateTime.parse(appointmentAt).plusMinutes(30)),
                expiresAt,
                now,
                now
            );
        }
    }
}
