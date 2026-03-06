import { useState, useEffect, useRef } from "react";

/* ═══════════════════════════════════════════
   LIFE CHIROPRACTIC — PATIENT BOOKING SYSTEM
   ═══════════════════════════════════════════ */

const APPOINTMENT_TYPES = [
  {
    id: "initial",
    label: "Initial Consultation",
    duration: 45,
    price: 65,
    description: "Full assessment including history, examination & first treatment",
    icon: "🩺",
    note: "New patients only",
  },
  {
    id: "followup",
    label: "Follow-up Visit",
    duration: 20,
    price: 42,
    description: "Ongoing treatment and progress review",
    icon: "🔄",
    note: "Existing patients",
  },
  {
    id: "reexam",
    label: "Re-examination",
    duration: 30,
    price: 55,
    description: "Comprehensive progress assessment with updated outcome measures",
    icon: "📋",
    note: "Usually every 12 visits",
  },
  {
    id: "emergency",
    label: "Acute / Urgent",
    duration: 30,
    price: 55,
    description: "Same-day or next-day appointment for sudden onset pain",
    icon: "⚡",
    note: "Subject to availability",
  },
];

/* ─── Generate mock availability ─── */
const generateSlots = (date) => {
  const day = date.getDay();
  if (day === 0) return []; // Sunday closed
  const slots = [];
  const morning = day === 6 ? [9, 10, 11] : [8, 9, 10, 11, 12];
  const afternoon = day === 6 ? [] : [14, 15, 16, 17];
  const all = [...morning, ...afternoon];

  all.forEach((h) => {
    [0, 20, 40].forEach((m) => {
      // Simulate some slots being taken
      const seed = (date.getDate() * 31 + h * 7 + m) % 10;
      if (seed < 4) return; // ~40% booked
      slots.push({
        hour: h,
        minute: m,
        label: `${h.toString().padStart(2, "0")}:${m.toString().padStart(2, "0")}`,
        period: h < 12 ? "Morning" : "Afternoon",
      });
    });
  });
  return slots;
};

const MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];
const DAYS_SHORT = ["Su", "Mo", "Tu", "We", "Th", "Fr", "Sa"];
const STEPS = ["Appointment Type", "Date & Time", "Your Details", "Confirm"];

