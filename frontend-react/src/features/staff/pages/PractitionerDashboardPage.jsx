import React from "react";
import { fetchJson } from "../../../shared/api";
import { useApiResource } from "../../../shared/hooks";
import { ErrorState, LoadingState, StatusPill } from "../../../shared/ui";

export default function PractitionerDashboardPage({ config }) {
  const resource = useApiResource(() => fetchJson(config.staffDashboardEndpoint), [config.staffDashboardEndpoint]);

  if (resource.loading) {
    return <LoadingState title="Loading practitioner dashboard" detail="Building your appointment and charting queue." />;
  }
  if (resource.error) {
    return <ErrorState detail={resource.error} onRetry={resource.reload} />;
  }

  const dashboard = resource.data.dashboard;
  const scheduleItems = dashboard.today_appointments.length ? dashboard.today_appointments : dashboard.upcoming_appointments;

  return (
    <div className="rp-page-grid">
      <section className="rp-card rp-hero-card">
        <div>
          <div className="rp-eyebrow">Practitioner dashboard</div>
          <h2>Your patient list and appointment charting</h2>
          <p>Review today’s visits, move through your SOAP queue, and jump straight into the patient chart.</p>
        </div>
        <div className="rp-header-card">
          <span>At a glance</span>
          <strong>{dashboard.patient_count} patients</strong>
          <small>{dashboard.upcoming_count} upcoming appointments</small>
          <small>{dashboard.charting_queue_count} need SOAP notes</small>
          <small>{dashboard.charted_count} charted appointments</small>
        </div>
      </section>

      <section className="rp-two-column">
        <article className="rp-card">
          <div className="rp-section-head">
            <div>
              <span className="rp-eyebrow">Schedule</span>
              <h2>Today’s appointments</h2>
            </div>
          </div>
          <div className="rp-stack-list">
            {scheduleItems.length ? scheduleItems.map((appointment) => (
              <div key={appointment.id} className="rp-list-card">
                <div className="rp-list-head">
                  <div>
                    <StatusPill tone={appointment.type_tone}>{appointment.type_label}</StatusPill>
                    <strong>{appointment.patient_name}</strong>
                  </div>
                  <StatusPill tone={appointment.has_soap_note ? "life" : "warm"}>
                    {appointment.has_soap_note ? "SOAP saved" : "SOAP not started"}
                  </StatusPill>
                </div>
                <p>{appointment.starts_label}</p>
                <small>{appointment.location_name || "Clinic location not set"}</small>
                <div className="rp-inline-actions rp-inline-actions-tight">
                  <a className="rp-button rp-button-primary" href={`/practitioner/appointments/${appointment.id}/soap`}>
                    {appointment.soap_note_action_label}
                  </a>
                  <a className="rp-button rp-button-secondary" href={`/staff/patients/${appointment.patient_user_id}`}>
                    Open patient chart
                  </a>
                </div>
              </div>
            )) : <div className="rp-empty-inline">No appointments are scheduled for you right now.</div>}
          </div>
        </article>

        <article className="rp-card">
          <div className="rp-section-head">
            <div>
              <span className="rp-eyebrow">SOAP charting</span>
              <h2>Charting queue</h2>
            </div>
          </div>
          <div className="rp-stack-list">
            {dashboard.charting_queue.length ? dashboard.charting_queue.map((appointment) => (
              <div key={appointment.id} className="rp-list-card">
                <div className="rp-list-head">
                  <div>
                    <strong>{appointment.patient_name}</strong>
                    <small>{appointment.type_label}</small>
                  </div>
                  <StatusPill tone="warm">Needs SOAP</StatusPill>
                </div>
                <p>{appointment.starts_label}</p>
                <div className="rp-inline-actions rp-inline-actions-tight">
                  <a className="rp-button rp-button-primary" href={`/practitioner/appointments/${appointment.id}/soap`}>
                    Add SOAP note
                  </a>
                  <a className="rp-button rp-button-secondary" href={`/staff/patients/${appointment.patient_user_id}`}>
                    Open chart
                  </a>
                </div>
              </div>
            )) : <div className="rp-empty-inline">No appointments currently need SOAP charting.</div>}
          </div>
        </article>
      </section>

      <section className="rp-two-column">
        <article className="rp-card">
          <div className="rp-section-head">
            <div>
              <span className="rp-eyebrow">Recently charted</span>
              <h2>Completed SOAP notes</h2>
            </div>
          </div>
          <div className="rp-stack-list">
            {dashboard.recent_charted.length ? dashboard.recent_charted.map((appointment) => (
              <div key={appointment.id} className="rp-list-card">
                <div className="rp-list-head">
                  <div>
                    <strong>{appointment.patient_name}</strong>
                    <small>{appointment.type_label}</small>
                  </div>
                  <StatusPill tone="life">Charted</StatusPill>
                </div>
                <p>{appointment.starts_label}</p>
                <small>{appointment.soap_note_updated_label || "SOAP note saved"}</small>
                <div className="rp-inline-actions rp-inline-actions-tight">
                  <a className="rp-button rp-button-primary" href={`/practitioner/appointments/${appointment.id}/soap`}>
                    Review SOAP note
                  </a>
                  <a className="rp-button rp-button-secondary" href={`/staff/patients/${appointment.patient_user_id}`}>
                    Open chart
                  </a>
                </div>
              </div>
            )) : <div className="rp-empty-inline">No SOAP notes have been completed recently.</div>}
          </div>
        </article>

        <article className="rp-card">
          <div className="rp-section-head">
            <div>
              <span className="rp-eyebrow">Patients</span>
              <h2>My patients</h2>
            </div>
          </div>
          <div className="rp-stack-list">
            {dashboard.patients.length ? dashboard.patients.map((patient) => {
              const noteTarget = patient.last_appointment || patient.next_appointment;
              return (
                <div key={patient.id} className="rp-list-card">
                  <div className="rp-list-head">
                    <div>
                      <strong>{patient.full_name}</strong>
                      <small>{patient.email}</small>
                    </div>
                    <StatusPill tone={patient.pending_soap_count ? "warm" : "life"}>
                      {patient.soap_note_count} saved
                    </StatusPill>
                  </div>
                  <p>
                    {patient.next_appointment
                      ? `Next: ${patient.next_appointment.starts_label}`
                      : "No future appointment"}
                  </p>
                  {patient.last_appointment ? <small>Last: {patient.last_appointment.starts_label}</small> : null}
                  <div className="rp-inline-actions rp-inline-actions-tight">
                    <a className="rp-button rp-button-secondary" href={`/staff/patients/${patient.id}`}>Open chart</a>
                    {noteTarget ? (
                      <a className="rp-button rp-button-primary" href={`/practitioner/appointments/${noteTarget.id}/soap`}>
                        {noteTarget.soap_note_action_label}
                      </a>
                    ) : null}
                  </div>
                </div>
              );
            }) : <div className="rp-empty-inline">No patients are linked to this practitioner yet.</div>}
          </div>
        </article>
      </section>
    </div>
  );
}
