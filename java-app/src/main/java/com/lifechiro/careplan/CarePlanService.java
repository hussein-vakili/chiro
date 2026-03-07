package com.lifechiro.careplan;

import com.lifechiro.booking.BookingAvailabilityService;
import com.lifechiro.shared.TimeSupport;
import java.time.LocalDate;
import java.time.OffsetDateTime;
import java.time.format.DateTimeFormatter;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Optional;
import org.springframework.stereotype.Service;

@Service
public class CarePlanService {
    private static final DateTimeFormatter SHORT_DAY = DateTimeFormatter.ofPattern("EEE dd MMM", Locale.UK);

    private final CarePlanRepository carePlanRepository;
    private final BookingAvailabilityService bookingAvailabilityService;

    public CarePlanService(CarePlanRepository carePlanRepository, BookingAvailabilityService bookingAvailabilityService) {
        this.carePlanRepository = carePlanRepository;
        this.bookingAvailabilityService = bookingAvailabilityService;
    }

    public CarePlanPageModel buildPatientPage(long patientUserId) {
        Optional<Map<String, Object>> planRow = carePlanRepository.findActivePlanForPatient(patientUserId);
        if (planRow.isEmpty()) {
            Map<String, Object> adherence = noPlanAdherence();
            return new CarePlanPageModel(null, List.of(), zeroStats(), null, null, adherence);
        }

        Map<String, Object> plan = buildPlanItem(planRow.get());
        List<Map<String, Object>> visits = carePlanRepository.findVisitsForPlan(longValue(plan.get("id"))).stream()
            .map(this::buildVisitItem)
            .peek(item -> item.put("patient_booking_url", buildPatientBookingUrl(item)))
            .toList();

        Map<String, Object> stats = new LinkedHashMap<>();
        stats.put("completed", (int) visits.stream().filter(item -> "completed".equals(item.get("status"))).count());
        stats.put("booked", (int) visits.stream().filter(item -> boolValue(item.get("booked"))).count());
        stats.put("unbooked", (int) visits.stream().filter(item -> "unbooked".equals(item.get("status"))).count());
        stats.put("cancelled", (int) visits.stream().filter(item -> "cancelled".equals(item.get("status"))).count());
        stats.put("remaining", visits.size() - intValue(stats.get("completed"), 0) - intValue(stats.get("cancelled"), 0));

        String today = LocalDate.now().toString();
        Map<String, Object> nextUnbooked = visits.stream()
            .filter(item -> "unbooked".equals(item.get("status")))
            .min(Comparator.comparing((Map<String, Object> item) -> stringValue(item.get("suggested_date")))
                .thenComparing(item -> intValue(item.get("visit_number"), 0)))
            .orElse(null);
        Map<String, Object> nextBooked = visits.stream()
            .filter(item -> "scheduled".equals(item.get("status")) && stringValue(item.get("effective_date_value")).compareTo(today) >= 0)
            .min(Comparator.comparing((Map<String, Object> item) -> stringValue(item.get("effective_date_value")))
                .thenComparing(item -> intValue(item.get("visit_number"), 0)))
            .orElse(null);

        Map<String, Object> adherence = buildAdherence(plan, visits, stats, nextBooked);
        return new CarePlanPageModel(plan, visits, stats, nextUnbooked, nextBooked, adherence);
    }

    public Optional<Map<String, Object>> findVisitForPatient(long patientUserId, String rawVisitId) {
        Long visitId = longValue(rawVisitId);
        if (visitId == null) {
            return Optional.empty();
        }
        return carePlanRepository.findVisitForPatient(visitId, patientUserId).map(this::buildVisitItem);
    }

    public boolean attachAppointmentToVisit(long patientUserId, long visitId, long appointmentId, String patientDetails, String note, String updatedAt) {
        Map<String, Object> visit = carePlanRepository.findVisitForPatient(visitId, patientUserId).orElse(null);
        if (visit == null) {
            return false;
        }
        if (visit.get("appointment_id") != null) {
            return false;
        }
        carePlanRepository.linkAppointmentToVisit(visitId, appointmentId, patientDetails, note, updatedAt);
        carePlanRepository.refreshPlanStatus(longValue(visit.get("care_plan_id")), updatedAt);
        return true;
    }