/* ─── Small Calendar ─── */
const MiniCalendar = ({ selected, onSelect, currentMonth, onMonthChange }) => {
  const year = currentMonth.getFullYear();
  const month = currentMonth.getMonth();
  const firstDay = new Date(year, month, 1).getDay();
  const daysInMonth = new Date(year, month + 1, 0).getDate();
  const today = new Date();
  today.setHours(0, 0, 0, 0);

  const cells = [];
  for (let i = 0; i < firstDay; i++) cells.push(null);
  for (let d = 1; d <= daysInMonth; d++) cells.push(d);

  const canGoPrev = !(month === today.getMonth() && year === today.getFullYear());

  return (
    <div>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 16 }}>
        <button
          onClick={() => canGoPrev && onMonthChange(new Date(year, month - 1, 1))}
          style={{
            background: "none", border: "none", cursor: canGoPrev ? "pointer" : "default",
            color: canGoPrev ? "var(--text)" : "var(--muted)", fontSize: 18, padding: "4px 8px",
            borderRadius: 6, transition: "background 0.15s",
          }}
          onMouseEnter={(e) => canGoPrev && (e.currentTarget.style.background = "var(--surface-alt)")}
          onMouseLeave={(e) => (e.currentTarget.style.background = "none")}
        >
          ‹
        </button>
        <span style={{ fontFamily: "var(--font-heading)", fontSize: 16, fontWeight: 600 }}>
          {MONTHS[month]} {year}
        </span>
        <button
          onClick={() => onMonthChange(new Date(year, month + 1, 1))}
          style={{
            background: "none", border: "none", cursor: "pointer",
            color: "var(--text)", fontSize: 18, padding: "4px 8px",
            borderRadius: 6, transition: "background 0.15s",
          }}
          onMouseEnter={(e) => (e.currentTarget.style.background = "var(--surface-alt)")}
          onMouseLeave={(e) => (e.currentTarget.style.background = "none")}
        >
          ›
        </button>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(7, 1fr)", gap: 2, textAlign: "center" }}>
        {DAYS_SHORT.map((d) => (
          <div key={d} style={{ fontSize: 11, color: "var(--text-muted)", fontWeight: 600, padding: "6px 0", letterSpacing: "0.05em" }}>{d}</div>
        ))}
        {cells.map((day, i) => {
          if (!day) return <div key={`e-${i}`} />;
          const date = new Date(year, month, day);
          date.setHours(0, 0, 0, 0);
          const isPast = date < today;
          const isSunday = date.getDay() === 0;
          const disabled = isPast || isSunday;
          const isSelected = selected && date.getTime() === selected.getTime();
          const isToday = date.getTime() === today.getTime();

          return (
            <button
              key={day}
              disabled={disabled}
              onClick={() => !disabled && onSelect(date)}
              style={{
                width: 38, height: 38, borderRadius: 10,
                border: isToday && !isSelected ? "1.5px solid var(--accent)" : "1.5px solid transparent",
                background: isSelected ? "var(--accent)" : "transparent",
                color: isSelected ? "#fff" : disabled ? "var(--muted)" : "var(--text)",
                fontSize: 13, fontWeight: isSelected || isToday ? 600 : 400,
                cursor: disabled ? "default" : "pointer",
                fontFamily: "var(--font-body)",
                transition: "all 0.15s",
                display: "flex", alignItems: "center", justifyContent: "center",
                margin: "0 auto",
              }}
              onMouseEnter={(e) => { if (!disabled && !isSelected) e.currentTarget.style.background = "var(--surface-alt)"; }}
              onMouseLeave={(e) => { if (!disabled && !isSelected) e.currentTarget.style.background = "transparent"; }}
            >
              {day}
            </button>
          );
        })}
      </div>
    </div>
  );
};

