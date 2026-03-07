package com.lifechiro.booking;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.lifechiro.auth.PortalUserDetails;
import com.lifechiro.auth.UserRepository;
import com.lifechiro.auth.model.PortalUserRecord;
import com.lifechiro.careplan.CarePlanService;
import com.lifechiro.shared.TimeSupport;
import java.time.Instant;
import java.time.LocalDateTime;
import java.time.OffsetDateTime;
import java.time.ZoneId;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Optional;
import org.springframework.stereotype.Service;

@Service
public class PatientAppointmentsService {
    private static final DateTimeFormatter DATE_LABEL = DateTimeFormatter.ofPattern("dd MMM yyyy", Locale.UK);
    private static final DateTimeFormatter TIME_LABEL_24H = DateTimeFormatter.ofPattern("HH:mm", Locale.UK);
    private static final DateTimeFormatter TIME_LABEL_12H = DateTimeFormatter.ofPattern("h:mma", Locale.UK);

    private final BookingRepository bookingRepository;
    private final BookingAvailabilityService bookingAvailabilityService;
    private final UserRepository userRepository;
    private final CarePlanService carePlanService;
    private final ObjectMapper objectMapper;

    public PatientAppointmentsService(
        BookingRepository bookingRepository,
        BookingAvailabilityService bookingAvailabilityService,
        UserRepository userRepository,
        CarePlanService carePlanService,
        ObjectMapper objectMapper
    ) {
        this.bookingRepository = bookingRepository;
        this.bookingAvailabilityService = bookingAvailabilityService;
        this.userRepository = userRepository;
        this.carePlanService = carePlanService;
        this.objectMapper = objectMapper;
    }

