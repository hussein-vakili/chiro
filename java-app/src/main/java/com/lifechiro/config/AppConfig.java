package com.lifechiro.config;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Configuration;

@Configuration
public class AppConfig {
    @Value("${lifechiro.database.path}")
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

    @Value("${lifechiro.default-staff.email}")
    private String defaultStaffEmail;

    @Value("${lifechiro.default-staff.password}")
    private String defaultStaffPassword;

    @Value("${lifechiro.default-staff.first-name}")
    private String defaultStaffFirstName;

    @Value("${lifechiro.default-staff.last-name}")
    private String defaultStaffLastName;

    @Value("${lifechiro.demo-invite.token}")
    private String demoInviteToken;

    @Value("${lifechiro.demo-invite.email}")
    private String demoInviteEmail;

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

    public String getDefaultStaffEmail() {
        return defaultStaffEmail;
    }

    public String getDefaultStaffPassword() {
        return defaultStaffPassword;
    }

    public String getDefaultStaffFirstName() {
        return defaultStaffFirstName;
    }

    public String getDefaultStaffLastName() {
        return defaultStaffLastName;
    }

    public String getDemoInviteToken() {
        return demoInviteToken;
    }

    public String getDemoInviteEmail() {
        return demoInviteEmail;
    }
}
