import { useState, useEffect, useRef } from "react";

const SECTIONS = {
  practitioner: [
    {
      id: "profile",
      label: "Profile & Practice",
      icon: "person",
      description: "Your professional identity",
    },
    {
      id: "clinic",
      label: "Clinic Configuration",
      icon: "clinic",
      description: "Hours, rooms & locations",
    },
    {
      id: "scheduling",
      label: "Scheduling",
      icon: "calendar",
      description: "Appointments & booking",
    },
    {
      id: "notifications",
      label: "Notifications",
      icon: "bell",
      description: "Reminders & messaging",
    },
    {
      id: "clinical",
      label: "Clinical Defaults",
      icon: "clipboard",
      description: "Outcome measures & forms",
    },
    {
      id: "billing",
      label: "Billing & Payments",
      icon: "card",
      description: "Fees, invoices & receipts",
    },
    {
      id: "security",
      label: "Security & Access",
      icon: "lock",
      description: "Authentication & roles",
    },
    {
      id: "data",
      label: "Data & Compliance",
      icon: "shield",
      description: "GDPR, retention & backups",
    },
    {
      id: "appearance",
      label: "Appearance",
      icon: "palette",
      description: "Branding & theme",
    },
    {
      id: "integrations",
      label: "Integrations",
      icon: "plug",
      description: "Third-party connections",
    },
    {
      id: "subscription",
      label: "Subscription",
      icon: "star",
      description: "Plan & usage",
    },
  ],
  client: [
    {
      id: "my-profile",
      label: "My Profile",
      icon: "person",
      description: "Personal details",
    },
    {
      id: "notification-prefs",
      label: "Notifications",
      icon: "bell",
      description: "How we contact you",
    },
    {
      id: "privacy",
      label: "Privacy & Data",
      icon: "shield",
      description: "Your data rights",
    },
    {
      id: "accessibility",
      label: "Accessibility",
      icon: "eye",
      description: "Display preferences",
    },
    {
      id: "support",
      label: "Help & Support",
      icon: "help",
      description: "Get assistance",
    },
  ],
};

const Icons = {
  person: () => (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="8" r="4" />
      <path d="M20 21a8 8 0 0 0-16 0" />
    </svg>
  ),
  clinic: () => (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M3 21h18" />
      <path d="M5 21V7l7-4 7 4v14" />
      <path d="M9 21v-4h6v4" />
      <path d="M10 10h4" />
      <path d="M12 8v4" />
    </svg>
  ),
  calendar: () => (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <rect x="3" y="4" width="18" height="18" rx="2" />
      <path d="M16 2v4M8 2v4M3 10h18" />
      <rect x="7" y="14" width="3" height="3" rx="0.5" />
    </svg>
  ),
  bell: () => (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" />
      <path d="M13.73 21a2 2 0 0 1-3.46 0" />
    </svg>
  ),
  clipboard: () => (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <rect x="5" y="2" width="14" height="20" rx="2" />
      <path d="M9 2h6v3H9z" />
      <path d="M9 12h6M9 16h4" />
    </svg>
  ),
  card: () => (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <rect x="2" y="5" width="20" height="14" rx="2" />
      <path d="M2 10h20" />
      <path d="M6 15h4" />
    </svg>
  ),
  lock: () => (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <rect x="5" y="11" width="14" height="10" rx="2" />
      <path d="M8 11V7a4 4 0 0 1 8 0v4" />
      <circle cx="12" cy="16" r="1.5" />
    </svg>
  ),
  shield: () => (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 2l8 4v6c0 5.5-3.8 10.7-8 12-4.2-1.3-8-6.5-8-12V6l8-4z" />
      <path d="M9 12l2 2 4-4" />
    </svg>
  ),
  palette: () => (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="10" />
      <circle cx="8" cy="9" r="1.5" fill="currentColor" />
      <circle cx="15" cy="8" r="1.5" fill="currentColor" />
      <circle cx="16" cy="13" r="1.5" fill="currentColor" />
      <circle cx="9" cy="14" r="1.5" fill="currentColor" />
    </svg>
  ),
  plug: () => (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 22v-5" />
      <path d="M9 8V2M15 8V2" />
      <rect x="6" y="8" width="12" height="5" rx="2" />
      <path d="M10 13v4h4v-4" />
    </svg>
  ),
  star: () => (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" />
    </svg>
  ),
  eye: () => (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
      <circle cx="12" cy="12" r="3" />
    </svg>
  ),
  help: () => (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="10" />
      <path d="M9 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3" />
      <circle cx="12" cy="18" r="0.5" fill="currentColor" />
    </svg>
  ),
  chevron: () => (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="9 18 15 12 9 6" />
    </svg>
  ),
  back: () => (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="15 18 9 12 15 6" />
    </svg>
  ),
  toggle: () => null,
  search: () => (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="11" cy="11" r="8" />
      <line x1="21" y1="21" x2="16.65" y2="16.65" />
    </svg>
  ),
};

