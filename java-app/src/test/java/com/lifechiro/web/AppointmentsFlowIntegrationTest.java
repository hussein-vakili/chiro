package com.lifechiro.web;

import static org.assertj.core.api.Assertions.assertThat;
import static org.hamcrest.Matchers.greaterThan;
import static org.hamcrest.Matchers.hasSize;
import static org.hamcrest.Matchers.is;
import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.csrf;
import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.user;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.redirectedUrl;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.redirectedUrlPattern;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.lifechiro.auth.PortalUserDetails;
import com.lifechiro.auth.model.PortalUserRecord;
import com.lifechiro.shared.TimeSupport;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
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
class AppointmentsFlowIntegrationTest {
    private static final Path TEST_DB_PATH = Path.of("target", "test-data", "appointments-flow-" + UUID.randomUUID() + ".sqlite3");

    @DynamicPropertySource
    static void registerProperties(DynamicPropertyRegistry registry) throws IOException {
        Files.createDirectories(TEST_DB_PATH.getParent());
        Files.deleteIfExists(TEST_DB_PATH);
        registry.add("lifechiro.database.path", () -> TEST_DB_PATH.toAbsolutePath().toString());
        registry.add("lifechiro.demo-invite.token", () -> "appointments-flow-invite-token");
        registry.add("lifechiro.demo-invite.email", () -> "appointments.patient@example.com");
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
    void patientAppointmentsPageRendersExistingAppointment() throws Exception {
        PortalUserDetails patient = insertPatient("portal.patient@example.com");
        jdbcTemplate.update(
            """
            INSERT INTO appointments (
                patient_user_id, clinician_user_id, location_id, service_id, appointment_type, status,
                starts_at, ends_at, note, patient_details, billing_status, booking_source,
                requires_payment, payment_status, booking_channel, service_label_snapshot,
                policy_snapshot_json, created_at, updated_at
            ) VALUES (?, 2, 1, 3, 'care_plan', 'scheduled', ?, ?, '', '', 'not_required', 'patient_portal', 0, 'not_required', 'portal_link', 'Follow-up Visit', '{}', ?, ?)
            """,
            patient.user().id(),
            "2026-03-12T10:00",
            "2026-03-12T10:15",
            TimeSupport.isoNowUtc(),
            TimeSupport.isoNowUtc()
        );

        mockMvc.perform(get("/appointments").with(user(patient)))
            .andExpect(status().isOk())
            .andExpect(content().string(org.hamcrest.Matchers.containsString("Your appointments and next booking.")))
            .andExpect(content().string(org.hamcrest.Matchers.containsString("Follow-up Visit")));
    }

    @Test
    void patientCanBookViaApiAndSeeAppointmentInOwnList() throws Exception {
        PortalUserDetails patient = insertPatient("api.patient@example.com");
        SlotSelection slot = firstAvailableSlot(patient);

        mockMvc.perform(post("/api/appointments")
                .with(user(patient))
                .with(csrf())
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(java.util.Map.of(
                    "service_id", 1,
                    "location_id", 1,
                    "clinician_user_id", 2,
                    "appointment_date", slot.date(),
                    "slot_start", slot.slotStart(),
                    "patient_details", "API booking note"
                ))))
            .andExpect(status().isCreated())
            .andExpect(jsonPath("$.ok", is(true)))
            .andExpect(jsonPath("$.appointment.service_label", is("New Patient Visit")));

        mockMvc.perform(get("/api/appointments").with(user(patient)))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.ok", is(true)))
            .andExpect(jsonPath("$.appointments", hasSize(1)))
            .andExpect(jsonPath("$.appointments[0].patient_details", is("API booking note")));
    }

    @Test
    void patientCanSelfBookAndCancelFromPortal() throws Exception {
        PortalUserDetails patient = insertPatient("flow.patient@example.com");
        SlotSelection slot = firstAvailableSlot(patient);

        mockMvc.perform(post("/appointments/self-book")
                .with(user(patient))
                .with(csrf())
                .param("service_id", "1")
                .param("location_id", "1")
                .param("clinician_user_id", "2")
                .param("appointment_date", slot.date())
                .param("slot_start", slot.slotStart())
                .param("patient_details", "Portal booking note"))
            .andExpect(status().is3xxRedirection())
            .andExpect(redirectedUrlPattern("/appointments**"));

        Long appointmentId = jdbcTemplate.queryForObject(
            "SELECT id FROM appointments WHERE patient_user_id = ? ORDER BY id DESC LIMIT 1",
            Long.class,
            patient.user().id()
        );
        assertThat(appointmentId).isNotNull();

        mockMvc.perform(post("/appointments/" + appointmentId + "/cancel")
                .with(user(patient))
                .with(csrf()))
            .andExpect(status().is3xxRedirection())
            .andExpect(redirectedUrl("/appointments"));

        String statusValue = jdbcTemplate.queryForObject(
            "SELECT status FROM appointments WHERE id = ?",
            String.class,
            appointmentId
        );
        assertThat(statusValue).isEqualTo("cancelled");
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

    private SlotSelection firstAvailableSlot(PortalUserDetails patient) throws Exception {
        String holdDate = jdbcTemplate.queryForObject(
            "SELECT substr(starts_at, 1, 10) FROM appointment_slot_holds WHERE invitation_id = (SELECT id FROM invitations WHERE token = 'appointments-flow-invite-token') LIMIT 1",
            String.class
        );
        MvcResult result = mockMvc.perform(get("/api/availability")
                .with(user(patient))
                .param("date", holdDate)
                .param("location_id", "1")
                .param("service_id", "1")
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
