import { useState, useMemo } from "react";

/*
  CARE PLAN → CALENDAR SYNC
  
  Logic:
  - Frequency: 1x or 2x per week
  - Duration: 3, 6, 9, or 12 weeks
  - Total visits = frequency × weeks
  - Midpoint visit = progress check
  - Final visit = reassessment
  - All others = follow-up
  - Supports "Book All Now" (auto-generate dates) and "Book As You Go" (track against plan)
*/

/* ─── Care Plan Engine ─── */
function generateCarePlan({ frequency, weeks, startDate, patientName }) {
  const totalVisits = frequency * weeks;
  const midpoint = Math.ceil(totalVisits / 2);
  const visits = [];

  let currentDate = new Date(startDate);
  // Advance to next weekday if weekend
  while (currentDate.getDay() === 0 || currentDate.getDay() === 6) {
    currentDate.setDate(currentDate.getDate() + 1);
  }

  for (let i = 1; i <= totalVisits; i++) {
    let type = "follow-up";
    let label = `Visit ${i}`;
    let duration = 20;
    let fee = 42;

    if (i === midpoint) {
      type = "progress-check";
      label = `Visit ${i} — Progress Check`;
      duration = 30;
      fee = 55;
    } else if (i === totalVisits) {
      type = "reassessment";
      label = `Visit ${i} — Reassessment`;
      duration = 30;
      fee = 55;
    }

    visits.push({
      number: i,
      type,
      label,
      duration,
      fee,
      date: new Date(currentDate),
      status: "scheduled", // scheduled | completed | missed | unbooked
      booked: false,
    });

    // Advance date
    if (frequency === 1) {
      currentDate.setDate(currentDate.getDate() + 7);
    } else {
      // 2x per week: Mon/Thu or Tue/Fri pattern
      const day = currentDate.getDay();
      if (day <= 3) {
        currentDate.setDate(currentDate.getDate() + 3); // e.g. Mon→Thu
      } else {
        currentDate.setDate(currentDate.getDate() + (7 - day + 1)); // e.g. Thu→Mon
      }
    }
    // Skip weekends
    while (currentDate.getDay() === 0 || currentDate.getDay() === 6) {
      currentDate.setDate(currentDate.getDate() + 1);
    }
  }

  return {
    patientName,
    frequency,
    weeks,
    totalVisits,
    midpoint,
    visits,
    startDate: new Date(startDate),
    createdAt: new Date(),
  };
}

/* ─── Constants ─── */
const FREQ_OPTIONS = [
  { value: 1, label: "Once a week", sub: "1× / week" },
  { value: 2, label: "Twice a week", sub: "2× / week" },
];
const WEEK_OPTIONS = [3, 6, 9, 12];
const DAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
const MONTHS_FULL = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];

const TYPE_META = {
  "follow-up": { color: "#2D8C78", bg: "rgba(45,140,120,0.08)", icon: "→", tagLabel: "Follow-up" },
  "progress-check": { color: "#D97706", bg: "rgba(217,119,6,0.08)", icon: "◆", tagLabel: "Progress Check" },
  "reassessment": { color: "#7C3AED", bg: "rgba(124,58,237,0.08)", icon: "★", tagLabel: "Reassessment" },
};

function formatDate(d) {
  return `${DAYS[d.getDay()]} ${d.getDate()} ${MONTHS[d.getMonth()]}`;
}
function formatDateLong(d) {
  return `${DAYS[d.getDay()]}, ${d.getDate()} ${MONTHS_FULL[d.getMonth()]} ${d.getFullYear()}`;
}