/* ─── Toggle Switch ─── */
const Toggle = ({ on, onChange, label }) => (
  <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "14px 0", borderBottom: "1px solid var(--border)" }}>
    <span style={{ fontSize: 14, color: "var(--text)", fontFamily: "var(--font-body)" }}>{label}</span>
    <button
      onClick={() => onChange(!on)}
      style={{
        width: 44,
        height: 24,
        borderRadius: 12,
        border: "none",
        background: on ? "var(--accent)" : "var(--muted)",
        cursor: "pointer",
        position: "relative",
        transition: "background 0.2s",
      }}
    >
      <div
        style={{
          width: 18,
          height: 18,
          borderRadius: 9,
          background: "#fff",
          position: "absolute",
          top: 3,
          left: on ? 23 : 3,
          transition: "left 0.2s cubic-bezier(.4,0,.2,1)",
          boxShadow: "0 1px 3px rgba(0,0,0,0.15)",
        }}
      />
    </button>
  </div>
);

/* ─── Select Dropdown ─── */
const Select = ({ label, value, options, onChange }) => (
  <div style={{ padding: "14px 0", borderBottom: "1px solid var(--border)" }}>
    <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
      <span style={{ fontSize: 14, color: "var(--text)", fontFamily: "var(--font-body)" }}>{label}</span>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        style={{
          padding: "6px 12px",
          borderRadius: 8,
          border: "1px solid var(--border)",
          background: "var(--surface)",
          color: "var(--text)",
          fontSize: 13,
          fontFamily: "var(--font-body)",
          cursor: "pointer",
          outline: "none",
        }}
      >
        {options.map((o) => (
          <option key={o.value} value={o.value}>{o.label}</option>
        ))}
      </select>
    </div>
  </div>
);

/* ─── Text Input Row ─── */
const InputRow = ({ label, value, onChange, placeholder }) => (
  <div style={{ padding: "14px 0", borderBottom: "1px solid var(--border)" }}>
    <label style={{ display: "block", fontSize: 12, color: "var(--text-secondary)", marginBottom: 6, fontFamily: "var(--font-body)", textTransform: "uppercase", letterSpacing: "0.04em" }}>{label}</label>
    <input
      type="text"
      value={value}
      onChange={(e) => onChange(e.target.value)}
      placeholder={placeholder}
      style={{
        width: "100%",
        padding: "10px 14px",
        borderRadius: 10,
        border: "1px solid var(--border)",
        background: "var(--surface)",
        color: "var(--text)",
        fontSize: 14,
        fontFamily: "var(--font-body)",
        outline: "none",
        boxSizing: "border-box",
      }}
    />
  </div>
);

/* ─── Action Button Row ─── */
const ActionRow = ({ label, description, buttonLabel, danger, onClick }) => (
  <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "16px 0", borderBottom: "1px solid var(--border)", gap: 16 }}>
    <div>
      <div style={{ fontSize: 14, color: "var(--text)", fontFamily: "var(--font-body)" }}>{label}</div>
      {description && <div style={{ fontSize: 12, color: "var(--text-secondary)", marginTop: 2, fontFamily: "var(--font-body)" }}>{description}</div>}
    </div>
    <button
      onClick={onClick}
      style={{
        padding: "8px 16px",
        borderRadius: 8,
        border: danger ? "1px solid #e5484d" : "1px solid var(--border)",
        background: danger ? "rgba(229,72,77,0.08)" : "var(--surface)",
        color: danger ? "#e5484d" : "var(--text)",
        fontSize: 13,
        fontFamily: "var(--font-body)",
        cursor: "pointer",
        whiteSpace: "nowrap",
        fontWeight: 500,
      }}
    >
      {buttonLabel}
    </button>
  </div>
);

