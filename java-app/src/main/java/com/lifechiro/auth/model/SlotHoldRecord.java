package com.lifechiro.auth.model;

public record SlotHoldRecord(
    long id,
    Long invitationId,
    Long leadId,
    long clinicianUserId,
    Long locationId,
    Long serviceId,
    String appointmentType,
    String startsAt,
    String endsAt,
    String status,
    String expiresAt,
    Long consumedAppointmentId,
    String createdAt,
    String updatedAt,
    String serviceLabel,
    String locationName,
    String clinicianName
) {
    public boolean isActive() {
        return "active".equalsIgnoreCase(status);
    }
}
