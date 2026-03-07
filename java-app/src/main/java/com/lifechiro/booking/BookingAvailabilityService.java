package com.lifechiro.booking;

import com.lifechiro.shared.TimeSupport;
import java.time.Instant;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.LocalTime;
import java.time.OffsetDateTime;
import java.time.ZoneId;
import java.time.format.DateTimeFormatter;
import java.time.format.TextStyle;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
import org.springframework.stereotype.Service;

@Service
public class BookingAvailabilityService {
    private static final int DEFAULT_SLOT_INCREMENT_MINUTES = 15;
    private static final int DEFAULT_BOOKING_SEARCH_WINDOW_DAYS = 21;
    private static final String DEFAULT_TIME_FORMAT = "24h";
    private static final Set<Integer> SLOT_INCREMENT_OPTIONS = Set.of(5, 10, 15, 20, 30, 60);
    private static final DateTimeFormatter DATE_LABEL = DateTimeFormatter.ofPattern("EEEE dd MMMM yyyy", Locale.UK);
    private static final DateTimeFormatter TWENTY_FOUR_HOUR = DateTimeFormatter.ofPattern("HH:mm", Locale.UK);
    private static final DateTimeFormatter TWELVE_HOUR = DateTimeFormatter.ofPattern("h:mma", Locale.UK);

    private final BookingRepository bookingRepository;

    public BookingAvailabilityService(BookingRepository bookingRepository) {
        this.bookingRepository = bookingRepository;
    }

    public List<Map<String, Object>> locationsPayload() {
        return bookingRepository.findActiveLocations().stream().map(location -> {
            Map<String, Object> item = new LinkedHashMap<>();
            item.put("value", location.id());
            item.put("label", location.name());
            item.put("address", location.address() == null ? "" : location.address());
            item.put("phone", location.phone() == null ? "" : location.phone());
            item.put("timezone", normalizeZoneId(location.timezone()).getId());
            return item;
        }).toList();
    }

    public List<Map<String, Object>> servicesPayload() {
        return bookingRepository.findActiveServices().stream().map(this::servicePayload).toList();
    }

    public List<Map<String, Object>> clinicianOptions() {
        return bookingRepository.findBookableClinicians().stream().map(clinician -> {
            Map<String, Object> item = new LinkedHashMap<>();
            item.put("value", clinician.id());
            item.put("label", clinician.displayName());
            item.put("email", clinician.email());
            item.put("role", clinician.role());
            return item;
        }).toList();
    }

    public boolean onlineBookingEnabled() {
        return settingEnabled("booking_enable_online", true);
    }

    public int currentCancellationWindowMinutes() {
        Integer hours = parseInteger(bookingRepository.findAppSetting("booking_cancellation_hours"));
        if (hours != null && hours >= 0 && hours <= 336) {
            return hours * 60;
        }
        return 24 * 60;
    }

    public String nextAvailableDate(
        String clinicianUserIdValue,
        String locationIdValue,
        String serviceIdValue,
        String appointmentType,
        String durationMinutesValue,
        String slotIncrementMinutesValue
    ) {
        List<LocationRow> locations = bookingRepository.findActiveLocations();
        LocationRow location = selectLocation(locationIdValue, locations)
            .orElseGet(() -> locations.isEmpty() ? null : locations.getFirst());
        ZoneId zoneId = location == null ? ZoneId.systemDefault() : normalizeZoneId(location.timezone());
        LocalDate today = LocalDate.now(zoneId);
        for (int offset = 0; offset < currentBookingSearchWindowDays(); offset += 1) {
            LocalDate candidate = today.plusDays(offset);
            Map<String, Object> availability = availabilityPayload(
                candidate.toString(),
                clinicianUserIdValue,
                locationIdValue,
                serviceIdValue,
                appointmentType,
                durationMinutesValue,
                slotIncrementMinutesValue
            );
            @SuppressWarnings("unchecked")
            List<Map<String, Object>> slots = (List<Map<String, Object>>) availability.get("available_slots");
            if (slots != null && !slots.isEmpty()) {
                return candidate.toString();
            }
        }
        return today.toString();
    }

