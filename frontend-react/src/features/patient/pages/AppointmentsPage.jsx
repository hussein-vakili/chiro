import React, { useEffect, useMemo, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useLocation, useSearchParams } from "react-router-dom";
import { buildUrl, fetchJson } from "../../../shared/api";
import { formatMoney } from "../../../shared/format";
import { useApiMutation, useApiResource } from "../../../shared/hooks";
import { ErrorState, LoadingState, StatusPill } from "../../../shared/ui";

export default function AppointmentsPage({ config }) {
  const location = useLocation();
  const [searchParams, setSearchParams] = useSearchParams();
  const queryClient = useQueryClient();
  const resource = useApiResource(
    () => fetchJson(buildUrl(config.appointmentsEndpoint, Object.fromEntries(searchParams.entries()))),
    [config.appointmentsEndpoint, location.search]
  );
  const [form, setForm] = useState(null);
  const [availability, setAvailability] = useState(null);
  const [selectedSlot, setSelectedSlot] = useState("");
  const [notice, setNotice] = useState("");
  const [errorNotice, setErrorNotice] = useState("");

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
  const journey = resource.data?.journey_summary;
  const selectedService = useMemo(() => {
    if (!page || !form) {
      return null;
    }
    return page.service_options.find((item) => String(item.id) === String(form.serviceId)) || null;
  }, [page, form]);
  const allowAnyClinician = Boolean(selectedService ? selectedService.routing_mode === "team_round_robin" : page?.allow_any_clinician);
  const selectedClinicianLabel = useMemo(() => {
    if (!page || !form) {
      return "your clinic team";
    }
    if (allowAnyClinician && (!form.clinicianUserId || form.clinicianUserId === "any")) {
      return "any available chiropractor";
    }
    return (
      page.clinician_options.find((item) => String(item.value) === String(form.clinicianUserId))?.label ||
      "your selected chiropractor"
    );
  }, [allowAnyClinician, page, form]);
  const shiftWindows = availability?.shift_windows || [];
  const shiftSummary = useMemo(() => {
    if (!shiftWindows.length) {
      return [];
    }
    const grouped = new Map();
    shiftWindows.forEach((windowItem) => {
      const key = windowItem.clinician_name || "Clinic team";
      if (!grouped.has(key)) {
        grouped.set(key, []);
      }
      grouped.get(key).push(windowItem.time_label);
    });
    return Array.from(grouped.entries()).map(([label, windows]) => ({
      label,
      windows: windows.join(" · "),
    }));
  }, [shiftWindows]);

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
            care_plan_visit_id: form.carePlanVisitId,
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

  const bookMutation = useApiMutation(
    (bookingPayload) =>
      fetchJson(config.bookAppointmentEndpoint, {
        method: "POST",
        body: JSON.stringify(bookingPayload),
      }),
    {
      onSuccess: async (_data, variables) => {
        setNotice(
          variables.care_plan_visit_id
            ? "Your next recommended care-plan visit is booked."
            : "Appointment booked from your portal."
        );
        setErrorNotice("");
        setSelectedSlot("");
        if (variables.care_plan_visit_id) {
          setSearchParams({});
        }
        await queryClient.invalidateQueries({ queryKey: resource.queryKey });
      },
      onError: (error) => {
        setErrorNotice(error.message || "Booking failed.");
      },
    }
  );

  const cancelMutation = useApiMutation(
    ({ appointmentId }) =>
      fetchJson(`${config.cancelAppointmentBase}/${appointmentId}/cancel`, {
        method: "POST",
        body: JSON.stringify({}),
      }),
    {
      onSuccess: async (data) => {
        setNotice(data.message || "Appointment cancelled.");
        setErrorNotice("");
        if (data.care_plan_visit_id) {
          setSearchParams({ care_plan_visit_id: String(data.care_plan_visit_id) });
        } else {
          await queryClient.invalidateQueries({ queryKey: resource.queryKey });
        }
      },
      onError: (error) => {
        setErrorNotice(error.message || "Cancellation failed.");
      },
    }
  );

  const busyAction = bookMutation.isPending || cancelMutation.isPending;

  const submitBooking = async (event) => {
    event.preventDefault();
    if (!form || !selectedSlot) {
      setErrorNotice("Choose a live time slot before confirming your booking.");
      return;
    }
    setNotice("");
    setErrorNotice("");
    await bookMutation.mutateAsync({
        service_id: form.serviceId,
        appointment_type: form.appointmentType,
        duration_minutes: form.durationMinutes,
        location_id: form.locationId,
        clinician_user_id: allowAnyClinician && (!form.clinicianUserId || form.clinicianUserId === "any") ? "any" : form.clinicianUserId,
        appointment_date: form.appointmentDate,
        slot_start: selectedSlot,
        patient_details: form.patientDetails,
        care_plan_visit_id: form.carePlanVisitId || undefined,
    });
  };

  const cancelAppointment = async (appointment) => {
    if (!window.confirm(`Cancel ${appointment.appointment_type_label} on ${appointment.starts_label}?`)) {
      return;
    }
    setNotice("");
    setErrorNotice("");
    await cancelMutation.mutateAsync({ appointmentId: appointment.id });
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
          <div className="rp-eyebrow">{journey.stage_label}</div>
          <h2>{journey.title}</h2>
          <p>{journey.detail}</p>
          {journey.helper ? <p className="rp-journey-helper">{journey.helper}</p> : null}
        </div>
        <div className="rp-header-card">
          <span>{journey.stage_label}</span>
          <strong>{page.care_plan.plan ? page.care_plan.adherence.title : page.schedule.next_appointment?.appointment_type_label || "No visits booked"}</strong>
          <small>{page.care_plan.plan ? page.care_plan.adherence.detail : page.schedule.next_appointment?.starts_label || "Choose a live slot below."}</small>
          <small>{page.schedule.next_appointment?.location_name || "Live portal calendar"}</small>
        </div>
      </section>

      <section className="rp-two-column">
        <article className="rp-card">
          <div className="rp-section-head">
            <div>
              <span className="rp-eyebrow">Booking focus</span>
              <h2>What matters in this stage</h2>
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
              <span className="rp-eyebrow">Stage checklist</span>
              <h2>Booking-related next steps</h2>
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
              <span className="rp-eyebrow">
                {page.selected_care_plan_visit ? "Recommended visit" : journey.state === "booked_first_visit" ? "Pre-visit scheduling" : "Self-service booking"}
              </span>
              <h2>{page.selected_care_plan_visit ? page.selected_care_plan_visit.label : journey.primary_action_label}</h2>
            </div>
            {page.selected_care_plan_visit ? <StatusPill tone={page.selected_care_plan_visit.visit_kind_tone}>{page.selected_care_plan_visit.visit_kind_label}</StatusPill> : null}
          </div>

          {page.selected_care_plan_visit ? (
            <div className="rp-selected-visit">
              <strong>{page.selected_care_plan_visit.suggested_long_label}</strong>
              <small>{page.selected_care_plan_visit.duration_minutes} min · linked to your active care plan</small>
            </div>
          ) : (
            <>
              <p>{journey.detail}</p>
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
            </>
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
              <div className="rp-slot-guidance">
                <div className="rp-mini-metric-grid">
                  <article className="rp-mini-metric">
                    <span>Appointment length</span>
                    <strong>{availability?.duration_minutes || form.durationMinutes} min</strong>
                    <small>Used to generate valid bookable slots.</small>
                  </article>
                  <article className="rp-mini-metric">
                    <span>Remaining live slots</span>
                    <strong>{availability?.available_slots?.length || 0}</strong>
                    <small>Only slots inside recurring weekly hours are shown.</small>
                  </article>
                  <article className="rp-mini-metric">
                    <span>Diary already blocking</span>
                    <strong>{availability?.booked_windows?.length || 0}</strong>
                    <small>Existing bookings and held slots already removed.</small>
                  </article>
                </div>
                <div className="rp-inline-note">
                  {allowAnyClinician && (!form.clinicianUserId || form.clinicianUserId === "any")
                    ? "Showing the remaining slots that fit the selected visit length across any available chiropractor's recurring weekly hours."
                    : `Showing only the remaining slots that fit ${selectedClinicianLabel}'s recurring weekly hours and the selected appointment length.`}
                </div>
                {shiftSummary.length ? (
                  <div className="rp-stack-list">
                    {shiftSummary.map((item) => (
                      <div key={`${item.label}-${item.windows}`} className="rp-list-card rp-availability-inline-card">
                        <div className="rp-list-head">
                          <strong>{item.label}</strong>
                          <small>{availability?.date_label || "Selected date"}</small>
                        </div>
                        <small>{item.windows}</small>
                      </div>
                    ))}
                  </div>
                ) : null}
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
