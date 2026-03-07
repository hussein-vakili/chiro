package com.lifechiro.auth.model;

public record InvitationRecord(
    long id,
    String email,
    String firstName,
    String lastName,
    String appointmentAt,
    String note,
    String token,
    String expiresAt,
    String createdAt,
    String acceptedAt,
    Long createdBy,
    Long acceptedUserId
) {
}