    private Map<String, Object> servicePayload(ServiceRow service) {
        Map<String, Object> item = new LinkedHashMap<>();
        item.put("id", service.id());
        item.put("service_key", service.serviceKey());
        item.put("label", service.label());
        item.put("description", service.description() == null ? "" : service.description());
        item.put("appointment_type", service.appointmentType());
        item.put("appointment_type_label", appointmentTypeLabel(service.appointmentType()));
        item.put("duration_minutes", service.durationMinutes());
        item.put("buffer_before_minutes", service.bufferBeforeMinutes());
        item.put("buffer_after_minutes", service.bufferAfterMinutes());
        item.put("requires_payment", service.requiresPayment());
        item.put("price_amount", service.priceAmount());
        item.put("currency", service.currency() == null ? "GBP" : service.currency());
        item.put("min_notice_minutes", service.minNoticeMinutes());
        item.put("max_bookings_per_day", service.maxBookingsPerDay());
        item.put("routing_mode", service.routingMode());
        item.put("routing_mode_label", routingModeLabel(service.routingMode()));
        item.put("active", service.active());
        item.put("display_order", service.displayOrder());
        return item;
    }

    public Map<String, Object> availabilityPayload(
        String dateValue,
        String clinicianUserIdValue,
        String locationIdValue,
        String serviceIdValue,
        String appointmentType,
        String durationMinutesValue,
        String slotIncrementMinutesValue
    ) {
        List<ServiceRow> services = bookingRepository.findActiveServices();
        ServiceRow selectedService = selectService(serviceIdValue, services)
            .orElseGet(() -> services.isEmpty() ? null : services.getFirst());
        BookingPolicy policy = resolveBookingPolicy(selectedService, appointmentType, parseInteger(durationMinutesValue));

        List<LocationRow> locations = bookingRepository.findActiveLocations();
        LocationRow location = selectLocation(locationIdValue, locations)
            .orElseGet(() -> locations.isEmpty() ? null : locations.getFirst());
        if (location == null) {
            return baseAvailabilityPayload(dateValue, null, policy, resolvedSlotIncrement(slotIncrementMinutesValue), "No clinic locations are available for booking.");
        }

        ZoneId zoneId = normalizeZoneId(location.timezone());
        String timeFormat = currentTimeFormat();
        int slotIncrementMinutes = resolvedSlotIncrement(slotIncrementMinutesValue);
        LocalDate targetDate = parseDate(dateValue);
        if (targetDate == null) {
            return baseAvailabilityPayload(dateValue, location.id(), policy, slotIncrementMinutes, "Choose a valid date.");
        }

        LocalDate today = LocalDate.now(zoneId);
        LocalDate latestAllowedDate = today.plusDays(currentBookingSearchWindowDays());
        if (targetDate.isAfter(latestAllowedDate)) {
            return baseAvailabilityPayload(
                targetDate.toString(),
                location.id(),
                policy,
                slotIncrementMinutes,
                "Bookings are currently limited to the next %d days.".formatted(currentBookingSearchWindowDays())
            );
        }
        if (!sameDayBookingEnabled() && !targetDate.isAfter(today)) {
            return baseAvailabilityPayload(
                targetDate.toString(),
                location.id(),
                policy,
                slotIncrementMinutes,
                "Same-day bookings are disabled in clinic settings."
            );
        }

        List<ClinicianRow> clinicians = bookingRepository.findBookableClinicians();
        boolean anyClinicianRequested = isAnyClinicianRequested(clinicianUserIdValue) && "team_round_robin".equals(policy.routingMode());
        List<Long> clinicianIds;
        if (anyClinicianRequested) {
            clinicianIds = clinicians.stream().map(ClinicianRow::id).toList();
        } else {
            Optional<ClinicianRow> selectedClinician = selectClinician(clinicianUserIdValue, clinicians)
                .or(() -> clinicians.isEmpty() ? Optional.empty() : Optional.of(clinicians.getFirst()));
            clinicianIds = selectedClinician.map(clinician -> List.of(clinician.id())).orElseGet(List::of);
        }

        if (clinicianIds.isEmpty()) {
            return baseAvailabilityPayload(targetDate.toString(), location.id(), policy, slotIncrementMinutes, "No chiropractor accounts are available for booking.");
        }

        List<ClinicianAvailability> perClinician = new ArrayList<>();
        for (Long clinicianId : clinicianIds) {
            ClinicianRow clinician = clinicians.stream().filter(item -> item.id() == clinicianId).findFirst().orElse(null);
            if (clinician == null) {
                continue;
            }
            perClinician.add(buildAvailabilityForClinician(targetDate, clinician, location, policy, slotIncrementMinutes, timeFormat, zoneId));
        }
        if (perClinician.isEmpty()) {
            return baseAvailabilityPayload(targetDate.toString(), location.id(), policy, slotIncrementMinutes, "No chiropractor availability could be loaded.");
        }

        List<Map<String, Object>> shiftWindows = new ArrayList<>();
        List<Map<String, Object>> downtimeWindows = new ArrayList<>();
        List<Map<String, Object>> bookedWindows = new ArrayList<>();
        List<Map<String, Object>> availableSlots = new ArrayList<>();

        if ("team_round_robin".equals(policy.routingMode()) && perClinician.size() > 1 && anyClinicianRequested) {
            Map<String, List<AvailableSlotView>> slotChoices = new LinkedHashMap<>();
            for (ClinicianAvailability availability : perClinician) {
                shiftWindows.addAll(availability.shiftWindows());
                downtimeWindows.addAll(availability.downtimeWindows());
                bookedWindows.addAll(availability.bookedWindows());
                for (AvailableSlotView slot : availability.availableSlots()) {
                    slotChoices.computeIfAbsent(slot.value(), key -> new ArrayList<>()).add(slot);
                }
            }
            for (List<AvailableSlotView> candidates : slotChoices.values()) {
                AvailableSlotView selected = candidates.stream()
                    .min(Comparator
                        .comparingInt(AvailableSlotView::dailyBookingCount)
                        .thenComparing(slot -> slot.clinicianName() == null ? "" : slot.clinicianName())
                        .thenComparingLong(AvailableSlotView::clinicianUserId))
                    .orElse(null);
                if (selected == null) {
                    continue;
                }
                Map<String, Object> item = slotPayload(selected);
                if (selected.clinicianName() != null && !selected.clinicianName().isBlank()) {
                    item.put("label", selected.label() + " · " + selected.clinicianName());
                }
                availableSlots.add(item);
            }
        } else {
            for (ClinicianAvailability availability : perClinician) {
                shiftWindows.addAll(availability.shiftWindows());
                downtimeWindows.addAll(availability.downtimeWindows());
                bookedWindows.addAll(availability.bookedWindows());
                for (AvailableSlotView slot : availability.availableSlots()) {
                    availableSlots.add(slotPayload(slot));
                }
            }
            availableSlots.sort(Comparator
                .<Map<String, Object>, String>comparing(item -> String.valueOf(item.get("value")))
                .thenComparing(item -> String.valueOf(item.getOrDefault("clinician_name", ""))));
        }

        Map<String, Object> payload = baseAvailabilityPayload(targetDate.toString(), location.id(), policy, slotIncrementMinutes, null);
        payload.put("date_label", DATE_LABEL.format(targetDate));
        payload.put("available_slots", availableSlots);
        payload.put("shift_windows", shiftWindows);
        payload.put("downtime_windows", downtimeWindows);
        payload.put("booked_windows", bookedWindows);
        return payload;
    }