    public AppointmentsPageModel buildPatientPage(PortalUserDetails principal, Map<String, String> queryParams) {
        CarePlanService.CarePlanPageModel carePlan = carePlanService.buildPatientPage(principal.user().id());
        Map<String, Object> selectedCarePlanVisit = carePlanService.findVisitForPatient(principal.user().id(), queryParams.get("care_plan_visit_id")).orElse(null);
        List<Map<String, Object>> serviceOptions = bookingAvailabilityService.servicesPayload();
        List<Map<String, Object>> locationOptions = bookingAvailabilityService.locationsPayload();
        List<Map<String, Object>> clinicianOptions = bookingAvailabilityService.clinicianOptions();

        String requestedServiceId = stringValue(queryParams.get("service_id"));
        if (requestedServiceId.isBlank() && selectedCarePlanVisit != null && selectedCarePlanVisit.get("plan_service_id") != null) {
            requestedServiceId = String.valueOf(selectedCarePlanVisit.get("plan_service_id"));
        }
        Map<String, Object> selectedService = selectService(requestedServiceId, serviceOptions)
            .orElseGet(() -> serviceOptions.isEmpty() ? Map.of() : serviceOptions.getFirst());
        String selectedAppointmentType = selectedCarePlanVisit != null ? "care_plan" : stringValue(selectedService.getOrDefault("appointment_type", "initial_consult"));
        int selectedDurationMinutes = selectedCarePlanVisit != null
            ? intValue(selectedCarePlanVisit.get("duration_minutes"), intValue(selectedService.get("duration_minutes"), 30))
            : intValue(selectedService.get("duration_minutes"), 30);
        String routingMode = stringValue(selectedService.getOrDefault("routing_mode", "specific_clinician"));
        boolean allowAnyClincian = "team_round_robin".equals(routingMode);

        Long selectedLocationId = selectOptionId(queryParams.get("location_id"), locationOptions)
            .orElseGet(() -> {
                if (selectedCarePlanVisit != null && selectedCarePlanVisit.get("plan_location_id") != null) {
                    return longValue(selectedCarePlanVisit.get("plan_location_id"));
                }
                return locationOptions.isEmpty() ? null : longValue(locationOptions.getFirst().get("value"));
            });

        String requestedClinicianChoice = queryParams.get("clinician_user_id");
        if ((requestedClinicianChoice == null || requestedClinicianChoice.isBlank()) && selectedCarePlanVisit != null) {
            requestedClinicianChoice = longValue(selectedCarePlanVisit.get("plan_clinician_user_id")) == null
                ? (allowAnyClincian ? "any" : "")
                : String.valueOf(selectedCarePlanVisit.get("plan_clinician_user_id"));
        }
        String selectedClinicianChoice = normalizeClinicianChoice(requestedClinicianChoice, allowAnyClincian, clinicianOptions);
        String bookingDate = stringValue(queryParams.get("appointment_date"));
        if (bookingDate.isBlank()) {
            bookingDate = selectedCarePlanVisit != null
                ? carePlanService.recommendedBookingDate(selectedCarePlanVisit)
                : bookingAvailabilityService.nextAvailableDate(
                    selectedClinicianChoice,
                    selectedLocationId == null ? null : String.valueOf(selectedLocationId),
                    selectedService.isEmpty() ? null : String.valueOf(selectedService.get("id")),
                    selectedAppointmentType,
                    String.valueOf(selectedDurationMinutes),
                    null
                );
        }

        Map<String, Object> availability = bookingAvailabilityService.availabilityPayload(
            bookingDate,
            selectedClinicianChoice,
            selectedLocationId == null ? null : String.valueOf(selectedLocationId),
            selectedService.isEmpty() ? null : String.valueOf(selectedService.get("id")),
            selectedAppointmentType,
            String.valueOf(selectedDurationMinutes),
            null
        );

        List<Map<String, Object>> allAppointments = loadAppointmentsForPatient(principal.user().id());
        List<Map<String, Object>> upcoming = allAppointments.stream().filter(item -> boolValue(item.get("is_upcoming"))).toList();
        List<Map<String, Object>> history = allAppointments.stream()
            .filter(item -> !boolValue(item.get("is_upcoming")))
            .sorted(Comparator.comparing((Map<String, Object> item) -> stringValue(item.get("starts_at"))).reversed())
            .toList();
        Map<String, Long> counts = new LinkedHashMap<>();
        counts.put("initial_consult", countType(upcoming, "initial_consult"));
        counts.put("report_of_findings", countType(upcoming, "report_of_findings"));
        counts.put("care_plan", countType(upcoming, "care_plan"));

        String bookingDisabledReason = bookingAvailabilityService.onlineBookingEnabled()
            ? null
            : "Online booking is disabled in clinic settings. Contact the clinic to schedule a visit.";

        return new AppointmentsPageModel(
            upcoming,
            history,
            upcoming.isEmpty() ? null : upcoming.getFirst(),
            counts,
            carePlan,
            selectedCarePlanVisit,
            serviceOptions,
            locationOptions,
            clinicianOptions,
            selectedService,
            selectedAppointmentType,
            selectedDurationMinutes,
            selectedLocationId,
            selectedClinicianChoice,
            allowAnyClincian,
            bookingDate,
            availability,
            bookingDisabledReason
        );
    }

    public List<Map<String, Object>> listAppointmentsForApi(PortalUserDetails principal, Long requestedPatientUserId) {
        boolean includeInternal = !principal.isClient();
        List<Map<String, Object>> rows;
        if (principal.isClient()) {
            rows = bookingRepository.findPatientAppointments(principal.user().id());
        } else if (requestedPatientUserId != null) {
            rows = bookingRepository.findPatientAppointments(requestedPatientUserId);
        } else {
            rows = bookingRepository.findAllAppointments();
        }
        return rows.stream().map(row -> serializeAppointment(buildAppointmentItem(row), includeInternal)).toList();
    }

    public BookingActionResult bookFromPortal(PortalUserDetails principal, Map<String, String> formData) {
        return createAppointment(principal, formData, "patient_portal", "portal_link");
    }

    public BookingActionResult bookFromApi(PortalUserDetails principal, Map<String, Object> payload) {
        Map<String, String> formData = new LinkedHashMap<>();
        payload.forEach((key, value) -> formData.put(key, value == null ? "" : String.valueOf(value)));
        return createAppointment(principal, formData, principal.isClient() ? "api_client" : "api_staff", "api");
    }