    public Optional<String> reopenVisitFromCancelledAppointment(long patientUserId, long appointmentId, String startsAt, String patientDetails, String note, String updatedAt) {
        Map<String, Object> visit = carePlanRepository.findVisitByAppointmentId(appointmentId).orElse(null);
        if (visit == null || longValue(visit.get("patient_user_id")) == null || longValue(visit.get("patient_user_id")) != patientUserId) {
            return Optional.empty();
        }
        if ("completed".equals(stringValue(visit.get("status")))) {
            return Optional.empty();
        }
        carePlanRepository.reopenVisitFromAppointment(appointmentId, startsAt, patientDetails, note, updatedAt);
        carePlanRepository.refreshPlanStatus(longValue(visit.get("care_plan_id")), updatedAt);
        Map<String, Object> reloaded = carePlanRepository.findVisitForPatient(longValue(visit.get("id")), patientUserId)
            .map(this::buildVisitItem)
            .orElse(null);
        if (reloaded == null) {
            return Optional.empty();
        }
        return Optional.of(buildPatientBookingUrl(reloaded));
    }

    public String recommendedBookingDate(Map<String, Object> visit) {
        String suggestedDate = stringValue(visit.get("suggested_date"));
        LocalDate today = LocalDate.now();
        if (!suggestedDate.isBlank()) {
            try {
                LocalDate parsed = LocalDate.parse(suggestedDate);
                if (!parsed.isBefore(today)) {
                    return suggestedDate;
                }
            } catch (Exception ignored) {
            }
        }
        String clinicianChoice = longValue(visit.get("plan_clinician_user_id")) == null ? "any" : String.valueOf(longValue(visit.get("plan_clinician_user_id")));
        return bookingAvailabilityService.nextAvailableDate(
            clinicianChoice,
            longValue(visit.get("plan_location_id")) == null ? null : String.valueOf(longValue(visit.get("plan_location_id"))),
            longValue(visit.get("plan_service_id")) == null ? null : String.valueOf(longValue(visit.get("plan_service_id"))),
            "care_plan",
            String.valueOf(intValue(visit.get("duration_minutes"), 15)),
            null
        );
    }

    private Map<String, Object> buildPlanItem(Map<String, Object> row) {
        String clinicianName = (stringValue(row.get("clinician_first_name")) + " " + stringValue(row.get("clinician_last_name"))).trim();
        Map<String, Object> item = new LinkedHashMap<>();
        item.put("id", longValue(row.get("id")));
        item.put("title", titleOrDefault(stringValue(row.get("title")), intValue(row.get("duration_weeks"), 6), intValue(row.get("frequency_per_week"), 1)));
        item.put("frequency_per_week", intValue(row.get("frequency_per_week"), 1));
        item.put("frequency_label", frequencyLabel(intValue(row.get("frequency_per_week"), 1)));
        item.put("duration_weeks", intValue(row.get("duration_weeks"), 6));
        item.put("total_visits", intValue(row.get("total_visits"), 0));
        item.put("midpoint_visit_number", intValue(row.get("midpoint_visit_number"), 0));
        item.put("booking_mode", stringValue(row.get("booking_mode")));
        item.put("booking_mode_label", bookingModeLabel(stringValue(row.get("booking_mode"))));
        item.put("status", stringValue(row.get("status")));
        item.put("status_label", titleCase(stringValue(row.get("status"))));
        item.put("service_id", longValue(row.get("service_id")));
        item.put("service_label", blankTo(stringValue(row.get("service_label")), "Care plan visit"));
        item.put("start_date", stringValue(row.get("start_date")));
        item.put("start_slot", stringValue(row.get("start_slot")));
        item.put("start_label", stringValue(row.get("start_slot")).isBlank() ? stringValue(row.get("start_date")) : TimeSupport.formatSchedule(stringValue(row.get("start_slot"))));
        item.put("note", stringValue(row.get("note")));
        item.put("patient_details", stringValue(row.get("patient_details")));
        item.put("location_id", longValue(row.get("location_id")));
        item.put("location_name", stringValue(row.get("location_name")));
        item.put("clinician_user_id", longValue(row.get("clinician_user_id")));
        item.put("clinician_name", clinicianName.isBlank() ? null : clinicianName);
        return item;
    }