    private ClinicianAvailability buildAvailabilityForClinician(
        LocalDate targetDate,
        ClinicianRow clinician,
        LocationRow location,
        BookingPolicy policy,
        int slotIncrementMinutes,
        String timeFormat,
        ZoneId zoneId
    ) {
        List<RenderedWindow> shiftWindowsRaw = new ArrayList<>();
        List<RenderedWindow> downtimeWindowsRaw = new ArrayList<>();
        for (ScheduleWindowRow row : bookingRepository.findScheduleWindowsForDay(weekdayValue(targetDate), clinician.id(), location.id())) {
            LocalDateTime startsAt = combineDateTime(targetDate, row.startsTime());
            LocalDateTime endsAt = combineDateTime(targetDate, row.endsTime());
            if (startsAt == null || endsAt == null || !endsAt.isAfter(startsAt)) {
                continue;
            }
            RenderedWindow item = new RenderedWindow(
                String.valueOf(row.id()),
                row.windowType(),
                windowTypeLabel(row.windowType()),
                row.label() == null || row.label().isBlank() ? windowTypeLabel(row.windowType()) : row.label(),
                formatTimeRange(startsAt, endsAt, timeFormat),
                startsAt,
                endsAt,
                clinician.id(),
                clinician.displayName()
            );
            if ("shift".equals(row.windowType())) {
                shiftWindowsRaw.add(item);
            } else {
                downtimeWindowsRaw.add(item);
            }
        }

        List<BlockedWindow> busyWindows = new ArrayList<>();
        for (BusyBlockRow row : bookingRepository.findAppointmentsForDate(targetDate, clinician.id())) {
            BlockedWindow window = blockedWindow(row, policy, clinician, location, timeFormat, zoneId, false);
            if (window != null) {
                busyWindows.add(window);
            }
        }
        for (BusyBlockRow row : bookingRepository.findActiveSlotHoldsForDate(targetDate, clinician.id())) {
            if (TimeSupport.isExpired(row.expiresAt())) {
                continue;
            }
            BlockedWindow window = blockedWindow(row, policy, clinician, location, timeFormat, zoneId, true);
            if (window != null) {
                busyWindows.add(window);
            }
        }

        List<Map<String, Object>> bookedWindows = busyWindows.stream().map(BlockedWindow::payload).toList();
        if (policy.maxBookingsPerDay() != null && busyWindows.size() >= policy.maxBookingsPerDay()) {
            return new ClinicianAvailability(
                clinician.id(),
                clinician.displayName(),
                shiftWindowsRaw.stream().map(RenderedWindow::payload).toList(),
                downtimeWindowsRaw.stream().map(RenderedWindow::payload).toList(),
                bookedWindows,
                List.of(),
                busyWindows.size()
            );
        }

        List<AvailableSlotView> availableSlots = new ArrayList<>();
        Set<String> seenValues = new LinkedHashSet<>();
        LocalDateTime now = LocalDateTime.now(zoneId);
        for (RenderedWindow shiftWindow : shiftWindowsRaw) {
            LocalDateTime slotStart = shiftWindow.startsAt();
            LocalDateTime lastStart = shiftWindow.endsAt().minusMinutes(policy.durationMinutes());
            while (!slotStart.isAfter(lastStart)) {
                LocalDateTime slotEnd = slotStart.plusMinutes(policy.durationMinutes());
                LocalDateTime blockedStart = slotStart.minusMinutes(policy.bufferBeforeMinutes());
                LocalDateTime blockedEnd = slotEnd.plusMinutes(policy.bufferAfterMinutes());
                if (!slotStart.isAfter(now.plusMinutes(policy.minNoticeMinutes()))) {
                    slotStart = slotStart.plusMinutes(slotIncrementMinutes);
                    continue;
                }
                if (blockedStart.isBefore(shiftWindow.startsAt()) || blockedEnd.isAfter(shiftWindow.endsAt())) {
                    slotStart = slotStart.plusMinutes(slotIncrementMinutes);
                    continue;
                }
                if (overlapsAny(blockedStart, blockedEnd, downtimeWindowsRaw)) {
                    slotStart = slotStart.plusMinutes(slotIncrementMinutes);
                    continue;
                }
                if (busyWindows.stream().anyMatch(window -> overlaps(blockedStart, blockedEnd, window.blockedStartsAt(), window.blockedEndsAt()))) {
                    slotStart = slotStart.plusMinutes(slotIncrementMinutes);
                    continue;
                }
                String slotValue = TimeSupport.localDateTimeValue(slotStart);
                if (seenValues.add(slotValue)) {
                    availableSlots.add(new AvailableSlotView(
                        slotValue,
                        formatTimeRange(slotStart, slotEnd, timeFormat),
                        formatTimeLabel(slotStart, timeFormat),
                        formatTimeLabel(slotEnd, timeFormat),
                        clinician.id(),
                        clinician.displayName(),
                        busyWindows.size()
                    ));
                }
                slotStart = slotStart.plusMinutes(slotIncrementMinutes);
            }
        }

        return new ClinicianAvailability(
            clinician.id(),
            clinician.displayName(),
            shiftWindowsRaw.stream().map(RenderedWindow::payload).toList(),
            downtimeWindowsRaw.stream().map(RenderedWindow::payload).toList(),
            bookedWindows,
            availableSlots,
            busyWindows.size()
        );
    }