    public BookingActionResult cancelAppointment(PortalUserDetails principal, long appointmentId) {
        Optional<Map<String, Object>> appointmentRow = bookingRepository.findPatientAppointmentById(appointmentId, principal.user().id());
        if (appointmentRow.isEmpty()) {
            return new BookingActionResult(false, "Appointment could not be found.", null, null, null);
        }
        Map<String, Object> appointment = buildAppointmentItem(appointmentRow.get());
        if (!"scheduled".equals(appointment.get("status"))) {
            return new BookingActionResult(false, "Only scheduled appointments can be cancelled.", null, null, null);
        }
        if (!boolValue(appointment.get("can_self_cancel"))) {
            return new BookingActionResult(false, "This appointment is inside the minimum notice window and can no longer be cancelled online.", null, null, null);
        }
        String now = TimeSupport.isoNowUtc();
        bookingRepository.cancelPatientAppointment(appointmentId, principal.user().id(), now);
        bookingRepository.logBookingEvent(
            "booking_cancelled",
            appointmentId,
            principal.user().id(),
            toJson(Map.of("source", "patient_portal", "self_service", true)),
            now
        );
        String redirectUrl = carePlanService.reopenVisitFromCancelledAppointment(
            principal.user().id(),
            appointmentId,
            stringValue(appointment.get("starts_at")),
            stringValue(appointment.get("patient_details")),
            stringValue(appointment.get("note")),
            now
        ).orElse(null);
        String message = redirectUrl == null
            ? "Appointment cancelled. You can book a new slot anytime."
            : "Appointment cancelled. Choose a new time to stay on track with your care plan.";
        return new BookingActionResult(true, message, appointmentId, appointment, redirectUrl);
    }

