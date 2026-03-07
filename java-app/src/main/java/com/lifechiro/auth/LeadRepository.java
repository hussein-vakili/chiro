package com.lifechiro.auth;

import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Repository;

@Repository
public class LeadRepository {
    private final JdbcTemplate jdbcTemplate;

    public LeadRepository(JdbcTemplate jdbcTemplate) {
        this.jdbcTemplate = jdbcTemplate;
    }

    public void markConvertedByInvitation(long invitationId, long convertedUserId, String updatedAt) {
        jdbcTemplate.update(
            """
            UPDATE leads
            SET status = 'converted',
                converted_user_id = ?,
                updated_at = ?
            WHERE invitation_id = ?
            """,
            convertedUserId,
            updatedAt,
            invitationId
        );
    }
}