    private BlockedWindow blockedWindow(
        BusyBlockRow row,
        BookingPolicy policy,
        ClinicianRow clinician,
        LocationRow location,
        String timeFormat,
        ZoneId zoneId,
        boolean hold
    ) {
        LocalDateTime startsAt = parseDateTime(row.startsAt(), zoneId);
        Integer durationMinutes = row.serviceDurationMinutes() != null ? row.serviceDurationMinutes() : policy.durationMinutes();
        LocalDateTime endsAt = row.endsAt() == null || row.endsAt().isBlank()
            ? (startsAt == null ? null : startsAt.plusMinutes(durationMinutes))
            : parseDateTime(row.endsAt(), zoneId);
        if (startsAt == null || endsAt == null) {
            return null;
        }
        int bufferBefore = row.serviceBufferBeforeMinutes() != null ? row.serviceBufferBeforeMinutes() : 0;
        int bufferAfter = row.serviceBufferAfterMinutes() != null ? row.serviceBufferAfterMinutes() : 0;
        String label = row.serviceLabel() == null || row.serviceLabel().isBlank()
            ? appointmentTypeLabel(row.appointmentType())
            : row.serviceLabel();
        if (hold) {
            label = label + " hold";
        }
        return new BlockedWindow(
            startsAt.minusMinutes(bufferBefore),
            endsAt.plusMinutes(bufferAfter),
            payloadWindow(row.id(), label, formatTimeRange(startsAt, endsAt, timeFormat), clinician.id(), clinician.displayName())
        );
    }