    private BookingActionResult createAppointment(PortalUserDetails principal, Map<String, String> formData, String bookingSource, String bookingChannel) {
        if (principal.isClient() && !bookingAvailabilityService.onlineBookingEnabled()) {
            return new BookingActionResult(false, "Online booking is disabled in clinic settings.", null, null, null);
        }

        String rawCarePlanVisitId = stringValue(formData.get("care_plan_visit_id"));
        Map<String, Object> carePlanVisit = null;
        Optional<Map<String, Object>> selectedService = selectService(formData.get("service_id"), bookingAvailabilityService.servicesPayload());
        if (selectedService.isEmpty()) {
            return new BookingActionResult(false, "Choose a valid appointment type.", null, null, null);
        }
        String appointmentType = stringValue(selectedService.get().get("appointment_type"));
        String slotStart = stringValue(formData.get("slot_start"));
        String appointmentDate = stringValue(formData.get("appointment_date"));
        String patientDetails = stringValue(formData.get("patient_details"));
        Long locationId = selectOptionId(formData.get("location_id"), bookingAvailabilityService.locationsPayload()).orElse(null);

        Long patientUserId = principal.user().id();
        if (!principal.isClient()) {
            String requestedPatientId = stringValue(formData.get("patient_user_id"));
            Integer parsedPatientId = parseInteger(requestedPatientId);
            if (parsedPatientId == null) {
                return new BookingActionResult(false, "A valid patient_user_id is required for staff bookings.", null, null, null);
            }
            PortalUserRecord patient = userRepository.findById(parsedPatientId.longValue()).orElse(null);
            if (patient == null || !"client".equalsIgnoreCase(patient.role())) {
                return new BookingActionResult(false, "A valid patient_user_id is required for staff bookings.", null, null, null);
            }
            patientUserId = patient.id();
        }

        if (!rawCarePlanVisitId.isBlank()) {
            carePlanVisit = carePlanService.findVisitForPatient(patientUserId, rawCarePlanVisitId).orElse(null);
            if (carePlanVisit == null) {
                return new BookingActionResult(false, "That care-plan visit could not be loaded.", null, null, null);
            }
            if (!"care_plan".equals(appointmentType)) {
                return new BookingActionResult(false, "This rebooking link is only for care-plan visits.", null, null, null);
            }
            if (carePlanVisit.get("appointment_id") != null) {
                return new BookingActionResult(false, "That care-plan step is already booked.", null, null, null);
            }
            if (locationId == null) {
                locationId = longValue(carePlanVisit.get("plan_location_id"));
            }
        }
        if (locationId == null) {
            return new BookingActionResult(false, "Choose a valid clinic location.", null, null, null);
        }

        String clinicianChoiceSeed = formData.get("clinician_user_id");
        if ((clinicianChoiceSeed == null || clinicianChoiceSeed.isBlank()) && carePlanVisit != null && carePlanVisit.get("plan_clinician_user_id") != null) {
            clinicianChoiceSeed = String.valueOf(carePlanVisit.get("plan_clinician_user_id"));
        }
        String clinicianChoice = normalizeClinicianChoice(
            clinicianChoiceSeed,
            "team_round_robin".equals(stringValue(selectedService.get().get("routing_mode"))),
            bookingAvailabilityService.clinicianOptions()
        );

        if (slotStart.isBlank()) {
            return new BookingActionResult(false, "Choose an available time slot.", null, null, null);
        }
        if (!appointmentDate.isBlank() && !slotStart.startsWith(appointmentDate)) {
            return new BookingActionResult(false, "Selected slot does not match the chosen date.", null, null, null);
        }

        int requestedDuration = carePlanVisit == null
            ? intValue(selectedService.get().get("duration_minutes"), 30)
            : intValue(carePlanVisit.get("duration_minutes"), intValue(selectedService.get().get("duration_minutes"), 30));
        Map<String, Object> availability = bookingAvailabilityService.availabilityPayload(
            appointmentDate.isBlank() ? slotStart.substring(0, Math.min(10, slotStart.length())) : appointmentDate,
            clinicianChoice,
            String.valueOf(locationId),
            String.valueOf(selectedService.get().get("id")),
            appointmentType,
            String.valueOf(requestedDuration),
            null
        );
        String availabilityError = stringValue(availability.get("error"));
        if (!availabilityError.isBlank()) {
            return new BookingActionResult(false, availabilityError, null, null, null);
        }

        @SuppressWarnings("unchecked")
        List<Map<String, Object>> availableSlots = (List<Map<String, Object>>) availability.get("available_slots");
        Map<String, Object> selectedSlot = availableSlots == null
            ? null
            : availableSlots.stream().filter(item -> slotStart.equals(stringValue(item.get("value")))).findFirst().orElse(null);
        if (selectedSlot == null) {
            return new BookingActionResult(false, "Selected slot is no longer available.", null, null, null);
        }

        LocalDateTime startsAt = parseDateTime(slotStart);
        if (startsAt == null) {
            return new BookingActionResult(false, "Choose a valid available time slot.", null, null, null);
        }
        int durationMinutes = intValue(availability.get("duration_minutes"), requestedDuration);
        LocalDateTime endsAt = startsAt.plusMinutes(durationMinutes);
        Long assignedClinicianId = longValue(selectedSlot.get("clinician_user_id"));
        String now = TimeSupport.isoNowUtc();
        String billingStatus = boolValue(availability.get("requires_payment")) ? "pending" : "not_required";
        Double paymentAmount = doubleValue(availability.get("price_amount"));
        String serviceLabel = carePlanVisit == null
            ? stringValue(availability.get("service_label"))
            : blankIfEmpty(stringValue(carePlanVisit.get("label")), stringValue(availability.get("service_label")));

        long appointmentId = bookingRepository.createAppointment(
            patientUserId,
            assignedClinicianId,
            locationId,
            longValue(availability.get("service_id")),
            stringValue(availability.get("appointment_type")),
            "scheduled",
            TimeSupport.localDateTimeValue(startsAt),
            TimeSupport.localDateTimeValue(endsAt),
            patientDetails,
            patientDetails,
            billingStatus,
            "",
            null,
            boolValue(availability.get("requires_payment")),
            billingStatus,
            paymentAmount,
            bookingChannel,
            serviceLabel,
            toJson(buildPolicySnapshot(availability, carePlanVisit)),
            bookingSource,
            now
        );
        if (carePlanVisit != null) {
            carePlanService.attachAppointmentToVisit(patientUserId, longValue(carePlanVisit.get("id")), appointmentId, patientDetails, patientDetails, now);
        }
        bookingRepository.logBookingEvent(
            "booking_created",
            appointmentId,
            patientUserId,
            toJson(Map.of(
                "source", bookingSource,
                "service_id", longValue(availability.get("service_id")),
                "service_label", stringValue(availability.get("service_label")),
                "location_id", locationId,
                "clinician_user_id", assignedClinicianId
            )),
            now
        );
        Map<String, Object> createdAppointment = buildAppointmentItem(bookingRepository.findAppointmentById(appointmentId).orElseThrow());
        String message = carePlanVisit == null
            ? "Appointment booked from your portal."
            : "Your next recommended care-plan visit is booked.";
        String redirectUrl = carePlanVisit == null ? null : "/care-plan";
        return new BookingActionResult(true, message, appointmentId, createdAppointment, redirectUrl);
    }

