package com.lifechiro.web;

import java.util.HashMap;
import java.util.Map;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping
public class LegacyRouteController {

    private ResponseEntity<Map<String, Object>> notImplemented(String route, String method) {
        Map<String, Object> payload = new HashMap<>();
        payload.put("status", "not_implemented");
        payload.put("route", route);
        payload.put("method", method);
        payload.put("message", "Route scaffolded during Flask-to-Java conversion. Business logic not migrated yet.");
        return ResponseEntity.ok(payload);
    }

    @GetMapping("/")
    public ResponseEntity<Map<String, Object>> root() {
        return notImplemented("/", "GET");
    }

    @RequestMapping(value = "/signup")
    public ResponseEntity<Map<String, Object>> signup() {
        return notImplemented("/signup", "GET/POST");
    }

    @RequestMapping(value = "/invite/{token}")
    public ResponseEntity<Map<String, Object>> invite(@PathVariable String token) {
        return notImplemented("/invite/{token}", "GET/POST");
    }

    @RequestMapping(value = "/login")
    public ResponseEntity<Map<String, Object>> login() {
        return notImplemented("/login", "GET/POST");
    }

    @RequestMapping(value = "/forgot-password")
    public ResponseEntity<Map<String, Object>> forgotPassword() {
        return notImplemented("/forgot-password", "GET/POST");
    }

    @RequestMapping(value = "/reset-password/{token}")
    public ResponseEntity<Map<String, Object>> resetPassword(@PathVariable String token) {
        return notImplemented("/reset-password/{token}", "GET/POST");
    }

    @PostMapping("/logout")
    public ResponseEntity<Map<String, Object>> logout() {
        return notImplemented("/logout", "POST");
    }

    @GetMapping("/dashboard")
    public ResponseEntity<Map<String, Object>> dashboard() {
        return notImplemented("/dashboard", "GET");
    }

    @GetMapping("/staff/dashboard")
    public ResponseEntity<Map<String, Object>> staffDashboard() {
        return notImplemented("/staff/dashboard", "GET");
    }

    @GetMapping("/staff/journal")
    public ResponseEntity<Map<String, Object>> staffJournalGet() {
        return notImplemented("/staff/journal", "GET");
    }

    @PostMapping("/staff/journal")
    public ResponseEntity<Map<String, Object>> staffJournalPost() {
        return notImplemented("/staff/journal", "POST");
    }

    @GetMapping("/staff/learning")
    public ResponseEntity<Map<String, Object>> staffLearningGet() {
        return notImplemented("/staff/learning", "GET");
    }

    @PostMapping("/staff/learning/progress")
    public ResponseEntity<Map<String, Object>> staffLearningProgress() {
        return notImplemented("/staff/learning/progress", "POST");
    }

    @RequestMapping("/staff/invitations/new")
    public ResponseEntity<Map<String, Object>> staffInvitationsNew() {
        return notImplemented("/staff/invitations/new", "GET/POST");
    }

    @GetMapping("/staff/calendar")
    public ResponseEntity<Map<String, Object>> staffCalendar() {
        return notImplemented("/staff/calendar", "GET");
    }

    @GetMapping("/staff/availability")
    public ResponseEntity<Map<String, Object>> staffAvailability() {
        return notImplemented("/staff/availability", "GET");
    }

    @PostMapping("/staff/schedule-windows")
    public ResponseEntity<Map<String, Object>> staffCreateScheduleWindow() {
        return notImplemented("/staff/schedule-windows", "POST");
    }

    @PostMapping("/staff/schedule-windows/{windowId}/delete")
    public ResponseEntity<Map<String, Object>> staffDeleteScheduleWindow(@PathVariable int windowId) {
        return notImplemented("/staff/schedule-windows/{windowId}/delete", "POST");
    }

    @PostMapping("/staff/locations")
    public ResponseEntity<Map<String, Object>> staffCreateLocation() {
        return notImplemented("/staff/locations", "POST");
    }

    @PostMapping("/staff/booking-services")
    public ResponseEntity<Map<String, Object>> staffBookingServices() {
        return notImplemented("/staff/booking-services", "POST");
    }

    @GetMapping("/staff/reminders")
    public ResponseEntity<Map<String, Object>> staffReminders() {
        return notImplemented("/staff/reminders", "GET");
    }

    @PostMapping("/staff/appointments/{appointmentId}/send-reminder")
    public ResponseEntity<Map<String, Object>> staffSendReminder(@PathVariable int appointmentId) {
        return notImplemented("/staff/appointments/{appointmentId}/send-reminder", "POST");
    }

