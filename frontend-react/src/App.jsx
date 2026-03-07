import React, { useCallback, useEffect, useMemo, useState } from "react";
import { NavLink, Navigate, Route, Routes, useLocation, useNavigate, useSearchParams } from "react-router-dom";

function buildUrl(endpoint, params = {}) {
  const url = new URL(endpoint, window.location.origin);
  Object.entries(params).forEach(([key, value]) => {
    if (value === undefined || value === null || value === "") {
      return;
    }
    url.searchParams.set(key, value);
  });
  return `${url.pathname}${url.search}`;
}

async function fetchJson(url, options = {}) {
  const headers = { Accept: "application/json", ...(options.headers || {}) };
  if (options.body && !headers["Content-Type"]) {
    headers["Content-Type"] = "application/json";
  }
  const response = await fetch(url, {
    credentials: "same-origin",
    ...options,
    headers,
  });
  const text = await response.text();
  let data = {};
  if (text) {
    try {
      data = JSON.parse(text);
    } catch (error) {
      throw new Error(`Invalid JSON response from ${url}`);
    }
  }
  return { response, data };
}

function toSpaPath(url, basename = "/app") {
  if (!url) {
    return "/";
  }
  const path = url.replace(/^https?:\/\/[^/]+/i, "");
  if (path === basename || path === `${basename}/`) {
    return "/";
  }
  if (path.startsWith(`${basename}/`)) {
    return path.slice(basename.length);
  }
  return path;
}

function formatMoney(amount, currency = "GBP") {
  if (amount === null || amount === undefined || amount === "") {
    return "No pre-payment";
  }
  try {
    return new Intl.NumberFormat("en-GB", { style: "currency", currency }).format(amount);
  } catch (error) {
    return `${amount} ${currency}`;
  }
}

function useApiResource(loadFn, deps) {
  const [state, setState] = useState({ loading: true, data: null, error: "", errorPayload: null });

  const reload = useCallback(async () => {
    setState((current) => ({ ...current, loading: true, error: "", errorPayload: null }));
    try {
      const { response, data } = await loadFn();
      if (!response.ok || data.ok === false) {
        const message = data.error || (data.errors ? data.errors.join(" ") : `Request failed (${response.status})`);
        setState({ loading: false, data: null, error: message, errorPayload: data || null });
        return;
      }
      setState({ loading: false, data, error: "", errorPayload: null });
    } catch (error) {
      setState({ loading: false, data: null, error: error.message || "Request failed.", errorPayload: null });
    }
  }, deps);

  useEffect(() => {
    reload();
  }, [reload]);

  return { ...state, reload };
}

function LoadingState({ title = "Loading portal", detail = "Pulling the latest clinic data." }) {
  return (
    <section className="rp-empty-card">
      <span className="rp-eyebrow">Loading</span>
      <h2>{title}</h2>
      <p>{detail}</p>
    </section>
  );
}

function ErrorState({ title = "Something went wrong", detail, actionLabel = "Try again", onRetry }) {
  return (
    <section className="rp-empty-card rp-empty-card-error">
      <span className="rp-eyebrow">Error</span>
      <h2>{title}</h2>
      <p>{detail}</p>
      {onRetry ? (
        <button type="button" className="rp-button rp-button-primary" onClick={onRetry}>
          {actionLabel}
        </button>
      ) : null}
    </section>
  );
}

function StatusPill({ tone = "sky", children }) {
  return <span className={`rp-pill tone-${tone}`}>{children}</span>;
}

