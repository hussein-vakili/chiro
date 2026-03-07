package com.lifechiro.auth;

import com.lifechiro.auth.model.PortalUserRecord;
import java.sql.PreparedStatement;
import java.sql.Statement;
import java.util.Optional;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.core.RowMapper;
import org.springframework.jdbc.support.GeneratedKeyHolder;
import org.springframework.jdbc.support.KeyHolder;
import org.springframework.stereotype.Repository;

@Repository
public class UserRepository {
    private static final RowMapper<PortalUserRecord> USER_ROW_MAPPER = (resultSet, rowNum) -> new PortalUserRecord(
        resultSet.getLong("id"),
        resultSet.getString("first_name"),
        resultSet.getString("last_name"),
        resultSet.getString("email"),
        resultSet.getString("password_hash"),
        resultSet.getString("role"),
        resultSet.getInt("is_active") != 0,
        resultSet.getString("created_at")
    );

    private final JdbcTemplate jdbcTemplate;

    public UserRepository(JdbcTemplate jdbcTemplate) {
        this.jdbcTemplate = jdbcTemplate;
    }

    public Optional<PortalUserRecord> findByEmail(String email) {
        return jdbcTemplate.query(
            """
            SELECT id, first_name, last_name, email, password_hash, role, COALESCE(is_active, 1) AS is_active, created_at
            FROM users
            WHERE lower(email) = lower(?)
            LIMIT 1
            """,
            USER_ROW_MAPPER,
            email
        ).stream().findFirst();
    }

    public Optional<PortalUserRecord> findById(long userId) {
        return jdbcTemplate.query(
            """
            SELECT id, first_name, last_name, email, password_hash, role, COALESCE(is_active, 1) AS is_active, created_at
            FROM users
            WHERE id = ?
            LIMIT 1
            """,
            USER_ROW_MAPPER,
            userId
        ).stream().findFirst();
    }

    public boolean existsByEmail(String email) {
        Integer count = jdbcTemplate.queryForObject(
            "SELECT COUNT(*) FROM users WHERE lower(email) = lower(?)",
            Integer.class,
            email
        );
        return count != null && count > 0;
    }

    public PortalUserRecord createInvitedClient(String firstName, String lastName, String email, String passwordHash, String createdAt) {
        KeyHolder keyHolder = new GeneratedKeyHolder();
        jdbcTemplate.update(connection -> {
            PreparedStatement statement = connection.prepareStatement(
                """
                INSERT INTO users (first_name, last_name, email, password_hash, role, is_active, created_at)
                VALUES (?, ?, ?, ?, 'client', 1, ?)
                """,
                Statement.RETURN_GENERATED_KEYS
            );
            statement.setString(1, firstName);
            statement.setString(2, lastName);
            statement.setString(3, email.toLowerCase());
            statement.setString(4, passwordHash);
            statement.setString(5, createdAt);
            return statement;
        }, keyHolder);
        Number key = keyHolder.getKey();
        if (key == null) {
            throw new IllegalStateException("Failed to create invited user");
        }
        return findById(key.longValue()).orElseThrow();
    }

    public long countClients() {
        Long count = jdbcTemplate.queryForObject(
            "SELECT COUNT(*) FROM users WHERE role = 'client'",
            Long.class
        );
        return count == null ? 0L : count;
    }
}
