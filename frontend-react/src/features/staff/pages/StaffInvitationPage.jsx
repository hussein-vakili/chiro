import React, { useCallback, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { buildUrl, fetchJson } from "../../../shared/api";
import { copyText } from "../../../shared/browser";
import { useApiResource } from "../../../shared/hooks";
import { ErrorState, LoadingState, StatusPill } from "../../../shared/ui";

export default function StaffInvitationPage({ config }) {
  const [searchParams, setSearchParams] = useSearchParams();
  const leadId = searchParams.get("lead_id") || "";
  const endpoint = useMemo(
    () => buildUrl(config.staffInvitationsEndpoint, { lead_id: leadId }),
    [config.staffInvitationsEndpoint, leadId]
  );
  const resource = useApiResource(() => fetchJson(endpoint), [endpoint]);
  const [workingPayload, setWorkingPayload] = useState(null);
  const [formState, setFormState] = useState({
    lead_id: "",
    first_name: "",
    last_name: "",
    email: "",
    appointment_at: "",
    note: "",
  });
  const [notice, setNotice] = useState("");
  const [errorNotice, setErrorNotice] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [copyState, setCopyState] = useState("");

  const viewData = workingPayload || resource.data;

  useEffect(() => {
    setWorkingPayload(null);
  }, [leadId]);

  useEffect(() => {
    if (!viewData?.invite_prefill) {
      return;
    }
    setFormState({
      lead_id: viewData.invite_prefill.lead_id || "",
      first_name: viewData.invite_prefill.first_name || "",
      last_name: viewData.invite_prefill.last_name || "",
      email: viewData.invite_prefill.email || "",
      appointment_at: viewData.invite_prefill.appointment_at || "",
      note: viewData.invite_prefill.note || "",
    });
  }, [viewData]);

  const openLead = useCallback((nextLeadId) => {
    const next = new URLSearchParams();
    if (nextLeadId) {
      next.set("lead_id", String(nextLeadId));
    }
    setNotice("");
    setErrorNotice("");
    setSearchParams(next);
  }, [setSearchParams]);

  const updateField = (key, value) => {
    setFormState((current) => ({ ...current, [key]: value }));
  };

  const submitInvite = async (event) => {
    event.preventDefault();
    setSubmitting(true);
    setNotice("");
    setErrorNotice("");
    const { response, data } = await fetchJson(config.staffCreateInvitationEndpoint, {
      method: "POST",
      body: JSON.stringify(formState),
    });
    setSubmitting(false);
    setWorkingPayload(data);
    if (!response.ok || data.ok === false) {
      setErrorNotice(data.error || "Invitation failed.");
      return;
    }
    setNotice(data.message || "Invitation created.");
  };

  const copyInviteLink = async (value) => {
    try {
      await copyText(value);
      setCopyState("Copied");
    } catch (_error) {
      setCopyState("Failed");
    }
    window.setTimeout(() => setCopyState(""), 1400);
  };

  if (resource.loading) {
    return <LoadingState title="Loading invitation workspace" detail="Preparing lead-linked invite creation." />;
  }
  if (resource.error) {
    return <ErrorState detail={resource.error} onRetry={resource.reload} />;
  }

  return (
    <div className="rp-page-grid">
      <section className="rp-card rp-hero-card">
        <div>
          <div className="rp-eyebrow">Clinician workflow</div>
          <h2>Create a patient onboarding invite</h2>
          <p>Generate an appointment-linked signup URL for a new client. Accepted invites connect back into the patient record and consume any held slot automatically.</p>
        </div>
        <div className="rp-header-card">
          <span>Invite policy</span>
          <strong>{workingPayload?.created_invitation ? "Invite ready" : "14-day expiry"}</strong>
          <small>Appointment slots are held when a time is attached.</small>
          <small>{viewData?.open_leads?.length || 0} open leads available for conversion.</small>
        </div>
      </section>

      {notice ? <div className="rp-alert rp-alert-success">{notice}</div> : null}
      {errorNotice ? <div className="rp-alert rp-alert-error">{errorNotice}</div> : null}

      <section className="rp-two-column">
        <article className="rp-card">
          <div className="rp-section-head">
            <div>
              <span className="rp-eyebrow">Open leads</span>
              <h2>Requests waiting for an invite</h2>
            </div>
          </div>
          <div className="rp-stack-list">
            {viewData.open_leads.length ? viewData.open_leads.map((lead) => (
              <button
                key={lead.id}
                type="button"
                className={`rp-thread-link ${String(lead.id) === leadId ? "active" : ""}`.trim()}
                onClick={() => openLead(lead.id)}
              >
                <div className="rp-thread-link-head">
                  <div>
                    <strong>{lead.full_name}</strong>
                    <small>{lead.email}</small>
                  </div>
                  <StatusPill tone={lead.status_tone}>{lead.status_label}</StatusPill>
                </div>
                <p>{lead.service_label} · {lead.requested_label}</p>
                <small>{lead.reason || lead.source_label}</small>
              </button>
            )) : <div className="rp-empty-inline">No open leads are waiting right now.</div>}
          </div>
          <div className="rp-inline-actions">
            <button type="button" className="rp-button rp-button-secondary" onClick={() => openLead("")}>
              Start blank invite
            </button>
          </div>
        </article>

        <article className="rp-card">
          <div className="rp-section-head">
            <div>
              <span className="rp-eyebrow">New invite</span>
              <h2>{viewData.linked_lead ? "Create from lead request" : "Manual invite"}</h2>
            </div>
          </div>
          {viewData.linked_lead ? (
            <div className="rp-list-card">
              <div className="rp-list-head">
                <div>
                  <strong>{viewData.linked_lead.full_name}</strong>
                  <small>{viewData.linked_lead.email}</small>
                </div>
                <StatusPill tone={viewData.linked_lead.status_tone}>{viewData.linked_lead.status_label}</StatusPill>
              </div>
              <p>{viewData.linked_lead.requested_label}</p>
              <small>{viewData.linked_lead.reason || "No patient note supplied."}</small>
            </div>
          ) : null}
          <form className="rp-form-stack" onSubmit={submitInvite}>
            <div className="rp-form-grid">
              <label>
                <span>First name</span>
                <input type="text" value={formState.first_name} onChange={(event) => updateField("first_name", event.target.value)} required />
              </label>
              <label>
                <span>Last name</span>
                <input type="text" value={formState.last_name} onChange={(event) => updateField("last_name", event.target.value)} required />
              </label>
              <label>
                <span>Email</span>
                <input type="email" value={formState.email} onChange={(event) => updateField("email", event.target.value)} required />
              </label>
              <label>
                <span>Appointment date and time</span>
                <input type="datetime-local" value={formState.appointment_at} onChange={(event) => updateField("appointment_at", event.target.value)} />
              </label>
            </div>
            <label>
              <span>Internal note for the patient</span>
              <textarea rows="5" value={formState.note} onChange={(event) => updateField("note", event.target.value)} placeholder="Arrival instructions, paperwork reminders, clinic-specific prep..." />
            </label>
            <button type="submit" className="rp-button rp-button-primary" disabled={submitting}>
              {submitting ? "Creating..." : "Create invitation"}
            </button>
          </form>
        </article>
      </section>

      <section className="rp-card">
        <div className="rp-section-head">
          <div>
            <span className="rp-eyebrow">{viewData.created_invitation ? "Latest invite" : (viewData.linked_lead ? "Lead request" : "Latest invite")}</span>
            <h2>{viewData.created_invitation ? `${viewData.created_invitation.first_name} ${viewData.created_invitation.last_name}` : (viewData.linked_lead ? viewData.linked_lead.full_name : "No invite created yet")}</h2>
          </div>
        </div>
        {viewData.created_invitation ? (
          <div className="rp-stack-list">
            <div className="rp-list-card">
              <div className="rp-list-head">
                <div>
                  <strong>Invite URL</strong>
                  <small>Copy into your email or SMS workflow</small>
                </div>
                <button type="button" className="rp-button rp-button-secondary" onClick={() => copyInviteLink(viewData.created_invitation.accept_url_external)}>
                  {copyState || "Copy link"}
                </button>
              </div>
              <p>{viewData.created_invitation.accept_url_external}</p>
            </div>
            <div className="rp-metric-grid">
              <article className="rp-mini-metric">
                <span>Email</span>
                <strong>{viewData.created_invitation.email}</strong>
                <small>Invite recipient</small>
              </article>
              <article className="rp-mini-metric">
                <span>Appointment</span>
                <strong>{viewData.created_invitation.appointment_at ? viewData.created_invitation.appointment_at.replace("T", " ") : "Not set"}</strong>
                <small>Requested slot</small>
              </article>
              <article className="rp-mini-metric">
                <span>Expiry</span>
                <strong>{viewData.created_invitation.expires_at.slice(0, 10)}</strong>
                <small>Invite expiry window</small>
              </article>
              {viewData.created_slot_hold ? (
                <article className="rp-mini-metric">
                  <span>Held until</span>
                  <strong>{viewData.created_slot_hold.expires_label}</strong>
                  <small>{viewData.created_slot_hold.service_label}</small>
                </article>
              ) : null}
            </div>
          </div>
        ) : viewData.linked_lead ? (
          <div className="rp-list-card">
            <p>This invite is linked to a live lead request from the public consultation page.</p>
            <small>{viewData.linked_lead.source_label} · {viewData.linked_lead.phone || "No phone number supplied"}</small>
          </div>
        ) : (
          <div className="rp-empty-inline">Once you submit the form, the generated onboarding link will appear here.</div>
        )}
      </section>
    </div>
  );
}