    private Map<String, Object> buildVisitItem(Map<String, Object> row) {
        String visitKind = blankTo(stringValue(row.get("visit_kind")), "follow_up");
        String suggestedDate = stringValue(row.get("suggested_date"));
        String suggestedStartsAt = stringValue(row.get("suggested_starts_at"));
        if (suggestedStartsAt.isBlank() && !suggestedDate.isBlank()) {
            suggestedStartsAt = suggestedDate + "T09:00";
        }
        String appointmentStartsAt = stringValue(row.get("appointment_starts_at"));
        String effectiveDateValue = appointmentStartsAt.isBlank() ? suggestedDate : safeDatePart(appointmentStartsAt, suggestedDate);
        String effectiveLabel = appointmentStartsAt.isBlank()
            ? blankTo(TimeSupport.formatSchedule(suggestedStartsAt), suggestedDate)
            : blankTo(TimeSupport.formatSchedule(appointmentStartsAt), suggestedDate);
        boolean booked = boolValue(row.get("booked")) || longValue(row.get("appointment_id")) != null;
        String status = stringValue(row.get("status")).trim().toLowerCase(Locale.UK);
        if (status.isBlank()) {
            status = booked ? "scheduled" : "unbooked";
        }

        Map<String, String> visitMeta = visitMeta(visitKind);
        Map<String, String> statusMeta = visitStatusMeta(status);
        String clinicianName = (stringValue(row.get("appointment_clinician_first_name")) + " " + stringValue(row.get("appointment_clinician_last_name"))).trim();

        Map<String, Object> item = new LinkedHashMap<>();
        item.put("id", longValue(row.get("id")));
        item.put("care_plan_id", longValue(row.get("care_plan_id")));
        item.put("visit_number", intValue(row.get("visit_number"), 0));
        item.put("visit_kind", visitKind);
        item.put("visit_kind_label", visitMeta.get("label"));
        item.put("visit_kind_tone", visitMeta.get("tone"));
        item.put("visit_icon", visitMeta.get("icon"));
        item.put("label", blankTo(stringValue(row.get("label")), defaultVisitLabel(intValue(row.get("visit_number"), 0), visitKind)));
        item.put("suggested_date", suggestedDate);
        item.put("suggested_starts_at", suggestedStartsAt);
        item.put("suggested_date_label", formatShortDay(suggestedDate));
        item.put("suggested_long_label", blankTo(TimeSupport.formatSchedule(suggestedStartsAt), suggestedDate));
        item.put("effective_date_value", effectiveDateValue);
        item.put("effective_label", effectiveLabel);
        item.put("duration_minutes", intValue(row.get("duration_minutes"), 15));
        item.put("fee_amount", doubleValue(row.get("fee_amount")));
        item.put("fee_label", doubleValue(row.get("fee_amount")) == null ? null : String.format(Locale.UK, "%.2f GBP", doubleValue(row.get("fee_amount"))));
        item.put("status", status);
        item.put("status_label", statusMeta.get("label"));
        item.put("status_tone", statusMeta.get("tone"));
        item.put("booked", booked);
        item.put("appointment_id", longValue(row.get("appointment_id")));
        item.put("patient_details", stringValue(row.get("patient_details")));
        item.put("note", stringValue(row.get("note")));
        item.put("is_linked", longValue(row.get("appointment_id")) != null);
        item.put("plan_service_id", longValue(row.get("plan_service_id")));
        item.put("plan_location_id", longValue(row.get("plan_location_id")));
        item.put("plan_clinician_user_id", longValue(row.get("plan_clinician_user_id")));
        item.put("plan_status", stringValue(row.get("plan_status")));
        item.put("appointment_status", stringValue(row.get("appointment_status")));
        item.put("appointment_location_name", stringValue(row.get("appointment_location_name")));
        item.put("appointment_clinician_name", clinicianName.isBlank() ? null : clinicianName);
        item.put("patient_booking_url", buildPatientBookingUrl(item));
        return item;
    }

