package com.lifechiro.config;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Configuration;

@Configuration
public class AppConfig {
    @Value("${lifechiro.database.path:${user.home}/.lifechiro/chiro.sqlite3}")
    private String databasePath;

    @Value("${lifechiro.secret:}")
    private String secretKey;

    @Value("${lifechiro.reminder.email-mode:outbox}")
    private String reminderEmailMode;

    @Value("${lifechiro.reminder.sms-mode:outbox}")
    private String reminderSmsMode;

    @Value("${lifechiro.smtp.host:}")
    private String smtpHost;

    @Value("${lifechiro.smtp.port:587}")
    private int smtpPort;

    @Value("${lifechiro.smtp.username:}")
    private String smtpUsername;

    @Value("${lifechiro.smtp.password:}")
    private String smtpPassword;

    public String getDatabasePath() {
        return databasePath;
    }

    public String getSecretKey() {
        return secretKey;
    }

    public String getReminderEmailMode() {
        return reminderEmailMode;
    }

    public String getReminderSmsMode() {
        return reminderSmsMode;
    }

    public String getSmtpHost() {
        return smtpHost;
    }

    public int getSmtpPort() {
        return smtpPort;
    }

    public String getSmtpUsername() {
        return smtpUsername;
    }

    public String getSmtpPassword() {
        return smtpPassword;
    }
}