    private boolean overlapsAny(LocalDateTime blockedStart, LocalDateTime blockedEnd, List<RenderedWindow> windows) {
        return windows.stream().anyMatch(window -> overlaps(blockedStart, blockedEnd, window.startsAt(), window.endsAt()));
    }

    private boolean overlaps(LocalDateTime startA, LocalDateTime endA, LocalDateTime startB, LocalDateTime endB) {
        return startA.isBefore(endB) && startB.isBefore(endA);
    }

    private Map<String, Object> slotPayload(AvailableSlotView slot) {
        Map<String, Object> item = new LinkedHashMap<>();
        item.put("value", slot.value());
        item.put("label", slot.label());
        item.put("start_label", slot.startLabel());
        item.put("end_label", slot.endLabel());
        item.put("clinician_user_id", slot.clinicianUserId());
        item.put("clinician_name", slot.clinicianName());
        return item;
    }

    private Map<String, Object> payloadWindow(String id, String label, String timeLabel, long clinicianUserId, String clinicianName) {
        Map<String, Object> item = new LinkedHashMap<>();
        item.put("id", id);
        item.put("label", label);
        item.put("time_label", timeLabel);
        item.put("clinician_user_id", clinicianUserId);
        item.put("clinician_name", clinicianName);
        return item;
    }

    private Map<String, Object> baseAvailabilityPayload(String dateValue, Long locationId, BookingPolicy policy, int slotIncrementMinutes, String error) {
        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("date_value", dateValue == null ? "" : dateValue);
        payload.put("date_label", dateValue == null ? "" : dateValue);
        payload.put("location_id", locationId);
        payload.put("error", error);
        payload.put("duration_minutes", policy.durationMinutes());
        payload.put("slot_increment_minutes", slotIncrementMinutes);
        payload.put("buffer_before_minutes", policy.bufferBeforeMinutes());
        payload.put("buffer_after_minutes", policy.bufferAfterMinutes());
        payload.put("min_notice_minutes", policy.minNoticeMinutes());
        payload.put("max_bookings_per_day", policy.maxBookingsPerDay());
        payload.put("routing_mode", policy.routingMode());
        payload.put("routing_mode_label", routingModeLabel(policy.routingMode()));
        payload.put("service_id", policy.serviceId());
        payload.put("service_label", policy.serviceLabel());
        payload.put("appointment_type", policy.appointmentType());
        payload.put("requires_payment", policy.requiresPayment());
        payload.put("price_amount", policy.priceAmount());
        payload.put("currency", policy.currency());
        payload.put("available_slots", List.of());
        payload.put("shift_windows", List.of());
        payload.put("downtime_windows", List.of());
        payload.put("booked_windows", List.of());
        return payload;
    }