    private List<Map<String, Object>> loadAppointmentsForPatient(long patientUserId) {
        return bookingRepository.findPatientAppointments(patientUserId).stream().map(this::buildAppointmentItem).toList();
    }

    private Map<String, Object> buildAppointmentItem(Map<String, Object> row) {
        String startsAtValue = stringValue(row.get("starts_at"));
        String endsAtValue = stringValue(row.get("ends_at"));
        LocalDateTime startsAt = parseDateTime(startsAtValue);
        LocalDateTime endsAt = parseDateTime(endsAtValue);
        String appointmentType = stringValue(row.get("appointment_type"));
        String status = stringValue(row.get("status"));
        String serviceLabel = stringValue(row.get("service_label"));
        if (serviceLabel.isBlank()) {
            serviceLabel = stringValue(row.get("service_label_snapshot"));
        }
        if (serviceLabel.isBlank()) {
            serviceLabel = appointmentTypeLabel(appointmentType);
        }
        int serviceMinNoticeMinutes = intValue(row.get("service_min_notice_minutes"), 0);
        int policyMinNoticeMinutes = Math.max(serviceMinNoticeMinutes, bookingAvailabilityService.currentCancellationWindowMinutes());
        LocalDateTime cancellationCutoff = startsAt == null ? null : startsAt.minusMinutes(policyMinNoticeMinutes);
        boolean canSelfCancel = startsAt != null
            && "scheduled".equals(status)
            && cancellationCutoff != null
            && LocalDateTime.now().isBefore(cancellationCutoff);
        String clinicianName = (stringValue(row.get("clinician_first_name")) + " " + stringValue(row.get("clinician_last_name"))).trim();
        String patientName = (stringValue(row.get("patient_first_name")) + " " + stringValue(row.get("patient_last_name"))).trim();
        boolean isUpcoming = startsAt != null && "scheduled".equals(status) && !startsAt.isBefore(LocalDateTime.now());

        Map<String, Object> item = new LinkedHashMap<>();
        item.put("id", longValue(row.get("id")));
        item.put("patient_user_id", longValue(row.get("patient_user_id")));
        item.put("clinician_user_id", longValue(row.get("clinician_user_id")));
        item.put("location_id", longValue(row.get("location_id")));
        item.put("location_name", stringValue(row.get("location_name")));
        item.put("service_id", longValue(row.get("service_id")));
        item.put("service_key", stringValue(row.get("service_key")));
        item.put("service_label", serviceLabel);
        item.put("service_duration_minutes", intValue(row.get("service_duration_minutes"), 0));
        item.put("service_buffer_before_minutes", intValue(row.get("service_buffer_before_minutes"), 0));
        item.put("service_buffer_after_minutes", intValue(row.get("service_buffer_after_minutes"), 0));
        item.put("service_routing_mode", stringValue(row.get("service_routing_mode")));
        item.put("service_routing_mode_label", routingModeLabel(stringValue(row.get("service_routing_mode"))));
        item.put("appointment_type", appointmentType);
        item.put("appointment_type_label", appointmentTypeLabel(appointmentType));
        item.put("status", status);
        item.put("status_label", appointmentStatusLabel(status));
        item.put("starts_at", startsAtValue);
        item.put("ends_at", endsAtValue);
        item.put("starts_label", TimeSupport.formatSchedule(startsAtValue));
        item.put("date_label", startsAt == null ? startsAtValue : DATE_LABEL.format(startsAt));
        item.put("time_label", startsAt == null ? "" : formatTimeLabel(startsAt));
        item.put("end_time_label", endsAt == null ? null : formatTimeLabel(endsAt));
        item.put("note", stringValue(row.get("note")));
        item.put("patient_details", stringValue(row.get("patient_details")));
        item.put("booking_source", stringValue(row.get("booking_source")));
        item.put("clinician_name", clinicianName.isBlank() ? null : clinicianName);
        item.put("patient_name", patientName.isBlank() ? null : patientName);
        item.put("patient_email", stringValue(row.get("patient_email")));
        item.put("billing_status", stringValue(row.get("billing_status")));
        item.put("billing_status_label", billingStatusLabel(stringValue(row.get("billing_status"))));
        item.put("billing_code", stringValue(row.get("billing_code")));
        item.put("billing_amount", doubleValue(row.get("billing_amount")));
        item.put("requires_payment", boolValue(row.get("requires_payment")) || boolValue(row.get("service_requires_payment")));
        item.put("payment_status", stringValue(row.get("payment_status")));
        item.put("payment_amount", doubleValue(row.get("payment_amount")) == null ? doubleValue(row.get("service_price_amount")) : doubleValue(row.get("payment_amount")));
        item.put("booking_channel", stringValue(row.get("booking_channel")));
        item.put("can_self_cancel", canSelfCancel);
        item.put("cancellation_cutoff_at", cancellationCutoff == null ? null : TimeSupport.localDateTimeValue(cancellationCutoff));
        item.put("cancellation_policy_label", cancellationCutoff == null ? null : "Changes allowed until " + TimeSupport.formatSchedule(TimeSupport.localDateTimeValue(cancellationCutoff)));
        item.put("is_upcoming", isUpcoming);
        return item;
    }

