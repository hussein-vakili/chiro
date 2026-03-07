package com.lifechiro.auth.model;

public record PortalUserRecord(
    long id,
    String firstName,
    String lastName,
    String email,
    String passwordHash,
    String role,
    boolean active,
    String createdAt
) {
    public String displayName() {
        return (firstName + " " + lastName).trim();
    }
}
