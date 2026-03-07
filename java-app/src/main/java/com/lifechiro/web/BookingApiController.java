package com.lifechiro.web;

import com.lifechiro.auth.PortalUserDetails;
import com.lifechiro.booking.BookingAvailabilityService;
import com.lifechiro.booking.PatientAppointmentsService;
import java.util.LinkedHashMap;
import java.util.Map;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api")
public class BookingApiController {
    private final BookingAvailabilityService bookingAvailabilityService;
    private final PatientAppointmentsService patientAppointmentsService;

    public BookingApiController(
        BookingAvailabilityService bookingAvailabilityService,
        PatientAppointmentsService patientAppointmentsService
    ) {
        this.bookingAvailabilityService = bookingAvailabilityService;
        this.patientAppointmentsService = patientAppointmentsService;
    }

    @GetMapping("/locations")
    public Map<String, Object> locations() {
        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("ok", true);
        payload.put("locations", bookingAvailabilityService.locationsPayload());
        return payload;
    }

    @GetMapping("/booking-services")
    public Map<String, Object> bookingServices() {
        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("ok", true);
        payload.put("services", bookingAvailabilityService.servicesPayload());
        return payload;
    }

    @GetMapping("/availability")
    public Map<String, Object> availability(
        @RequestParam(name = "date", required = false) String dateValue,
        @RequestParam(name = "clinician_user_id", required = false) String clinicianUserIdValue,
        @RequestParam(name = "location_id", required = false) String locationIdValue,
        @RequestParam(name = "service_id", required = false) String serviceIdValue,
        @RequestParam(name = "appointment_type", required = false) String appointmentType,
        @RequestParam(name = "duration_minutes", required = false) String durationMinutesValue,
        @RequestParam(name = "slot_increment_minutes", required = false) String slotIncrementMinutesValue
    ) {
        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("ok", true);
        payload.put(
            "availability",
            bookingAvailabilityService.availabilityPayload(
                dateValue,
                clinicianUserIdValue,
                locationIdValue,
                serviceIdValue,
                appointmentType,
                durationMinutesValue,
                slotIncrementMinutesValue
            )
        );
        return payload;
    }

    @GetMapping("/appointments")
    public Map<String, Object> appointments(
        @AuthenticationPrincipal PortalUserDetails principal,
        @RequestParam(name = "patient_user_id", required = false) Long patientUserId
    ) {
        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("ok", true);
        payload.put("appointments", patientAppointmentsService.listAppointmentsForApi(principal, patientUserId));
        return payload;
    }

    @PostMapping("/appointments")
    public ResponseEntity<Map<String, Object>> createAppointment(
        @AuthenticationPrincipal PortalUserDetails principal,
        @RequestBody Map<String, Object> requestBody
    ) {
        PatientAppointmentsService.BookingActionResult result = patientAppointmentsService.bookFromApi(principal, requestBody);
        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("ok", result.success());
        if (!result.success()) {
            payload.put("errors", java.util.List.of(result.message()));
            return ResponseEntity.status(HttpStatus.BAD_REQUEST).body(payload);
        }
        payload.put("appointment", patientAppointmentsService.serializeAppointment(result.appointment(), !principal.isClient()));
        return ResponseEntity.status(HttpStatus.CREATED).body(payload);
    }
}