/* ─── Tag Selector ─── */
const TagSelector = ({ label, tags, selected, onChange }) => (
  <div style={{ padding: "14px 0", borderBottom: "1px solid var(--border)" }}>
    <div style={{ fontSize: 12, color: "var(--text-secondary)", marginBottom: 10, fontFamily: "var(--font-body)", textTransform: "uppercase", letterSpacing: "0.04em" }}>{label}</div>
    <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
      {tags.map((tag) => {
        const active = selected.includes(tag);
        return (
          <button
            key={tag}
            onClick={() => onChange(active ? selected.filter((t) => t !== tag) : [...selected, tag])}
            style={{
              padding: "6px 14px",
              borderRadius: 20,
              border: active ? "1.5px solid var(--accent)" : "1px solid var(--border)",
              background: active ? "rgba(45,140,120,0.1)" : "transparent",
              color: active ? "var(--accent)" : "var(--text-secondary)",
              fontSize: 13,
              fontFamily: "var(--font-body)",
              cursor: "pointer",
              fontWeight: active ? 600 : 400,
              transition: "all 0.15s ease",
            }}
          >
            {tag}
          </button>
        );
      })}
    </div>
  </div>
);

/* ─── Section Content Panels ─── */
const SectionContent = ({ sectionId, role }) => {
  const [toggles, setToggles] = useState({});
  const [inputs, setInputs] = useState({});
  const [selects, setSelects] = useState({});
  const [tags, setTags] = useState({ measures: ["NDI", "ODI"], days: ["Mon", "Tue", "Wed", "Thu", "Fri"] });

  const t = (key) => toggles[key] ?? false;
  const st = (key, val) => setToggles((p) => ({ ...p, [key]: val }));
  const i = (key) => inputs[key] ?? "";
  const si = (key, val) => setInputs((p) => ({ ...p, [key]: val }));
  const s = (key) => selects[key] ?? "";
  const ss = (key, val) => setSelects((p) => ({ ...p, [key]: val }));

  const panels = {
    /* ── Practitioner Panels ── */
    profile: (
      <>
        <InputRow label="Full Name" value={i("name")} onChange={(v) => si("name", v)} placeholder="Dr. Hussein — DC" />
        <InputRow label="GCC Registration No." value={i("gcc")} onChange={(v) => si("gcc", v)} placeholder="00000" />
        <InputRow label="Qualifications" value={i("quals")} onChange={(v) => si("quals", v)} placeholder="DC, MSc Chiropractic" />
        <InputRow label="Clinic Name" value={i("clinic")} onChange={(v) => si("clinic", v)} placeholder="Life Chiropractic" />
        <InputRow label="Email" value={i("email")} onChange={(v) => si("email", v)} placeholder="clinic@example.com" />
        <InputRow label="Phone" value={i("phone")} onChange={(v) => si("phone", v)} placeholder="+44 7700 000000" />
        <InputRow label="Address" value={i("address")} onChange={(v) => si("address", v)} placeholder="123 High Street, London" />
        <ActionRow label="Clinic Logo" description="Upload your logo for patient-facing pages" buttonLabel="Upload" onClick={() => {}} />
        <InputRow label="Bio" value={i("bio")} onChange={(v) => si("bio", v)} placeholder="Short bio for your patient portal..." />
      </>
    ),
    clinic: (
      <>
        <TagSelector label="Operating Days" tags={["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]} selected={tags.days} onChange={(v) => setTags((p) => ({ ...p, days: v }))} />
        <InputRow label="Opening Time" value={i("open") || "08:00"} onChange={(v) => si("open", v)} placeholder="08:00" />
        <InputRow label="Closing Time" value={i("close") || "18:00"} onChange={(v) => si("close", v)} placeholder="18:00" />
        <InputRow label="Lunch Break Start" value={i("lunch1") || "13:00"} onChange={(v) => si("lunch1", v)} placeholder="13:00" />
        <InputRow label="Lunch Break End" value={i("lunch2") || "14:00"} onChange={(v) => si("lunch2", v)} placeholder="14:00" />
        <InputRow label="Number of Treatment Rooms" value={i("rooms") || "2"} onChange={(v) => si("rooms", v)} placeholder="2" />
        <Toggle label="Multi-practitioner mode" on={t("multi")} onChange={(v) => st("multi", v)} />
        <ActionRow label="Manage Staff Accounts" description="Add or edit associate practitioners" buttonLabel="Manage" onClick={() => {}} />
      </>
    ),
    scheduling: (
      <>
        <Select label="Initial Consultation Duration" value={s("init") || "45"} onChange={(v) => ss("init", v)} options={[{ value: "30", label: "30 min" }, { value: "45", label: "45 min" }, { value: "60", label: "60 min" }]} />
        <Select label="Follow-up Duration" value={s("followup") || "20"} onChange={(v) => ss("followup", v)} options={[{ value: "15", label: "15 min" }, { value: "20", label: "20 min" }, { value: "30", label: "30 min" }]} />
        <Select label="Buffer Between Appointments" value={s("buffer") || "5"} onChange={(v) => ss("buffer", v)} options={[{ value: "0", label: "None" }, { value: "5", label: "5 min" }, { value: "10", label: "10 min" }, { value: "15", label: "15 min" }]} />
        <Select label="Max Advance Booking" value={s("advance") || "4w"} onChange={(v) => ss("advance", v)} options={[{ value: "1w", label: "1 week" }, { value: "2w", label: "2 weeks" }, { value: "4w", label: "4 weeks" }, { value: "8w", label: "8 weeks" }]} />
        <Toggle label="Enable online booking" on={t("booking")} onChange={(v) => st("booking", v)} />
        <Toggle label="Allow same-day bookings" on={t("sameday")} onChange={(v) => st("sameday", v)} />
        <Select label="Cancellation Window" value={s("cancel") || "24"} onChange={(v) => ss("cancel", v)} options={[{ value: "12", label: "12 hours" }, { value: "24", label: "24 hours" }, { value: "48", label: "48 hours" }]} />
        <Toggle label="Charge for no-shows" on={t("noshow")} onChange={(v) => st("noshow", v)} />
      </>
    ),
    notifications: (
      <>
        <Toggle label="Appointment confirmation email" on={t("confirmEmail")} onChange={(v) => st("confirmEmail", v)} />
        <Toggle label="Appointment confirmation SMS" on={t("confirmSms")} onChange={(v) => st("confirmSms", v)} />
        <Toggle label="24-hour reminder" on={t("remind24")} onChange={(v) => st("remind24", v)} />
        <Toggle label="1-hour reminder" on={t("remind1")} onChange={(v) => st("remind1", v)} />
        <Toggle label="Post-visit summary email" on={t("postVisit")} onChange={(v) => st("postVisit", v)} />
        <Toggle label="Recall reminders for lapsed patients" on={t("recall")} onChange={(v) => st("recall", v)} />
        <Select label="Recall After Inactivity" value={s("recallDays") || "60"} onChange={(v) => ss("recallDays", v)} options={[{ value: "30", label: "30 days" }, { value: "60", label: "60 days" }, { value: "90", label: "90 days" }]} />
        <ActionRow label="Email Templates" description="Customise confirmation, reminder & recall templates" buttonLabel="Edit" onClick={() => {}} />
      </>
    ),
    clinical: (
      <>
        <TagSelector label="Default Outcome Measures" tags={["NDI", "ODI", "QuickDASH", "HIT-6", "SF-36", "PSFS", "VAS Pain"]} selected={tags.measures} onChange={(v) => setTags((p) => ({ ...p, measures: v }))} />
        <Select label="Default Re-examination Interval" value={s("reexam") || "12"} onChange={(v) => ss("reexam", v)} options={[{ value: "6", label: "6 visits" }, { value: "12", label: "12 visits" }, { value: "custom", label: "Custom" }]} />
        <Toggle label="Use MCID thresholds for re-exam decisions" on={t("mcid")} onChange={(v) => st("mcid", v)} />
        <Toggle label="Auto-assign intake form to new patients" on={t("intake")} onChange={(v) => st("intake", v)} />
        <Toggle label="Include consent form in intake" on={t("consent")} onChange={(v) => st("consent", v)} />
        <ActionRow label="Manage Intake Forms" description="Create or edit pre-visit questionnaire steps" buttonLabel="Manage" onClick={() => {}} />
        <ActionRow label="Treatment Protocols" description="Configure tissue-based healing timelines" buttonLabel="Configure" onClick={() => {}} />
      </>
    ),
    billing: (
      <>
        <InputRow label="Initial Consultation Fee (£)" value={i("feeInit") || "65"} onChange={(v) => si("feeInit", v)} placeholder="65" />
        <InputRow label="Follow-up Fee (£)" value={i("feeFU") || "42"} onChange={(v) => si("feeFU", v)} placeholder="42" />
        <TagSelector label="Accepted Payment Methods" tags={["Card", "Cash", "Bank Transfer", "Apple Pay", "Google Pay"]} selected={tags.payment || ["Card"]} onChange={(v) => setTags((p) => ({ ...p, payment: v }))} />
        <Toggle label="Auto-generate invoice after visit" on={t("autoInvoice")} onChange={(v) => st("autoInvoice", v)} />
        <Toggle label="Send receipt via email" on={t("receipt")} onChange={(v) => st("receipt", v)} />
        <ActionRow label="Invoice Template" description="Customise header, footer & layout" buttonLabel="Edit" onClick={() => {}} />
        <InputRow label="VAT Number (if applicable)" value={i("vat")} onChange={(v) => si("vat", v)} placeholder="GB 123 4567 89" />
      </>
    ),
    security: (
      <>
        <Toggle label="Two-factor authentication" on={t("2fa")} onChange={(v) => st("2fa", v)} />
        <Select label="Session Timeout" value={s("timeout") || "30"} onChange={(v) => ss("timeout", v)} options={[{ value: "15", label: "15 min" }, { value: "30", label: "30 min" }, { value: "60", label: "1 hour" }, { value: "120", label: "2 hours" }]} />
        <ActionRow label="Change Password" description="Update your login credentials" buttonLabel="Change" onClick={() => {}} />
        <ActionRow label="Staff Accounts & Roles" description="Manage associate access levels" buttonLabel="Manage" onClick={() => {}} />
        <Toggle label="Show audit log" on={t("audit")} onChange={(v) => st("audit", v)} />
        <ActionRow label="Active Sessions" description="View and terminate logged-in devices" buttonLabel="View" onClick={() => {}} />
      </>
    ),
    data: (
      <>
        <InputRow label="ICO Registration Reference" value={i("ico")} onChange={(v) => si("ico", v)} placeholder="ZA000000" />
        <Select label="Data Retention Period" value={s("retention") || "7y"} onChange={(v) => ss("retention", v)} options={[{ value: "3y", label: "3 years" }, { value: "7y", label: "7 years" }, { value: "10y", label: "10 years" }]} />
        <Toggle label="Auto-anonymise after retention period" on={t("anon")} onChange={(v) => st("anon", v)} />
        <ActionRow label="Export All Data" description="Download a full GDPR-compliant export" buttonLabel="Export" onClick={() => {}} />
        <ActionRow label="Manage Patient Consent Records" description="View and update consent status" buttonLabel="View" onClick={() => {}} />
        <Toggle label="Automatic daily backups" on={t("backup")} onChange={(v) => st("backup", v)} />
        <ActionRow label="Backup History" description="View and restore previous backups" buttonLabel="View" onClick={() => {}} />
      </>
    ),
    appearance: (
      <>
        <Select label="Theme" value={s("theme") || "light"} onChange={(v) => ss("theme", v)} options={[{ value: "light", label: "Light" }, { value: "dark", label: "Dark" }, { value: "auto", label: "System" }]} />
        <InputRow label="Primary Brand Colour" value={i("brandColor") || "#2D8C78"} onChange={(v) => si("brandColor", v)} placeholder="#2D8C78" />
        <ActionRow label="Upload Logo" description="Used in patient portal, invoices & emails" buttonLabel="Upload" onClick={() => {}} />
        <Select label="Font Style" value={s("font") || "modern"} onChange={(v) => ss("font", v)} options={[{ value: "modern", label: "Modern (DM Sans)" }, { value: "classic", label: "Classic (Lora)" }, { value: "clean", label: "Clean (Source Sans)" }]} />
        <Toggle label="Show clinic branding on patient portal" on={t("brandPortal")} onChange={(v) => st("brandPortal", v)} />
      </>
    ),
    integrations: (
      <>
        <ActionRow label="Payment Processor" description="Connect Stripe, Square, or SumUp" buttonLabel="Connect" onClick={() => {}} />
        <ActionRow label="Calendar Sync" description="Sync with Google Calendar or Outlook" buttonLabel="Connect" onClick={() => {}} />
        <ActionRow label="Email Provider" description="Connect Mailgun, SendGrid, or Amazon SES" buttonLabel="Connect" onClick={() => {}} />
        <ActionRow label="SMS Provider" description="Connect Twilio or Vonage" buttonLabel="Connect" onClick={() => {}} />
        <ActionRow label="Accounting" description="Export to Xero, QuickBooks, or FreeAgent" buttonLabel="Connect" onClick={() => {}} />
      </>
    ),
    subscription: (
      <>
        <div style={{ padding: "20px 0", borderBottom: "1px solid var(--border)" }}>
          <div style={{ display: "flex", alignItems: "baseline", gap: 8 }}>
            <span style={{ fontSize: 28, fontWeight: 700, color: "var(--text)", fontFamily: "var(--font-heading)" }}>Pro</span>
            <span style={{ fontSize: 13, color: "var(--accent)", fontWeight: 600, padding: "2px 10px", borderRadius: 20, background: "rgba(45,140,120,0.1)" }}>Active</span>
          </div>
          <div style={{ fontSize: 13, color: "var(--text-secondary)", marginTop: 4, fontFamily: "var(--font-body)" }}>Renews 1 Apr 2026 · £79/mo</div>
        </div>
        <ActionRow label="Upgrade / Downgrade" description="Change your subscription plan" buttonLabel="View Plans" onClick={() => {}} />
        <ActionRow label="Billing History" description="Download past invoices" buttonLabel="View" onClick={() => {}} />
        <ActionRow label="Payment Method" description="Visa ending 4242" buttonLabel="Update" onClick={() => {}} />
      </>
    ),

    /* ── Client Panels ── */
    "my-profile": (
      <>
        <InputRow label="Full Name" value={i("cname")} onChange={(v) => si("cname", v)} placeholder="Jane Smith" />
        <InputRow label="Date of Birth" value={i("dob")} onChange={(v) => si("dob", v)} placeholder="DD/MM/YYYY" />
        <InputRow label="Email" value={i("cemail")} onChange={(v) => si("cemail", v)} placeholder="jane@example.com" />
        <InputRow label="Phone" value={i("cphone")} onChange={(v) => si("cphone", v)} placeholder="+44 7700 000000" />
        <InputRow label="Emergency Contact" value={i("emergency")} onChange={(v) => si("emergency", v)} placeholder="Name — Relationship — Phone" />
        <InputRow label="GP Name & Practice" value={i("gp")} onChange={(v) => si("gp", v)} placeholder="Dr. Jones, High Street Surgery" />
      </>
    ),
    "notification-prefs": (
      <>
        <Toggle label="Appointment reminders by email" on={t("cremindE")} onChange={(v) => st("cremindE", v)} />
        <Toggle label="Appointment reminders by SMS" on={t("cremindS")} onChange={(v) => st("cremindS", v)} />
        <Toggle label="Push notifications" on={t("cpush")} onChange={(v) => st("cpush", v)} />
        <Toggle label="Receive recall reminders" on={t("crecall")} onChange={(v) => st("crecall", v)} />
        <Toggle label="Educational content & tips" on={t("cedu")} onChange={(v) => st("cedu", v)} />
      </>
    ),
    privacy: (
      <>
        <ActionRow label="View My Data" description="See all data your clinic holds about you" buttonLabel="View" onClick={() => {}} />
        <ActionRow label="Export My Data" description="Download a copy of your records" buttonLabel="Export" onClick={() => {}} />
        <ActionRow label="Manage Consent" description="Update what data we can collect and use" buttonLabel="Manage" onClick={() => {}} />
        <ActionRow label="Delete My Account" description="Permanently remove all your data" buttonLabel="Delete" danger onClick={() => {}} />
      </>
    ),
    accessibility: (
      <>
        <Select label="Text Size" value={s("fontSize") || "md"} onChange={(v) => ss("fontSize", v)} options={[{ value: "sm", label: "Small" }, { value: "md", label: "Medium" }, { value: "lg", label: "Large" }, { value: "xl", label: "Extra Large" }]} />
        <Toggle label="High contrast mode" on={t("contrast")} onChange={(v) => st("contrast", v)} />
        <Select label="Language" value={s("lang") || "en"} onChange={(v) => ss("lang", v)} options={[{ value: "en", label: "English" }, { value: "cy", label: "Cymraeg (Welsh)" }, { value: "ar", label: "العربية (Arabic)" }, { value: "pl", label: "Polski (Polish)" }]} />
        <Toggle label="Reduce animations" on={t("reduceMotion")} onChange={(v) => st("reduceMotion", v)} />
      </>
    ),
    support: (
      <>
        <ActionRow label="Help Centre" description="Browse FAQs and guides" buttonLabel="Open" onClick={() => {}} />
        <ActionRow label="Contact Your Clinic" description="Send a message to your chiropractor" buttonLabel="Message" onClick={() => {}} />
        <ActionRow label="Report a Problem" description="Let us know if something isn't working" buttonLabel="Report" onClick={() => {}} />
        <ActionRow label="App Version" description="v1.0.0" buttonLabel="Check for Updates" onClick={() => {}} />
      </>
    ),
  };

  return panels[sectionId] || <div style={{ padding: 20, color: "var(--text-secondary)" }}>Coming soon</div>;
};

/* ─── Main App ─── */
export default function SettingsPage() {
  const [role, setRole] = useState("practitioner");
  const [activeSection, setActiveSection] = useState(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [saveFlash, setSaveFlash] = useState(false);
  const contentRef = useRef(null);

  const sections = SECTIONS[role];
  const filtered = searchQuery
    ? sections.filter(
        (s) =>
          s.label.toLowerCase().includes(searchQuery.toLowerCase()) ||
          s.description.toLowerCase().includes(searchQuery.toLowerCase())
      )
    : sections;

  const activeData = sections.find((s) => s.id === activeSection);

  const handleSave = () => {
    setSaveFlash(true);
    setTimeout(() => setSaveFlash(false), 2000);
  };

  useEffect(() => {
    if (contentRef.current) contentRef.current.scrollTop = 0;
  }, [activeSection]);

  return (
    <>
      <link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Playfair+Display:wght@500;600;700&display=swap" rel="stylesheet" />
      <style>{`
        :root {
          --bg: #F7F6F3;
          --surface: #FFFFFF;
          --surface-hover: #F0EFEC;
          --border: #E8E6E1;
          --text: #1A1A1A;
          --text-secondary: #7A7770;
          --accent: #2D8C78;
          --accent-hover: #247060;
          --muted: #D4D2CC;
          --font-heading: 'Playfair Display', serif;
          --font-body: 'DM Sans', sans-serif;
          --danger: #E5484D;
        }
      `}</style>
      <div style={{
        minHeight: "100vh",
        background: "var(--bg)",
        fontFamily: "var(--font-body)",
        color: "var(--text)",
      }}>
        {/* ── Top Bar ── */}
        <div style={{
          background: "var(--surface)",
          borderBottom: "1px solid var(--border)",
          padding: "0 28px",
          height: 64,
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          position: "sticky",
          top: 0,
          zIndex: 100,
        }}>
          <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
            {activeSection && (
              <button
                onClick={() => setActiveSection(null)}
                style={{
                  background: "none",
                  border: "none",
                  cursor: "pointer",
                  color: "var(--text-secondary)",
                  display: "flex",
                  alignItems: "center",
                  padding: 4,
                  borderRadius: 6,
                  transition: "color 0.15s",
                }}
                onMouseEnter={(e) => (e.currentTarget.style.color = "var(--text)")}
                onMouseLeave={(e) => (e.currentTarget.style.color = "var(--text-secondary)")}
              >
                <Icons.back />
              </button>
            )}
            <h1 style={{
              fontFamily: "var(--font-heading)",
              fontSize: activeSection ? 18 : 22,
              fontWeight: 600,
              margin: 0,
              letterSpacing: "-0.01em",
            }}>
              {activeSection ? activeData?.label : "Settings"}
            </h1>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            {/* Role Switcher */}
            <div style={{
              display: "flex",
              background: "var(--bg)",
              borderRadius: 10,
              padding: 3,
              gap: 2,
            }}>
              {[
                { key: "practitioner", label: "Practitioner" },
                { key: "client", label: "Client" },
              ].map((r) => (
                <button
                  key={r.key}
                  onClick={() => { setRole(r.key); setActiveSection(null); setSearchQuery(""); }}
                  style={{
                    padding: "7px 16px",
                    borderRadius: 8,
                    border: "none",
                    background: role === r.key ? "var(--surface)" : "transparent",
                    color: role === r.key ? "var(--text)" : "var(--text-secondary)",
                    fontSize: 13,
                    fontWeight: role === r.key ? 600 : 400,
                    cursor: "pointer",
                    fontFamily: "var(--font-body)",
                    boxShadow: role === r.key ? "0 1px 3px rgba(0,0,0,0.06)" : "none",
                    transition: "all 0.2s",
                  }}
                >
                  {r.label}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* ── Content ── */}
        <div ref={contentRef} style={{ maxWidth: 640, margin: "0 auto", padding: "24px 20px 100px" }}>
          {!activeSection ? (
            <>
              {/* Search */}
              <div style={{
                position: "relative",
                marginBottom: 20,
              }}>
                <div style={{ position: "absolute", left: 14, top: "50%", transform: "translateY(-50%)", color: "var(--text-secondary)" }}>
                  <Icons.search />
                </div>
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Search settings..."
                  style={{
                    width: "100%",
                    padding: "13px 14px 13px 42px",
                    borderRadius: 14,
                    border: "1px solid var(--border)",
                    background: "var(--surface)",
                    fontSize: 14,
                    fontFamily: "var(--font-body)",
                    color: "var(--text)",
                    outline: "none",
                    boxSizing: "border-box",
                    transition: "border-color 0.15s",
                  }}
                  onFocus={(e) => (e.target.style.borderColor = "var(--accent)")}
                  onBlur={(e) => (e.target.style.borderColor = "var(--border)")}
                />
              </div>

              {/* Section List */}
              <div style={{
                display: "flex",
                flexDirection: "column",
                gap: 6,
              }}>
                {filtered.map((section, idx) => {
                  const Icon = Icons[section.icon];
                  return (
                    <button
                      key={section.id}
                      onClick={() => setActiveSection(section.id)}
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: 14,
                        padding: "16px 18px",
                        borderRadius: 14,
                        border: "1px solid var(--border)",
                        background: "var(--surface)",
                        cursor: "pointer",
                        textAlign: "left",
                        transition: "all 0.15s ease",
                        animation: `fadeSlideIn 0.25s ease ${idx * 30}ms both`,
                      }}
                      onMouseEnter={(e) => {
                        e.currentTarget.style.background = "var(--surface-hover)";
                        e.currentTarget.style.borderColor = "var(--muted)";
                        e.currentTarget.style.transform = "translateY(-1px)";
                      }}
                      onMouseLeave={(e) => {
                        e.currentTarget.style.background = "var(--surface)";
                        e.currentTarget.style.borderColor = "var(--border)";
                        e.currentTarget.style.transform = "translateY(0)";
                      }}
                    >
                      <div style={{
                        width: 40,
                        height: 40,
                        borderRadius: 10,
                        background: "rgba(45,140,120,0.08)",
                        color: "var(--accent)",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        flexShrink: 0,
                      }}>
                        <Icon />
                      </div>
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <div style={{ fontSize: 14, fontWeight: 600, color: "var(--text)", fontFamily: "var(--font-body)" }}>{section.label}</div>
                        <div style={{ fontSize: 12, color: "var(--text-secondary)", marginTop: 1, fontFamily: "var(--font-body)" }}>{section.description}</div>
                      </div>
                      <div style={{ color: "var(--muted)", flexShrink: 0 }}>
                        <Icons.chevron />
                      </div>
                    </button>
                  );
                })}
                {filtered.length === 0 && (
                  <div style={{ textAlign: "center", padding: 40, color: "var(--text-secondary)", fontSize: 14 }}>
                    No settings found for "{searchQuery}"
                  </div>
                )}
              </div>
            </>
          ) : (
            /* ── Detail Panel ── */
            <div style={{
              background: "var(--surface)",
              borderRadius: 16,
              border: "1px solid var(--border)",
              padding: "8px 22px 22px",
              animation: "fadeSlideIn 0.2s ease both",
            }}>
              <SectionContent sectionId={activeSection} role={role} />

              {/* Save Button */}
              <div style={{ marginTop: 24, display: "flex", justifyContent: "flex-end" }}>
                <button
                  onClick={handleSave}
                  style={{
                    padding: "11px 32px",
                    borderRadius: 10,
                    border: "none",
                    background: saveFlash ? "#22956C" : "var(--accent)",
                    color: "#fff",
                    fontSize: 14,
                    fontWeight: 600,
                    fontFamily: "var(--font-body)",
                    cursor: "pointer",
                    transition: "all 0.2s",
                    boxShadow: "0 2px 8px rgba(45,140,120,0.2)",
                  }}
                  onMouseEnter={(e) => { if (!saveFlash) e.currentTarget.style.background = "var(--accent-hover)"; }}
                  onMouseLeave={(e) => { if (!saveFlash) e.currentTarget.style.background = "var(--accent)"; }}
                >
                  {saveFlash ? "✓ Saved" : "Save Changes"}
                </button>
              </div>
            </div>
          )}
        </div>
      </div>

      <style>{`
        @keyframes fadeSlideIn {
          from { opacity: 0; transform: translateY(8px); }
          to { opacity: 1; transform: translateY(0); }
        }
        input::placeholder { color: var(--muted); }
        select:focus { border-color: var(--accent) !important; }
        * { box-sizing: border-box; }
      `}</style>
    </>
  );
}