    private BookingPolicy resolveBookingPolicy(ServiceRow service, String appointmentType, Integer durationMinutes) {
        if (service != null) {
            return new BookingPolicy(
                service.id(),
                service.label(),
                service.appointmentType(),
                service.durationMinutes(),
                service.bufferBeforeMinutes(),
                service.bufferAfterMinutes(),
                service.requiresPayment(),
                service.priceAmount(),
                service.currency() == null ? "GBP" : service.currency(),
                service.minNoticeMinutes(),
                service.maxBookingsPerDay(),
                service.routingMode() == null || service.routingMode().isBlank() ? "specific_clinician" : service.routingMode()
            );
        }
        String safeType = appointmentType == null || appointmentType.isBlank() ? "care_plan" : appointmentType;
        int safeDuration = durationMinutes != null ? durationMinutes : defaultDurationForType(safeType);
        return new BookingPolicy(
            null,
            appointmentTypeLabel(safeType),
            safeType,
            safeDuration,
            0,
            0,
            false,
            null,
            "GBP",
            0,
            null,
            "specific_clinician"
        );
    }

    private Optional<ServiceRow> selectService(String serviceIdValue, List<ServiceRow> services) {
        Integer serviceId = parseInteger(serviceIdValue);
        if (serviceId == null) {
            return Optional.empty();
        }
        return services.stream().filter(service -> service.id() == serviceId).findFirst();
    }

    private Optional<LocationRow> selectLocation(String locationIdValue, List<LocationRow> locations) {
        Integer locationId = parseInteger(locationIdValue);
        if (locationId == null) {
            return Optional.empty();
        }
        return locations.stream().filter(location -> location.id() == locationId).findFirst();
    }

    private Optional<ClinicianRow> selectClinician(String clinicianUserIdValue, List<ClinicianRow> clinicians) {
        Integer clinicianId = parseInteger(clinicianUserIdValue);
        if (clinicianId == null) {
            return Optional.empty();
        }
        return clinicians.stream().filter(clinician -> clinician.id() == clinicianId).findFirst();
    }

    private int resolvedSlotIncrement(String requestedValue) {
        Integer requested = parseInteger(requestedValue);
        if (requested != null && SLOT_INCREMENT_OPTIONS.contains(requested)) {
            return requested;
        }
        Integer fromSettings = parseInteger(bookingRepository.findAppSetting("calendar_slot_increment_minutes"));
        if (fromSettings != null && SLOT_INCREMENT_OPTIONS.contains(fromSettings)) {
            return fromSettings;
        }
        return DEFAULT_SLOT_INCREMENT_MINUTES;
    }

    private int currentBookingSearchWindowDays() {
        Integer value = parseInteger(bookingRepository.findAppSetting("booking_search_window_days"));
        if (value != null && value >= 1 && value <= 120) {
            return value;
        }
        return DEFAULT_BOOKING_SEARCH_WINDOW_DAYS;
    }

    private boolean sameDayBookingEnabled() {
        return settingEnabled("booking_allow_same_day", true);
    }

    private String currentTimeFormat() {
        String value = bookingRepository.findAppSetting("calendar_time_format");
        if ("12h".equalsIgnoreCase(value) || "24h".equalsIgnoreCase(value)) {
            return value.toLowerCase(Locale.UK);
        }
        return DEFAULT_TIME_FORMAT;
    }

    private boolean settingEnabled(String key, boolean defaultValue) {
        String rawValue = bookingRepository.findAppSetting(key);
        if (rawValue == null || rawValue.isBlank()) {
            return defaultValue;
        }
        return switch (rawValue.trim().toLowerCase(Locale.UK)) {
            case "1", "true", "yes", "on" -> true;
            case "0", "false", "no", "off" -> false;
            default -> defaultValue;
        };
    }

    private ZoneId normalizeZoneId(String value) {
        try {
            return value == null || value.isBlank() ? ZoneId.systemDefault() : ZoneId.of(value);
        } catch (Exception ignored) {
            return ZoneId.systemDefault();
        }
    }

    private LocalDate parseDate(String value) {
        try {
            return value == null || value.isBlank() ? null : LocalDate.parse(value);
        } catch (Exception ignored) {
            return null;
        }
    }

    private LocalDateTime combineDateTime(LocalDate date, String timeValue) {
        LocalTime time = parseTime(timeValue);
        if (date == null || time == null) {
            return null;
        }
        return LocalDateTime.of(date, time);
    }

    private LocalTime parseTime(String value) {
        try {
            return value == null || value.isBlank() ? null : LocalTime.parse(value);
        } catch (Exception ignored) {
            return null;
        }
    }

