import React, { useCallback, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { buildUrl, fetchJson } from "../../../shared/api";
import { copyText } from "../../../shared/browser";
import { formatMoney } from "../../../shared/format";
import { useApiResource } from "../../../shared/hooks";
import { ErrorState, LoadingState, StatusPill } from "../../../shared/ui";

function mondayIndexForToday() {
  return (new Date().getDay() + 6) % 7;
}

function flattenScheduleTemplates(scheduleTemplates = []) {
  return scheduleTemplates.flatMap((day) =>
    (day.windows || []).map((windowItem) => ({
      ...windowItem,
      weekday: day.weekday,
      weekday_label: day.label,
    }))
  );
}

export default function StaffCalendarPage({ config }) {
  const [searchParams, setSearchParams] = useSearchParams();
  const month = searchParams.get("month") || "";
  const [notice, setNotice] = useState("");
  const [errorNotice, setErrorNotice] = useState("");
  const [sendingKey, setSendingKey] = useState("");
  const [copyState, setCopyState] = useState("");
  const [savingAvailability, setSavingAvailability] = useState(false);
  const [removingWindowId, setRemovingWindowId] = useState("");
  const [savingServiceId, setSavingServiceId] = useState("");
  const [availabilityForm, setAvailabilityForm] = useState({
    clinicianUserId: "",
    locationId: "",
    weekday: String(mondayIndexForToday()),
    windowType: "shift",
    startsTime: "09:00",
    endsTime: "17:00",
    label: "",
  });
  const [durationDrafts, setDurationDrafts] = useState({});
  const endpoint = useMemo(
    () => buildUrl(config.staffCalendarEndpoint, { month }),
    [config.staffCalendarEndpoint, month]
  );
  const resource = useApiResource(() => fetchJson(endpoint), [endpoint]);

  useEffect(() => {
    if (!resource.data) {
      return;
    }
    const viewerId = resource.data.viewer?.role === "clinician" ? String(resource.data.viewer.id) : "";
    const firstClinicianId = viewerId || String(resource.data.clinician_options?.[0]?.value || "");
    const firstLocationId = String(resource.data.location_options?.[0]?.value || resource.data.locations?.[0]?.id || "");
    setAvailabilityForm((current) => ({
      ...current,
      clinicianUserId: current.clinicianUserId || firstClinicianId,
      locationId: current.locationId || firstLocationId,
      weekday: current.weekday || String(mondayIndexForToday()),
    }));
    setDurationDrafts(
      Object.fromEntries(
        (resource.data.service_inventory || []).map((service) => [service.id, String(service.duration_minutes)])
      )
    );
  }, [resource.data]);

  const availabilityGroups = useMemo(() => {
    if (!resource.data) {
      return [];
    }
    const weekdayMap = new Map((resource.data.weekday_options || []).map((item) => [item.value, item.label]));
    const groups = new Map(
      (resource.data.clinician_options || []).map((option) => [
        `clinician-${option.value}`,
        {
          key: `clinician-${option.value}`,
          label: option.label,
          helper: option.email || "",
          clinicianUserId: option.value,
          days: new Map(),
          totalWindows: 0,
        },
      ])
    );

    flattenScheduleTemplates(resource.data.schedule_templates).forEach((windowItem) => {
      const groupKey = windowItem.clinician_user_id ? `clinician-${windowItem.clinician_user_id}` : "clinic-wide";
      if (!groups.has(groupKey)) {
        groups.set(groupKey, {
          key: groupKey,
          label: "Clinic-wide fallback",
          helper: "Used when a clinician-specific block is not set.",
          clinicianUserId: null,
          days: new Map(),
          totalWindows: 0,
        });
      }
      const group = groups.get(groupKey);
      if (!group.days.has(windowItem.weekday)) {
        group.days.set(windowItem.weekday, {
          weekday: windowItem.weekday,
          label: weekdayMap.get(windowItem.weekday) || windowItem.weekday_label,
          windows: [],
        });
      }
      group.days.get(windowItem.weekday).windows.push(windowItem);
      group.totalWindows += 1;
    });

    return Array.from(groups.values())
      .map((group) => ({
        ...group,
        days: Array.from(group.days.values()).sort((a, b) => a.weekday - b.weekday),
      }))
      .sort((a, b) => {
        if (a.clinicianUserId === null) {
          return 1;
        }
        if (b.clinicianUserId === null) {
          return -1;
        }
        return a.label.localeCompare(b.label);
      });
  }, [resource.data]);

  const setMonth = useCallback((nextMonth) => {
    const next = new URLSearchParams();
    if (nextMonth) {
      next.set("month", nextMonth);
    }
    setSearchParams(next);
  }, [setSearchParams]);

  const updateAvailabilityField = (key, value) => {
    setAvailabilityForm((current) => ({ ...current, [key]: value }));
  };

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

  const submitAvailability = async (event) => {
    event.preventDefault();
    if (!resource.data) {
      return;
    }
    setSavingAvailability(true);
    setNotice("");
    setErrorNotice("");
    const payload = {
      clinician_user_id: availabilityForm.clinicianUserId,
      location_id: availabilityForm.locationId,
      weekday: availabilityForm.weekday,
      window_type: availabilityForm.windowType,
      starts_time: availabilityForm.startsTime,
      ends_time: availabilityForm.endsTime,
      label: availabilityForm.label,
    };
    const { response, data } = await fetchJson(resource.data.routes.create_schedule_window, {
      method: "POST",
      body: JSON.stringify(payload),
    });
    setSavingAvailability(false);
    if (!response.ok || data.ok === false) {
      setErrorNotice(data.error || "Availability could not be saved.");
      return;
    }
    setNotice(data.message || "Recurring weekly availability saved.");
    setAvailabilityForm((current) => ({
      ...current,
      label: "",
    }));
    resource.reload();
  };

  const removeAvailabilityWindow = async (windowId) => {
    if (!resource.data) {
      return;
    }
    setRemovingWindowId(String(windowId));
    setNotice("");
    setErrorNotice("");
    const { response, data } = await fetchJson(`${resource.data.routes.delete_schedule_window_base}/${windowId}/delete`, {
      method: "POST",
      body: JSON.stringify({}),
    });
    setRemovingWindowId("");
    if (!response.ok || data.ok === false) {
      setErrorNotice(data.error || "Availability could not be removed.");
      return;
    }
    setNotice(data.message || "Recurring weekly availability removed.");
    resource.reload();
  };

  const saveServiceDuration = async (serviceId) => {
    if (!resource.data) {
      return;
    }
    setSavingServiceId(String(serviceId));
    setNotice("");
    setErrorNotice("");
    const { response, data } = await fetchJson(`${resource.data.routes.update_service_duration_base}/${serviceId}/duration`, {
      method: "POST",
      body: JSON.stringify({ duration_minutes: durationDrafts[serviceId] }),
    });
    setSavingServiceId("");
    if (!response.ok || data.ok === false) {
      setErrorNotice(data.error || "Appointment duration could not be updated.");
      return;
    }
    setNotice(data.message || "Appointment duration updated.");
    resource.reload();
  };

  const copyBookingLink = async (bookingPageUrl) => {
    try {
      await copyText(new URL(bookingPageUrl, window.location.origin).toString());
      setCopyState("Copied");
    } catch (_error) {
      setCopyState("Failed");
    }
    window.setTimeout(() => setCopyState(""), 1400);
  };

  if (resource.loading) {
    return <LoadingState title="Loading calendar" detail="Preparing the live diary, inventory, and reminder queue." />;
  }
  if (resource.error) {
    return <ErrorState detail={resource.error} onRetry={resource.reload} />;
  }

  const data = resource.data;

  return (
    <div className="rp-page-grid">
      <section className="rp-card rp-hero-card">
        <div>
          <div className="rp-eyebrow">Clinic calendar</div>
          <h2>Live schedule and booking inventory</h2>
          <p>Clinicians can define recurring weekly hours here, and the patient booking page will only show slots that fit those hours, the visit length, and the remaining diary capacity.</p>
        </div>
        <div className="rp-header-card">
          <span>{data.calendar.month_label}</span>
          <strong>{data.upcoming.length} upcoming visits</strong>
          <small>{data.counts.initial_consult} initial consultations</small>
          <small>{data.counts.report_of_findings} ROF · {data.counts.care_plan} care plan</small>
        </div>
      </section>

      <section className="rp-card">
        <div className="rp-calendar-toolbar">
          <div className="rp-inline-actions">
            <button type="button" className="rp-button rp-button-secondary" onClick={() => setMonth(data.calendar.previous_month)}>
              Previous
            </button>
            <strong>{data.calendar.month_label}</strong>
            <button type="button" className="rp-button rp-button-secondary" onClick={() => setMonth(data.calendar.next_month)}>
              Next
            </button>
          </div>
          <div className="rp-inline-actions">
            <a className="rp-button rp-button-secondary" href={data.routes.legacy_calendar}>Open full editor</a>
            <a className="rp-button rp-button-secondary" href={data.routes.legacy_settings}>Settings</a>
            <a className="rp-button rp-button-secondary" href={data.routes.legacy_reminders}>Reminder center</a>
          </div>
        </div>
        <div className="rp-chip-row">
          <StatusPill tone="life">Initial Consultation</StatusPill>
          <StatusPill tone="sky">Report of Findings</StatusPill>
          <StatusPill tone="warm">Care Plan Visit</StatusPill>
        </div>
      </section>

      {notice ? <div className="rp-alert rp-alert-success">{notice}</div> : null}
      {errorNotice ? <div className="rp-alert rp-alert-error">{errorNotice}</div> : null}

      <section className="rp-metric-grid">
        <article className="rp-card rp-metric-card">
          <span>Reminder queue</span>
          <strong>{data.reminders.length}</strong>
          <small>ROF and care-plan visits due for reminders.</small>
        </article>
        <article className="rp-card rp-metric-card">
          <span>Weekly blocks</span>
          <strong>{flattenScheduleTemplates(data.schedule_templates).length}</strong>
          <small>Recurring clinician and clinic-wide availability templates.</small>
        </article>
        <article className="rp-card rp-metric-card">
          <span>Locations</span>
          <strong>{data.locations.length}</strong>
          <small>Clinic sites used by booking and schedule templates.</small>
        </article>
        <article className="rp-card rp-metric-card">
          <span>Integration events</span>
          <strong>{data.booking_events.length}</strong>
          <small>{data.booking_event_counts.pending} pending · {data.booking_event_counts.delivered} delivered</small>
        </article>
      </section>

      <section className="rp-two-column">
        <article className="rp-card rp-section-stack">
          <div className="rp-section-head">
            <div>
              <span className="rp-eyebrow">Clinician availability</span>
              <h2>Recurring weekly hours</h2>
            </div>
          </div>
          <p>Use one block per weekday and time range. The booking flow reuses these recurring hours for every future week and removes slots that conflict with existing bookings or slot holds.</p>
          <form className="rp-form-stack" onSubmit={submitAvailability}>
            <div className="rp-form-grid">
              <label>
                <span>Chiropractor</span>
                <select value={availabilityForm.clinicianUserId} onChange={(event) => updateAvailabilityField("clinicianUserId", event.target.value)}>
                  {data.clinician_options.map((option) => (
                    <option key={option.value} value={option.value}>{option.label}</option>
                  ))}
                </select>
              </label>
              <label>
                <span>Location</span>
                <select value={availabilityForm.locationId} onChange={(event) => updateAvailabilityField("locationId", event.target.value)}>
                  {data.locations.map((location) => (
                    <option key={location.id} value={location.id}>{location.name}</option>
                  ))}
                </select>
              </label>
              <label>
                <span>Weekday</span>
                <select value={availabilityForm.weekday} onChange={(event) => updateAvailabilityField("weekday", event.target.value)}>
                  {data.weekday_options.map((option) => (
                    <option key={option.value} value={option.value}>{option.label}</option>
                  ))}
                </select>
              </label>
            </div>
            <div className="rp-form-grid">
              <label>
                <span>Availability type</span>
                <select value={availabilityForm.windowType} onChange={(event) => updateAvailabilityField("windowType", event.target.value)}>
                  {data.schedule_window_type_options.map((option) => (
                    <option key={option.value} value={option.value}>{option.label}</option>
                  ))}
                </select>
              </label>
              <label>
                <span>Start time</span>
                <input type="time" value={availabilityForm.startsTime} onChange={(event) => updateAvailabilityField("startsTime", event.target.value)} required />
              </label>
              <label>
                <span>End time</span>
                <input type="time" value={availabilityForm.endsTime} onChange={(event) => updateAvailabilityField("endsTime", event.target.value)} required />
              </label>
            </div>
            <label>
              <span>Label</span>
              <input
                type="text"
                value={availabilityForm.label}
                onChange={(event) => updateAvailabilityField("label", event.target.value)}
                placeholder={availabilityForm.windowType === "downtime" ? "Lunch, admin time, holiday block" : "Morning clinic, afternoon shift"}
              />
            </label>
            <div className="rp-inline-actions">
              <button type="submit" className="rp-button rp-button-primary" disabled={savingAvailability}>
                {savingAvailability ? "Saving..." : "Save recurring availability"}
              </button>
            </div>
          </form>

          <div className="rp-stack-list">
            {availabilityGroups.length ? availabilityGroups.map((group) => (
              <div key={group.key} className="rp-list-card rp-availability-group">
                <div className="rp-list-head">
                  <div>
                    <strong>{group.label}</strong>
                    <small>{group.helper || `${group.totalWindows} recurring block${group.totalWindows === 1 ? "" : "s"}`}</small>
                  </div>
                  <StatusPill tone={group.totalWindows ? "life" : "muted"}>{group.totalWindows} block{group.totalWindows === 1 ? "" : "s"}</StatusPill>
                </div>
                {group.days.length ? (
                  <div className="rp-stack-list">
                    {group.days.map((day) => (
                      <div key={`${group.key}-${day.weekday}`} className="rp-mini-metric rp-availability-day-card">
                        <div className="rp-list-head">
                          <strong>{day.label}</strong>
                          <small>{day.windows.length} saved</small>
                        </div>
                        <div className="rp-stack-list">
                          {day.windows.map((windowItem) => (
                            <div key={windowItem.id} className="rp-window-row">
                              <div>
                                <div className="rp-inline-actions rp-inline-actions-tight">
                                  <StatusPill tone={windowItem.window_tone}>{windowItem.window_type_label}</StatusPill>
                                  <strong>{windowItem.time_label}</strong>
                                </div>
                                <small>{windowItem.label}{windowItem.location_name ? ` · ${windowItem.location_name}` : ""}</small>
                              </div>
                              <button
                                type="button"
                                className="rp-button rp-button-secondary"
                                onClick={() => removeAvailabilityWindow(windowItem.id)}
                                disabled={removingWindowId === String(windowItem.id)}
                              >
                                {removingWindowId === String(windowItem.id) ? "Removing..." : "Remove"}
                              </button>
                            </div>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="rp-empty-inline">No recurring weekly hours saved yet for this clinician.</div>
                )}
              </div>
            )) : <div className="rp-empty-inline">No recurring weekly availability has been configured yet.</div>}
          </div>
        </article>

        <article className="rp-card rp-section-stack">
          <div className="rp-section-head">
            <div>
              <span className="rp-eyebrow">Appointment duration</span>
              <h2>Visit lengths used for booking</h2>
            </div>
          </div>
          <p>Patient-facing slot generation uses the service duration below together with the clinician’s weekly hours, buffers, and existing bookings. Update the duration here instead of changing the booking engine.</p>
          <div className="rp-stack-list">
            {data.service_inventory.length ? data.service_inventory.map((service) => (
              <div key={service.id} className="rp-list-card rp-duration-card">
                <div className="rp-list-head">
                  <div>
                    <strong>{service.label}</strong>
                    <small>{service.appointment_type_label} · {service.routing_mode_label}</small>
                  </div>
                  <StatusPill tone={service.active ? "life" : "muted"}>{service.active ? "Active" : "Inactive"}</StatusPill>
                </div>
                <p>{service.description || "No description provided."}</p>
                <div className="rp-duration-toolbar">
                  <label className="rp-duration-field">
                    <span>Appointment length</span>
                    <select
                      value={durationDrafts[service.id] || String(service.duration_minutes)}
                      onChange={(event) => setDurationDrafts((current) => ({ ...current, [service.id]: event.target.value }))}
                    >
                      {data.appointment_duration_options.map((option) => (
                        <option key={option.value} value={option.value}>{option.label}</option>
                      ))}
                    </select>
                  </label>
                  <button
                    type="button"
                    className="rp-button rp-button-primary"
                    onClick={() => saveServiceDuration(service.id)}
                    disabled={savingServiceId === String(service.id)}
                  >
                    {savingServiceId === String(service.id) ? "Saving..." : "Save length"}
                  </button>
                </div>
                <small>
                  Buffers {service.buffer_before_minutes}m/{service.buffer_after_minutes}m · {service.upcoming_count || 0} upcoming · {service.requires_payment ? formatMoney(service.price_amount, service.currency) : "No payment at booking"}
                </small>
              </div>
            )) : <div className="rp-empty-inline">No booking services configured yet.</div>}
          </div>
        </article>
      </section>

      <section className="rp-two-column">
        <article className="rp-card">
          <div className="rp-section-head">
            <div>
              <span className="rp-eyebrow">Clinic locations</span>
              <h2>Booking sites</h2>
            </div>
            <a className="rp-button rp-button-secondary" href={data.routes.legacy_calendar}>Manage locations</a>
          </div>
          <div className="rp-stack-list">
            {data.locations.length ? data.locations.map((location) => (
              <div key={location.id} className="rp-list-card">
                <div className="rp-list-head">
                  <div>
                    <strong>{location.name}</strong>
                    <small>{location.timezone}</small>
                  </div>
                  <StatusPill tone={location.active ? "life" : "muted"}>
                    {location.active ? "Active" : "Inactive"}
                  </StatusPill>
                </div>
                <p>{location.address || "No address saved."}</p>
                <small>{location.phone || "No phone number saved."}</small>
              </div>
            )) : <div className="rp-empty-inline">No clinic locations exist yet.</div>}
          </div>
        </article>

        <article className="rp-card rp-section-stack">
          <div className="rp-section-head">
            <div>
              <span className="rp-eyebrow">Booking access</span>
              <h2>Share the patient booking page</h2>
            </div>
          </div>
          <div className="rp-form-stack">
            <label>
              <span>Booking link</span>
              <input type="text" readOnly value={new URL(data.routes.booking_page, window.location.origin).toString()} />
            </label>
            <div className="rp-inline-actions">
              <button type="button" className="rp-button rp-button-primary" onClick={() => copyBookingLink(data.routes.booking_page)}>
                {copyState || "Copy booking link"}
              </button>
              <a className="rp-button rp-button-secondary" href={data.routes.booking_page}>
                Open patient booking
              </a>
            </div>
          </div>
          <div className="rp-section-head">
            <div>
              <span className="rp-eyebrow">Integration pipeline</span>
              <h2>Recent booking events</h2>
            </div>
          </div>
          <div className="rp-stack-list">
            {data.booking_events.length ? data.booking_events.map((event) => (
              <div key={event.id} className="rp-list-card">
                <div className="rp-list-head">
                  <div>
                    <strong>{event.event_label}</strong>
                    <small>{event.service_label}</small>
                  </div>
                  <StatusPill tone={event.delivery_status === "delivered" ? "life" : event.delivery_status === "failed" ? "rose" : "warm"}>
                    {event.delivery_status}
                  </StatusPill>
                </div>
                <p>{event.patient_name}{event.starts_label ? ` · ${event.starts_label}` : ""}</p>
                <small>Logged {event.created_label}</small>
              </div>
            )) : <div className="rp-empty-inline">No integration events recorded yet.</div>}
          </div>
        </article>
      </section>

      <section className="rp-two-column">
        <article className="rp-card">
          <div className="rp-section-head">
            <div>
              <span className="rp-eyebrow">Month view</span>
              <h2>{data.calendar.month_label}</h2>
            </div>
          </div>
          <div className="rp-calendar-grid">
            {["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"].map((day) => (
              <div key={day} className="rp-calendar-head">{day}</div>
            ))}
            {data.calendar.weeks.flat().map((day) => (
              <div key={day.iso} className={`rp-calendar-cell ${day.in_month ? "" : "is-outside"} ${day.is_today ? "is-today" : ""}`.trim()}>
                <div className="rp-calendar-date">
                  <span>{day.day}</span>
                  {day.appointments.length ? <small>{day.appointments.length}</small> : null}
                </div>
                <div className="rp-calendar-items">
                  {day.appointments.slice(0, 3).map((appointment) => (
                    <a key={appointment.id} className={`rp-calendar-item tone-${appointment.type_tone}`} href={`/staff/patients/${appointment.patient_user_id}`}>
                      <strong>{appointment.patient_name}</strong>
                      <small>{appointment.time_label} · {appointment.type_short_label}</small>
                    </a>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </article>

        <article className="rp-card">
          <div className="rp-section-head">
            <div>
              <span className="rp-eyebrow">Next scheduled visits</span>
              <h2>Upcoming diary</h2>
            </div>
          </div>
          <div className="rp-stack-list">
            {data.upcoming.length ? data.upcoming.map((appointment) => (
              <div key={appointment.id} className="rp-list-card">
                <div className="rp-list-head">
                  <div>
                    <StatusPill tone={appointment.type_tone}>{appointment.appointment_type_label}</StatusPill>
                    <strong>{appointment.patient_name}</strong>
                  </div>
                  <StatusPill tone={appointment.status === "scheduled" ? "sky" : "muted"}>{appointment.status_label}</StatusPill>
                </div>
                <p>{appointment.starts_label}</p>
                <small>{appointment.location_name || "Clinic location not set"} · {appointment.billing_status_label}</small>
                {appointment.reminder_label ? <small>{appointment.reminder_label}</small> : null}
                {appointment.note ? <small>{appointment.note}</small> : null}
                <div className="rp-inline-actions rp-inline-actions-tight">
                  <a className="rp-button rp-button-secondary" href={`/staff/patients/${appointment.patient_user_id}`}>Open patient chart</a>
                </div>
              </div>
            )) : <div className="rp-empty-inline">No appointments are scheduled yet.</div>}
          </div>
        </article>
      </section>

      <section className="rp-card">
        <div className="rp-section-head">
          <div>
            <span className="rp-eyebrow">Reminder queue</span>
            <h2>Due this week</h2>
          </div>
          <a className="rp-button rp-button-secondary" href={data.routes.legacy_reminders}>Open reminder center</a>
        </div>
        <div className="rp-stack-list">
          {data.reminders.length ? data.reminders.map((appointment) => (
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
                <a className="rp-button rp-button-secondary" href={`/staff/patients/${appointment.patient_user_id}`}>Open patient chart</a>
              </div>
            </div>
          )) : <div className="rp-empty-inline">No Report of Findings or care-plan reminders are due this week.</div>}
        </div>
      </section>
    </div>
  );
}