    public Map<String, Object> serializeAppointment(Map<String, Object> item, boolean includeInternal) {
        Map<String, Object> data = new LinkedHashMap<>();
        data.put("id", item.get("id"));
        data.put("patient_user_id", item.get("patient_user_id"));
        data.put("clinician_user_id", item.get("clinician_user_id"));
        data.put("location_id", item.get("location_id"));
        data.put("location_name", item.get("location_name"));
        data.put("service_id", item.get("service_id"));
        data.put("service_key", item.get("service_key"));
        data.put("service_label", item.get("service_label"));
        data.put("service_duration_minutes", item.get("service_duration_minutes"));
        data.put("service_buffer_before_minutes", item.get("service_buffer_before_minutes"));
        data.put("service_buffer_after_minutes", item.get("service_buffer_after_minutes"));
        data.put("service_routing_mode", item.get("service_routing_mode"));
        data.put("service_routing_mode_label", item.get("service_routing_mode_label"));
        data.put("appointment_type", item.get("appointment_type"));
        data.put("appointment_type_label", item.get("appointment_type_label"));
        data.put("status", item.get("status"));
        data.put("status_label", item.get("status_label"));
        data.put("starts_at", item.get("starts_at"));
        data.put("ends_at", item.get("ends_at"));
        data.put("starts_label", item.get("starts_label"));
        data.put("date_label", item.get("date_label"));
        data.put("time_label", item.get("time_label"));
        data.put("end_time_label", item.get("end_time_label"));
        data.put("note", item.get("note"));
        data.put("patient_details", item.get("patient_details"));
        data.put("booking_source", item.get("booking_source"));
        data.put("clinician_name", item.get("clinician_name"));
        data.put("billing_status", item.get("billing_status"));
        data.put("billing_status_label", item.get("billing_status_label"));
        data.put("billing_code", item.get("billing_code"));
        data.put("billing_amount", item.get("billing_amount"));
        data.put("requires_payment", item.get("requires_payment"));
        data.put("payment_status", item.get("payment_status"));
        data.put("payment_amount", item.get("payment_amount"));
        data.put("booking_channel", item.get("booking_channel"));
        data.put("can_self_cancel", item.get("can_self_cancel"));
        data.put("cancellation_cutoff_at", item.get("cancellation_cutoff_at"));
        if (includeInternal) {
            data.put("patient_name", item.get("patient_name"));
            data.put("patient_email", item.get("patient_email"));
        }
        return data;
    }

