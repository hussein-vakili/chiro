package com.lifechiro.web;

import static org.assertj.core.api.Assertions.assertThat;
import static org.hamcrest.Matchers.containsString;
import static org.hamcrest.Matchers.greaterThan;
import static org.hamcrest.Matchers.hasSize;
import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.csrf;
import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.user;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.redirectedUrl;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.redirectedUrlPattern;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.lifechiro.auth.PortalUserDetails;
import com.lifechiro.auth.model.PortalUserRecord;
import com.lifechiro.shared.TimeSupport;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Map;
import java.util.UUID;
import org.junit.jupiter.api.AfterAll;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.MvcResult;

@SpringBootTest
@AutoConfigureMockMvc
class CarePlanFlowIntegrationTest {
    private static final Path TEST_DB_PATH = Path.of("target", "test-data", "care-plan-flow-" + UUID.randomUUID() + ".sqlite3");

    @DynamicPropertySource
    static void registerProperties(DynamicPropertyRegistry registry) throws IOException {
        Files.createDirectories(TEST_DB_PATH.getParent());
        Files.deleteIfExists(TEST_DB_PATH);
        registry.add("lifechiro.database.path", () -> TEST_DB_PATH.toAbsolutePath().toString());
        registry.add("lifechiro.demo-invite.token", () -> "care-plan-flow-invite-token");
        registry.add("lifechiro.demo-invite.email", () -> "care-plan.patient@example.com");
        registry.add("lifechiro.default-staff.email", () -> "staff@example.com");
        registry.add("lifechiro.default-staff.password", () -> "staffpass123");
        registry.add("lifechiro.default-staff.first-name", () -> "Dr");
        registry.add("lifechiro.default-staff.last-name", () -> "Stone");
    }

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private JdbcTemplate jdbcTemplate;

    @Autowired
    private ObjectMapper objectMapper;

    @AfterAll
    static void cleanup() throws IOException {
        Files.deleteIfExists(TEST_DB_PATH);
    }

    @Test
    void carePlanPageRendersActivePlan() throws Exception {
        PortalUserDetails patient = insertPatient("care.plan.page@example.com");
        SlotSelection slot = firstAvailableSlot(patient, 3);
        insertCarePlan(patient.user().id(), slot.date(), slot.slotStart());

        mockMvc.perform(get("/care-plan").with(user(patient)))
            .andExpect(status().isOk())
            .andExpect(content().string(containsString("6-week care plan")))
            .andExpect(content().string(containsString("Book this visit")));

        Long visitId = jdbcTemplate.queryForObject("SELECT id FROM care_plan_visits LIMIT 1", Long.class);
        mockMvc.perform(get("/appointments").with(user(patient)).param("care_plan_visit_id", String.valueOf(visitId)))
            .andExpect(status().isOk())
            .andExpect(content().string(containsString("This booking is linked to your active care plan")));
    }

    @Test
    void patientCanBookAndReopenCarePlanVisit() throws Exception {
        PortalUserDetails patient = insertPatient("care.plan.flow@example.com");
        SlotSelection slot = firstAvailableSlot(patient, 3);
        long visitId = insertCarePlan(patient.user().id(), slot.date(), slot.slotStart());

        mockMvc.perform(post("/appointments/self-book")
                .with(user(patient))
                .with(csrf())
                .param("care_plan_visit_id", String.valueOf(visitId))
                .param("service_id", "3")
                .param("location_id", "1")
                .param("clinician_user_id", "2")
                .param("appointment_date", slot.date())
                .param("slot_start", slot.slotStart())
                .param("patient_details", "Care plan booking note"))
            .andExpect(status().is3xxRedirection())
            .andExpect(redirectedUrl("/care-plan"));

        Map<String, Object> visitRow = jdbcTemplate.queryForMap(
            "SELECT status, booked, appointment_id FROM care_plan_visits WHERE id = ?",
            visitId
        );
        assertThat(visitRow.get("status")).isEqualTo("scheduled");
        assertThat(((Number) visitRow.get("booked")).intValue()).isEqualTo(1);
        Long appointmentId = ((Number) visitRow.get("appointment_id")).longValue();

        Map<String, Object> appointmentRow = jdbcTemplate.queryForMap(
            "SELECT service_label_snapshot, policy_snapshot_json FROM appointments WHERE id = ?",
            appointmentId
        );
        assertThat(appointmentRow.get("service_label_snapshot")).isEqualTo("Visit 1");
        assertThat(String.valueOf(appointmentRow.get("policy_snapshot_json"))).contains("care_plan_visit_id");

        mockMvc.perform(post("/appointments/" + appointmentId + "/cancel")
                .with(user(patient))
                .with(csrf()))
            .andExpect(status().is3xxRedirection())
            .andExpect(redirectedUrl("/appointments?care_plan_visit_id=" + visitId));

        Map<String, Object> reopenedVisit = jdbcTemplate.queryForMap(
            "SELECT status, booked, appointment_id FROM care_plan_visits WHERE id = ?",
            visitId
        );
        assertThat(reopenedVisit.get("status")).isEqualTo("unbooked");
        assertThat(((Number) reopenedVisit.get("booked")).intValue()).isEqualTo(0);
        assertThat(reopenedVisit.get("appointment_id")).isNull();
    }

