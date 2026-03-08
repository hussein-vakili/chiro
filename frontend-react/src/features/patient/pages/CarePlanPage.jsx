import React from "react";
import { useNavigate } from "react-router-dom";
import { fetchJson } from "../../../shared/api";
import { useApiResource } from "../../../shared/hooks";
import { ErrorState, LoadingState, StatusPill } from "../../../shared/ui";

export default function CarePlanPage({ config }) {
  const navigate = useNavigate();
  const resource = useApiResource(() => fetchJson(config.carePlanEndpoint), [config.carePlanEndpoint]);

  if (resource.loading) {
    return <LoadingState title="Loading care plan" detail="Syncing your current stage of care." />;
  }
  if (resource.error) {
    return <ErrorState detail={resource.error} onRetry={resource.reload} />;
  }

  const carePlan = resource.data.care_plan;
  const journey = resource.data.journey_summary;
  if (!carePlan.plan) {
    return (
      <section className="rp-empty-card">
        <span className="rp-eyebrow">{journey.stage_label}</span>
        <h2>{journey.title}</h2>
        <p>{journey.detail}</p>
        {journey.helper ? <p className="rp-journey-helper">{journey.helper}</p> : null}
        <div className="rp-inline-actions">
          <a className="rp-button rp-button-primary" href={journey.primary_action_url}>
            {journey.primary_action_label}
          </a>
          {journey.secondary_action_url ? (
            <a className="rp-button rp-button-secondary" href={journey.secondary_action_url}>
              {journey.secondary_action_label}
            </a>
          ) : null}
        </div>
      </section>
    );
  }

  return (
    <div className="rp-page-grid">
      <section className="rp-card rp-hero-card">
        <div>
          <div className="rp-eyebrow">{journey.stage_label}</div>
          <h2>{journey.title}</h2>
          <p>{journey.detail}</p>
          {journey.helper ? <p className="rp-journey-helper">{journey.helper}</p> : null}
        </div>
        <div className="rp-header-card">
          <span>Status</span>
          <strong>{carePlan.adherence.title}</strong>
          <small>{carePlan.adherence.progress_label}</small>
          <small>{carePlan.plan.frequency_label} · {carePlan.plan.total_visits} visits</small>
        </div>
      </section>

      <section className="rp-two-column">
        <article className="rp-card">
          <div className="rp-section-head">
            <div>
              <span className="rp-eyebrow">Current focus</span>
              <h2>What to do in this stage</h2>
            </div>
          </div>
          <div className="rp-stack-list">
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
        </article>

        <article className="rp-card">
          <div className="rp-section-head">
            <div>
              <span className="rp-eyebrow">Checklist</span>
              <h2>Plan-specific next steps</h2>
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
      </section>

      <section className="rp-metric-grid">
        <article className="rp-card rp-metric-card">
          <span>Completed</span>
          <strong>{carePlan.stats.completed}</strong>
          <small>{carePlan.adherence.progress_label}</small>
        </article>
        <article className="rp-card rp-metric-card">
          <span>Booked</span>
          <strong>{carePlan.stats.booked}</strong>
          <small>{carePlan.next_booked ? carePlan.next_booked.effective_label : "No upcoming visit booked"}</small>
        </article>
        <article className="rp-card rp-metric-card">
          <span>Needs booking</span>
          <strong>{carePlan.adherence.needs_booking_count}</strong>
          <small>{carePlan.adherence.detail}</small>
        </article>
      </section>

      <section className="rp-card">
        <div className="rp-section-head">
          <div>
            <span className="rp-eyebrow">Plan summary</span>
            <h2>{carePlan.plan.title}</h2>
          </div>
          <StatusPill tone={carePlan.adherence.tone}>{carePlan.adherence.state.replace(/_/g, " ")}</StatusPill>
        </div>
        <p>
          {carePlan.plan.frequency_label} for {carePlan.plan.duration_weeks} weeks · {carePlan.plan.total_visits} visits
        </p>
        <div className="rp-inline-actions">
          <a className="rp-button rp-button-primary" href={journey.primary_action_url}>
            {journey.primary_action_label}
          </a>
          <a className="rp-button rp-button-secondary" href={journey.secondary_action_url || carePlan.adherence.secondary_action_url}>
            {journey.secondary_action_label || carePlan.adherence.secondary_action_label}
          </a>
        </div>
      </section>

      <section className="rp-card">
        <div className="rp-section-head">
          <div>
            <span className="rp-eyebrow">Visits</span>
            <h2>Plan timeline</h2>
          </div>
        </div>
        <div className="rp-stack-list">
          {carePlan.visits.map((visit) => (
            <div key={visit.id} className="rp-list-card">
              <div className="rp-list-head">
                <div>
                  <StatusPill tone={visit.visit_kind_tone}>{visit.visit_kind_label}</StatusPill>
                  <strong>{visit.label}</strong>
                </div>
                <StatusPill tone={visit.status_tone}>{visit.status_label}</StatusPill>
              </div>
              <p>{visit.effective_label}</p>
              <small>{visit.duration_minutes} minutes{visit.appointment_clinician_name ? ` · ${visit.appointment_clinician_name}` : ""}</small>
              {!visit.booked ? (
                <div className="rp-inline-actions rp-inline-actions-tight">
                  <button type="button" className="rp-button rp-button-secondary" onClick={() => navigate(`/appointments?care_plan_visit_id=${visit.id}`)}>
                    Book this visit
                  </button>
                </div>
              ) : null}
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