    private LocalDateTime parseDateTime(String value, ZoneId zoneId) {
        if (value == null || value.isBlank()) {
            return null;
        }
        try {
            return LocalDateTime.parse(value);
        } catch (Exception ignored) {
        }
        try {
            return OffsetDateTime.parse(value).atZoneSameInstant(zoneId).toLocalDateTime();
        } catch (Exception ignored) {
        }
        try {
            Instant instant = Instant.parse(value);
            return LocalDateTime.ofInstant(instant, zoneId);
        } catch (Exception ignored) {
        }
        return null;
    }

    private String formatTimeRange(LocalDateTime startsAt, LocalDateTime endsAt, String timeFormat) {
        return formatTimeLabel(startsAt, timeFormat) + " - " + formatTimeLabel(endsAt, timeFormat);
    }

    private String formatTimeLabel(LocalDateTime value, String timeFormat) {
        if (value == null) {
            return "";
        }
        if ("12h".equals(timeFormat)) {
            return TWELVE_HOUR.format(value).toLowerCase(Locale.UK);
        }
        return TWENTY_FOUR_HOUR.format(value);
    }

    private int weekdayValue(LocalDate value) {
        return value.getDayOfWeek().getValue() - 1;
    }

    private Integer parseInteger(String value) {
        try {
            return value == null || value.isBlank() ? null : Integer.parseInt(value.trim());
        } catch (Exception ignored) {
            return null;
        }
    }

    private int defaultDurationForType(String appointmentType) {
        return switch (appointmentType) {
            case "initial_consult", "report_of_findings" -> 30;
            default -> 15;
        };
    }

    private String appointmentTypeLabel(String appointmentType) {
        return switch (appointmentType) {
            case "initial_consult" -> "Initial Consult";
            case "report_of_findings" -> "Report Of Findings";
            case "care_plan" -> "Care Plan";
            default -> titleCase(appointmentType);
        };
    }

    private String routingModeLabel(String routingMode) {
        return switch (routingMode) {
            case "team_round_robin" -> "Any available chiropractor";
            default -> "Specific chiropractor";
        };
    }

    private String windowTypeLabel(String windowType) {
        return switch (windowType) {
            case "downtime" -> "Downtime";
            default -> "Shift";
        };
    }

    private boolean isAnyClinicianRequested(String value) {
        if (value == null) {
            return true;
        }
        String normalized = value.trim().toLowerCase(Locale.UK);
        return normalized.isEmpty() || normalized.equals("any") || normalized.equals("team");
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

    private record BookingPolicy(
        Long serviceId,
        String serviceLabel,
        String appointmentType,
        int durationMinutes,
        int bufferBeforeMinutes,
        int bufferAfterMinutes,
        boolean requiresPayment,
        Double priceAmount,
        String currency,
        int minNoticeMinutes,
        Integer maxBookingsPerDay,
        String routingMode
    ) {
    }

    private record RenderedWindow(
        String id,
        String windowType,
        String windowTypeLabel,
        String label,
        String timeLabel,
        LocalDateTime startsAt,
        LocalDateTime endsAt,
        long clinicianUserId,
        String clinicianName
    ) {
        Map<String, Object> payload() {
            Map<String, Object> item = new LinkedHashMap<>();
            item.put("id", id);
            item.put("label", label);
            item.put("time_label", timeLabel);
            item.put("window_type", windowType);
            item.put("window_type_label", windowTypeLabel);
            item.put("window_tone", "downtime".equals(windowType) ? "rose" : "life");
            item.put("clinician_user_id", clinicianUserId);
            item.put("clinician_name", clinicianName);
            return item;
        }
    }

    private record BlockedWindow(
        LocalDateTime blockedStartsAt,
        LocalDateTime blockedEndsAt,
        Map<String, Object> payload
    ) {
    }

    private record AvailableSlotView(
        String value,
        String label,
        String startLabel,
        String endLabel,
        long clinicianUserId,
        String clinicianName,
        int dailyBookingCount
    ) {
    }

    private record ClinicianAvailability(
        long clinicianUserId,
        String clinicianName,
        List<Map<String, Object>> shiftWindows,
        List<Map<String, Object>> downtimeWindows,
        List<Map<String, Object>> bookedWindows,
        List<AvailableSlotView> availableSlots,
        int dailyBookingCount
    ) {
    }
}
