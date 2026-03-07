package com.lifechiro.shared;

import java.time.Instant;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.OffsetDateTime;
import java.time.ZoneId;
import java.time.format.DateTimeFormatter;
import java.time.temporal.ChronoUnit;

public final class TimeSupport {
    private static final DateTimeFormatter DATE_TIME_LABEL = DateTimeFormatter.ofPattern("dd MMM yyyy '·' HH:mm");
    private static final DateTimeFormatter DATE_LABEL = DateTimeFormatter.ofPattern("dd MMM yyyy");

    private TimeSupport() {
    }

    public static String isoNowUtc() {
        return Instant.now().truncatedTo(ChronoUnit.SECONDS).toString();
    }

    public static String localDateTimeValue(LocalDateTime value) {
        return value.truncatedTo(ChronoUnit.MINUTES).format(DateTimeFormatter.ofPattern("yyyy-MM-dd'T'HH:mm"));
    }

    public static boolean isExpired(String value) {
        Instant instant = parseInstant(value);
        return instant != null && instant.isBefore(Instant.now());
    }

    public static String formatSchedule(String value) {
        if (value == null || value.isBlank()) {
            return null;
        }
        try {
            return DATE_TIME_LABEL.format(OffsetDateTime.parse(value));
        } catch (Exception ignored) {
        }
        try {
            return DATE_TIME_LABEL.format(LocalDateTime.parse(value));
        } catch (Exception ignored) {
        }
        try {
            return DATE_LABEL.format(LocalDate.parse(value));
        } catch (Exception ignored) {
        }
        return value;
    }

    public static Instant parseInstant(String value) {
        if (value == null || value.isBlank()) {
            return null;
        }
        try {
            return Instant.parse(value);
        } catch (Exception ignored) {
        }
        try {
            return OffsetDateTime.parse(value).toInstant();
        } catch (Exception ignored) {
        }
        try {
            return LocalDateTime.parse(value).atZone(ZoneId.systemDefault()).toInstant();
        } catch (Exception ignored) {
        }
        try {
            return LocalDate.parse(value).atStartOfDay(ZoneId.systemDefault()).toInstant();
        } catch (Exception ignored) {
        }
        return null;
    }
}
