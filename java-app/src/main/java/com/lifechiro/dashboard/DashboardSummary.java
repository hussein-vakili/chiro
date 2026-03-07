package com.lifechiro.dashboard;

public record DashboardSummary(
    String title,
    String detail,
    String primaryMetricLabel,
    String primaryMetricValue,
    String secondaryMetricLabel,
    String secondaryMetricValue
) {
}