    private Optional<Map<String, Object>> selectService(String serviceIdValue, List<Map<String, Object>> services) {
        Long serviceId = longValue(serviceIdValue);
        if (serviceId == null) {
            return Optional.empty();
        }
        return services.stream().filter(item -> serviceId.equals(longValue(item.get("id")))).findFirst();
    }

    private Optional<Long> selectOptionId(String rawValue, List<Map<String, Object>> options) {
        Long value = longValue(rawValue);
        if (value == null) {
            return Optional.empty();
        }
        return options.stream().map(item -> longValue(item.get("value"))).filter(value::equals).findFirst();
    }

    private String normalizeClinicianChoice(String rawValue, boolean allowAnyClincian, List<Map<String, Object>> clinicianOptions) {
        String trimmed = stringValue(rawValue).trim();
        if (allowAnyClincian && (trimmed.isBlank() || "any".equalsIgnoreCase(trimmed) || "team".equalsIgnoreCase(trimmed))) {
            return "any";
        }
        Long clinicianId = longValue(trimmed);
        if (clinicianId != null) {
            boolean valid = clinicianOptions.stream().anyMatch(item -> clinicianId.equals(longValue(item.get("value"))));
            if (valid) {
                return String.valueOf(clinicianId);
            }
        }
        if (allowAnyClincian) {
            return "any";
        }
        return clinicianOptions.isEmpty() ? "" : String.valueOf(clinicianOptions.getFirst().get("value"));
    }

    private long countType(List<Map<String, Object>> items, String appointmentType) {
        return items.stream().filter(item -> appointmentType.equals(item.get("appointment_type"))).count();
    }

    private Map<String, Object> buildPolicySnapshot(Map<String, Object> availability, Map<String, Object> carePlanVisit) {
        Map<String, Object> snapshot = new LinkedHashMap<>();
        snapshot.put("service_id", availability.get("service_id"));
        snapshot.put("service_label", carePlanVisit == null ? availability.get("service_label") : blankIfEmpty(carePlanVisit.get("label"), availability.get("service_label")));
        snapshot.put("appointment_type", availability.get("appointment_type"));
        snapshot.put("duration_minutes", carePlanVisit == null ? availability.get("duration_minutes") : carePlanVisit.get("duration_minutes"));
        snapshot.put("buffer_before_minutes", availability.get("buffer_before_minutes"));
        snapshot.put("buffer_after_minutes", availability.get("buffer_after_minutes"));
        snapshot.put("requires_payment", availability.get("requires_payment"));
        snapshot.put("price_amount", availability.get("price_amount"));
        snapshot.put("currency", availability.get("currency"));
        snapshot.put("min_notice_minutes", availability.get("min_notice_minutes"));
        snapshot.put("max_bookings_per_day", availability.get("max_bookings_per_day"));
        snapshot.put("routing_mode", availability.get("routing_mode"));
        if (carePlanVisit != null) {
            snapshot.put("care_plan_visit_id", carePlanVisit.get("id"));
            snapshot.put("visit_kind", carePlanVisit.get("visit_kind"));
        }
        return snapshot;
    }

    private String toJson(Object value) {
        try {
            return objectMapper.writeValueAsString(value);
        } catch (JsonProcessingException exception) {
            throw new IllegalStateException("Failed to serialize booking payload", exception);
        }
    }

    private LocalDateTime parseDateTime(String value) {
        if (value == null || value.isBlank()) {
            return null;
        }
        try {
            return LocalDateTime.parse(value);
        } catch (Exception ignored) {
        }
        try {
            return OffsetDateTime.parse(value).toLocalDateTime();
        } catch (Exception ignored) {
        }
        try {
            return LocalDateTime.ofInstant(Instant.parse(value), ZoneId.systemDefault());
        } catch (Exception ignored) {
        }
        return null;
    }

    private String formatTimeLabel(LocalDateTime value) {
        String timeFormat = stringValue(bookingRepository.findAppSetting("calendar_time_format"));
        if ("12h".equalsIgnoreCase(timeFormat)) {
            return TIME_LABEL_12H.format(value).toLowerCase(Locale.UK);
        }
        return TIME_LABEL_24H.format(value);
    }

