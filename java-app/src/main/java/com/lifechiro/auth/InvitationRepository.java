package com.lifechiro.auth;

import com.lifechiro.auth.model.InvitationRecord;
import java.util.Optional;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.core.RowMapper;
import org.springframework.stereotype.Repository;

@Repository
public class InvitationRepository {
    private static final RowMapper<InvitationRecord> INVITATION_ROW_MAPPER = (resultSet, rowNum) -> new InvitationRecord(
        resultSet.getLong("id"),
        resultSet.getString("email"),
        resultSet.getString("first_name"),
        resultSet.getString("last_name"),
        resultSet.getString("appointment_at"),
        resultSet.getString("note"),
        resultSet.getString("token"),
        resultSet.getString("expires_at"),
        resultSet.getString("created_at"),
        resultSet.getString("accepted_at"),
        resultSet.getObject("created_by") == null ? null : resultSet.getLong("created_by"),
        resultSet.getObject("accepted_user_id") == null ? null : resultSet.getLong("accepted_user_id")
    );

    private final JdbcTemplate jdbcTemplate;

    public InvitationRepository(JdbcTemplate jdbcTemplate) {
        this.jdbcTemplate = jdbcTemplate;
    }

    public Optional<InvitationRecord> findByToken(String token) {
        return jdbcTemplate.query(
            """
            SELECT *
            FROM invitations
            WHERE token = ?
            LIMIT 1
            """,
            INVITATION_ROW_MAPPER,
            token
        ).stream().findFirst();
    }

    public void markAccepted(long invitationId, long acceptedUserId, String acceptedAt) {
        jdbcTemplate.update(
            """
            UPDATE invitations
            SET accepted_at = ?, accepted_user_id = ?
            WHERE id = ?
            """,
            acceptedAt,
            acceptedUserId,
            invitationId
        );
    }

    public long countPendingInvitations() {
        Long count = jdbcTemplate.queryForObject(
            "SELECT COUNT(*) FROM invitations WHERE accepted_at IS NULL",
            Long.class
        );
        return count == null ? 0L : count;
    }
}