    private Map<String, Object> buildAdherence(
        Map<String, Object> plan,
        List<Map<String, Object>> visits,
        Map<String, Object> stats,
        Map<String, Object> nextBooked
    ) {
        String today = LocalDate.now().toString();
        int totalVisits = Math.max(intValue(plan.get("total_visits"), 0), Math.max(visits.size(), 1));
        int completedCount = intValue(stats.get("completed"), 0);
        int completionPercent = Math.round((completedCount * 100f) / totalVisits);
        List<Map<String, Object>> overdueVisits = visits.stream()
            .filter(item -> "unbooked".equals(item.get("status")) && stringValue(item.get("suggested_date")).compareTo(today) < 0)
            .sorted(Comparator.comparing((Map<String, Object> item) -> stringValue(item.get("suggested_date")))
                .thenComparing(item -> intValue(item.get("visit_number"), 0)))
            .toList();
        List<Map<String, Object>> openVisits = visits.stream()
            .filter(item -> "unbooked".equals(item.get("status")) && stringValue(item.get("suggested_date")).compareTo(today) >= 0)
            .sorted(Comparator.comparing((Map<String, Object> item) -> stringValue(item.get("suggested_date")))
                .thenComparing(item -> intValue(item.get("visit_number"), 0)))
            .toList();
        Map<String, Object> nextActionVisit = !overdueVisits.isEmpty() ? overdueVisits.getFirst() : (openVisits.isEmpty() ? null : openVisits.getFirst());

        if ("completed".equals(plan.get("status"))) {
            return adherencePayload(
                true,
                "completed",
                "life",
                "You've completed this stage of care",
                "Your recommended care-plan visits are complete. Keep an eye on the portal for your next review or maintenance visit.",
                "Open appointments",
                "/appointments",
                "Return to dashboard",
                "/dashboard",
                nextBooked,
                null,
                0,
                0,
                completedCount,
                totalVisits,
                completionPercent
            );
        }

        if (!overdueVisits.isEmpty()) {
            Map<String, Object> focusVisit = overdueVisits.getFirst();
            String detail = overdueVisits.size() == 1
                ? "1 care-plan visit is overdue. Rebook " + stringValue(focusVisit.get("label")).toLowerCase(Locale.UK) + " to stay on track."
                : overdueVisits.size() + " care-plan visits are overdue. Rebook " + stringValue(focusVisit.get("label")).toLowerCase(Locale.UK) + " to stay on track.";
            return adherencePayload(
                true,
                "overdue",
                "rose",
                "You're due for your next visit",
                detail,
                "Rebook overdue visit",
                stringValue(focusVisit.get("patient_booking_url")),
                "Open appointments",
                "/appointments",
                nextBooked,
                focusVisit,
                overdueVisits.size() + openVisits.size(),
                overdueVisits.size(),
                completedCount,
                totalVisits,
                completionPercent
            );
        }

        if (nextActionVisit != null) {
            String detail = stringValue(nextActionVisit.get("label")) + " is ready to book for " + stringValue(nextActionVisit.get("suggested_long_label")) + ".";
            if (nextBooked != null) {
                detail = "Your next visit is booked for " + stringValue(nextBooked.get("effective_label")) + ". You can also secure "
                    + stringValue(nextActionVisit.get("label")).toLowerCase(Locale.UK) + " now.";
            }
            return adherencePayload(
                true,
                "needs_booking",
                nextBooked == null ? "sky" : "warm",
                "Book your next recommended visit",
                detail,
                "Book next visit",
                stringValue(nextActionVisit.get("patient_booking_url")),
                "Open appointments",
                "/appointments",
                nextBooked,
                nextActionVisit,
                openVisits.size(),
                0,
                completedCount,
                totalVisits,
                completionPercent
            );
        }

        if (nextBooked != null) {
            return adherencePayload(
                true,
                "on_track",
                "life",
                "You're on track",
                "Your next care-plan visit is booked for " + stringValue(nextBooked.get("effective_label")) + ".",
                "View appointments",
                "/appointments",
                "Return to dashboard",
                "/dashboard",
                nextBooked,
                null,
                0,
                0,
                completedCount,
                totalVisits,
                completionPercent
            );
        }

        return adherencePayload(
            true,
            "active",
            "muted",
            "Care plan is active",
            "The clinic has published your plan. Open appointments to confirm the next step.",
            "Open appointments",
            "/appointments",
            "Return to dashboard",
            "/dashboard",
            null,
            null,
            0,
            0,
            completedCount,
            totalVisits,
            completionPercent
        );
    }

    private Map<String, Object> adherencePayload(
        boolean exists,
        String state,
        String tone,
        String title,
        String detail,
        String actionLabel,
        String actionUrl,
        String secondaryActionLabel,
        String secondaryActionUrl,
        Map<String, Object> nextBooked,
        Map<String, Object> nextActionVisit,
        int needsBookingCount,
        int overdueCount,
        int completedCount,
        int totalVisits,
        int completionPercent
    ) {
        Map<String, Object> item = new LinkedHashMap<>();
        item.put("exists", exists);
        item.put("state", state);
        item.put("tone", tone);
        item.put("title", title);
        item.put("detail", detail);
        item.put("action_label", actionLabel);
        item.put("action_url", actionUrl);
        item.put("secondary_action_label", secondaryActionLabel);
        item.put("secondary_action_url", secondaryActionUrl);
        item.put("next_booked", nextBooked);
        item.put("next_action_visit", nextActionVisit);
        item.put("needs_booking_count", needsBookingCount);
        item.put("overdue_count", overdueCount);
        item.put("progress_label", completedCount + " of " + totalVisits + " visits completed");
        item.put("completion_percent", completionPercent);
        return item;
    }

    private Map<String, Object> noPlanAdherence() {
        return adherencePayload(
            false,
            "locked",
            "muted",
            "Care plan not yet published",
            "Your chiropractor will publish the next stage of care here after your review.",
            "Open appointments",
            "/appointments",
            "Return to dashboard",
            "/dashboard",
            null,
            null,
            0,
            0,
            0,
            1,
            0
        );
    }