function PortalLayout({ session, config }) {
  return (
    <div className="rp-shell">
      <header className="rp-header">
        <div>
          <div className="rp-eyebrow">React patient portal</div>
          <h1>{session.user.first_name}, your portal is live.</h1>
          <p>
            This React workspace now sits on top of the same booking, care-plan, results, and messaging logic used by the
            clinic app.
          </p>
        </div>
        <div className="rp-header-card">
          <span>{session.ui_branding.clinic_name}</span>
          <strong>{session.user.display_name}</strong>
          <small>{session.user.email}</small>
        </div>
      </header>

      <nav className="rp-top-nav" aria-label="Portal sections">
        {session.nav.map((item) =>
          item.legacy ? (
            <a key={item.key} className="rp-top-link" href={item.url}>
              {item.label}
            </a>
          ) : (
            <NavLink
              key={item.key}
              className={({ isActive }) => `rp-top-link ${isActive ? "active" : ""}`.trim()}
              to={toSpaPath(item.url, config.routerBasename)}
              end={item.key === "dashboard"}
            >
              {item.label}
            </NavLink>
          )
        )}
      </nav>

      <Routes>
        <Route path="/" element={<DashboardPage config={config} session={session} />} />
        <Route path="/intake" element={<IntakePage config={config} />} />
        <Route path="/appointments" element={<AppointmentsPage config={config} session={session} />} />
        <Route path="/care-plan" element={<CarePlanPage config={config} />} />
        <Route path="/messages" element={<MessagesPage config={config} />} />
        <Route path="/results" element={<ResultsPage config={config} />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </div>
  );
}

function StaffPortalLayout({ session, config }) {
  return (
    <div className="rp-shell">
      <header className="rp-header">
        <div>
          <div className="rp-eyebrow">React staff portal</div>
          <h1>{session.user.first_name}, clinic operations are live.</h1>
          <p>
            This workspace now runs the staff dashboard in React while keeping complex legacy screens available inside the
            same shell during the migration.
          </p>
        </div>
        <div className="rp-header-card">
          <span>{session.ui_branding.clinic_name}</span>
          <strong>{session.user.display_name}</strong>
          <small>{session.user.role === "clinician" ? "Practitioner access" : "Staff access"}</small>
        </div>
      </header>

      <nav className="rp-top-nav" aria-label="Staff sections">
        {session.nav.map((item) => (
          <NavLink
            key={item.key}
            className={({ isActive }) => `rp-top-link ${isActive ? "active" : ""}`.trim()}
            to={toSpaPath(item.url, config.routerBasename)}
            end={item.key === "dashboard"}
          >
            {item.label}
          </NavLink>
        ))}
      </nav>

      <Routes>
        <Route path="/" element={session.user.role === "clinician" ? <PractitionerDashboardPage config={config} /> : <ClinicOpsPage config={config} />} />
        <Route path="/clinic-ops" element={<ClinicOpsPage config={config} />} />
        <Route path="/calendar" element={<LegacyEmbedPage src="/staff/calendar?embed=1" title="Calendar" detail="The live diary is still running in the legacy view while the staff shell migrates." />} />
        <Route path="/settings" element={<LegacyEmbedPage src="/staff/settings?embed=1" title="Settings" detail="Clinic configuration is still rendered by the legacy settings workspace." />} />
        <Route path="/reminders" element={<LegacyEmbedPage src="/staff/reminders?embed=1" title="Reminders" detail="Reminder operations remain on the legacy page for now." />} />
        <Route path="/journal" element={<LegacyEmbedPage src="/staff/journal?embed=1" title="Journal" detail="Practitioner journal remains on the legacy page for now." />} />
        <Route path="/learning" element={<LegacyEmbedPage src="/staff/learning?embed=1" title="Learning" detail="Learning content remains on the legacy page for now." />} />
        <Route path="/messaging" element={<LegacyEmbedPage src="/staff/messaging?embed=1" title="Messaging" detail="Staff messaging remains on the legacy page for now." />} />
        <Route path="/new-invite" element={<LegacyEmbedPage src="/staff/invitations/new?embed=1" title="New invite" detail="Invitation creation remains on the legacy page for now." />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </div>
  );
}

function ClinicOpsPage({ config }) {
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

function PractitionerDashboardPage({ config }) {
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

function LegacyEmbedPage({ src, title, detail }) {
  const standaloneUrl = src.replace("?embed=1", "").replace("&embed=1", "");

  return (
    <div className="rp-page-grid">
      <section className="rp-card rp-hero-card">
        <div>
          <div className="rp-eyebrow">Legacy workspace</div>
          <h2>{title}</h2>
          <p>{detail}</p>
        </div>
        <div className="rp-header-card">
          <span>Mode</span>
          <strong>Embedded</strong>
          <small>Kept live while the React migration continues.</small>
          <a className="rp-button rp-button-secondary" href={standaloneUrl}>
            Open standalone page
          </a>
        </div>
      </section>

      <section className="rp-card">
        <div className="rp-embed-frame-wrap">
          <iframe className="rp-embed-frame" src={src} title={title} />
        </div>
      </section>
    </div>
  );
}

function DashboardPage({ config, session }) {
  const resource = useApiResource(() => fetchJson(config.dashboardEndpoint), [config.dashboardEndpoint]);

  if (resource.loading) {
    return <LoadingState title="Loading dashboard" detail="Building your next-step summary." />;
  }
  if (resource.error) {
    return <ErrorState detail={resource.error} onRetry={resource.reload} />;
  }

  const dashboard = resource.data.dashboard;

  return (
    <div className="rp-page-grid">
      <section className="rp-card rp-hero-card">
        <div>
          <div className="rp-eyebrow">Next best step</div>
          <h2>{dashboard.next_step.title}</h2>
          <p>{dashboard.next_step.detail}</p>
        </div>
        <div className="rp-hero-actions">
          <a className="rp-button rp-button-primary" href={dashboard.next_step.action_url}>
            {dashboard.next_step.action_label}
          </a>
          <span className={`rp-note tone-${dashboard.next_step.tone}`}>{session.user.email}</span>
        </div>
      </section>

      <section className="rp-metric-grid">
        {dashboard.portal_metrics.map((metric) => (
          <article key={metric.label} className="rp-card rp-metric-card">
            <span>{metric.label}</span>
            <strong>{metric.value}</strong>
            <small>{metric.detail}</small>
          </article>
        ))}
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

function IntakePage({ config }) {
  const resource = useApiResource(() => fetchJson(config.intakeEndpoint), [config.intakeEndpoint]);

  return (
    <div className="rp-page-grid">
      <section className="rp-card rp-hero-card">
        <div>
          <div className="rp-eyebrow">Intake</div>
          <h2>Complete your onboarding form</h2>
          <p>
            The intake route now lives inside the React portal, while the existing questionnaire engine still handles the
            underlying form logic and autosave behavior.
          </p>
        </div>
        <div className="rp-header-card">
          <span>Status</span>
          <strong>
            {resource.data?.status === "submitted"
              ? "Submitted"
              : resource.data?.status === "draft"
                ? "Draft in progress"
                : "Not started"}
          </strong>
          <small>Changes save directly to your portal record.</small>
        </div>
      </section>

      <section className="rp-card">
        <div className="rp-section-head">
          <div>
            <span className="rp-eyebrow">Embedded intake</span>
            <h2>Client questionnaire</h2>
          </div>
          <a className="rp-button rp-button-secondary" href="/intake" target="_blank" rel="noreferrer">
            Open standalone
          </a>
        </div>
        {resource.loading ? <div className="rp-empty-inline">Checking your current intake status...</div> : null}
        {resource.error ? <div className="rp-alert rp-alert-error">{resource.error}</div> : null}
        <div className="rp-intake-frame-wrap">
          <iframe className="rp-intake-frame" src={config.intakeEmbedEndpoint} title="Patient intake form" />
        </div>
      </section>
    </div>
  );
}

function AppointmentsPage({ config }) {
  const location = useLocation();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const resource = useApiResource(
    () => fetchJson(buildUrl(config.appointmentsEndpoint, Object.fromEntries(searchParams.entries()))),
    [config.appointmentsEndpoint, location.search]
  );
  const [form, setForm] = useState(null);
  const [availability, setAvailability] = useState(null);
  const [selectedSlot, setSelectedSlot] = useState("");
  const [notice, setNotice] = useState("");
  const [errorNotice, setErrorNotice] = useState("");
  const [busyAction, setBusyAction] = useState(false);

  useEffect(() => {
    const page = resource.data?.appointments;
    if (!page) {
      return;
    }
    setForm({
      serviceId: String(page.selected_service_id || ""),
      appointmentType: page.selected_appointment_type || "care_plan",
      durationMinutes: String(page.selected_duration_minutes || page.booking_policy.duration_minutes || 15),
      locationId: String(page.selected_location_id || ""),
      clinicianUserId: page.selected_clinician_choice || (page.allow_any_clinician ? "any" : ""),
      appointmentDate: page.booking_date || "",
      patientDetails: "",
      carePlanVisitId: page.selected_care_plan_visit ? String(page.selected_care_plan_visit.id) : "",
    });
    setAvailability(page.booking_availability);
    setSelectedSlot("");
  }, [resource.data]);

  const page = resource.data?.appointments;
  const selectedService = useMemo(() => {
    if (!page || !form) {
      return null;
    }
    return page.service_options.find((item) => String(item.id) === String(form.serviceId)) || null;
  }, [page, form]);

  const allowAnyClinician = Boolean(selectedService ? selectedService.routing_mode === "team_round_robin" : page?.allow_any_clinician);

  useEffect(() => {
    if (!page || !form) {
      return;
    }
    let cancelled = false;
    const loadAvailability = async () => {
      try {
        const { response, data } = await fetchJson(
          buildUrl(config.availabilityEndpoint, {
            date: form.appointmentDate,
            location_id: form.locationId,
            clinician_user_id: allowAnyClinician && (!form.clinicianUserId || form.clinicianUserId === "any") ? "any" : form.clinicianUserId,
            service_id: form.serviceId,
            appointment_type: form.appointmentType,
            duration_minutes: form.durationMinutes,
          })
        );
        if (cancelled) {
          return;
        }
        if (!response.ok || data.ok === false) {
          setAvailability({ ...(availability || {}), error: data.error || "Availability could not be loaded.", available_slots: [] });
          return;
        }
        setAvailability(data.availability);
      } catch (error) {
        if (!cancelled) {
          setAvailability({ ...(availability || {}), error: error.message, available_slots: [] });
        }
      }
    };
    loadAvailability();
    return () => {
      cancelled = true;
    };
  }, [config.availabilityEndpoint, page, form, allowAnyClinician]);

  const onSelectService = (service) => {
    if (!form || page?.selected_care_plan_visit) {
      return;
    }
    setSelectedSlot("");
    setForm((current) => ({
      ...current,
      serviceId: String(service.id),
      appointmentType: service.appointment_type,
      durationMinutes: String(service.duration_minutes),
      clinicianUserId: service.routing_mode === "team_round_robin" ? "any" : current.clinicianUserId,
    }));
  };

  const updateField = (key, value) => {
    setSelectedSlot("");
    setForm((current) => ({ ...current, [key]: value }));
  };

  const submitBooking = async (event) => {
    event.preventDefault();
    if (!form || !selectedSlot) {
      setErrorNotice("Choose a live time slot before confirming your booking.");
      return;
    }
    setBusyAction(true);
    setNotice("");
    setErrorNotice("");
    const { response, data } = await fetchJson(config.bookAppointmentEndpoint, {
      method: "POST",
      body: JSON.stringify({
        service_id: form.serviceId,
        appointment_type: form.appointmentType,
        duration_minutes: form.durationMinutes,
        location_id: form.locationId,
        clinician_user_id: allowAnyClinician && (!form.clinicianUserId || form.clinicianUserId === "any") ? "any" : form.clinicianUserId,
        appointment_date: form.appointmentDate,
        slot_start: selectedSlot,
        patient_details: form.patientDetails,
        care_plan_visit_id: form.carePlanVisitId || undefined,
      }),
    });
    setBusyAction(false);
    if (!response.ok || data.ok === false) {
      setErrorNotice(data.errors ? data.errors.join(" ") : data.error || "Booking failed.");
      return;
    }
    setNotice(
      form.carePlanVisitId
        ? "Your next recommended care-plan visit is booked."
        : "Appointment booked from your portal."
    );
    setErrorNotice("");
    setSelectedSlot("");
    if (form.carePlanVisitId) {
      setSearchParams({});
    }
    resource.reload();
  };

  const cancelAppointment = async (appointment) => {
    if (!window.confirm(`Cancel ${appointment.appointment_type_label} on ${appointment.starts_label}?`)) {
      return;
    }
    setBusyAction(true);
    setNotice("");
    setErrorNotice("");
    const { response, data } = await fetchJson(`${config.cancelAppointmentBase}/${appointment.id}/cancel`, {
      method: "POST",
      body: JSON.stringify({}),
    });
    setBusyAction(false);
    if (!response.ok || data.ok === false) {
      setErrorNotice(data.errors ? data.errors.join(" ") : data.error || "Cancellation failed.");
      return;
    }
    setNotice(data.message || "Appointment cancelled.");
    if (data.care_plan_visit_id) {
      setSearchParams({ care_plan_visit_id: String(data.care_plan_visit_id) });
    }
    resource.reload();
  };

  if (resource.loading || !page || !form) {
    return <LoadingState title="Loading appointments" detail="Syncing the live diary and your booking options." />;
  }
  if (resource.error) {
    return <ErrorState detail={resource.error} onRetry={resource.reload} />;
  }

  return (
    <div className="rp-page-grid">
      <section className="rp-card rp-hero-card">
        <div>
          <div className="rp-eyebrow">Appointments</div>
          <h2>Your visit calendar</h2>
          <p>Book and manage visits against the same service rules, availability windows, and care-plan steps used by the clinic diary.</p>
        </div>
        <div className="rp-header-card">
          <span>{page.care_plan.plan ? "Care plan" : "Next visit"}</span>
          <strong>{page.care_plan.plan ? page.care_plan.adherence.title : page.schedule.next_appointment?.appointment_type_label || "No visits booked"}</strong>
          <small>{page.care_plan.plan ? page.care_plan.adherence.detail : page.schedule.next_appointment?.starts_label || "Choose a live slot below."}</small>
        </div>
      </section>

      {notice ? <div className="rp-alert rp-alert-success">{notice}</div> : null}
      {errorNotice ? <div className="rp-alert rp-alert-error">{errorNotice}</div> : null}
      {page.booking_disabled_reason ? <div className="rp-alert rp-alert-error">{page.booking_disabled_reason}</div> : null}

      <section className="rp-card">
        <div className="rp-section-head">
          <div>
            <span className="rp-eyebrow">Visit types</span>
            <h2>Booked appointments</h2>
          </div>
        </div>
        <div className="rp-chip-row">
          <StatusPill tone="life">{page.schedule.counts.initial_consult} Initial Consultation</StatusPill>
          <StatusPill tone="sky">{page.schedule.counts.report_of_findings} Report of Findings</StatusPill>
          <StatusPill tone="warm">{page.schedule.counts.care_plan} Care Plan Visit</StatusPill>
        </div>
      </section>

      <section className="rp-two-column">
        <article className="rp-card rp-booking-card">
          <div className="rp-section-head">
            <div>
              <span className="rp-eyebrow">Self-service booking</span>
              <h2>{page.selected_care_plan_visit ? page.selected_care_plan_visit.label : "Choose an appointment type"}</h2>
            </div>
            {page.selected_care_plan_visit ? <StatusPill tone={page.selected_care_plan_visit.visit_kind_tone}>{page.selected_care_plan_visit.visit_kind_label}</StatusPill> : null}
          </div>

          {page.selected_care_plan_visit ? (
            <div className="rp-selected-visit">
              <strong>{page.selected_care_plan_visit.suggested_long_label}</strong>
              <small>{page.selected_care_plan_visit.duration_minutes} min · linked to your active care plan</small>
            </div>
          ) : (
            <div className="rp-service-grid">
              {page.service_options.map((service) => (
                <button
                  key={service.id}
                  type="button"
                  className={`rp-service-card ${String(service.id) === String(form.serviceId) ? "active" : ""}`.trim()}
                  onClick={() => onSelectService(service)}
                >
                  <div>
                    <strong>{service.label}</strong>
                    <p>{service.description || service.appointment_type_label}</p>
                  </div>
                  <small>
                    {service.duration_minutes} min · {service.routing_mode_label}
                  </small>
                </button>
              ))}
            </div>
          )}

          <form className="rp-booking-form" onSubmit={submitBooking}>
            <div className="rp-form-grid">
              <label>
                <span>Location</span>
                <select value={form.locationId} onChange={(event) => updateField("locationId", event.target.value)} disabled={Boolean(page.booking_disabled_reason)}>
                  {page.location_options.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                <span>Chiropractor</span>
                <select value={form.clinicianUserId} onChange={(event) => updateField("clinicianUserId", event.target.value)} disabled={Boolean(page.booking_disabled_reason)}>
                  {allowAnyClinician ? <option value="any">Any available</option> : null}
                  {page.clinician_options.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </label>
            </div>

            <div className="rp-form-grid">
              <label>
                <span>Date</span>
                <input type="date" value={form.appointmentDate} onChange={(event) => updateField("appointmentDate", event.target.value)} disabled={Boolean(page.booking_disabled_reason)} />
              </label>
              <label>
                <span>Booking note</span>
                <input
                  type="text"
                  value={form.patientDetails}
                  onChange={(event) => updateField("patientDetails", event.target.value)}
                  placeholder="Any note for the clinic"
                  disabled={Boolean(page.booking_disabled_reason)}
                />
              </label>
            </div>

            <div className="rp-slot-panel">
              <div className="rp-slot-head">
                <div>
                  <strong>{availability?.date_label || "Available times"}</strong>
                  <small>
                    {availability?.service_label || selectedService?.label || "Booking service"}
                    {availability?.requires_payment ? ` · ${formatMoney(availability.price_amount, availability.currency)}` : ""}
                  </small>
                </div>
                {availability?.routing_mode_label ? <StatusPill tone="sky">{availability.routing_mode_label}</StatusPill> : null}
              </div>
              {availability?.error ? <div className="rp-empty-inline">{availability.error}</div> : null}
              <div className="rp-slot-grid">
                {(availability?.available_slots || []).map((slot) => (
                  <button
                    key={slot.value}
                    type="button"
                    className={`rp-slot ${selectedSlot === slot.value ? "active" : ""}`.trim()}
                    onClick={() => setSelectedSlot(slot.value)}
                  >
                    <strong>{slot.start_label}</strong>
                    <small>{slot.clinician_name || "Clinic team"}</small>
                  </button>
                ))}
              </div>
              {!availability?.available_slots?.length && !availability?.error ? (
                <div className="rp-empty-inline">No live times are available for the current filters. Change the date or chiropractor.</div>
              ) : null}
            </div>

            <div className="rp-inline-actions">
              <button type="submit" className="rp-button rp-button-primary" disabled={busyAction || Boolean(page.booking_disabled_reason)}>
                {busyAction ? "Working..." : "Confirm booking"}
              </button>
            </div>
          </form>
        </article>

        <article className="rp-card">
          <div className="rp-section-head">
            <div>
              <span className="rp-eyebrow">Upcoming visits</span>
              <h2>Your live schedule</h2>
            </div>
          </div>
          {page.schedule.upcoming.length ? (
            <div className="rp-stack-list">
              {page.schedule.upcoming.map((appointment) => (
                <div key={appointment.id} className="rp-list-card">
                  <div className="rp-list-head">
                    <div>
                      <StatusPill tone={appointment.type_tone}>{appointment.type_label}</StatusPill>
                      <strong>{appointment.starts_label}</strong>
                    </div>
                    <StatusPill tone={appointment.status_tone}>{appointment.status_label}</StatusPill>
                  </div>
                  <p>{appointment.location_name || "Clinic location not set"}{appointment.clinician_name ? ` · ${appointment.clinician_name}` : ""}</p>
                  {appointment.patient_details ? <small>{appointment.patient_details}</small> : null}
                  {appointment.reminder_label ? <small>{appointment.reminder_label}</small> : null}
                  {appointment.can_self_cancel ? (
                    <div className="rp-inline-actions rp-inline-actions-tight">
                      <button type="button" className="rp-button rp-button-secondary" onClick={() => cancelAppointment(appointment)} disabled={busyAction}>
                        Cancel online
                      </button>
                    </div>
                  ) : null}
                </div>
              ))}
            </div>
          ) : (
            <div className="rp-empty-inline">No future appointments are booked yet.</div>
          )}
        </article>
      </section>

      <section className="rp-card">
        <div className="rp-section-head">
          <div>
            <span className="rp-eyebrow">History</span>
            <h2>Past visits</h2>
          </div>
        </div>
        {page.schedule.history.length ? (
          <div className="rp-history-grid">
            {page.schedule.history.slice(0, 8).map((appointment) => (
              <div key={appointment.id} className="rp-history-card">
                <div className="rp-list-head">
                  <strong>{appointment.date_label}</strong>
                  <StatusPill tone={appointment.status_tone}>{appointment.status_label}</StatusPill>
                </div>
                <p>{appointment.type_label}</p>
                <small>{appointment.location_name || "Clinic location not set"}</small>
              </div>
            ))}
          </div>
        ) : (
          <div className="rp-empty-inline">No appointment history yet.</div>
        )}
      </section>
    </div>
  );
}

function CarePlanPage({ config }) {
  const navigate = useNavigate();
  const resource = useApiResource(() => fetchJson(config.carePlanEndpoint), [config.carePlanEndpoint]);

  if (resource.loading) {
    return <LoadingState title="Loading care plan" detail="Syncing your current stage of care." />;
  }
  if (resource.error) {
    return <ErrorState detail={resource.error} onRetry={resource.reload} />;
  }

  const carePlan = resource.data.care_plan;
  if (!carePlan.plan) {
    return (
      <section className="rp-empty-card">
        <span className="rp-eyebrow">Care plan</span>
        <h2>No active care plan</h2>
        <p>Your chiropractor has not published an active plan yet.</p>
      </section>
    );
  }

  return (
    <div className="rp-page-grid">
      <section className="rp-card rp-hero-card">
        <div>
          <div className="rp-eyebrow">Care plan</div>
          <h2>{carePlan.plan.title}</h2>
          <p>
            {carePlan.plan.frequency_label} for {carePlan.plan.duration_weeks} weeks · {carePlan.plan.total_visits} visits
          </p>
        </div>
        <div className="rp-header-card">
          <span>Status</span>
          <strong>{carePlan.adherence.title}</strong>
          <small>{carePlan.adherence.progress_label}</small>
        </div>
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
            <span className="rp-eyebrow">Next action</span>
            <h2>{carePlan.adherence.title}</h2>
          </div>
          <StatusPill tone={carePlan.adherence.tone}>{carePlan.adherence.state.replace(/_/g, " ")}</StatusPill>
        </div>
        <p>{carePlan.adherence.detail}</p>
        <div className="rp-inline-actions">
          <a className="rp-button rp-button-primary" href={carePlan.adherence.action_url}>
            {carePlan.adherence.action_label}
          </a>
          <a className="rp-button rp-button-secondary" href={carePlan.adherence.secondary_action_url}>
            {carePlan.adherence.secondary_action_label}
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

function MessagesPage({ config }) {
  const resource = useApiResource(() => fetchJson(config.messagesEndpoint), [config.messagesEndpoint]);
  const [topic, setTopic] = useState("appointment");
  const [body, setBody] = useState("");
  const [notice, setNotice] = useState("");
  const [errorNotice, setErrorNotice] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const sendMessage = async (event) => {
    event.preventDefault();
    setSubmitting(true);
    setNotice("");
    setErrorNotice("");
    const { response, data } = await fetchJson(config.messagesEndpoint, {
      method: "POST",
      body: JSON.stringify({ topic, body }),
    });
    setSubmitting(false);
    if (!response.ok || data.ok === false) {
      setErrorNotice(data.errors ? data.errors.join(" ") : data.error || "Message failed.");
      return;
    }
    setBody("");
    setNotice(data.message || "Message sent.");
    resource.reload();
  };

  if (resource.loading) {
    return <LoadingState title="Loading messages" detail="Opening your secure thread." />;
  }
  if (resource.error) {
    return <ErrorState detail={resource.error} onRetry={resource.reload} />;
  }

  const messages = resource.data.messages;
  const topics = resource.data.message_topics;

  return (
    <div className="rp-two-column">
      <section className="rp-card">
        <div className="rp-section-head">
          <div>
            <span className="rp-eyebrow">Messages</span>
            <h2>Your chiropractic thread</h2>
          </div>
          <StatusPill tone={resource.data.unread_before_open ? "rose" : "life"}>
            {resource.data.unread_before_open ? `${resource.data.unread_before_open} unread` : "Up to date"}
          </StatusPill>
        </div>
        <div className="rp-message-stream">
          {messages.length ? (
            messages.map((message) => (
              <article key={message.id} className={`rp-message ${message.sender_role === "client" ? "is-client" : "is-staff"}`.trim()}>
                <div className="rp-message-bubble">
                  <div className="rp-list-head">
                    <div>
                      <StatusPill tone={message.topic_tone}>{message.topic_label}</StatusPill>
                      <strong>{message.sender_name}</strong>
                    </div>
                  </div>
                  <p>{message.body}</p>
                  <small>{message.created_label}</small>
                </div>
              </article>
            ))
          ) : (
            <div className="rp-empty-inline">No messages yet. Send your first secure update to the clinic.</div>
          )}
        </div>
      </section>

      <section className="rp-card">
        <div className="rp-section-head">
          <div>
            <span className="rp-eyebrow">Send message</span>
            <h2>Write to your care team</h2>
          </div>
        </div>
        {notice ? <div className="rp-alert rp-alert-success">{notice}</div> : null}
        {errorNotice ? <div className="rp-alert rp-alert-error">{errorNotice}</div> : null}
        <form className="rp-form-stack" onSubmit={sendMessage}>
          <label>
            <span>Topic</span>
            <select value={topic} onChange={(event) => setTopic(event.target.value)}>
              {topics.map((item) => (
                <option key={item.value} value={item.value}>
                  {item.label}
                </option>
              ))}
            </select>
          </label>
          <label>
            <span>Message</span>
            <textarea rows="6" value={body} onChange={(event) => setBody(event.target.value)} placeholder="Write your update, question, or booking request..." />
          </label>
          <button type="submit" className="rp-button rp-button-primary" disabled={submitting}>
            {submitting ? "Sending..." : "Send message"}
          </button>
        </form>
      </section>
    </div>
  );
}

function ResultsPage({ config }) {
  const resource = useApiResource(() => fetchJson(config.resultsEndpoint), [config.resultsEndpoint]);

  if (resource.loading) {
    return <LoadingState title="Loading results" detail="Pulling your latest published findings." />;
  }
  if (resource.error) {
    if (resource.errorPayload?.redirect) {
      return (
        <section className="rp-empty-card">
          <span className="rp-eyebrow">Results</span>
          <h2>Results are not ready yet</h2>
          <p>{resource.error}</p>
          <a className="rp-button rp-button-primary" href={resource.errorPayload.redirect}>
            Open intake form
          </a>
        </section>
      );
    }
    return <ErrorState detail={resource.error} onRetry={resource.reload} />;
  }

  const summary = resource.data.results.summary;
  const report = summary.visit_report || null;
  const questionnaires = summary.questionnaires || [];

  return (
    <div className="rp-page-grid">
      <section className="rp-card rp-hero-card">
        <div>
          <div className="rp-eyebrow">Results</div>
          <h2>{summary.full_name}</h2>
          <p>{report?.patient_summary || "Your chiropractor has shared your latest findings and recommendations."}</p>
        </div>
        <div className="rp-header-card">
          <span>Status</span>
          <strong>{summary.status === "submitted" ? "Submitted" : "Draft"}</strong>
          <small>Updated {summary.updated_at || "today"}</small>
        </div>
      </section>

      <section className="rp-two-column">
        <article className="rp-card">
          <div className="rp-section-head">
            <div>
              <span className="rp-eyebrow">Chief complaint</span>
              <h2>{summary.reason?.chiefComplaint || "Not recorded yet"}</h2>
            </div>
          </div>
          <div className="rp-chip-row">
            {(summary.reason_tags || []).map((tag) => (
              <StatusPill key={tag} tone="life">{tag}</StatusPill>
            ))}
          </div>
          <div className="rp-key-value-list">
            <div><span>Current pain</span><strong>{summary.pain?.currentLevel ?? "-"}/10</strong></div>
            <div><span>Worst pain</span><strong>{summary.pain?.worstLevel ?? "-"}/10</strong></div>
            <div><span>Commitment</span><strong>{summary.goals?.commitmentLevel || "-"}/10</strong></div>
            <div><span>Submitted</span><strong>{summary.submitted_at || "Not recorded"}</strong></div>
          </div>
        </article>

        <article className="rp-card">
          <div className="rp-section-head">
            <div>
              <span className="rp-eyebrow">Recommendations</span>
              <h2>What to focus on</h2>
            </div>
          </div>
          <div className="rp-text-stack">
            <p>{report?.patient_key_findings || report?.assessment || "Your findings will appear here after the assessment is published."}</p>
            <p>{report?.patient_recommendations || report?.care_plan || "Recommendations have not been published yet."}</p>
            {report?.follow_up_plan ? <p>{report.follow_up_plan}</p> : null}
          </div>
        </article>
      </section>

      <section className="rp-card">
        <div className="rp-section-head">
          <div>
            <span className="rp-eyebrow">Outcome scores</span>
            <h2>Questionnaires</h2>
          </div>
        </div>
        {questionnaires.length ? (
          <div className="rp-history-grid">
            {questionnaires.map((questionnaire) => (
              <div key={questionnaire.questionnaireId} className="rp-history-card">
                <strong>{questionnaire.displayName}</strong>
                <p>{questionnaire.percent ?? questionnaire.rawScore}%</p>
                <small>{questionnaire.interpretation || "No interpretation"}</small>
              </div>
            ))}
          </div>
        ) : (
          <div className="rp-empty-inline">No questionnaire scores have been saved yet.</div>
        )}
      </section>

      <section className="rp-two-column">
        <article className="rp-card">
          <div className="rp-section-head">
            <div>
              <span className="rp-eyebrow">Pain areas</span>
              <h2>Reported regions</h2>
            </div>
          </div>
          <div className="rp-chip-row">
            {(summary.pain_areas || []).map((area) => (
              <StatusPill key={area} tone="rose">{area}</StatusPill>
            ))}
          </div>
        </article>

        <article className="rp-card">
          <div className="rp-section-head">
            <div>
              <span className="rp-eyebrow">Goals</span>
              <h2>Patient priorities</h2>
            </div>
          </div>
          <div className="rp-chip-row">
            {(summary.goal_tags || []).map((goal) => (
              <StatusPill key={goal} tone="warm">{goal}</StatusPill>
            ))}
          </div>
          {summary.next_steps?.length ? (
            <ul className="rp-bullet-list">
              {summary.next_steps.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          ) : null}
        </article>
      </section>
    </div>
  );
}

function LegacyRedirectPage({ to, label }) {
  useEffect(() => {
    window.location.assign(to);
  }, [to]);

  return <LoadingState title={`Opening ${label}`} detail="Handing you over to the legacy flow while this section is still being migrated." />;
}

export default function App({ config }) {
  const sessionResource = useApiResource(() => fetchJson(config.sessionEndpoint), [config.sessionEndpoint]);

  if (sessionResource.loading) {
    return <LoadingState detail="Checking your portal session and clinic settings." />;
  }

  if (sessionResource.error) {
    return <ErrorState detail={sessionResource.error} onRetry={sessionResource.reload} />;
  }

  if (config.portalKind === "staff") {
    return <StaffPortalLayout session={sessionResource.data} config={config} />;
  }

  return <PortalLayout session={sessionResource.data} config={config} />;
}
