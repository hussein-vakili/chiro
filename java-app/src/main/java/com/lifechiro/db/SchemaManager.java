package com.lifechiro.db;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import org.springframework.boot.ApplicationArguments;
import org.springframework.boot.ApplicationRunner;
import org.springframework.core.io.ClassPathResource;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Component;
import org.springframework.util.StreamUtils;

@Component
public class SchemaManager implements ApplicationRunner {
    private static final String SCHEMA_RESOURCE = "db/schema.sql";

    private final JdbcTemplate jdbcTemplate;

    public SchemaManager(JdbcTemplate jdbcTemplate) {
        this.jdbcTemplate = jdbcTemplate;
    }

    @Override
    public void run(ApplicationArguments args) throws Exception {
        String schema = loadSchema();
        executeStatements(schema);
    }

    private String loadSchema() throws IOException {
        ClassPathResource resource = new ClassPathResource(SCHEMA_RESOURCE);
        return StreamUtils.copyToString(resource.getInputStream(), StandardCharsets.UTF_8);
    }

    private void executeStatements(String schema) {
        String[] statements = schema.split(";");
        for (String statement : statements) {
            String sql = statement.trim();
            if (sql.isEmpty()) {
                continue;
            }
            if (!sql.toLowerCase().endsWith(";")) {
                sql = sql + ";";
            }
            jdbcTemplate.execute(sql);
        }
    }
}
