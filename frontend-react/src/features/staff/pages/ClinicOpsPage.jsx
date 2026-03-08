import React from "react";
import { buildUrl, fetchJson } from "../../../shared/api";
import { useApiResource } from "../../../shared/hooks";
import { ErrorState, LoadingState, StatusPill } from "../../../shared/ui";

export default function ClinicOpsPage({ config }) {
  const resource = useApiResource(
    () => fetchJson(buildUrl(config.staffDashboardEndpoint, { view: "clinic_ops" })),
    [config.staffDashboardEndpoint]
  );

  if (resource.loading) {
    return <LoadingState title="Loading clinic ops" detail="Building the front-desk and clinic dashboard." />;
  }
  if (resource.error) {
    return <ErrorState detail={resource.error} onRetry={resource.reload} />;
  }

  const dashboard = resource.data.dashboard;

  return (
    <div className="rp-page-grid">
      <section className="rp-card rp-hero-card">
        <div>
          <div className="rp-eyebrow">Clinic ops</div>
          <h2>Clinic onboarding operations</h2>
          <p>
            Monitor patient readiness, lead conversion, reminder workload, and care-plan follow-up from one React dashboard.
          </p>
        </div>
        <div className="rp-header-card">
          <span>At a glance</span>
          <strong>{dashboard.patient_count} patients</strong>
          <small>{dashboard.submitted_count} submitted intakes</small>
          <small>{dashboard.pending_invite_count} active invites</small>
          <small>{dashboard.open_lead_count} open lead requests</small>
        </div>
      </section>

      <section className="rp-metric-grid">
        <article className="rp-card rp-metric-card">
          <span>Upcoming visits</span>
          <strong>{dashboard.upcoming_appointments.length}</strong>
          <small>Live scheduled appointments pulled from the shared diary.</small>
        </article>
        <article className="rp-card rp-metric-card">
          <span>Reminder queue</span>
          <strong>{dashboard.appointment_reminders.length}</strong>
          <small>ROF and care-plan visits needing follow-up soon.</small>
        </article>
        <article className="rp-card rp-metric-card">
          <span>Care-plan follow-up</span>
          <strong>{dashboard.care_plan_follow_up_count}</strong>
          <small>Patients who are overdue or missing their next booking.</small>
        </article>
        <article className="rp-card rp-metric-card">
          <span>Open leads</span>
          <strong>{dashboard.open_lead_count}</strong>
          <small>New patient requests waiting on conversion or invite action.</small>
        </article>
      </section>

      <section className="rp-two-column">
        <article className="rp-card">
          <div className="rp-section-head">
            <div>
              <span className="rp-eyebrow">Patients</span>
              <h2>Recent portal patients</h2>
            </div>
          </div>
          <div className="rp-stack-list">
            {dashboard.patients.slice(0, 8).map((patient) => (
              <div key={patient.id} className="rp-list-card">
                <div className="rp-list-head">
                  <div>
                    <strong>{patient.first_name} {patient.last_name}</strong>
                    <small>{patient.email}</small>
                  </div>
                  <StatusPill tone={patient.intake_status === "submitted" ? "life" : patient.intake_status ? "warm" : "muted"}>
                    {patient.intake_status || "not started"}
                  </StatusPill>
                </div>
                <p>
                  {patient.next_appointment
                    ? `${patient.next_appointment.starts_label} · ${patient.next_appointment.type_label}`
                    : "No next appointment scheduled"}
                </p>
                <small>{patient.visit_report_status || "Consult not started"}</small>
                <div className="rp-inline-actions rp-inline-actions-tight">
                  <a className="rp-button rp-button-secondary" href={`/staff/patients/${patient.id}`}>
                    Open patient chart
                  </a>
                </div>
              </div>
            ))}
          </div>
        </article>

        <article className="rp-card">
          <div className="rp-section-head">
            <div>
              <span className="rp-eyebrow">Reminder queue</span>
              <h2>Visits due soon</h2>
            </div>
          </div>
          <div className="rp-stack-list">
            {dashboard.appointment_reminders.length ? dashboard.appointment_reminders.map((appointment) => (
              <div key={appointment.id} className="rp-list-card">
                <div className="rp-list-head">
                  <div>
                    <strong>{appointment.patient_name}</strong>
                    <small>{appointment.type_label}</small>
                  </div>
                  <StatusPill tone={appointment.reminder_tone || "sky"}>{appointment.reminder_label || "Reminder"}</StatusPill>
                </div>
                <p>{appointment.starts_label}</p>
                <small>{appointment.location_name || "Clinic location not set"}</small>
                <div className="rp-inline-actions rp-inline-actions-tight">
                  <a className="rp-button rp-button-secondary" href={`/staff/patients/${appointment.patient_user_id}`}>
                    Open patient chart
                  </a>
                </div>
              </div>
            )) : <div className="rp-empty-inline">No ROF or care-plan reminders are due soon.</div>}
          </div>
        </article>
      </section>

      <section className="rp-two-column">
        <article className="rp-card">
          <div className="rp-section-head">
            <div>
              <span className="rp-eyebrow">Care-plan follow-up</span>
              <h2>Patients needing action</h2>
            </div>
          </div>
          <div className="rp-stack-list">
            {dashboard.care_plan_follow_up_queue.length ? dashboard.care_plan_follow_up_queue.map((item) => (
              <div key={item.patient_user_id} className="rp-list-card">
                <div className="rp-list-head">
                  <div>
                    <strong>{item.patient_name}</strong>
                    <small>{item.patient_email}</small>
                  </div>
                  <StatusPill tone={item.tone}>{item.title}</StatusPill>
                </div>
                <p>{item.detail}</p>
                {item.visit_label ? <small>{item.visit_label} · {item.visit_date_label}</small> : null}
                <div className="rp-inline-actions rp-inline-actions-tight">
                  <a className="rp-button rp-button-primary" href={item.book_visit_url}>Book next visit</a>
                  <a className="rp-button rp-button-secondary" href={item.open_chart_url}>Open chart</a>
                </div>
              </div>
            )) : <div className="rp-empty-inline">No care-plan follow-up actions are waiting right now.</div>}
          </div>
        </article>

        <article className="rp-card">
          <div className="rp-section-head">
            <div>
              <span className="rp-eyebrow">New patient requests</span>
              <h2>Lead queue</h2>
            </div>
          </div>
          <div className="rp-stack-list">
            {dashboard.open_leads.length ? dashboard.open_leads.map((lead) => (
              <div key={lead.id} className="rp-list-card">
                <div className="rp-list-head">
                  <div>
                    <strong>{lead.full_name}</strong>
                    <small>{lead.email}</small>
                  </div>
                  <StatusPill tone={lead.status_tone}>{lead.status_label}</StatusPill>
                </div>
                <p>{lead.service_label} · {lead.requested_label}</p>
                {lead.reason ? <small>{lead.reason}</small> : null}
                <div className="rp-inline-actions rp-inline-actions-tight">
                  <a className="rp-button rp-button-secondary" href={lead.has_active_invite && lead.invite_url ? lead.invite_url : lead.create_invite_url}>
                    {lead.has_active_invite ? "Open invite" : "Create invite"}
                  </a>
                </div>
              </div>
            )) : <div className="rp-empty-inline">No open lead requests yet.</div>}
          </div>
        </article>
      </section>
    </div>
  );
}