    private String appointmentTypeLabel(String appointmentType) {
        return switch (appointmentType) {
            case "initial_consult" -> "Initial Consultation";
            case "report_of_findings" -> "Report of Findings";
            case "care_plan" -> "Care Plan Visit";
            default -> titleCase(appointmentType);
        };
    }

    private String appointmentStatusLabel(String status) {
        return switch (status) {
            case "scheduled" -> "Scheduled";
            case "completed" -> "Completed";
            case "cancelled" -> "Cancelled";
            default -> titleCase(status);
        };
    }

    private String billingStatusLabel(String status) {
        return switch (status) {
            case "paid" -> "Paid";
            case "not_required" -> "Not required";
            case "pending" -> "Pending";
            default -> titleCase(status);
        };
    }

    private String routingModeLabel(String routingMode) {
        return switch (routingMode) {
            case "team_round_robin" -> "Any available chiropractor";
            default -> "Specific chiropractor";
        };
    }

    private String titleCase(String value) {
        if (value == null || value.isBlank()) {
            return "";
        }
        String[] parts = value.replace('_', ' ').split("\\s+");
        StringBuilder builder = new StringBuilder();
        for (String part : parts) {
            if (part.isBlank()) {
                continue;
            }
            if (!builder.isEmpty()) {
                builder.append(' ');
            }
            builder.append(part.substring(0, 1).toUpperCase(Locale.UK));
            builder.append(part.substring(1).toLowerCase(Locale.UK));
        }
        return builder.toString();
    }

    private String stringValue(Object value) {
        return value == null ? "" : String.valueOf(value);
    }

    private String blankIfEmpty(Object preferred, Object fallback) {
        String preferredValue = stringValue(preferred);
        return preferredValue.isBlank() ? stringValue(fallback) : preferredValue;
    }

    private boolean boolValue(Object value) {
        if (value == null) {
            return false;
        }
        if (value instanceof Boolean booleanValue) {
            return booleanValue;
        }
        if (value instanceof Number number) {
            return number.intValue() != 0;
        }
        String rawValue = String.valueOf(value).trim().toLowerCase(Locale.UK);
        return rawValue.equals("1") || rawValue.equals("true") || rawValue.equals("yes") || rawValue.equals("on");
    }

    private Integer parseInteger(String value) {
        try {
            return value == null || value.isBlank() ? null : Integer.parseInt(value.trim());
        } catch (Exception ignored) {
            return null;
        }
    }

    private int intValue(Object value, int defaultValue) {
        if (value instanceof Number number) {
            return number.intValue();
        }
        Integer parsed = parseInteger(stringValue(value));
        return parsed == null ? defaultValue : parsed;
    }

    private Long longValue(Object value) {
        if (value instanceof Number number) {
            return number.longValue();
        }
        try {
            String rawValue = stringValue(value);
            return rawValue.isBlank() ? null : Long.parseLong(rawValue.trim());
        } catch (Exception ignored) {
            return null;
        }
    }

    private Double doubleValue(Object value) {
        if (value instanceof Number number) {
            return number.doubleValue();
        }
        try {
            String rawValue = stringValue(value);
            return rawValue.isBlank() ? null : Double.parseDouble(rawValue.trim());
        } catch (Exception ignored) {
            return null;
        }
    }

    public record BookingActionResult(
        boolean success,
        String message,
        Long appointmentId,
        Map<String, Object> appointment,
        String redirectUrl
    ) {
    }

    public record AppointmentsPageModel(
        List<Map<String, Object>> upcomingAppointments,
        List<Map<String, Object>> appointmentHistory,
        Map<String, Object> nextAppointment,
        Map<String, Long> counts,
        CarePlanService.CarePlanPageModel carePlan,
        Map<String, Object> selectedCarePlanVisit,
        List<Map<String, Object>> serviceOptions,
        List<Map<String, Object>> locationOptions,
        List<Map<String, Object>> clinicianOptions,
        Map<String, Object> selectedService,
        String selectedAppointmentType,
        int selectedDurationMinutes,
        Long selectedLocationId,
        String selectedClinicianChoice,
        boolean allowAnyClinician,
        String bookingDate,
        Map<String, Object> availability,
        String bookingDisabledReason
    ) {
    }
}
