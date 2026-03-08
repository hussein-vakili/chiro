import React, { useState } from "react";
import { fetchJson } from "../../../shared/api";
import { useApiResource } from "../../../shared/hooks";
import { ErrorState, LoadingState, StatusPill } from "../../../shared/ui";

export default function StaffRemindersPage({ config }) {
  const [notice, setNotice] = useState("");
  const [errorNotice, setErrorNotice] = useState("");
  const [sendingKey, setSendingKey] = useState("");
  const resource = useApiResource(() => fetchJson(config.staffRemindersEndpoint), [config.staffRemindersEndpoint]);

  const sendReminder = async (appointmentId, channel) => {
    setSendingKey(`${appointmentId}:${channel}`);
    setNotice("");
    setErrorNotice("");
    const { response, data } = await fetchJson(`/api/staff/appointments/${appointmentId}/send-reminder`, {
      method: "POST",
      body: JSON.stringify({ channel }),
    });
    setSendingKey("");
    if (!response.ok || data.ok === false) {
      setErrorNotice(data.error || data.message || "Reminder failed.");
      return;
    }
    setNotice(data.message || "Reminder sent.");
    resource.reload();
  };

  if (resource.loading) {
    return <LoadingState title="Loading reminders" detail="Preparing the live reminder queue and delivery history." />;
  }
  if (resource.error) {
    return <ErrorState detail={resource.error} onRetry={resource.reload} />;
  }

  const data = resource.data.reminders;

  return (
    <div className="rp-page-grid">
      <section className="rp-card rp-hero-card">
        <div>
          <div className="rp-eyebrow">Reminder center</div>
          <h2>Appointment reminders</h2>
          <p>Send and track email or SMS reminders for upcoming Reports of Findings and care-plan visits from the React staff workspace.</p>
        </div>
        <div className="rp-header-card">
          <span>Delivery modes</span>
          <strong>{data.due_reminders.length} due now</strong>
          <small>Email mode: {data.email_mode}</small>
          <small>SMS mode: {data.sms_mode}</small>
        </div>
      </section>

      {notice ? <div className="rp-alert rp-alert-success">{notice}</div> : null}
      {errorNotice ? <div className="rp-alert rp-alert-error">{errorNotice}</div> : null}

      <section className="rp-metric-grid">
        <article className="rp-card rp-metric-card">
          <span>Due reminders</span>
          <strong>{data.due_reminders.length}</strong>
          <small>ROF and care-plan visits currently within the reminder window.</small>
        </article>
        <article className="rp-card rp-metric-card">
          <span>Logged</span>
          <strong>{data.delivery_counts.logged}</strong>
          <small>Recorded to the outbox.</small>
        </article>
        <article className="rp-card rp-metric-card">
          <span>Sent</span>
          <strong>{data.delivery_counts.sent}</strong>
          <small>Provider deliveries completed.</small>
        </article>
        <article className="rp-card rp-metric-card">
          <span>Failed</span>
          <strong>{data.delivery_counts.failed}</strong>
          <small>Delivery attempts needing review.</small>
        </article>
      </section>

      <section className="rp-two-column">
        <article className="rp-card">
          <div className="rp-section-head">
            <div>
              <span className="rp-eyebrow">Due reminders</span>
              <h2>Send from queue</h2>
            </div>
            <div className="rp-inline-actions">
              <a className="rp-button rp-button-secondary" href={data.routes.legacy_calendar}>Calendar</a>
              <a className="rp-button rp-button-secondary" href={data.routes.legacy_reminders}>Legacy center</a>
            </div>
          </div>
          <div className="rp-stack-list">
            {data.due_reminders.length ? data.due_reminders.map((appointment) => (
              <div key={appointment.id} className="rp-list-card">
                <div className="rp-list-head">
                  <div>
                    <strong>{appointment.patient_name}</strong>
                    <small>{appointment.appointment_type_label}</small>
                  </div>
                  <StatusPill tone={appointment.reminder_tone || "sky"}>{appointment.reminder_label || "Reminder"}</StatusPill>
                </div>
                <p>{appointment.starts_label}</p>
                <small>{appointment.location_name || "Clinic location not set"}</small>
                <div className="rp-reminder-meta">
                  <span>{appointment.patient_email || "No email on file"}</span>
                  <span>{appointment.patient_phone || "No phone on file"}</span>
                </div>
                <div className="rp-inline-actions rp-inline-actions-tight">
                  <button
                    type="button"
                    className="rp-button rp-button-secondary"
                    onClick={() => sendReminder(appointment.id, "email")}
                    disabled={!appointment.can_email || sendingKey === `${appointment.id}:email`}
                  >
                    {sendingKey === `${appointment.id}:email` ? "Sending..." : "Send email"}
                  </button>
                  <button
                    type="button"
                    className="rp-button rp-button-secondary"
                    onClick={() => sendReminder(appointment.id, "sms")}
                    disabled={!appointment.can_sms || sendingKey === `${appointment.id}:sms`}
                  >
                    {sendingKey === `${appointment.id}:sms` ? "Sending..." : "Send SMS"}
                  </button>
                  <button
                    type="button"
                    className="rp-button rp-button-primary"
                    onClick={() => sendReminder(appointment.id, "both")}
                    disabled={(!appointment.can_email && !appointment.can_sms) || sendingKey === `${appointment.id}:both`}
                  >
                    {sendingKey === `${appointment.id}:both` ? "Sending..." : "Send both"}
                  </button>
                  <a className="rp-button rp-button-secondary" href={`/staff/patients/${appointment.patient_user_id}`}>Open patient chart</a>
                </div>
              </div>
            )) : <div className="rp-empty-inline">No Report of Findings or care-plan reminders are due right now.</div>}
          </div>
        </article>

        <article className="rp-card">
          <div className="rp-section-head">
            <div>
              <span className="rp-eyebrow">Delivery summary</span>
              <h2>Recent outcome mix</h2>
            </div>
          </div>
          <div className="rp-stack-list">
            <div className="rp-mini-metric">
              <strong>Email mode</strong>
              <small>{data.email_mode}</small>
            </div>
            <div className="rp-mini-metric">
              <strong>SMS mode</strong>
              <small>{data.sms_mode}</small>
            </div>
            <div className="rp-mini-metric">
              <strong>Processing model</strong>
              <small>The local build records deliveries to the outbox unless direct providers are configured.</small>
            </div>
          </div>
        </article>
      </section>

      <section className="rp-card">
        <div className="rp-section-head">
          <div>
            <span className="rp-eyebrow">Delivery history</span>
            <h2>Recent reminder activity</h2>
          </div>
        </div>
        <div className="rp-stack-list">
          {data.recent_deliveries.length ? data.recent_deliveries.map((delivery) => (
            <div key={delivery.id} className="rp-list-card">
              <div className="rp-list-head">
                <div>
                  <strong>{delivery.patient_name}</strong>
                  <small>{delivery.appointment_type_label} · {delivery.starts_label}</small>
                </div>
                <div className="rp-inline-actions rp-inline-actions-tight">
                  <StatusPill tone={delivery.channel_tone}>{delivery.channel_label}</StatusPill>
                  <StatusPill tone={delivery.status_tone}>{delivery.status_label}</StatusPill>
                </div>
              </div>
              <p>{delivery.recipient || "Missing contact details"}</p>
              <small>{delivery.delivery_mode}</small>
              {delivery.subject ? <small>Subject: {delivery.subject}</small> : null}
              <div className="rp-message-preview">{delivery.message}</div>
              {delivery.error_message ? <div className="rp-inline-note rp-inline-note-error">{delivery.error_message}</div> : null}
              <div className="rp-inline-actions rp-inline-actions-tight">
                {delivery.launch_link ? <a className="rp-button rp-button-secondary" href={delivery.launch_link}>Open in device app</a> : null}
                <a className="rp-button rp-button-secondary" href={`/staff/patients/${delivery.patient_user_id}`}>Open patient chart</a>
              </div>
            </div>
          )) : <div className="rp-empty-inline">No reminder deliveries have been recorded yet.</div>}
        </div>
      </section>
    </div>
  );
}