    @PostMapping("/staff/patients/{userId}/appointments")
    public ResponseEntity<Map<String, Object>> staffPatientAppointments(@PathVariable int userId) {
        return notImplemented("/staff/patients/{userId}/appointments", "POST");
    }

    @PostMapping("/staff/patients/{userId}/appointments/{appointmentId}")
    public ResponseEntity<Map<String, Object>> staffPatientAppointmentsUpdate(
        @PathVariable int userId,
        @PathVariable int appointmentId
    ) {
        return notImplemented("/staff/patients/{userId}/appointments/{appointmentId}", "POST");
    }

    @GetMapping("/appointments")
    public ResponseEntity<Map<String, Object>> appointments() {
        return notImplemented("/appointments", "GET");
    }

    @PostMapping("/appointments/self-book")
    public ResponseEntity<Map<String, Object>> appointmentsSelfBook() {
        return notImplemented("/appointments/self-book", "POST");
    }

    @PostMapping("/appointments/{appointmentId}/cancel")
    public ResponseEntity<Map<String, Object>> appointmentsCancel(@PathVariable int appointmentId) {
        return notImplemented("/appointments/{appointmentId}/cancel", "POST");
    }

    @GetMapping("/staff/patients/{userId}")
    public ResponseEntity<Map<String, Object>> staffPatientProfile(@PathVariable int userId) {
        return notImplemented("/staff/patients/{userId}", "GET");
    }

    @GetMapping("/staff/patients/{userId}/summit-assessment")
    public ResponseEntity<Map<String, Object>> staffPatientSummitAssessment(@PathVariable int userId) {
        return notImplemented("/staff/patients/{userId}/summit-assessment", "GET");
    }

    @GetMapping("/staff/patients/{userId}/decision-support")
    public ResponseEntity<Map<String, Object>> staffPatientDecisionSupport(@PathVariable int userId) {
        return notImplemented("/staff/patients/{userId}/decision-support", "GET");
    }

    @GetMapping("/staff/tools/claude-ddx-tool.jsx")
    public ResponseEntity<Map<String, Object>> staffToolsClaudeDdxtool() {
        return notImplemented("/staff/tools/claude-ddx-tool.jsx", "GET");
    }

    @RequestMapping(value = "/practitioner/appointments/{appointmentId}/soap")
    public ResponseEntity<Map<String, Object>> practitionerSoap(@PathVariable int appointmentId) {
        return notImplemented("/practitioner/appointments/{appointmentId}/soap", "GET/POST");
    }

    @PostMapping("/staff/patients/{userId}/notes")
    public ResponseEntity<Map<String, Object>> staffPatientNotes(@PathVariable int userId) {
        return notImplemented("/staff/patients/{userId}/notes", "POST");
    }

    @PostMapping("/staff/patients/{userId}/initial-consult")
    public ResponseEntity<Map<String, Object>> staffPatientInitialConsult(@PathVariable int userId) {
        return notImplemented("/staff/patients/{userId}/initial-consult", "POST");
    }

    @GetMapping("/intake")
    public ResponseEntity<Map<String, Object>> intakeGet() {
        return notImplemented("/intake", "GET");
    }

    @RequestMapping("/api/intake")
    public ResponseEntity<Map<String, Object>> apiIntake() {
        return notImplemented("/api/intake", "GET/POST");
    }

    @GetMapping("/api/locations")
    public ResponseEntity<Map<String, Object>> apiLocations() {
        return notImplemented("/api/locations", "GET");
    }

    @GetMapping("/api/booking-services")
    public ResponseEntity<Map<String, Object>> apiBookingServices() {
        return notImplemented("/api/booking-services", "GET");
    }

    @GetMapping("/api/availability")
    public ResponseEntity<Map<String, Object>> apiAvailability() {
        return notImplemented("/api/availability", "GET");
    }

    @RequestMapping("/api/appointments")
    public ResponseEntity<Map<String, Object>> apiAppointments() {
        return notImplemented("/api/appointments", "GET/POST");
    }

    @GetMapping("/results")
    public ResponseEntity<Map<String, Object>> results() {
        return notImplemented("/results", "GET");
    }

    @GetMapping("/staff/patients/{userId}/results-preview")
    public ResponseEntity<Map<String, Object>> staffPatientResultsPreview(@PathVariable int userId) {
        return notImplemented("/staff/patients/{userId}/results-preview", "GET");
    }
}
