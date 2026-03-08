import React from "react";
import { fetchJson } from "../../../shared/api";
import { useApiResource } from "../../../shared/hooks";
import { ErrorState, LoadingState, StatusPill } from "../../../shared/ui";

export default function DashboardPage({ config, session }) {
  const resource = useApiResource(() => fetchJson(config.dashboardEndpoint), [config.dashboardEndpoint]);

  if (resource.loading) {
    return <LoadingState title="Loading dashboard" detail="Building your next-step summary." />;
  }
  if (resource.error) {
    return <ErrorState detail={resource.error} onRetry={resource.reload} />;
  }

  const dashboard = resource.data.dashboard;
  const journey = dashboard.journey_summary;

  return (
    <div className="rp-page-grid">
      <section className="rp-card rp-hero-card">
        <div>
          <div className="rp-eyebrow">{journey.stage_label}</div>
          <h2>{journey.title}</h2>
          <p>{journey.detail}</p>
          {journey.helper ? <p className="rp-journey-helper">{journey.helper}</p> : null}
        </div>
        <div className="rp-hero-actions">
          <a className="rp-button rp-button-primary" href={journey.primary_action_url}>
            {journey.primary_action_label}
          </a>
          {journey.secondary_action_url ? (
            <a className="rp-button rp-button-secondary" href={journey.secondary_action_url}>
              {journey.secondary_action_label}
            </a>
          ) : null}
          <StatusPill tone={journey.tone}>{journey.stage_label}</StatusPill>
          <span className={`rp-note tone-${journey.tone}`}>{session.user.email}</span>
        </div>
      </section>

      <section className="rp-card">
        <div className="rp-section-head">
          <div>
            <span className="rp-eyebrow">Journey focus</span>
            <h2>What matters in this stage</h2>
          </div>
        </div>
        <div className="rp-action-grid">
          {journey.focus.map((item) => (
            <a key={`${item.label}-${item.title}`} href={item.url} className="rp-action-card">
              <div className="rp-action-top">
                <div>
                  <span className="rp-action-label">{item.label}</span>
                  <strong>{item.title}</strong>
                </div>
                <StatusPill tone={item.tone}>{item.label}</StatusPill>
              </div>
              <p>{item.detail}</p>
            </a>
          ))}
        </div>
      </section>

      <section className="rp-two-column">
        <article className="rp-card">
          <div className="rp-section-head">
            <div>
              <span className="rp-eyebrow">This stage</span>
              <h2>Your checklist right now</h2>
            </div>
          </div>
          <div className="rp-stack-list">
            {journey.checklist.map((item) => (
              <div key={`${item.label}-${item.value}`} className="rp-list-card">
                <div className="rp-list-head">
                  <div>
                    <span className="rp-action-label">{item.label}</span>
                    <strong>{item.value}</strong>
                  </div>
                  <StatusPill tone={item.tone}>{item.label}</StatusPill>
                </div>
                <p>{item.detail}</p>
                {item.url ? (
                  <div className="rp-inline-actions rp-inline-actions-tight">
                    <a className="rp-button rp-button-secondary" href={item.url}>
                      {item.action_label || "Open"}
                    </a>
                  </div>
                ) : null}
              </div>
            ))}
          </div>
        </article>

        <article className="rp-card">
          <div className="rp-section-head">
            <div>
              <span className="rp-eyebrow">Portal metrics</span>
              <h2>Key signals</h2>
            </div>
          </div>
          <div className="rp-mini-metric-grid">
            {dashboard.portal_metrics.map((metric) => (
              <div key={metric.label} className="rp-mini-metric">
                <span>{metric.label}</span>
                <strong>{metric.value}</strong>
                <small>{metric.detail}</small>
              </div>
            ))}
          </div>
        </article>
      </section>

      <section className="rp-card">
        <div className="rp-section-head">
          <div>
            <span className="rp-eyebrow">Portal actions</span>
            <h2>What you can do now</h2>
          </div>
        </div>
        <div className="rp-action-grid">
          {dashboard.portal_actions.map((action) => (
            <a key={action.label} href={action.url} className="rp-action-card">
              <div className="rp-action-top">
                <div>
                  <span className="rp-action-label">{action.label}</span>
                  <strong>{action.title}</strong>
                </div>
                <StatusPill tone={action.tone}>{action.badge}</StatusPill>
              </div>
              <p>{action.detail}</p>
            </a>
          ))}
        </div>
      </section>

      {dashboard.care_plan.plan ? (
        <section className="rp-two-column">
          <article className="rp-card">
            <div className="rp-section-head">
              <div>
                <span className="rp-eyebrow">Care plan</span>
                <h2>{dashboard.care_plan.plan.title}</h2>
              </div>
              <StatusPill tone={dashboard.care_plan.adherence.tone}>{dashboard.care_plan.adherence.title}</StatusPill>
            </div>
            <p>
              {dashboard.care_plan.plan.frequency_label} for {dashboard.care_plan.plan.duration_weeks} weeks · {dashboard.care_plan.plan.total_visits} visits
            </p>
            <div className="rp-mini-metric-grid">
              <div className="rp-mini-metric">
                <span>Progress</span>
                <strong>{dashboard.care_plan.adherence.completion_percent}%</strong>
                <small>{dashboard.care_plan.adherence.progress_label}</small>
              </div>
              <div className="rp-mini-metric">
                <span>Booked</span>
                <strong>{dashboard.care_plan.stats.booked}</strong>
                <small>{dashboard.care_plan.stats.remaining} visits remaining</small>
              </div>
              <div className="rp-mini-metric">
                <span>Needs booking</span>
                <strong>{dashboard.care_plan.adherence.needs_booking_count}</strong>
                <small>{dashboard.care_plan.adherence.detail}</small>
              </div>
            </div>
            <div className="rp-inline-actions">
              <a className="rp-button rp-button-primary" href={dashboard.care_plan.adherence.action_url}>
                {dashboard.care_plan.adherence.action_label}
              </a>
              <a className="rp-button rp-button-secondary" href={dashboard.care_plan.adherence.secondary_action_url}>
                {dashboard.care_plan.adherence.secondary_action_label}
              </a>
            </div>
          </article>

          <article className="rp-card">
            <div className="rp-section-head">
              <div>
                <span className="rp-eyebrow">Journey</span>
                <h2>Your care stages</h2>
              </div>
            </div>
            <div className="rp-journey-list">
              {dashboard.portal_journey.map((item) => (
                <div key={item.step} className="rp-journey-item">
                  <div className="rp-journey-step">{item.step}</div>
                  <div className="rp-journey-copy">
                    <span>{item.label}</span>
                    <strong>{item.title}</strong>
                    <p>{item.detail}</p>
                  </div>
                  <a href={item.url}>{item.action_label}</a>
                </div>
              ))}
            </div>
          </article>
        </section>
      ) : null}

      <section className="rp-two-column">
        <article className="rp-card">
          <div className="rp-section-head">
            <div>
              <span className="rp-eyebrow">Upcoming visits</span>
              <h2>Your calendar</h2>
            </div>
          </div>
          {dashboard.schedule.upcoming.length ? (
            <div className="rp-stack-list">
              {dashboard.schedule.upcoming.slice(0, 4).map((appointment) => (
                <div key={appointment.id} className="rp-list-card">
                  <div className="rp-list-head">
                    <div>
                      <StatusPill tone={appointment.type_tone}>{appointment.type_label}</StatusPill>
                      <strong>{appointment.date_label}</strong>
                    </div>
                    <StatusPill tone={appointment.status_tone}>{appointment.status_label}</StatusPill>
                  </div>
                  <p>{appointment.time_label}{appointment.end_time_label ? ` - ${appointment.end_time_label}` : ""}</p>
                  <small>
                    {appointment.location_name || "Clinic location not set"}
                    {appointment.clinician_name ? ` · ${appointment.clinician_name}` : ""}
                  </small>
                </div>
              ))}
            </div>
          ) : (
            <div className="rp-empty-inline">No future appointments are booked yet.</div>
          )}
        </article>

        <article className="rp-card">
          <div className="rp-section-head">
            <div>
              <span className="rp-eyebrow">Messages</span>
              <h2>Recent thread activity</h2>
            </div>
            <StatusPill tone={dashboard.unread_message_count ? "rose" : "life"}>
              {dashboard.unread_message_count ? `${dashboard.unread_message_count} unread` : "Up to date"}
            </StatusPill>
          </div>
          {dashboard.recent_messages.length ? (
            <div className="rp-stack-list">
              {dashboard.recent_messages.map((item) => (
                <div key={item.id} className="rp-list-card">
                  <div className="rp-list-head">
                    <div>
                      <StatusPill tone={item.topic_tone}>{item.topic_label}</StatusPill>
                      <strong>{item.sender_name}</strong>
                    </div>
                    {item.is_unread_for_patient ? <StatusPill tone="rose">New</StatusPill> : null}
                  </div>
                  <p>{item.body}</p>
                  <small>{item.created_label}</small>
                </div>
              ))}
            </div>
          ) : (
            <div className="rp-empty-inline">No messages yet. Start a secure thread when you need the clinic.</div>
          )}
        </article>
      </section>
    </div>
  );
}
