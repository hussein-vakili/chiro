import React, { useCallback, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { fetchJson } from "../../../shared/api";
import { copyText } from "../../../shared/browser";
import { useApiResource } from "../../../shared/hooks";
import { ErrorState, LoadingState, StatusPill } from "../../../shared/ui";

export default function StaffSettingsPage({ config }) {
  const [searchParams, setSearchParams] = useSearchParams();
  const [filterQuery, setFilterQuery] = useState("");
  const [copyState, setCopyState] = useState("");
  const resource = useApiResource(() => fetchJson(config.staffSettingsEndpoint), [config.staffSettingsEndpoint]);

  const sectionItems = useMemo(() => ([
    { key: "profile", title: "Profile & Practice", detail: "Professional identity and clinic details", search: "profile practice clinic identity branding" },
    { key: "clinic", title: "Clinic Configuration", detail: "Hours, rooms, locations, and availability", search: "clinic configuration hours rooms locations availability" },
    { key: "scheduling", title: "Scheduling", detail: "Calendar defaults and booking rules", search: "scheduling calendar booking slots cancellation inventory" },
    { key: "notifications", title: "Notifications", detail: "Reminder and messaging preferences", search: "notifications reminders sms email recall" },
    { key: "clinical", title: "Clinical Defaults", detail: "Outcome measures and intake defaults", search: "clinical outcome measures intake consent" },
    { key: "billing", title: "Billing & Payments", detail: "Fees and payment preferences", search: "billing payments fees invoice receipts" },
    { key: "security", title: "Security & Access", detail: "Sessions, chiropractors, and account access", search: "security access chiropractors sessions" },
    { key: "data", title: "Data & Compliance", detail: "Retention, backups, and the live database", search: "data compliance backups retention database" },
    { key: "appearance", title: "Appearance", detail: "Theme, font, and portal branding", search: "appearance theme colour font branding" },
    { key: "integrations", title: "Integrations", detail: "Providers, booking link, and event pipeline", search: "integrations providers booking link pipeline" },
    { key: "subscription", title: "Subscription", detail: "Usage snapshot", search: "subscription usage plan" },
  ]), []);

  const visibleSections = useMemo(() => {
    const query = filterQuery.trim().toLowerCase();
    if (!query) {
      return sectionItems;
    }
    return sectionItems.filter((item) => `${item.title} ${item.detail} ${item.search}`.toLowerCase().includes(query));
  }, [filterQuery, sectionItems]);

  const requestedSection = searchParams.get("section") || "profile";
  const activeSection = visibleSections.some((item) => item.key === requestedSection)
    ? requestedSection
    : (visibleSections[0]?.key || "profile");

  useEffect(() => {
    if (activeSection !== requestedSection) {
      const next = new URLSearchParams(searchParams);
      next.set("section", activeSection);
      setSearchParams(next, { replace: true });
    }
  }, [activeSection, requestedSection, searchParams, setSearchParams]);

  const openSection = useCallback((sectionKey) => {
    const next = new URLSearchParams(searchParams);
    next.set("section", sectionKey);
    setSearchParams(next);
  }, [searchParams, setSearchParams]);

  const copyBookingLink = async (bookingLink) => {
    try {
      await copyText(bookingLink);
      setCopyState("Copied");
    } catch (_error) {
      setCopyState("Failed");
    }
    window.setTimeout(() => setCopyState(""), 1400);
  };

  if (resource.loading) {
    return <LoadingState title="Loading settings" detail="Preparing the clinic configuration workspace." />;
  }
  if (resource.error) {
    return <ErrorState detail={resource.error} onRetry={resource.reload} />;
  }

  const settings = resource.data.settings;
  const appSettings = settings.app_settings;
  const clinicDays = settings.settings_lists.clinic_open_days || [];
  const outcomeMeasures = settings.settings_lists.clinical_outcome_measures || [];
  const paymentMethods = settings.settings_lists.billing_payment_methods || [];
  const backupDownloadUrl = settings.routes.download_backup;
  const bookingLinkAbsolute = new URL(settings.booking_link, window.location.origin).toString();

  const renderHiddenFields = (sectionKey) => (
    <>
      <input type="hidden" name="return_to" value="react_settings" />
      <input type="hidden" name="section" value={sectionKey} />
    </>
  );

  return (
    <div className="rp-page-grid">
      <section className="rp-card rp-hero-card">
        <div>
          <div className="rp-eyebrow">Settings workspace</div>
          <h2>Configure the clinic in the React shell</h2>
          <p>These forms still save through the live backend validators, but the settings workspace itself now runs inside the React staff portal.</p>
        </div>
        <div className="rp-header-card">
          <span>Live system</span>
          <strong>{appSettings.practice_clinic_name || "Life Chiropractic"}</strong>
          <small>{settings.active_chiropractor_count}/{settings.max_active_chiropractors} chiropractors active</small>
          <small>{appSettings.calendar_slot_increment_minutes} minute slot increments</small>
          <small>{settings.database_summary.size_label} SQLite database</small>
        </div>
      </section>

      <section className="rp-settings-shell">
        <aside className="rp-card rp-settings-nav">
          <div className="rp-section-head">
            <div>
              <span className="rp-eyebrow">Settings areas</span>
              <h2>Navigator</h2>
            </div>
          </div>
          <label className="rp-form-stack">
            <span>Search sections</span>
            <input
              type="search"
              value={filterQuery}
              onChange={(event) => setFilterQuery(event.target.value)}
              placeholder="Search settings sections..."
            />
          </label>
          <div className="rp-settings-link-list">
            {visibleSections.length ? visibleSections.map((item) => (
              <button
                key={item.key}
                type="button"
                className={`rp-settings-link ${activeSection === item.key ? "active" : ""}`.trim()}
                onClick={() => openSection(item.key)}
              >
                <strong>{item.title}</strong>
                <small>{item.detail}</small>
              </button>
            )) : <div className="rp-empty-inline">No sections match that search.</div>}
          </div>
          <a className="rp-button rp-button-secondary" href={settings.routes.legacy_settings}>Open legacy settings</a>
        </aside>

        <div className="rp-settings-content">
          {activeSection === "profile" ? (
            <section className="rp-card">
              <div className="rp-section-head">
                <div>
                  <span className="rp-eyebrow">Profile & Practice</span>
                  <h2>Professional identity</h2>
                </div>
              </div>
              <p>These values drive the clinic name and patient-facing branding across the portal.</p>
              <form className="rp-form-stack" method="post" action={settings.routes.profile_action}>
                {renderHiddenFields("profile")}
                <div className="rp-form-grid">
                  <label><span>Practitioner name</span><input type="text" name="practice_practitioner_name" defaultValue={appSettings.practice_practitioner_name} placeholder="Dr. Hussein Vakili" /></label>
                  <label><span>Registration number</span><input type="text" name="practice_registration_number" defaultValue={appSettings.practice_registration_number} placeholder="GCC / licence reference" /></label>
                  <label><span>Qualifications</span><input type="text" name="practice_qualifications" defaultValue={appSettings.practice_qualifications} placeholder="DC, MSc Chiropractic" /></label>
                  <label><span>Clinic name</span><input type="text" name="practice_clinic_name" defaultValue={appSettings.practice_clinic_name} required /></label>
                  <label><span>Clinic email</span><input type="email" name="practice_email" defaultValue={appSettings.practice_email} placeholder="clinic@example.com" /></label>
                  <label><span>Clinic phone</span><input type="text" name="practice_phone" defaultValue={appSettings.practice_phone} placeholder="+44 7700 000000" /></label>
                </div>
                <label><span>Clinic address</span><textarea name="practice_address" rows="3" defaultValue={appSettings.practice_address} /></label>
                <label><span>Practice bio</span><textarea name="practice_bio" rows="4" defaultValue={appSettings.practice_bio} /></label>
                <button type="submit" className="rp-button rp-button-primary">Save profile settings</button>
              </form>
            </section>
          ) : null}

          {activeSection === "clinic" ? (
            <section className="rp-page-grid">
              <section className="rp-card">
                <div className="rp-section-head">
                  <div>
                    <span className="rp-eyebrow">Clinic Configuration</span>
                    <h2>Hours and rooms</h2>
                  </div>
                </div>
                <form className="rp-form-stack" method="post" action={settings.routes.clinic_action}>
                  {renderHiddenFields("clinic")}
                  <div>
                    <span>Operating days</span>
                    <div className="rp-tag-cloud">
                      {["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"].map((day) => (
                        <label key={day} className="rp-checkbox-chip">
                          <input type="checkbox" name="clinic_open_days" value={day} defaultChecked={clinicDays.includes(day)} />
                          <span>{day}</span>
                        </label>
                      ))}
                    </div>
                  </div>
                  <div className="rp-form-grid">
                    <label><span>Opening time</span><input type="time" name="clinic_open_time" defaultValue={appSettings.clinic_open_time} /></label>
                    <label><span>Closing time</span><input type="time" name="clinic_close_time" defaultValue={appSettings.clinic_close_time} /></label>
                    <label><span>Lunch break start</span><input type="time" name="clinic_lunch_start" defaultValue={appSettings.clinic_lunch_start} /></label>
                    <label><span>Lunch break end</span><input type="time" name="clinic_lunch_end" defaultValue={appSettings.clinic_lunch_end} /></label>
                    <label><span>Treatment rooms</span><input type="number" min="1" max="50" name="clinic_rooms" defaultValue={appSettings.clinic_rooms} /></label>
                    <label className="rp-inline-toggle"><span>Multi-practitioner mode</span><input type="checkbox" name="clinic_multi_practitioner_mode" defaultChecked={appSettings.clinic_multi_practitioner_mode === "1"} /></label>
                  </div>
                  <button type="submit" className="rp-button rp-button-primary">Save clinic configuration</button>
                </form>
              </section>

              <section className="rp-two-column">
                <article className="rp-card">
                  <div className="rp-section-head">
                    <div>
                      <span className="rp-eyebrow">Locations</span>
                      <h2>Clinic sites</h2>
                    </div>
                  </div>
                  <div className="rp-stack-list">
                    {settings.locations.length ? settings.locations.map((location) => (
                      <div key={location.id} className="rp-list-card">
                        <div className="rp-list-head">
                          <div>
                            <strong>{location.name}</strong>
                            <small>{location.timezone}</small>
                          </div>
                          <StatusPill tone={location.active ? "life" : "muted"}>{location.active ? "Active" : "Inactive"}</StatusPill>
                        </div>
                        <p>{location.address || "No address saved."}</p>
                        <small>{location.phone || "No phone number saved."}</small>
                      </div>
                    )) : <div className="rp-empty-inline">No locations configured yet.</div>}
                  </div>
                  <form className="rp-form-stack" method="post" action={settings.routes.create_location}>
                    {renderHiddenFields("clinic")}
                    <div className="rp-form-grid">
                      <label><span>Name</span><input type="text" name="name" placeholder="Main Clinic" required /></label>
                      <label><span>Slug</span><input type="text" name="slug" placeholder="main-clinic" required /></label>
                      <label><span>Phone</span><input type="text" name="phone" placeholder="555-0101" /></label>
                      <label><span>Timezone</span><input type="text" name="timezone" defaultValue="Europe/London" /></label>
                    </div>
                    <label><span>Address</span><textarea name="address" rows="3" placeholder="123 Wellness Way" /></label>
                    <button type="submit" className="rp-button rp-button-primary">Add location</button>
                  </form>
                </article>

                <article className="rp-card">
                  <div className="rp-section-head">
                    <div>
                      <span className="rp-eyebrow">Availability templates</span>
                      <h2>Weekly schedule</h2>
                    </div>
                    <div className="rp-inline-actions">
                      <a className="rp-button rp-button-primary" href={`${config.routerBasename}/calendar`}>Open React calendar editor</a>
                      <a className="rp-button rp-button-secondary" href={settings.routes.legacy_calendar}>Open full editor</a>
                    </div>
                  </div>
                  <div className="rp-stack-list">
                    {settings.schedule_templates.map((day) => (
                      <div key={day.weekday} className="rp-list-card">
                        <div className="rp-list-head">
                          <strong>{day.label}</strong>
                          <small>{day.windows.length} blocks</small>
                        </div>
                        {day.windows.length ? (
                          <div className="rp-stack-list">
                            {day.windows.map((windowItem) => (
                              <div key={windowItem.id} className="rp-mini-metric">
                                <div className="rp-inline-actions">
                                  <StatusPill tone={windowItem.window_tone}>{windowItem.window_type_label}</StatusPill>
                                  <small>{windowItem.time_label}</small>
                                </div>
                                <small>{windowItem.label}{windowItem.location_name ? ` · ${windowItem.location_name}` : ""}{windowItem.clinician_name ? ` · ${windowItem.clinician_name}` : " · Clinic-wide"}</small>
                              </div>
                            ))}
                          </div>
                        ) : <div className="rp-empty-inline">No schedule template configured.</div>}
                      </div>
                    ))}
                  </div>
                </article>
              </section>
            </section>
          ) : null}

          {activeSection === "scheduling" ? (
            <section className="rp-page-grid">
              <section className="rp-card">
                <div className="rp-section-head">
                  <div>
                    <span className="rp-eyebrow">Scheduling</span>
                    <h2>Calendar defaults and booking rules</h2>
                  </div>
                </div>
                <form className="rp-form-stack" method="post" action={settings.routes.update_general}>
                  {renderHiddenFields("scheduling")}
                  <div className="rp-form-grid">
                    <label>
                      <span>Time format</span>
                      <select name="calendar_time_format" defaultValue={appSettings.calendar_time_format}>
                        {settings.time_format_options.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
                      </select>
                    </label>
                    <label>
                      <span>Slot increment</span>
                      <select name="calendar_slot_increment_minutes" defaultValue={appSettings.calendar_slot_increment_minutes}>
                        {settings.slot_increment_options.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
                      </select>
                    </label>
                    <label><span>Max advance booking window (days)</span><input type="number" min="1" max="120" name="booking_search_window_days" defaultValue={settings.booking_search_window_days} required /></label>
                    <label><span>Cancellation window (hours)</span><input type="number" min="0" max="336" name="booking_cancellation_hours" defaultValue={appSettings.booking_cancellation_hours} required /></label>
                    <label className="rp-inline-toggle"><span>Online booking</span><input type="checkbox" name="booking_enable_online" defaultChecked={appSettings.booking_enable_online === "1"} /></label>
                    <label className="rp-inline-toggle"><span>Allow same-day bookings</span><input type="checkbox" name="booking_allow_same_day" defaultChecked={appSettings.booking_allow_same_day === "1"} /></label>
                    <label><span>No-show fee</span><input type="text" name="booking_no_show_fee" defaultValue={appSettings.booking_no_show_fee} placeholder="Optional" /></label>
                    <label><span>Max active chiropractors</span><input type="number" min="1" max="100" name="max_active_chiropractors" defaultValue={settings.max_active_chiropractors} required /></label>
                  </div>
                  <button type="submit" className="rp-button rp-button-primary">Save scheduling settings</button>
                </form>
              </section>

              <section className="rp-card">
                <div className="rp-section-head">
                  <div>
                    <span className="rp-eyebrow">Booking inventory</span>
                    <h2>Services overview</h2>
                  </div>
                  <a className="rp-button rp-button-secondary" href={settings.routes.legacy_calendar}>Manage services</a>
                </div>
                <div className="rp-stack-list">
                  {settings.service_inventory.length ? settings.service_inventory.map((service) => (
                    <div key={service.id} className="rp-list-card">
                      <div className="rp-list-head">
                        <div>
                          <strong>{service.label}</strong>
                          <small>{service.appointment_type_label} · {service.duration_minutes} min</small>
                        </div>
                        <StatusPill tone={service.active ? "life" : "muted"}>{service.active ? "Active" : "Inactive"}</StatusPill>
                      </div>
                      <p>{service.description || "No description provided."}</p>
                      <small>{service.routing_mode_label} · Buffers {service.buffer_before_minutes}m/{service.buffer_after_minutes}m · {service.upcoming_count || 0} upcoming</small>
                    </div>
                  )) : <div className="rp-empty-inline">No booking services configured yet.</div>}
                </div>
              </section>
            </section>
          ) : null}

          {activeSection === "notifications" ? (
            <section className="rp-card">
              <div className="rp-section-head">
                <div>
                  <span className="rp-eyebrow">Notifications</span>
                  <h2>Reminder and messaging preferences</h2>
                </div>
              </div>
              <form className="rp-form-stack" method="post" action={settings.routes.notifications_action}>
                {renderHiddenFields("notifications")}
                <div className="rp-form-grid">
                  <label className="rp-inline-toggle"><span>Appointment confirmation email</span><input type="checkbox" name="notifications_confirmation_email" defaultChecked={appSettings.notifications_confirmation_email === "1"} /></label>
                  <label className="rp-inline-toggle"><span>Appointment confirmation SMS</span><input type="checkbox" name="notifications_confirmation_sms" defaultChecked={appSettings.notifications_confirmation_sms === "1"} /></label>
                  <label className="rp-inline-toggle"><span>24-hour reminder</span><input type="checkbox" name="notifications_reminder_24h" defaultChecked={appSettings.notifications_reminder_24h === "1"} /></label>
                  <label className="rp-inline-toggle"><span>1-hour reminder</span><input type="checkbox" name="notifications_reminder_1h" defaultChecked={appSettings.notifications_reminder_1h === "1"} /></label>
                  <label className="rp-inline-toggle"><span>Post-visit summary email</span><input type="checkbox" name="notifications_post_visit_email" defaultChecked={appSettings.notifications_post_visit_email === "1"} /></label>
                  <label className="rp-inline-toggle"><span>Recall reminders for lapsed patients</span><input type="checkbox" name="notifications_recall_enabled" defaultChecked={appSettings.notifications_recall_enabled === "1"} /></label>
                  <label><span>Recall after inactivity (days)</span><input type="number" min="7" max="365" name="notifications_recall_days" defaultValue={appSettings.notifications_recall_days} /></label>
                </div>
                <button type="submit" className="rp-button rp-button-primary">Save notification settings</button>
              </form>
            </section>
          ) : null}

          {activeSection === "clinical" ? (
            <section className="rp-card">
              <div className="rp-section-head">
                <div>
                  <span className="rp-eyebrow">Clinical Defaults</span>
                  <h2>Outcome measures and intake defaults</h2>
                </div>
              </div>
              <form className="rp-form-stack" method="post" action={settings.routes.clinical_action}>
                {renderHiddenFields("clinical")}
                <div>
                  <span>Default outcome measures</span>
                  <div className="rp-tag-cloud">
                    {["NDI", "ODI", "QuickDASH", "HIT-6", "SF-36", "PSFS", "VAS Pain"].map((measure) => (
                      <label key={measure} className="rp-checkbox-chip">
                        <input type="checkbox" name="clinical_outcome_measures" value={measure} defaultChecked={outcomeMeasures.includes(measure)} />
                        <span>{measure}</span>
                      </label>
                    ))}
                  </div>
                </div>
                <div className="rp-form-grid">
                  <label><span>Re-examination interval (visits)</span><input type="number" min="1" max="52" name="clinical_reexam_interval" defaultValue={appSettings.clinical_reexam_interval} /></label>
                  <label className="rp-inline-toggle"><span>Use MCID thresholds</span><input type="checkbox" name="clinical_use_mcid" defaultChecked={appSettings.clinical_use_mcid === "1"} /></label>
                  <label className="rp-inline-toggle"><span>Auto-assign intake to new patients</span><input type="checkbox" name="clinical_auto_assign_intake" defaultChecked={appSettings.clinical_auto_assign_intake === "1"} /></label>
                  <label className="rp-inline-toggle"><span>Include consent form in intake</span><input type="checkbox" name="clinical_include_consent" defaultChecked={appSettings.clinical_include_consent === "1"} /></label>
                </div>
                <button type="submit" className="rp-button rp-button-primary">Save clinical defaults</button>
              </form>
            </section>
          ) : null}

          {activeSection === "billing" ? (
            <section className="rp-card">
              <div className="rp-section-head">
                <div>
                  <span className="rp-eyebrow">Billing & Payments</span>
                  <h2>Fees and payment preferences</h2>
                </div>
              </div>
              <form className="rp-form-stack" method="post" action={settings.routes.billing_action}>
                {renderHiddenFields("billing")}
                <div className="rp-form-grid">
                  <label><span>Initial consultation fee</span><input type="text" name="billing_initial_fee" defaultValue={appSettings.billing_initial_fee} placeholder="65" /></label>
                  <label><span>Follow-up fee</span><input type="text" name="billing_followup_fee" defaultValue={appSettings.billing_followup_fee} placeholder="42" /></label>
                </div>
                <div>
                  <span>Accepted payment methods</span>
                  <div className="rp-tag-cloud">
                    {["Card", "Cash", "Bank Transfer", "Apple Pay", "Google Pay"].map((method) => (
                      <label key={method} className="rp-checkbox-chip">
                        <input type="checkbox" name="billing_payment_methods" value={method} defaultChecked={paymentMethods.includes(method)} />
                        <span>{method}</span>
                      </label>
                    ))}
                  </div>
                </div>
                <div className="rp-form-grid">
                  <label className="rp-inline-toggle"><span>Auto-generate invoice after visit</span><input type="checkbox" name="billing_auto_invoice" defaultChecked={appSettings.billing_auto_invoice === "1"} /></label>
                  <label className="rp-inline-toggle"><span>Email receipts automatically</span><input type="checkbox" name="billing_email_receipts" defaultChecked={appSettings.billing_email_receipts === "1"} /></label>
                </div>
                <button type="submit" className="rp-button rp-button-primary">Save billing settings</button>
              </form>
            </section>
          ) : null}

          {activeSection === "security" ? (
            <section className="rp-page-grid">
              <section className="rp-card">
                <div className="rp-section-head">
                  <div>
                    <span className="rp-eyebrow">Security & Access</span>
                    <h2>Session and access controls</h2>
                  </div>
                </div>
                <form className="rp-form-stack" method="post" action={settings.routes.security_action}>
                  {renderHiddenFields("security")}
                  <div className="rp-form-grid">
                    <label><span>Max active chiropractors</span><input type="number" min="1" max="100" name="max_active_chiropractors" defaultValue={settings.max_active_chiropractors} /></label>
                    <label>
                      <span>Session timeout</span>
                      <select name="security_session_timeout" defaultValue={appSettings.security_session_timeout}>
                        {[15, 30, 60, 120].map((option) => <option key={option} value={option}>{option} minutes</option>)}
                      </select>
                    </label>
                    <label className="rp-inline-toggle"><span>Two-factor authentication required</span><input type="checkbox" name="security_two_factor" defaultChecked={appSettings.security_two_factor === "1"} /></label>
                  </div>
                  <button type="submit" className="rp-button rp-button-primary">Save security settings</button>
                </form>
              </section>

              <section className="rp-two-column">
                <article className="rp-card">
                  <div className="rp-section-head">
                    <div>
                      <span className="rp-eyebrow">Chiropractor roster</span>
                      <h2>Active seats</h2>
                    </div>
                  </div>
                  <p>Capacity remaining: {settings.remaining_chiropractor_capacity} active seat{settings.remaining_chiropractor_capacity === 1 ? "" : "s"}.</p>
                  <div className="rp-stack-list">
                    {settings.chiropractors.length ? settings.chiropractors.map((chiropractor) => (
                      <div key={chiropractor.id} className="rp-list-card">
                        <div className="rp-list-head">
                          <div>
                            <strong>{chiropractor.full_name}</strong>
                            <small>{chiropractor.email}</small>
                          </div>
                          <StatusPill tone={chiropractor.is_active ? "life" : "rose"}>{chiropractor.status_label}</StatusPill>
                        </div>
                        <p>{chiropractor.upcoming_appointment_count} upcoming appointments · {chiropractor.availability_template_count} availability templates</p>
                        <small>Created {chiropractor.created_label}</small>
                        <form className="rp-inline-actions rp-inline-actions-tight" method="post" action={`${settings.routes.update_chiropractor_status_base}/${chiropractor.id}/status`}>
                          {renderHiddenFields("security")}
                          <input type="hidden" name="is_active" value={chiropractor.is_active ? "0" : "1"} />
                          <button type="submit" className="rp-button rp-button-secondary">
                            {chiropractor.is_active ? "Deactivate" : "Activate"}
                          </button>
                        </form>
                      </div>
                    )) : <div className="rp-empty-inline">No chiropractor accounts exist yet.</div>}
                  </div>
                </article>

                <article className="rp-card">
                  <div className="rp-section-head">
                    <div>
                      <span className="rp-eyebrow">Add chiropractor</span>
                      <h2>Create booking access</h2>
                    </div>
                  </div>
                  <form className="rp-form-stack" method="post" action={settings.routes.create_chiropractor}>
                    {renderHiddenFields("security")}
                    <div className="rp-form-grid">
                      <label><span>First name</span><input type="text" name="first_name" required /></label>
                      <label><span>Last name</span><input type="text" name="last_name" required /></label>
                      <label><span>Email</span><input type="email" name="email" required /></label>
                      <label><span>Temporary password</span><input type="password" name="password" minLength="8" required /></label>
                    </div>
                    <button type="submit" className="rp-button rp-button-primary">Create chiropractor</button>
                  </form>
                </article>
              </section>
            </section>
          ) : null}

          {activeSection === "data" ? (
            <section className="rp-page-grid">
              <section className="rp-card">
                <div className="rp-section-head">
                  <div>
                    <span className="rp-eyebrow">Data & Compliance</span>
                    <h2>Retention and backup policy</h2>
                  </div>
                </div>
                <form className="rp-form-stack" method="post" action={settings.routes.data_action}>
                  {renderHiddenFields("data")}
                  <div className="rp-form-grid">
                    <label><span>ICO registration reference</span><input type="text" name="data_ico_reference" defaultValue={appSettings.data_ico_reference} placeholder="ZA000000" /></label>
                    <label>
                      <span>Retention period</span>
                      <select name="data_retention_period" defaultValue={appSettings.data_retention_period}>
                        <option value="3y">3 years</option>
                        <option value="7y">7 years</option>
                        <option value="10y">10 years</option>
                      </select>
                    </label>
                    <label className="rp-inline-toggle"><span>Auto-anonymise after retention window</span><input type="checkbox" name="data_auto_anonymize" defaultChecked={appSettings.data_auto_anonymize === "1"} /></label>
                    <label className="rp-inline-toggle"><span>Automatic daily backups</span><input type="checkbox" name="data_daily_backups" defaultChecked={appSettings.data_daily_backups === "1"} /></label>
                  </div>
                  <button type="submit" className="rp-button rp-button-primary">Save data settings</button>
                </form>
              </section>

              <section className="rp-card">
                <div className="rp-section-head">
                  <div>
                    <span className="rp-eyebrow">Database summary</span>
                    <h2>{settings.database_summary.engine}</h2>
                  </div>
                  <a className="rp-button rp-button-primary" href={backupDownloadUrl}>Download SQLite backup</a>
                </div>
                <div className="rp-metric-grid">
                  <article className="rp-mini-metric"><span>Tables</span><strong>{settings.database_summary.table_count}</strong><small>{settings.database_summary.size_label}</small></article>
                  <article className="rp-mini-metric"><span>Users</span><strong>{settings.database_summary.counts.users}</strong><small>{settings.database_summary.counts.appointments} appointments</small></article>
                  <article className="rp-mini-metric"><span>Messages</span><strong>{settings.database_summary.counts.messages}</strong><small>{settings.database_summary.counts.journal_entries} journal entries</small></article>
                </div>
                <label className="rp-form-stack">
                  <span>Database file</span>
                  <input type="text" readOnly value={settings.database_summary.path} />
                </label>
                <label className="rp-form-stack">
                  <span>Tables</span>
                  <textarea rows="4" readOnly value={settings.database_summary.tables.join(", ")} />
                </label>
              </section>
            </section>
          ) : null}

          {activeSection === "appearance" ? (
            <section className="rp-card">
              <div className="rp-section-head">
                <div>
                  <span className="rp-eyebrow">Appearance</span>
                  <h2>Branding and theme</h2>
                </div>
              </div>
              <form className="rp-form-stack" method="post" action={settings.routes.appearance_action}>
                {renderHiddenFields("appearance")}
                <div className="rp-form-grid">
                  <label>
                    <span>Theme</span>
                    <select name="appearance_theme" defaultValue={appSettings.appearance_theme}>
                      <option value="light">Light</option>
                      <option value="dark">Dark</option>
                      <option value="auto">System</option>
                    </select>
                  </label>
                  <label><span>Brand colour</span><input type="text" name="appearance_brand_color" defaultValue={appSettings.appearance_brand_color} placeholder="#3b7a57" /></label>
                  <label>
                    <span>Font style</span>
                    <select name="appearance_font_style" defaultValue={appSettings.appearance_font_style}>
                      <option value="modern">Modern</option>
                      <option value="classic">Classic</option>
                      <option value="clean">Clean</option>
                    </select>
                  </label>
                  <label className="rp-inline-toggle"><span>Show clinic branding in portal</span><input type="checkbox" name="appearance_show_portal_branding" defaultChecked={appSettings.appearance_show_portal_branding === "1"} /></label>
                </div>
                <button type="submit" className="rp-button rp-button-primary">Save appearance settings</button>
              </form>
            </section>
          ) : null}

          {activeSection === "integrations" ? (
            <section className="rp-page-grid">
              <section className="rp-card">
                <div className="rp-section-head">
                  <div>
                    <span className="rp-eyebrow">Integrations</span>
                    <h2>Providers and booking link</h2>
                  </div>
                </div>
                <form className="rp-form-stack" method="post" action={settings.routes.integrations_action}>
                  {renderHiddenFields("integrations")}
                  <div className="rp-form-grid">
                    <label>
                      <span>Payment provider</span>
                      <select name="integration_payment_provider" defaultValue={appSettings.integration_payment_provider}>
                        <option value="">Not connected</option>
                        <option value="Stripe">Stripe</option>
                        <option value="Square">Square</option>
                        <option value="SumUp">SumUp</option>
                      </select>
                    </label>
                    <label>
                      <span>Calendar sync</span>
                      <select name="integration_calendar_sync" defaultValue={appSettings.integration_calendar_sync}>
                        <option value="">Not connected</option>
                        <option value="Google Calendar">Google Calendar</option>
                        <option value="Outlook">Outlook</option>
                      </select>
                    </label>
                    <label>
                      <span>Email provider</span>
                      <select name="integration_email_provider" defaultValue={appSettings.integration_email_provider}>
                        <option value="">Default outbox</option>
                        <option value="Mailgun">Mailgun</option>
                        <option value="SendGrid">SendGrid</option>
                        <option value="Amazon SES">Amazon SES</option>
                      </select>
                    </label>
                    <label>
                      <span>SMS provider</span>
                      <select name="integration_sms_provider" defaultValue={appSettings.integration_sms_provider}>
                        <option value="">Default outbox</option>
                        <option value="Twilio">Twilio</option>
                        <option value="Vonage">Vonage</option>
                      </select>
                    </label>
                  </div>
                  <button type="submit" className="rp-button rp-button-primary">Save integration settings</button>
                </form>
              </section>

              <section className="rp-two-column">
                <article className="rp-card">
                  <div className="rp-section-head">
                    <div>
                      <span className="rp-eyebrow">Booking link</span>
                      <h2>Patient booking page</h2>
                    </div>
                  </div>
                  <label className="rp-form-stack">
                    <span>Booking URL</span>
                    <input type="text" readOnly value={bookingLinkAbsolute} />
                  </label>
                  <div className="rp-inline-actions">
                    <button type="button" className="rp-button rp-button-primary" onClick={() => copyBookingLink(bookingLinkAbsolute)}>
                      {copyState || "Copy booking link"}
                    </button>
                    <a className="rp-button rp-button-secondary" href={settings.booking_link}>Open booking page</a>
                  </div>
                </article>

                <article className="rp-card">
                  <div className="rp-section-head">
                    <div>
                      <span className="rp-eyebrow">Event pipeline</span>
                      <h2>Recent booking events</h2>
                    </div>
                  </div>
                  <div className="rp-inline-actions">
                    <StatusPill tone="warm">{settings.booking_event_counts.pending} pending</StatusPill>
                    <StatusPill tone="life">{settings.booking_event_counts.delivered} delivered</StatusPill>
                    <StatusPill tone="rose">{settings.booking_event_counts.failed} failed</StatusPill>
                  </div>
                  <div className="rp-stack-list">
                    {settings.booking_events.length ? settings.booking_events.map((event) => (
                      <div key={event.id} className="rp-list-card">
                        <div className="rp-list-head">
                          <div>
                            <strong>{event.event_label}</strong>
                            <small>{event.patient_name}{event.starts_label ? ` · ${event.starts_label}` : ""}</small>
                          </div>
                          <StatusPill tone={event.delivery_status === "delivered" ? "life" : event.delivery_status === "failed" ? "rose" : "warm"}>{event.delivery_status}</StatusPill>
                        </div>
                        <p>{event.service_label}</p>
                      </div>
                    )) : <div className="rp-empty-inline">No booking events have been recorded yet.</div>}
                  </div>
                </article>
              </section>
            </section>
          ) : null}

          {activeSection === "subscription" ? (
            <section className="rp-card">
              <div className="rp-section-head">
                <div>
                  <span className="rp-eyebrow">Subscription</span>
                  <h2>Usage snapshot</h2>
                </div>
              </div>
              <div className="rp-metric-grid">
                <article className="rp-card rp-metric-card">
                  <span>Active chiropractors</span>
                  <strong>{settings.active_chiropractor_count}</strong>
                  <small>{settings.database_summary.counts.users} total user accounts</small>
                </article>
                <article className="rp-card rp-metric-card">
                  <span>Appointments</span>
                  <strong>{settings.database_summary.counts.appointments}</strong>
                  <small>{settings.database_summary.counts.messages} patient messages stored</small>
                </article>
                <article className="rp-card rp-metric-card">
                  <span>Booking services</span>
                  <strong>{settings.database_summary.counts.services}</strong>
                  <small>{settings.database_summary.counts.locations} locations configured</small>
                </article>
              </div>
            </section>
          ) : null}
        </div>
      </section>
    </div>
  );
}
