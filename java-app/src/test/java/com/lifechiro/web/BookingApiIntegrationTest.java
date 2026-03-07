package com.lifechiro.web;

import static org.hamcrest.Matchers.greaterThan;
import static org.hamcrest.Matchers.hasItem;
import static org.hamcrest.Matchers.hasSize;
import static org.hamcrest.Matchers.is;
import static org.hamcrest.Matchers.not;
import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.user;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
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

@SpringBootTest
@AutoConfigureMockMvc
class BookingApiIntegrationTest {
    private static final Path TEST_DB_PATH = Path.of("target", "test-data", "booking-api-" + UUID.randomUUID() + ".sqlite3");

    @DynamicPropertySource
    static void registerProperties(DynamicPropertyRegistry registry) throws IOException {
        Files.createDirectories(TEST_DB_PATH.getParent());
        Files.deleteIfExists(TEST_DB_PATH);
        registry.add("lifechiro.database.path", () -> TEST_DB_PATH.toAbsolutePath().toString());
        registry.add("lifechiro.demo-invite.token", () -> "booking-api-invite-token");
        registry.add("lifechiro.demo-invite.email", () -> "booking.patient@example.com");
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
    void bookingInventoryApisReturnSeededLocationsAndServices() throws Exception {
        mockMvc.perform(get("/api/locations").with(user("staff@example.com").roles("CLINICIAN")))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.ok", is(true)))
            .andExpect(jsonPath("$.locations", hasSize(1)))
            .andExpect(jsonPath("$.locations[0].label", is("Main Clinic")));

        mockMvc.perform(get("/api/booking-services").with(user("staff@example.com").roles("CLINICIAN")))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.ok", is(true)))
            .andExpect(jsonPath("$.services", hasSize(greaterThan(0))))
            .andExpect(jsonPath("$.services[*].label", hasItem("New Patient Visit")));
    }

    @Test
    void availabilityApiReturnsSlotsAndBlocksTheSeededHeldSlot() throws Exception {
        String holdDate = jdbcTemplate.queryForObject(
            "SELECT substr(starts_at, 1, 10) FROM appointment_slot_holds WHERE invitation_id = (SELECT id FROM invitations WHERE token = 'booking-api-invite-token') LIMIT 1",
            String.class
        );
        String heldSlot = jdbcTemplate.queryForObject(
            "SELECT starts_at FROM appointment_slot_holds WHERE invitation_id = (SELECT id FROM invitations WHERE token = 'booking-api-invite-token') LIMIT 1",
            String.class
        );

        mockMvc.perform(get("/api/availability")
                .with(user("staff@example.com").roles("CLINICIAN"))
                .param("date", holdDate)
                .param("location_id", "1")
                .param("service_id", "1")
                .param("clinician_user_id", "2"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.ok", is(true)))
            .andExpect(jsonPath("$.availability.date_value", is(holdDate)))
            .andExpect(jsonPath("$.availability.service_label", is("New Patient Visit")))
            .andExpect(jsonPath("$.availability.available_slots", hasSize(greaterThan(0))))
            .andExpect(jsonPath("$.availability.available_slots[*].value", not(hasItem(heldSlot))))
            .andExpect(jsonPath("$.availability.booked_windows[*].label", hasItem("New Patient Visit hold")));
    }
}