    private Map<String, Object> zeroStats() {
        Map<String, Object> stats = new LinkedHashMap<>();
        stats.put("completed", 0);
        stats.put("booked", 0);
        stats.put("unbooked", 0);
        stats.put("cancelled", 0);
        stats.put("remaining", 0);
        return stats;
    }

    private String buildPatientBookingUrl(Map<String, Object> visit) {
        return "/appointments?care_plan_visit_id=" + longValue(visit.get("id"));
    }

    private Map<String, String> visitMeta(String visitKind) {
        return switch (visitKind) {
            case "progress_check" -> Map.of("label", "Progress Check", "tone", "warm", "icon", "<>");
            case "reassessment" -> Map.of("label", "Reassessment", "tone", "sky", "icon", "**");
            default -> Map.of("label", "Follow-up", "tone", "life", "icon", "->");
        };
    }

    private Map<String, String> visitStatusMeta(String status) {
        return switch (status) {
            case "scheduled" -> Map.of("label", "Booked", "tone", "sky");
            case "completed" -> Map.of("label", "Completed", "tone", "life");
            case "cancelled" -> Map.of("label", "Cancelled", "tone", "rose");
            case "missed" -> Map.of("label", "Missed", "tone", "rose");
            default -> Map.of("label", "Unbooked", "tone", "muted");
        };
    }

    private String bookingModeLabel(String bookingMode) {
        return switch (bookingMode) {
            case "as_you_go" -> "Book as you go";
            default -> "Book all now";
        };
    }

    private String frequencyLabel(int frequencyPerWeek) {
        return switch (frequencyPerWeek) {
            case 2 -> "Twice weekly";
            case 1 -> "Weekly";
            default -> frequencyPerWeek + "x per week";
        };
    }

    private String defaultVisitLabel(int visitNumber, String visitKind) {
        String label = visitMeta(visitKind).get("label");
        return visitNumber > 0 ? label + " " + visitNumber : label;
    }

    private String titleOrDefault(String title, int durationWeeks, int frequencyPerWeek) {
        if (!title.isBlank()) {
            return title;
        }
        return durationWeeks + "-week care plan · " + frequencyLabel(frequencyPerWeek);
    }

    private String formatShortDay(String dateValue) {
        try {
            return SHORT_DAY.format(LocalDate.parse(dateValue));
        } catch (Exception ignored) {
            return dateValue;
        }
    }

    private String safeDatePart(String dateTimeValue, String fallback) {
        if (dateTimeValue == null || dateTimeValue.isBlank()) {
            return fallback;
        }
        if (dateTimeValue.length() >= 10) {
            return dateTimeValue.substring(0, 10);
        }
        try {
            return OffsetDateTime.parse(dateTimeValue).toLocalDate().toString();
        } catch (Exception ignored) {
            return fallback;
        }
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

    private String blankTo(String value, String fallback) {
        return value == null || value.isBlank() ? fallback : value;
    }

    private int intValue(Object value, int defaultValue) {
        if (value instanceof Number number) {
            return number.intValue();
        }
        try {
            String raw = stringValue(value);
            return raw.isBlank() ? defaultValue : Integer.parseInt(raw.trim());
        } catch (Exception ignored) {
            return defaultValue;
        }
    }

    private Long longValue(Object value) {
        if (value instanceof Number number) {
            return number.longValue();
        }
        try {
            String raw = stringValue(value);
            return raw.isBlank() ? null : Long.parseLong(raw.trim());
        } catch (Exception ignored) {
            return null;
        }
    }

    private Double doubleValue(Object value) {
        if (value instanceof Number number) {
            return number.doubleValue();
        }
        try {
            String raw = stringValue(value);
            return raw.isBlank() ? null : Double.parseDouble(raw.trim());
        } catch (Exception ignored) {
            return null;
        }
    }

    private boolean boolValue(Object value) {
        if (value instanceof Boolean bool) {
            return bool;
        }
        if (value instanceof Number number) {
            return number.intValue() != 0;
        }
        String raw = stringValue(value).trim().toLowerCase(Locale.UK);
        return raw.equals("1") || raw.equals("true") || raw.equals("yes") || raw.equals("on");
    }

    public record CarePlanPageModel(
        Map<String, Object> plan,
        List<Map<String, Object>> visits,
        Map<String, Object> stats,
        Map<String, Object> nextUnbooked,
        Map<String, Object> nextBooked,
        Map<String, Object> adherence
    ) {
    }
}
