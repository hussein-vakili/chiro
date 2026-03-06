package com.lifechiro.db;

import com.lifechiro.config.AppConfig;
import java.io.File;
import java.nio.file.Path;
import javax.sql.DataSource;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.datasource.DriverManagerDataSource;

@Configuration
public class DataConfig {

    @Bean
    public DataSource dataSource(AppConfig config) {
        File dbFile = Path.of(config.getDatabasePath()).toFile();
        File parent = dbFile.getParentFile();
        if (parent != null) {
            parent.mkdirs();
        }

        DriverManagerDataSource dataSource = new DriverManagerDataSource();
        dataSource.setDriverClassName("org.sqlite.JDBC");
        dataSource.setUrl("jdbc:sqlite:" + dbFile.getAbsolutePath());
        return dataSource;
    }

    @Bean
    public JdbcTemplate jdbcTemplate(DataSource dataSource) {
        return new JdbcTemplate(dataSource);
    }
}