    @Test
    void carePlanVisitCanBeBookedViaApi() throws Exception {
        PortalUserDetails patient = insertPatient("care.plan.api@example.com");
        SlotSelection slot = firstAvailableSlot(patient, 3);
        long visitId = insertCarePlan(patient.user().id(), slot.date(), slot.slotStart());

        mockMvc.perform(post("/api/appointments")
                .with(user(patient))
                .with(csrf())
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(Map.of(
                    "care_plan_visit_id", visitId,
                    "service_id", 3,
                    "location_id", 1,
                    "clinician_user_id", 2,
                    "appointment_date", slot.date(),
                    "slot_start", slot.slotStart(),
                    "patient_details", "API care plan"
                ))))
            .andExpect(status().isCreated())
            .andExpect(jsonPath("$.appointment.service_label").value("Visit 1"));
    }

    private PortalUserDetails insertPatient(String email) {
        String createdAt = TimeSupport.isoNowUtc();
        jdbcTemplate.update(
            "INSERT INTO users (first_name, last_name, email, password_hash, role, is_active, created_at) VALUES ('Pat', 'Example', ?, 'unused', 'client', 1, ?)",
            email,
            createdAt
        );
        Long userId = jdbcTemplate.queryForObject(
            "SELECT id FROM users WHERE lower(email) = lower(?) LIMIT 1",
            Long.class,
            email
        );
        return new PortalUserDetails(new PortalUserRecord(userId, "Pat", "Example", email, "unused", "client", true, createdAt));
    }

    private long insertCarePlan(long patientUserId, String suggestedDate, String suggestedStartsAt) {
        String now = TimeSupport.isoNowUtc();
        jdbcTemplate.update(
            """
            INSERT INTO care_plans (
                patient_user_id, clinician_user_id, location_id, service_id, title, frequency_per_week, duration_weeks,
                total_visits, midpoint_visit_number, booking_mode, start_date, start_slot, status, patient_details, note, created_at, updated_at
            ) VALUES (?, 2, 1, 3, '6-week care plan', 2, 6, 12, 6, 'as_you_go', ?, ?, 'active', '', '', ?, ?)
            """,
            patientUserId,
            suggestedDate,
            suggestedStartsAt,
            now,
            now
        );
        Long carePlanId = jdbcTemplate.queryForObject(
            "SELECT id FROM care_plans WHERE patient_user_id = ? ORDER BY id DESC LIMIT 1",
            Long.class,
            patientUserId
        );
        jdbcTemplate.update(
            """
            INSERT INTO care_plan_visits (
                care_plan_id, visit_number, visit_kind, label, suggested_date, suggested_starts_at,
                duration_minutes, fee_amount, status, booked, appointment_id, patient_details, note, created_at, updated_at
            ) VALUES (?, 1, 'follow_up', 'Visit 1', ?, ?, 15, NULL, 'unbooked', 0, NULL, '', '', ?, ?)
            """,
            carePlanId,
            suggestedDate,
            suggestedStartsAt,
            now,
            now
        );
        return jdbcTemplate.queryForObject(
            "SELECT id FROM care_plan_visits WHERE care_plan_id = ? ORDER BY id DESC LIMIT 1",
            Long.class,
            carePlanId
        );
    }

    private SlotSelection firstAvailableSlot(PortalUserDetails patient, int serviceId) throws Exception {
        String holdDate = jdbcTemplate.queryForObject(
            "SELECT substr(starts_at, 1, 10) FROM appointment_slot_holds WHERE invitation_id = (SELECT id FROM invitations WHERE token = 'care-plan-flow-invite-token') LIMIT 1",
            String.class
        );
        MvcResult result = mockMvc.perform(get("/api/availability")
                .with(user(patient))
                .param("date", holdDate)
                .param("location_id", "1")
                .param("service_id", String.valueOf(serviceId))
                .param("clinician_user_id", "2"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.availability.available_slots", hasSize(greaterThan(0))))
            .andReturn();
        JsonNode payload = objectMapper.readTree(result.getResponse().getContentAsString());
        String slotStart = payload.path("availability").path("available_slots").get(0).path("value").asText();
        return new SlotSelection(holdDate, slotStart);
    }

    private record SlotSelection(String date, String slotStart) {
    }
}