/* ─── Step Indicator ─── */
const StepIndicator = ({ current, steps }) => (
  <div style={{ display: "flex", alignItems: "center", gap: 0, marginBottom: 32 }}>
    {steps.map((s, i) => (
      <div key={i} style={{ display: "flex", alignItems: "center", flex: i < steps.length - 1 ? 1 : "none" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <div style={{
            width: 28, height: 28, borderRadius: 8,
            background: i < current ? "var(--accent)" : i === current ? "var(--accent)" : "var(--surface-alt)",
            color: i <= current ? "#fff" : "var(--text-muted)",
            display: "flex", alignItems: "center", justifyContent: "center",
            fontSize: 12, fontWeight: 600, fontFamily: "var(--font-body)",
            transition: "all 0.3s",
          }}>
            {i < current ? "✓" : i + 1}
          </div>
          <span style={{
            fontSize: 12, fontWeight: i === current ? 600 : 400,
            color: i <= current ? "var(--text)" : "var(--text-muted)",
            fontFamily: "var(--font-body)",
            whiteSpace: "nowrap",
            display: "none",
          }}>{s}</span>
        </div>
        {i < steps.length - 1 && (
          <div style={{
            flex: 1, height: 2, margin: "0 8px",
            background: i < current ? "var(--accent)" : "var(--border)",
            borderRadius: 1, transition: "background 0.3s",
            minWidth: 20,
          }} />
        )}
      </div>
    ))}
  </div>
);

/* ═══ MAIN COMPONENT ═══ */
export default function BookingSystem() {
  const [step, setStep] = useState(0);
  const [selectedType, setSelectedType] = useState(null);
  const [selectedDate, setSelectedDate] = useState(null);
  const [selectedSlot, setSelectedSlot] = useState(null);
  const [currentMonth, setCurrentMonth] = useState(new Date());
  const [form, setForm] = useState({ name: "", email: "", phone: "", dob: "", notes: "", isNew: true });
  const [submitted, setSubmitted] = useState(false);
  const [animKey, setAnimKey] = useState(0);
  const contentRef = useRef(null);

  const slots = selectedDate ? generateSlots(selectedDate) : [];
  const morningSlots = slots.filter((s) => s.period === "Morning");
  const afternoonSlots = slots.filter((s) => s.period === "Afternoon");
  const typeData = APPOINTMENT_TYPES.find((t) => t.id === selectedType);

  const goTo = (s) => {
    setAnimKey((k) => k + 1);
    setStep(s);
  };

  const canProceed = () => {
    if (step === 0) return !!selectedType;
    if (step === 1) return !!selectedDate && !!selectedSlot;
    if (step === 2) return form.name && form.email && form.phone;
    return true;
  };

  const handleSubmit = () => {
    setSubmitted(true);
  };

  const formatDate = (d) => {
    if (!d) return "";
    const days = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];
    return `${days[d.getDay()]}, ${d.getDate()} ${MONTHS[d.getMonth()]} ${d.getFullYear()}`;
  };

  if (submitted) {
    return (
      <>
        <link href="https://fonts.googleapis.com/css2?family=Fraunces:wght@400;500;600;700&family=Outfit:wght@300;400;500;600&display=swap" rel="stylesheet" />
        <style>{cssVars}</style>
        <div style={{
          minHeight: "100vh", background: "var(--bg)", display: "flex", alignItems: "center", justifyContent: "center",
          fontFamily: "var(--font-body)", padding: 20,
        }}>
          <div style={{
            background: "var(--surface)", borderRadius: 24, padding: "48px 36px", maxWidth: 480,
            width: "100%", textAlign: "center", border: "1px solid var(--border)",
            animation: "scaleIn 0.4s cubic-bezier(.16,1,.3,1)",
            boxShadow: "0 20px 60px rgba(0,0,0,0.04)",
          }}>
            <div style={{
              width: 64, height: 64, borderRadius: 16, background: "rgba(45,140,120,0.1)",
              display: "flex", alignItems: "center", justifyContent: "center",
              margin: "0 auto 20px", fontSize: 28, animation: "scaleIn 0.5s 0.15s cubic-bezier(.16,1,.3,1) both",
            }}>✓</div>
            <h2 style={{ fontFamily: "var(--font-heading)", fontSize: 26, fontWeight: 600, margin: "0 0 8px", color: "var(--text)" }}>
              Booking Confirmed
            </h2>
            <p style={{ color: "var(--text-muted)", fontSize: 14, margin: "0 0 28px", lineHeight: 1.6 }}>
              A confirmation has been sent to {form.email}
            </p>

            <div style={{
              background: "var(--surface-alt)", borderRadius: 14, padding: "20px 24px",
              textAlign: "left", marginBottom: 24,
            }}>
              {[
                { label: "Appointment", value: typeData?.label },
                { label: "Date", value: formatDate(selectedDate) },
                { label: "Time", value: selectedSlot?.label },
                { label: "Duration", value: `${typeData?.duration} minutes` },
                { label: "Fee", value: `£${typeData?.price}` },
              ].map((row) => (
                <div key={row.label} style={{ display: "flex", justifyContent: "space-between", padding: "8px 0", borderBottom: "1px solid var(--border)" }}>
                  <span style={{ fontSize: 13, color: "var(--text-muted)" }}>{row.label}</span>
                  <span style={{ fontSize: 13, fontWeight: 500, color: "var(--text)" }}>{row.value}</span>
                </div>
              ))}
            </div>

            {selectedType === "initial" && (
              <div style={{
                background: "rgba(45,140,120,0.06)", border: "1px solid rgba(45,140,120,0.15)",
                borderRadius: 12, padding: "14px 18px", marginBottom: 24, textAlign: "left",
              }}>
                <div style={{ fontSize: 13, fontWeight: 600, color: "var(--accent)", marginBottom: 4 }}>Before your visit</div>
                <div style={{ fontSize: 13, color: "var(--text-muted)", lineHeight: 1.6 }}>
                  We'll email you a pre-visit questionnaire to complete before your appointment. This helps us make the most of your consultation time.
                </div>
              </div>
            )}

            <div style={{ display: "flex", gap: 10 }}>
              <button
                onClick={() => { setSubmitted(false); setStep(0); setSelectedType(null); setSelectedDate(null); setSelectedSlot(null); setForm({ name: "", email: "", phone: "", dob: "", notes: "", isNew: true }); }}
                style={{
                  flex: 1, padding: "13px 20px", borderRadius: 12,
                  border: "1px solid var(--border)", background: "var(--surface)",
                  color: "var(--text)", fontSize: 14, fontWeight: 500,
                  cursor: "pointer", fontFamily: "var(--font-body)",
                }}
              >
                Book Another
              </button>
              <button
                style={{
                  flex: 1, padding: "13px 20px", borderRadius: 12,
                  border: "none", background: "var(--accent)", color: "#fff",
                  fontSize: 14, fontWeight: 600, cursor: "pointer", fontFamily: "var(--font-body)",
                }}
              >
                Add to Calendar
              </button>
            </div>
          </div>
        </div>
      </>
    );
  }

  return (
    <>
      <link href="https://fonts.googleapis.com/css2?family=Fraunces:wght@400;500;600;700&family=Outfit:wght@300;400;500;600&display=swap" rel="stylesheet" />
      <style>{cssVars}</style>

      <div style={{ minHeight: "100vh", background: "var(--bg)", fontFamily: "var(--font-body)" }}>
        {/* ── Header ── */}
        <div style={{
          background: "var(--surface)", borderBottom: "1px solid var(--border)",
          padding: "0 24px", height: 64, display: "flex", alignItems: "center", justifyContent: "space-between",
          position: "sticky", top: 0, zIndex: 50,
        }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <div style={{
              width: 34, height: 34, borderRadius: 9, background: "var(--accent)",
              display: "flex", alignItems: "center", justifyContent: "center",
              color: "#fff", fontFamily: "var(--font-heading)", fontSize: 16, fontWeight: 700,
            }}>L</div>
            <span style={{ fontFamily: "var(--font-heading)", fontSize: 17, fontWeight: 600, color: "var(--text)" }}>
              Life Chiropractic
            </span>
          </div>
          <div style={{ fontSize: 13, color: "var(--text-muted)" }}>
            Need help? <span style={{ color: "var(--accent)", fontWeight: 500, cursor: "pointer" }}>Contact us</span>
          </div>
        </div>

        {/* ── Main Content ── */}
        <div style={{ maxWidth: 680, margin: "0 auto", padding: "28px 20px 80px" }}>
          {/* Hero */}
          <div style={{ marginBottom: 28, animation: "fadeIn 0.4s ease" }}>
            <h1 style={{
              fontFamily: "var(--font-heading)", fontSize: 30, fontWeight: 600,
              color: "var(--text)", margin: "0 0 6px", letterSpacing: "-0.02em",
            }}>
              Book an Appointment
            </h1>
            <p style={{ color: "var(--text-muted)", fontSize: 15, margin: 0, lineHeight: 1.5 }}>
              Choose your appointment type and find a time that works for you.
            </p>
          </div>

          <StepIndicator current={step} steps={STEPS} />

          {/* ═══ STEP 0: Appointment Type ═══ */}
          {step === 0 && (
            <div key={`step0-${animKey}`} style={{ animation: "slideUp 0.3s ease" }}>
              <h2 style={{ fontFamily: "var(--font-heading)", fontSize: 20, fontWeight: 600, margin: "0 0 16px" }}>
                What type of appointment do you need?
              </h2>
              <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                {APPOINTMENT_TYPES.map((type, idx) => {
                  const active = selectedType === type.id;
                  return (
                    <button
                      key={type.id}
                      onClick={() => setSelectedType(type.id)}
                      style={{
                        display: "flex", alignItems: "center", gap: 16,
                        padding: "18px 20px", borderRadius: 16, textAlign: "left",
                        border: active ? "2px solid var(--accent)" : "1.5px solid var(--border)",
                        background: active ? "rgba(45,140,120,0.04)" : "var(--surface)",
                        cursor: "pointer", transition: "all 0.2s",
                        animation: `slideUp 0.3s ease ${idx * 50}ms both`,
                      }}
                      onMouseEnter={(e) => { if (!active) { e.currentTarget.style.borderColor = "var(--muted)"; e.currentTarget.style.transform = "translateY(-1px)"; } }}
                      onMouseLeave={(e) => { if (!active) { e.currentTarget.style.borderColor = "var(--border)"; e.currentTarget.style.transform = "translateY(0)"; } }}
                    >
                      <div style={{
                        width: 48, height: 48, borderRadius: 12,
                        background: active ? "rgba(45,140,120,0.1)" : "var(--surface-alt)",
                        display: "flex", alignItems: "center", justifyContent: "center",
                        fontSize: 22, flexShrink: 0, transition: "background 0.2s",
                      }}>{type.icon}</div>
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 2 }}>
                          <span style={{ fontSize: 15, fontWeight: 600, color: "var(--text)" }}>{type.label}</span>
                          <span style={{
                            fontSize: 11, fontWeight: 500, padding: "2px 8px", borderRadius: 20,
                            background: "var(--surface-alt)", color: "var(--text-muted)",
                          }}>{type.note}</span>
                        </div>
                        <div style={{ fontSize: 13, color: "var(--text-muted)", marginBottom: 4, lineHeight: 1.4 }}>{type.description}</div>
                        <div style={{ display: "flex", gap: 12, fontSize: 12, color: "var(--text-muted)" }}>
                          <span style={{ fontWeight: 500 }}>{type.duration} min</span>
                          <span>·</span>
                          <span style={{ fontWeight: 500 }}>£{type.price}</span>
                        </div>
                      </div>
                      <div style={{
                        width: 22, height: 22, borderRadius: 11,
                        border: active ? "6px solid var(--accent)" : "2px solid var(--muted)",
                        flexShrink: 0, transition: "all 0.2s",
                        boxSizing: "border-box",
                      }} />
                    </button>
                  );
                })}
              </div>
            </div>
          )}

          {/* ═══ STEP 1: Date & Time ═══ */}
          {step === 1 && (
            <div key={`step1-${animKey}`} style={{ animation: "slideUp 0.3s ease" }}>
              <h2 style={{ fontFamily: "var(--font-heading)", fontSize: 20, fontWeight: 600, margin: "0 0 4px" }}>
                Pick a date and time
              </h2>
              <p style={{ fontSize: 13, color: "var(--text-muted)", margin: "0 0 20px" }}>
                {typeData?.label} · {typeData?.duration} min · £{typeData?.price}
              </p>

              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20, alignItems: "start" }}>
                {/* Calendar */}
                <div style={{
                  background: "var(--surface)", borderRadius: 16, border: "1px solid var(--border)",
                  padding: "18px 16px",
                }}>
                  <MiniCalendar
                    selected={selectedDate}
                    onSelect={(d) => { setSelectedDate(d); setSelectedSlot(null); }}
                    currentMonth={currentMonth}
                    onMonthChange={setCurrentMonth}
                  />
                </div>

                {/* Time Slots */}
                <div style={{
                  background: "var(--surface)", borderRadius: 16, border: "1px solid var(--border)",
                  padding: "18px 16px", minHeight: 280,
                }}>
                  {!selectedDate ? (
                    <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: 240, color: "var(--text-muted)", fontSize: 14 }}>
                      Select a date to view times
                    </div>
                  ) : slots.length === 0 ? (
                    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", height: 240, color: "var(--text-muted)", fontSize: 14, textAlign: "center", gap: 8 }}>
                      <span style={{ fontSize: 24 }}>😴</span>
                      <span>No availability on this date</span>
                      <span style={{ fontSize: 12 }}>Try another day</span>
                    </div>
                  ) : (
                    <div>
                      {[{ label: "Morning", items: morningSlots }, { label: "Afternoon", items: afternoonSlots }]
                        .filter((g) => g.items.length > 0)
                        .map((group) => (
                          <div key={group.label} style={{ marginBottom: 16 }}>
                            <div style={{ fontSize: 11, fontWeight: 600, color: "var(--text-muted)", marginBottom: 8, textTransform: "uppercase", letterSpacing: "0.06em" }}>
                              {group.label}
                            </div>
                            <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 6 }}>
                              {group.items.map((slot) => {
                                const active = selectedSlot?.label === slot.label;
                                return (
                                  <button
                                    key={slot.label}
                                    onClick={() => setSelectedSlot(slot)}
                                    style={{
                                      padding: "10px 6px", borderRadius: 10, fontSize: 13, fontWeight: 500,
                                      border: active ? "1.5px solid var(--accent)" : "1px solid var(--border)",
                                      background: active ? "rgba(45,140,120,0.08)" : "var(--surface)",
                                      color: active ? "var(--accent)" : "var(--text)",
                                      cursor: "pointer", fontFamily: "var(--font-body)", transition: "all 0.15s",
                                    }}
                                    onMouseEnter={(e) => { if (!active) e.currentTarget.style.borderColor = "var(--muted)"; }}
                                    onMouseLeave={(e) => { if (!active) e.currentTarget.style.borderColor = "var(--border)"; }}
                                  >
                                    {slot.label}
                                  </button>
                                );
                              })}
                            </div>
                          </div>
                        ))}
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* ═══ STEP 2: Details ═══ */}
          {step === 2 && (
            <div key={`step2-${animKey}`} style={{ animation: "slideUp 0.3s ease" }}>
              <h2 style={{ fontFamily: "var(--font-heading)", fontSize: 20, fontWeight: 600, margin: "0 0 4px" }}>
                Your details
              </h2>
              <p style={{ fontSize: 13, color: "var(--text-muted)", margin: "0 0 20px" }}>
                {formatDate(selectedDate)} at {selectedSlot?.label}
              </p>

              <div style={{
                background: "var(--surface)", borderRadius: 16, border: "1px solid var(--border)", padding: "24px 22px",
              }}>
                {/* New/Returning toggle */}
                <div style={{ display: "flex", gap: 8, marginBottom: 24 }}>
                  {[{ key: true, label: "New Patient" }, { key: false, label: "Returning Patient" }].map((opt) => (
                    <button
                      key={String(opt.key)}
                      onClick={() => setForm((f) => ({ ...f, isNew: opt.key }))}
                      style={{
                        flex: 1, padding: "11px 16px", borderRadius: 10, fontSize: 13, fontWeight: 500,
                        border: form.isNew === opt.key ? "1.5px solid var(--accent)" : "1px solid var(--border)",
                        background: form.isNew === opt.key ? "rgba(45,140,120,0.06)" : "transparent",
                        color: form.isNew === opt.key ? "var(--accent)" : "var(--text-muted)",
                        cursor: "pointer", fontFamily: "var(--font-body)", transition: "all 0.15s",
                      }}
                    >
                      {opt.label}
                    </button>
                  ))}
                </div>

                {[
                  { key: "name", label: "Full Name", placeholder: "Jane Smith", required: true },
                  { key: "email", label: "Email Address", placeholder: "jane@example.com", required: true },
                  { key: "phone", label: "Phone Number", placeholder: "+44 7700 000000", required: true },
                  { key: "dob", label: "Date of Birth", placeholder: "DD/MM/YYYY", required: false },
                ].map((field) => (
                  <div key={field.key} style={{ marginBottom: 16 }}>
                    <label style={{
                      display: "block", fontSize: 12, fontWeight: 500, color: "var(--text-muted)",
                      marginBottom: 6, textTransform: "uppercase", letterSpacing: "0.04em",
                    }}>
                      {field.label} {field.required && <span style={{ color: "var(--accent)" }}>*</span>}
                    </label>
                    <input
                      type="text"
                      value={form[field.key]}
                      onChange={(e) => setForm((f) => ({ ...f, [field.key]: e.target.value }))}
                      placeholder={field.placeholder}
                      style={{
                        width: "100%", padding: "12px 16px", borderRadius: 10,
                        border: "1px solid var(--border)", background: "var(--surface-alt)",
                        fontSize: 14, fontFamily: "var(--font-body)", color: "var(--text)",
                        outline: "none", boxSizing: "border-box", transition: "border-color 0.15s",
                      }}
                      onFocus={(e) => (e.target.style.borderColor = "var(--accent)")}
                      onBlur={(e) => (e.target.style.borderColor = "var(--border)")}
                    />
                  </div>
                ))}

                <div>
                  <label style={{
                    display: "block", fontSize: 12, fontWeight: 500, color: "var(--text-muted)",
                    marginBottom: 6, textTransform: "uppercase", letterSpacing: "0.04em",
                  }}>Additional Notes</label>
                  <textarea
                    value={form.notes}
                    onChange={(e) => setForm((f) => ({ ...f, notes: e.target.value }))}
                    placeholder="Anything you'd like us to know..."
                    rows={3}
                    style={{
                      width: "100%", padding: "12px 16px", borderRadius: 10,
                      border: "1px solid var(--border)", background: "var(--surface-alt)",
                      fontSize: 14, fontFamily: "var(--font-body)", color: "var(--text)",
                      outline: "none", boxSizing: "border-box", resize: "vertical", transition: "border-color 0.15s",
                    }}
                    onFocus={(e) => (e.target.style.borderColor = "var(--accent)")}
                    onBlur={(e) => (e.target.style.borderColor = "var(--border)")}
                  />
                </div>
              </div>
            </div>
          )}

          {/* ═══ STEP 3: Confirm ═══ */}
          {step === 3 && (
            <div key={`step3-${animKey}`} style={{ animation: "slideUp 0.3s ease" }}>
              <h2 style={{ fontFamily: "var(--font-heading)", fontSize: 20, fontWeight: 600, margin: "0 0 16px" }}>
                Review & confirm
              </h2>

              <div style={{
                background: "var(--surface)", borderRadius: 16, border: "1px solid var(--border)", padding: "24px 22px",
              }}>
                {/* Summary card */}
                <div style={{
                  background: "var(--surface-alt)", borderRadius: 12, padding: "18px 20px", marginBottom: 20,
                }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 14, marginBottom: 16 }}>
                    <div style={{ fontSize: 28 }}>{typeData?.icon}</div>
                    <div>
                      <div style={{ fontSize: 16, fontWeight: 600, fontFamily: "var(--font-heading)" }}>{typeData?.label}</div>
                      <div style={{ fontSize: 13, color: "var(--text-muted)" }}>{typeData?.duration} minutes · £{typeData?.price}</div>
                    </div>
                  </div>

                  {[
                    { icon: "📅", value: formatDate(selectedDate) },
                    { icon: "🕐", value: selectedSlot?.label },
                    { icon: "👤", value: form.name },
                    { icon: "✉️", value: form.email },
                    { icon: "📱", value: form.phone },
                  ].map((row, i) => (
                    <div key={i} style={{ display: "flex", alignItems: "center", gap: 10, padding: "7px 0", fontSize: 14, color: "var(--text)" }}>
                      <span style={{ fontSize: 14, width: 22, textAlign: "center" }}>{row.icon}</span>
                      <span>{row.value}</span>
                    </div>
                  ))}
                  {form.notes && (
                    <div style={{ marginTop: 8, padding: "10px 14px", background: "var(--surface)", borderRadius: 8, fontSize: 13, color: "var(--text-muted)", lineHeight: 1.5 }}>
                      "{form.notes}"
                    </div>
                  )}
                </div>

                {/* Cancellation policy */}
                <div style={{
                  background: "rgba(45,140,120,0.04)", border: "1px solid rgba(45,140,120,0.12)",
                  borderRadius: 10, padding: "12px 16px", marginBottom: 8, fontSize: 13,
                  color: "var(--text-muted)", lineHeight: 1.5,
                }}>
                  <strong style={{ color: "var(--text)", fontWeight: 600 }}>Cancellation policy:</strong> Please give at least 24 hours' notice if you need to cancel or reschedule. Late cancellations may be charged the full appointment fee.
                </div>
              </div>
            </div>
          )}

          {/* ── Navigation Buttons ── */}
          <div style={{
            display: "flex", justifyContent: "space-between", alignItems: "center",
            marginTop: 28, gap: 12,
          }}>
            {step > 0 ? (
              <button
                onClick={() => goTo(step - 1)}
                style={{
                  padding: "13px 24px", borderRadius: 12, border: "1px solid var(--border)",
                  background: "var(--surface)", color: "var(--text)", fontSize: 14, fontWeight: 500,
                  cursor: "pointer", fontFamily: "var(--font-body)", transition: "all 0.15s",
                }}
                onMouseEnter={(e) => (e.currentTarget.style.background = "var(--surface-alt)")}
                onMouseLeave={(e) => (e.currentTarget.style.background = "var(--surface)")}
              >
                Back
              </button>
            ) : <div />}

            <button
              onClick={() => step === 3 ? handleSubmit() : goTo(step + 1)}
              disabled={!canProceed()}
              style={{
                padding: "13px 32px", borderRadius: 12, border: "none",
                background: canProceed() ? "var(--accent)" : "var(--muted)",
                color: "#fff", fontSize: 14, fontWeight: 600,
                cursor: canProceed() ? "pointer" : "default",
                fontFamily: "var(--font-body)", transition: "all 0.2s",
                boxShadow: canProceed() ? "0 4px 14px rgba(45,140,120,0.2)" : "none",
              }}
              onMouseEnter={(e) => { if (canProceed()) e.currentTarget.style.background = "#247060"; }}
              onMouseLeave={(e) => { if (canProceed()) e.currentTarget.style.background = "var(--accent)"; }}
            >
              {step === 3 ? "Confirm Booking" : "Continue"}
            </button>
          </div>
        </div>
      </div>
    </>
  );
}

const cssVars = `
  :root {
    --bg: #FAF9F7;
    --surface: #FFFFFF;
    --surface-alt: #F3F2EF;
    --border: #E6E4DF;
    --muted: #CBC9C3;
    --text: #191816;
    --text-muted: #78756E;
    --accent: #2D8C78;
    --accent-dark: #247060;
    --font-heading: 'Fraunces', serif;
    --font-body: 'Outfit', sans-serif;
  }
  * { box-sizing: border-box; }
  input::placeholder, textarea::placeholder { color: var(--muted); }
  @keyframes slideUp {
    from { opacity: 0; transform: translateY(12px); }
    to { opacity: 1; transform: translateY(0); }
  }
  @keyframes fadeIn {
    from { opacity: 0; }
    to { opacity: 1; }
  }
  @keyframes scaleIn {
    from { opacity: 0; transform: scale(0.92); }
    to { opacity: 1; transform: scale(1); }
  }
`;