/* ─── Mini Calendar Month ─── */
function CalendarMonth({ year, month, visits }) {
  const firstDay = new Date(year, month, 1).getDay();
  const daysInMonth = new Date(year, month + 1, 0).getDate();
  const cells = [];
  for (let i = 0; i < firstDay; i++) cells.push(null);
  for (let d = 1; d <= daysInMonth; d++) cells.push(d);

  const visitDates = {};
  visits.forEach((v) => {
    const vd = v.date;
    if (vd.getFullYear() === year && vd.getMonth() === month) {
      visitDates[vd.getDate()] = v;
    }
  });

  return (
    <div>
      <div style={{ fontSize: 13, fontWeight: 600, fontFamily: "var(--fh)", marginBottom: 10, color: "var(--text)" }}>
        {MONTHS_FULL[month]} {year}
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(7, 1fr)", gap: 2, textAlign: "center" }}>
        {["S", "M", "T", "W", "T", "F", "S"].map((d, i) => (
          <div key={i} style={{ fontSize: 9, fontWeight: 600, color: "var(--dim)", padding: "4px 0", letterSpacing: "0.05em" }}>{d}</div>
        ))}
        {cells.map((day, i) => {
          if (!day) return <div key={`e${i}`} />;
          const visit = visitDates[day];
          const meta = visit ? TYPE_META[visit.type] : null;
          return (
            <div
              key={day}
              style={{
                width: 30, height: 30, borderRadius: 8, margin: "0 auto",
                display: "flex", alignItems: "center", justifyContent: "center",
                fontSize: 11, fontWeight: visit ? 700 : 400,
                color: visit ? meta.color : "var(--text)",
                background: visit ? meta.bg : "transparent",
                border: visit ? `1.5px solid ${meta.color}30` : "1.5px solid transparent",
                position: "relative",
              }}
              title={visit ? visit.label : ""}
            >
              {day}
              {visit && visit.type !== "follow-up" && (
                <div style={{
                  position: "absolute", top: -2, right: -2,
                  width: 7, height: 7, borderRadius: 4,
                  background: meta.color, border: "1.5px solid var(--surface)",
                }} />
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

/* ═══════════════════════════════
   MAIN COMPONENT
   ═══════════════════════════════ */
export default function CarePlanSystem() {
  const [view, setView] = useState("builder"); // builder | plan
  const [patient, setPatient] = useState("Sarah Mitchell");
  const [frequency, setFrequency] = useState(2);
  const [weeks, setWeeks] = useState(6);
  const [startDate, setStartDate] = useState(() => {
    const d = new Date();
    d.setDate(d.getDate() + ((1 + 7 - d.getDay()) % 7 || 7)); // next Monday
    return d.toISOString().split("T")[0];
  });
  const [bookingMode, setBookingMode] = useState("all"); // all | asYouGo
  const [plan, setPlan] = useState(null);
  const [selectedVisit, setSelectedVisit] = useState(null);

  const totalVisits = frequency * weeks;
  const midpoint = Math.ceil(totalVisits / 2);
  const totalFee = useMemo(() => {
    let sum = 0;
    for (let i = 1; i <= totalVisits; i++) {
      if (i === midpoint) sum += 55;
      else if (i === totalVisits) sum += 55;
      else sum += 42;
    }
    return sum;
  }, [totalVisits, midpoint]);

  const handleCreate = () => {
    const p = generateCarePlan({
      frequency,
      weeks,
      startDate: new Date(startDate),
      patientName: patient,
    });
    if (bookingMode === "all") {
      p.visits = p.visits.map((v) => ({ ...v, booked: true, status: "scheduled" }));
    } else {
      // Book as you go — only first visit is booked
      p.visits = p.visits.map((v, i) => ({
        ...v,
        booked: i === 0,
        status: i === 0 ? "scheduled" : "unbooked",
      }));
    }
    setPlan(p);
    setView("plan");
    setSelectedVisit(null);
  };

  const handleBookNext = () => {
    if (!plan) return;
    const nextUnbooked = plan.visits.findIndex((v) => !v.booked);
    if (nextUnbooked >= 0) {
      const updated = { ...plan, visits: [...plan.visits] };
      updated.visits[nextUnbooked] = { ...updated.visits[nextUnbooked], booked: true, status: "scheduled" };
      setPlan(updated);
    }
  };

  const handleComplete = (idx) => {
    if (!plan) return;
    const updated = { ...plan, visits: [...plan.visits] };
    updated.visits[idx] = { ...updated.visits[idx], status: "completed" };
    setPlan(updated);
  };

  const handleMiss = (idx) => {
    if (!plan) return;
    const updated = { ...plan, visits: [...plan.visits] };
    updated.visits[idx] = { ...updated.visits[idx], status: "missed" };
    setPlan(updated);
  };

  // Calendar months needed
  const calendarMonths = useMemo(() => {
    if (!plan) return [];
    const months = new Set();
    plan.visits.forEach((v) => {
      months.add(`${v.date.getFullYear()}-${v.date.getMonth()}`);
    });
    return Array.from(months).map((m) => {
      const [y, mo] = m.split("-").map(Number);
      return { year: y, month: mo };
    });
  }, [plan]);

  // Stats
  const stats = useMemo(() => {
    if (!plan) return {};
    const completed = plan.visits.filter((v) => v.status === "completed").length;
    const booked = plan.visits.filter((v) => v.booked).length;
    const missed = plan.visits.filter((v) => v.status === "missed").length;
    const remaining = plan.totalVisits - completed - missed;
    const nextVisit = plan.visits.find((v) => v.status === "scheduled" && v.booked);
    const nextUnbooked = plan.visits.find((v) => !v.booked);
    return { completed, booked, missed, remaining, nextVisit, nextUnbooked };
  }, [plan]);

  return (
    <>
      <link href="https://fonts.googleapis.com/css2?family=Fraunces:ital,wght@0,400;0,500;0,600;0,700;1,400&family=Outfit:wght@300;400;500;600;700&display=swap" rel="stylesheet" />
      <style>{`
        :root {
          --bg: #F4F3F0;
          --surface: #FFFFFF;
          --surface-alt: #ECEAE6;
          --border: #DDD9D3;
          --text: #181714;
          --dim: #8A857C;
          --accent: #2D8C78;
          --accent-l: #4CC9AD;
          --warn: #D97706;
          --purple: #7C3AED;
          --danger: #E5484D;
          --fh: 'Fraunces', serif;
          --fb: 'Outfit', sans-serif;
        }
        * { box-sizing: border-box; margin: 0; }
        input::placeholder { color: var(--dim); }
        @keyframes enter { from { opacity:0; transform:translateY(12px); } to { opacity:1; transform:translateY(0); } }
      `}</style>

      <div style={{ minHeight: "100vh", background: "var(--bg)", fontFamily: "var(--fb)", color: "var(--text)" }}>

        {/* ── Header ── */}
        <div style={{
          background: "var(--surface)", borderBottom: "1px solid var(--border)",
          padding: "0 24px", height: 58, display: "flex", alignItems: "center", justifyContent: "space-between",
          position: "sticky", top: 0, zIndex: 50,
        }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <div style={{ width: 30, height: 30, borderRadius: 8, background: "var(--accent)", display: "flex", alignItems: "center", justifyContent: "center", color: "#fff", fontFamily: "var(--fh)", fontSize: 14, fontWeight: 700 }}>L</div>
            <span style={{ fontFamily: "var(--fh)", fontSize: 15, fontWeight: 600 }}>Life Chiropractic</span>
          </div>
          {view === "plan" && (
            <button
              onClick={() => { setView("builder"); setPlan(null); }}
              style={{ fontSize: 13, color: "var(--accent)", background: "none", border: "none", cursor: "pointer", fontWeight: 500, fontFamily: "var(--fb)" }}
            >
              ← New Care Plan
            </button>
          )}
        </div>

        <div style={{ maxWidth: 920, margin: "0 auto", padding: "28px 24px 80px" }}>

          {/* ═══════════════════════════
             BUILDER VIEW
             ═══════════════════════════ */}
          {view === "builder" && (
            <div style={{ animation: "enter 0.3s ease" }}>
              <div style={{ marginBottom: 28 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
                  <div style={{ width: 7, height: 7, borderRadius: 4, background: "var(--accent)" }} />
                  <span style={{ fontSize: 10, fontWeight: 600, letterSpacing: "0.14em", textTransform: "uppercase", color: "var(--accent)" }}>Care Plan Builder</span>
                </div>
                <h1 style={{ fontFamily: "var(--fh)", fontSize: 30, fontWeight: 600, letterSpacing: "-0.02em" }}>
                  Create Care Plan
                </h1>
                <p style={{ fontSize: 14, color: "var(--dim)", marginTop: 6, lineHeight: 1.5 }}>
                  Set frequency and duration. Appointments auto-schedule with a progress check at the midpoint and reassessment as the final visit.
                </p>
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
                {/* Left — Config */}
                <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                  {/* Patient */}
                  <div style={{ background: "var(--surface)", borderRadius: 14, border: "1px solid var(--border)", padding: "20px 22px" }}>
                    <label style={{ display: "block", fontSize: 10, fontWeight: 600, letterSpacing: "0.1em", textTransform: "uppercase", color: "var(--dim)", marginBottom: 8 }}>Patient Name</label>
                    <input
                      value={patient}
                      onChange={(e) => setPatient(e.target.value)}
                      placeholder="Patient name"
                      style={{ width: "100%", padding: "11px 14px", borderRadius: 10, border: "1px solid var(--border)", background: "var(--surface-alt)", fontSize: 14, fontFamily: "var(--fb)", color: "var(--text)", outline: "none" }}
                    />
                  </div>

                  {/* Frequency */}
                  <div style={{ background: "var(--surface)", borderRadius: 14, border: "1px solid var(--border)", padding: "20px 22px" }}>
                    <label style={{ display: "block", fontSize: 10, fontWeight: 600, letterSpacing: "0.1em", textTransform: "uppercase", color: "var(--dim)", marginBottom: 10 }}>Frequency</label>
                    <div style={{ display: "flex", gap: 8 }}>
                      {FREQ_OPTIONS.map((opt) => (
                        <button
                          key={opt.value}
                          onClick={() => setFrequency(opt.value)}
                          style={{
                            flex: 1, padding: "14px 16px", borderRadius: 10, cursor: "pointer", textAlign: "center",
                            border: frequency === opt.value ? "2px solid var(--accent)" : "1.5px solid var(--border)",
                            background: frequency === opt.value ? "rgba(45,140,120,0.05)" : "transparent",
                            transition: "all 0.15s",
                          }}
                        >
                          <div style={{ fontSize: 14, fontWeight: 600, color: frequency === opt.value ? "var(--accent)" : "var(--text)" }}>{opt.label}</div>
                          <div style={{ fontSize: 11, color: "var(--dim)", marginTop: 2 }}>{opt.sub}</div>
                        </button>
                      ))}
                    </div>
                  </div>

                  {/* Weeks */}
                  <div style={{ background: "var(--surface)", borderRadius: 14, border: "1px solid var(--border)", padding: "20px 22px" }}>
                    <label style={{ display: "block", fontSize: 10, fontWeight: 600, letterSpacing: "0.1em", textTransform: "uppercase", color: "var(--dim)", marginBottom: 10 }}>Duration</label>
                    <div style={{ display: "flex", gap: 8 }}>
                      {WEEK_OPTIONS.map((w) => (
                        <button
                          key={w}
                          onClick={() => setWeeks(w)}
                          style={{
                            flex: 1, padding: "14px 10px", borderRadius: 10, cursor: "pointer", textAlign: "center",
                            border: weeks === w ? "2px solid var(--accent)" : "1.5px solid var(--border)",
                            background: weeks === w ? "rgba(45,140,120,0.05)" : "transparent",
                            transition: "all 0.15s",
                          }}
                        >
                          <div style={{ fontSize: 18, fontWeight: 700, color: weeks === w ? "var(--accent)" : "var(--text)", fontFamily: "var(--fh)" }}>{w}</div>
                          <div style={{ fontSize: 10, color: "var(--dim)", marginTop: 2 }}>weeks</div>
                        </button>
                      ))}
                    </div>
                  </div>

                  {/* Start Date */}
                  <div style={{ background: "var(--surface)", borderRadius: 14, border: "1px solid var(--border)", padding: "20px 22px" }}>
                    <label style={{ display: "block", fontSize: 10, fontWeight: 600, letterSpacing: "0.1em", textTransform: "uppercase", color: "var(--dim)", marginBottom: 8 }}>Start Date</label>
                    <input
                      type="date"
                      value={startDate}
                      onChange={(e) => setStartDate(e.target.value)}
                      style={{ width: "100%", padding: "11px 14px", borderRadius: 10, border: "1px solid var(--border)", background: "var(--surface-alt)", fontSize: 14, fontFamily: "var(--fb)", color: "var(--text)", outline: "none" }}
                    />
                  </div>

                  {/* Booking Mode */}
                  <div style={{ background: "var(--surface)", borderRadius: 14, border: "1px solid var(--border)", padding: "20px 22px" }}>
                    <label style={{ display: "block", fontSize: 10, fontWeight: 600, letterSpacing: "0.1em", textTransform: "uppercase", color: "var(--dim)", marginBottom: 10 }}>Booking Mode</label>
                    <div style={{ display: "flex", gap: 8 }}>
                      {[
                        { key: "all", label: "Book All Now", desc: "Schedule every visit upfront" },
                        { key: "asYouGo", label: "Book As You Go", desc: "Patient books each visit" },
                      ].map((opt) => (
                        <button
                          key={opt.key}
                          onClick={() => setBookingMode(opt.key)}
                          style={{
                            flex: 1, padding: "14px 14px", borderRadius: 10, cursor: "pointer", textAlign: "left",
                            border: bookingMode === opt.key ? "2px solid var(--accent)" : "1.5px solid var(--border)",
                            background: bookingMode === opt.key ? "rgba(45,140,120,0.05)" : "transparent",
                            transition: "all 0.15s",
                          }}
                        >
                          <div style={{ fontSize: 13, fontWeight: 600, color: bookingMode === opt.key ? "var(--accent)" : "var(--text)" }}>{opt.label}</div>
                          <div style={{ fontSize: 11, color: "var(--dim)", marginTop: 2 }}>{opt.desc}</div>
                        </button>
                      ))}
                    </div>
                  </div>
                </div>

                {/* Right — Preview Summary */}
                <div>
                  <div style={{
                    background: "var(--surface)", borderRadius: 14, border: "1px solid var(--border)",
                    padding: "24px 22px", position: "sticky", top: 80,
                  }}>
                    <div style={{ fontSize: 10, fontWeight: 600, letterSpacing: "0.1em", textTransform: "uppercase", color: "var(--dim)", marginBottom: 16 }}>Plan Preview</div>

                    <div style={{ fontFamily: "var(--fh)", fontSize: 22, fontWeight: 600, marginBottom: 4 }}>{patient || "Patient"}</div>
                    <div style={{ fontSize: 13, color: "var(--dim)", marginBottom: 20 }}>{frequency}× per week for {weeks} weeks</div>

                    {/* Visit breakdown */}
                    <div style={{ background: "var(--surface-alt)", borderRadius: 10, padding: "16px 18px", marginBottom: 16 }}>
                      <div style={{ display: "flex", justifyContent: "space-between", padding: "6px 0", borderBottom: "1px solid var(--border)" }}>
                        <span style={{ fontSize: 13, color: "var(--dim)" }}>Total Visits</span>
                        <span style={{ fontSize: 15, fontWeight: 700, fontFamily: "var(--fh)", color: "var(--text)" }}>{totalVisits}</span>
                      </div>
                      <div style={{ display: "flex", justifyContent: "space-between", padding: "6px 0", borderBottom: "1px solid var(--border)" }}>
                        <span style={{ fontSize: 13, color: "var(--dim)" }}>Follow-ups</span>
                        <span style={{ fontSize: 13, fontWeight: 600, color: TYPE_META["follow-up"].color }}>{totalVisits - 2}</span>
                      </div>
                      <div style={{ display: "flex", justifyContent: "space-between", padding: "6px 0", borderBottom: "1px solid var(--border)" }}>
                        <span style={{ fontSize: 13, color: "var(--dim)" }}>Progress Check</span>
                        <span style={{ fontSize: 13, fontWeight: 600, color: TYPE_META["progress-check"].color }}>Visit {midpoint}</span>
                      </div>
                      <div style={{ display: "flex", justifyContent: "space-between", padding: "6px 0", borderBottom: "1px solid var(--border)" }}>
                        <span style={{ fontSize: 13, color: "var(--dim)" }}>Reassessment</span>
                        <span style={{ fontSize: 13, fontWeight: 600, color: TYPE_META["reassessment"].color }}>Visit {totalVisits} (final)</span>
                      </div>
                      <div style={{ display: "flex", justifyContent: "space-between", padding: "8px 0 2px" }}>
                        <span style={{ fontSize: 13, fontWeight: 600, color: "var(--text)" }}>Estimated Total Fee</span>
                        <span style={{ fontSize: 15, fontWeight: 700, fontFamily: "var(--fh)", color: "var(--text)" }}>£{totalFee}</span>
                      </div>
                    </div>

                    {/* Visual timeline */}
                    <div style={{ marginBottom: 20 }}>
                      <div style={{ fontSize: 10, fontWeight: 600, letterSpacing: "0.1em", textTransform: "uppercase", color: "var(--dim)", marginBottom: 10 }}>Visit Sequence</div>
                      <div style={{ display: "flex", gap: 3, flexWrap: "wrap" }}>
                        {Array.from({ length: totalVisits }, (_, i) => {
                          const num = i + 1;
                          let type = "follow-up";
                          if (num === midpoint) type = "progress-check";
                          if (num === totalVisits) type = "reassessment";
                          const meta = TYPE_META[type];
                          return (
                            <div
                              key={i}
                              title={`Visit ${num}: ${meta.tagLabel}`}
                              style={{
                                width: totalVisits > 16 ? 20 : 26,
                                height: totalVisits > 16 ? 20 : 26,
                                borderRadius: 5,
                                background: meta.bg,
                                border: `1.5px solid ${meta.color}40`,
                                display: "flex", alignItems: "center", justifyContent: "center",
                                fontSize: totalVisits > 16 ? 8 : 10,
                                fontWeight: 700, color: meta.color,
                              }}
                            >
                              {num}
                            </div>
                          );
                        })}
                      </div>
                      <div style={{ display: "flex", gap: 12, marginTop: 10 }}>
                        {Object.entries(TYPE_META).map(([key, meta]) => (
                          <div key={key} style={{ display: "flex", alignItems: "center", gap: 5 }}>
                            <div style={{ width: 8, height: 8, borderRadius: 3, background: meta.color }} />
                            <span style={{ fontSize: 10, color: "var(--dim)" }}>{meta.tagLabel}</span>
                          </div>
                        ))}
                      </div>
                    </div>

                    {/* Create Button */}
                    <button
                      onClick={handleCreate}
                      disabled={!patient}
                      style={{
                        width: "100%", padding: "14px 20px", borderRadius: 12, border: "none",
                        background: patient ? "var(--accent)" : "var(--border)",
                        color: "#fff", fontSize: 14, fontWeight: 600, cursor: patient ? "pointer" : "default",
                        fontFamily: "var(--fb)", transition: "all 0.2s",
                        boxShadow: patient ? "0 4px 14px rgba(45,140,120,0.25)" : "none",
                      }}
                    >
                      {bookingMode === "all" ? "Create Plan & Book All Visits" : "Create Plan & Book First Visit"}
                    </button>
                    <div style={{ fontSize: 11, color: "var(--dim)", textAlign: "center", marginTop: 8 }}>
                      {bookingMode === "all" ? "All visits will sync to calendar" : "Patient books remaining visits individually"}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* ═══════════════════════════
             PLAN VIEW
             ═══════════════════════════ */}
          {view === "plan" && plan && (
            <div style={{ animation: "enter 0.3s ease" }}>
              {/* Plan Header */}
              <div style={{ marginBottom: 24 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
                  <div style={{ width: 7, height: 7, borderRadius: 4, background: "var(--accent)" }} />
                  <span style={{ fontSize: 10, fontWeight: 600, letterSpacing: "0.14em", textTransform: "uppercase", color: "var(--accent)" }}>Active Care Plan</span>
                </div>
                <h1 style={{ fontFamily: "var(--fh)", fontSize: 28, fontWeight: 600, letterSpacing: "-0.02em" }}>
                  {plan.patientName}
                </h1>
                <p style={{ fontSize: 13, color: "var(--dim)", marginTop: 4 }}>
                  {plan.frequency}× per week · {plan.weeks} weeks · {plan.totalVisits} visits · Started {formatDateLong(plan.startDate)}
                </p>
              </div>

              {/* Stats Bar */}
              <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 10, marginBottom: 16 }}>
                {[
                  { label: "Completed", value: stats.completed, total: plan.totalVisits, color: "var(--accent)" },
                  { label: "Booked", value: stats.booked, total: plan.totalVisits, color: "#3B82F6" },
                  { label: "Remaining", value: stats.remaining, total: plan.totalVisits, color: "var(--dim)" },
                  { label: "Missed", value: stats.missed, total: plan.totalVisits, color: "var(--danger)" },
                ].map((s) => (
                  <div key={s.label} style={{ background: "var(--surface)", borderRadius: 12, border: "1px solid var(--border)", padding: "16px 18px" }}>
                    <div style={{ fontSize: 24, fontWeight: 700, fontFamily: "var(--fh)", color: s.color }}>{s.value}</div>
                    <div style={{ fontSize: 11, color: "var(--dim)", marginTop: 2 }}>{s.label}</div>
                    {/* Progress bar */}
                    <div style={{ height: 3, borderRadius: 2, background: "var(--surface-alt)", marginTop: 8 }}>
                      <div style={{ height: 3, borderRadius: 2, background: s.color, width: `${(s.value / s.total) * 100}%`, transition: "width 0.3s" }} />
                    </div>
                  </div>
                ))}
              </div>

              {/* Book Next (if as-you-go) */}
              {stats.nextUnbooked && (
                <div style={{
                  background: "rgba(45,140,120,0.06)", border: "1.5px solid rgba(45,140,120,0.2)",
                  borderRadius: 14, padding: "16px 22px", marginBottom: 16,
                  display: "flex", alignItems: "center", justifyContent: "space-between",
                }}>
                  <div>
                    <div style={{ fontSize: 14, fontWeight: 600, color: "var(--text)" }}>
                      Next unbooked: {stats.nextUnbooked.label}
                    </div>
                    <div style={{ fontSize: 12, color: "var(--dim)", marginTop: 2 }}>
                      Suggested date: {formatDate(stats.nextUnbooked.date)} · {stats.nextUnbooked.duration} min · £{stats.nextUnbooked.fee}
                    </div>
                  </div>
                  <button
                    onClick={handleBookNext}
                    style={{
                      padding: "10px 20px", borderRadius: 10, border: "none",
                      background: "var(--accent)", color: "#fff", fontSize: 13,
                      fontWeight: 600, cursor: "pointer", fontFamily: "var(--fb)",
                    }}
                  >
                    Book This Visit
                  </button>
                </div>
              )}

              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, alignItems: "start" }}>
                {/* Visit List */}
                <div>
                  <div style={{ fontSize: 10, fontWeight: 600, letterSpacing: "0.1em", textTransform: "uppercase", color: "var(--dim)", marginBottom: 10 }}>
                    All Visits ({plan.totalVisits})
                  </div>
                  <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                    {plan.visits.map((v, idx) => {
                      const meta = TYPE_META[v.type];
                      const isSelected = selectedVisit === idx;
                      return (
                        <button
                          key={idx}
                          onClick={() => setSelectedVisit(isSelected ? null : idx)}
                          style={{
                            display: "flex", alignItems: "center", gap: 12,
                            padding: "12px 16px", borderRadius: 12, textAlign: "left", cursor: "pointer",
                            border: isSelected ? `2px solid ${meta.color}` : "1px solid var(--border)",
                            background: isSelected ? meta.bg : "var(--surface)",
                            transition: "all 0.15s", width: "100%",
                            opacity: v.status === "missed" ? 0.5 : 1,
                          }}
                        >
                          {/* Visit number circle */}
                          <div style={{
                            width: 32, height: 32, borderRadius: 8, flexShrink: 0,
                            background: v.status === "completed" ? meta.color : meta.bg,
                            color: v.status === "completed" ? "#fff" : meta.color,
                            display: "flex", alignItems: "center", justifyContent: "center",
                            fontSize: 12, fontWeight: 700,
                          }}>
                            {v.status === "completed" ? "✓" : v.number}
                          </div>
                          <div style={{ flex: 1, minWidth: 0 }}>
                            <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                              <span style={{ fontSize: 13, fontWeight: 600, color: "var(--text)" }}>
                                Visit {v.number}
                              </span>
                              <span style={{
                                fontSize: 9, fontWeight: 600, padding: "2px 7px", borderRadius: 4,
                                background: meta.bg, color: meta.color, textTransform: "uppercase", letterSpacing: "0.04em",
                              }}>
                                {meta.tagLabel}
                              </span>
                            </div>
                            <div style={{ fontSize: 11, color: "var(--dim)", marginTop: 2 }}>
                              {v.booked ? formatDate(v.date) : "Not yet booked"} · {v.duration} min · £{v.fee}
                            </div>
                          </div>
                          {/* Status indicator */}
                          <div style={{
                            width: 8, height: 8, borderRadius: 4, flexShrink: 0,
                            background: v.status === "completed" ? "var(--accent)"
                              : v.status === "scheduled" ? "#3B82F6"
                              : v.status === "missed" ? "var(--danger)"
                              : "var(--border)",
                          }} />
                        </button>
                      );
                    })}
                  </div>
                </div>

                {/* Right side — Calendar + Detail */}
                <div style={{ position: "sticky", top: 80 }}>
                  {/* Calendar Sync View */}
                  <div style={{
                    background: "var(--surface)", borderRadius: 14, border: "1px solid var(--border)",
                    padding: "20px 22px", marginBottom: 12,
                  }}>
                    <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 16 }}>
                      <div style={{ fontSize: 10, fontWeight: 600, letterSpacing: "0.1em", textTransform: "uppercase", color: "var(--dim)" }}>
                        Calendar Sync
                      </div>
                      <div style={{
                        fontSize: 10, fontWeight: 600, padding: "3px 10px", borderRadius: 20,
                        background: "rgba(59,130,246,0.08)", color: "#3B82F6",
                      }}>
                        {stats.booked} / {plan.totalVisits} synced
                      </div>
                    </div>
                    <div style={{ display: "grid", gridTemplateColumns: calendarMonths.length > 2 ? "repeat(2, 1fr)" : `repeat(${calendarMonths.length}, 1fr)`, gap: 16 }}>
                      {calendarMonths.map((m) => (
                        <CalendarMonth
                          key={`${m.year}-${m.month}`}
                          year={m.year}
                          month={m.month}
                          visits={plan.visits.filter((v) => v.booked)}
                        />
                      ))}
                    </div>
                  </div>

                  {/* Visit Detail */}
                  {selectedVisit !== null && (
                    <div style={{
                      background: "var(--surface)", borderRadius: 14, border: "1px solid var(--border)",
                      padding: "20px 22px", animation: "enter 0.2s ease",
                    }}>
                      {(() => {
                        const v = plan.visits[selectedVisit];
                        const meta = TYPE_META[v.type];
                        return (
                          <>
                            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 12 }}>
                              <span style={{ fontSize: 16, fontWeight: 700, fontFamily: "var(--fh)", color: meta.color }}>{v.label}</span>
                            </div>
                            <div style={{ background: "var(--surface-alt)", borderRadius: 10, padding: "14px 16px", marginBottom: 14 }}>
                              {[
                                { l: "Date", v: v.booked ? formatDateLong(v.date) : "Not yet booked" },
                                { l: "Type", v: meta.tagLabel },
                                { l: "Duration", v: `${v.duration} minutes` },
                                { l: "Fee", v: `£${v.fee}` },
                                { l: "Status", v: v.status.charAt(0).toUpperCase() + v.status.slice(1) },
                              ].map((row) => (
                                <div key={row.l} style={{ display: "flex", justifyContent: "space-between", padding: "5px 0", borderBottom: "1px solid var(--border)" }}>
                                  <span style={{ fontSize: 12, color: "var(--dim)" }}>{row.l}</span>
                                  <span style={{ fontSize: 12, fontWeight: 500, color: "var(--text)" }}>{row.v}</span>
                                </div>
                              ))}
                            </div>
                            {v.type === "progress-check" && (
                              <div style={{ background: "rgba(217,119,6,0.06)", border: "1px solid rgba(217,119,6,0.15)", borderRadius: 8, padding: "10px 14px", marginBottom: 14, fontSize: 12, color: "var(--dim)", lineHeight: 1.5 }}>
                                <strong style={{ color: "var(--warn)" }}>Progress Check:</strong> Re-administer outcome measures (NDI/ODI/QuickDASH), compare against MCID thresholds, review treatment goals.
                              </div>
                            )}
                            {v.type === "reassessment" && (
                              <div style={{ background: "rgba(124,58,237,0.06)", border: "1px solid rgba(124,58,237,0.15)", borderRadius: 8, padding: "10px 14px", marginBottom: 14, fontSize: 12, color: "var(--dim)", lineHeight: 1.5 }}>
                                <strong style={{ color: "var(--purple)" }}>Reassessment:</strong> Full re-examination with all outcome measures. Determine discharge, maintenance plan, or new care plan.
                              </div>
                            )}
                            {v.status === "scheduled" && (
                              <div style={{ display: "flex", gap: 8 }}>
                                <button onClick={() => handleComplete(selectedVisit)} style={{ flex: 1, padding: "10px 14px", borderRadius: 8, border: "none", background: "var(--accent)", color: "#fff", fontSize: 12, fontWeight: 600, cursor: "pointer", fontFamily: "var(--fb)" }}>
                                  Mark Complete
                                </button>
                                <button onClick={() => handleMiss(selectedVisit)} style={{ flex: 1, padding: "10px 14px", borderRadius: 8, border: "1px solid var(--danger)", background: "rgba(229,72,77,0.06)", color: "var(--danger)", fontSize: 12, fontWeight: 600, cursor: "pointer", fontFamily: "var(--fb)" }}>
                                  Mark Missed
                                </button>
                              </div>
                            )}
                          </>
                        );
                      })()}
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </>
  );
}
