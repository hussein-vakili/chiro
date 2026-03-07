package com.lifechiro.web;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.csrf;
import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.user;
import static org.springframework.security.test.web.servlet.response.SecurityMockMvcResultMatchers.authenticated;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.redirectedUrl;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

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
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.MvcResult;

@SpringBootTest
@AutoConfigureMockMvc
class AuthFlowIntegrationTest {
    private static final Path TEST_DB_PATH = Path.of("target", "test-data", "auth-flow-" + UUID.randomUUID() + ".sqlite3");

    @DynamicPropertySource
    static void registerProperties(DynamicPropertyRegistry registry) throws IOException {
        Files.createDirectories(TEST_DB_PATH.getParent());
        Files.deleteIfExists(TEST_DB_PATH);
        registry.add("lifechiro.database.path", () -> TEST_DB_PATH.toAbsolutePath().toString());
        registry.add("lifechiro.demo-invite.token", () -> "integration-invite-token");
        registry.add("lifechiro.demo-invite.email", () -> "integration.patient@example.com");
        registry.add("lifechiro.default-staff.email", () -> "staff@example.com");
        registry.add("lifechiro.default-staff.password", () -> "staffpass123");
        registry.add("lifechiro.default-staff.first-name", () -> "Dr");
        registry.add("lifechiro.default-staff.last-name", () -> "Stone");
    }

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private JdbcTemplate jdbcTemplate;

    @AfterAll
    static void cleanup() throws IOException {
        Files.deleteIfExists(TEST_DB_PATH);
    }

    @Test
    void loginPageRendersSingleCsrfField() throws Exception {
        MvcResult result = mockMvc.perform(get("/login"))
            .andExpect(status().isOk())
            .andReturn();

        String body = result.getResponse().getContentAsString();
        assertThat(countOccurrences(body, "name=\"_csrf\"")).isEqualTo(1);
    }

    @Test
    void staffCanSignInUsingSeededWerkzeugCompatiblePassword() throws Exception {
        mockMvc.perform(post("/login")
                .with(csrf())
                .param("username", "staff@example.com")
                .param("password", "staffpass123"))
            .andExpect(status().is3xxRedirection())
            .andExpect(redirectedUrl("/dashboard"))
            .andExpect(authenticated().withUsername("staff@example.com"));
    }

    @Test
    void acceptingInvitationCreatesClientConsumesHoldAndCreatesAppointment() throws Exception {
        mockMvc.perform(post("/invite/integration-invite-token")
                .with(csrf())
                .param("password", "TempPass123!")
                .param("confirm_password", "TempPass123!"))
            .andExpect(status().is3xxRedirection())
            .andExpect(redirectedUrl("/dashboard"))
            .andExpect(authenticated().withUsername("integration.patient@example.com"));

        Long userId = jdbcTemplate.queryForObject(
            "SELECT id FROM users WHERE lower(email) = lower('integration.patient@example.com')",
            Long.class
        );
        assertThat(userId).isNotNull();

        String acceptedAt = jdbcTemplate.queryForObject(
            "SELECT accepted_at FROM invitations WHERE token = 'integration-invite-token'",
            String.class
        );
        assertThat(acceptedAt).isNotBlank();

        String holdStatus = jdbcTemplate.queryForObject(
            """
            SELECT status
            FROM appointment_slot_holds
            WHERE invitation_id = (SELECT id FROM invitations WHERE token = 'integration-invite-token')
            """,
            String.class
        );
        assertThat(holdStatus).isEqualTo("consumed");

        Integer appointmentCount = jdbcTemplate.queryForObject(
            """
            SELECT COUNT(*)
            FROM appointments
            WHERE source_invitation_id = (SELECT id FROM invitations WHERE token = 'integration-invite-token')
            """,
            Integer.class
        );
        assertThat(appointmentCount).isEqualTo(1);

        Map<String, Object> appointment = jdbcTemplate.queryForMap(
            """
            SELECT requires_payment, payment_status, service_label_snapshot, policy_snapshot_json
            FROM appointments
            WHERE source_invitation_id = (SELECT id FROM invitations WHERE token = 'integration-invite-token')
            LIMIT 1
            """
        );
        assertThat(((Number) appointment.get("requires_payment")).intValue()).isEqualTo(1);
        assertThat(appointment.get("payment_status")).isEqualTo("pending");
        assertThat(appointment.get("service_label_snapshot")).isEqualTo("New Patient Visit");
        assertThat(String.valueOf(appointment.get("policy_snapshot_json"))).contains("New Patient Visit");
    }

    @Test
    void signedInUsersAreRedirectedAwayFromInvitePage() throws Exception {
        mockMvc.perform(get("/invite/integration-invite-token")
                .with(user("staff@example.com").roles("CLINICIAN")))
            .andExpect(status().is3xxRedirection())
            .andExpect(redirectedUrl("/dashboard"));
    }

    private static int countOccurrences(String value, String token) {
        int count = 0;
        int index = 0;
        while ((index = value.indexOf(token, index)) != -1) {
            count += 1;
            index += token.length();
        }
        return count;
    }
}
