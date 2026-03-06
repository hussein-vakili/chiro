import { useState, useMemo } from "react";

const CATEGORIES = [
  {
    id: "savings",
    title: "What You Have",
    icon: "💰",
    color: "#16a34a",
    fields: [
      { id: "cash_savings", label: "Cash savings available", default: 0 },
      { id: "investments_liquid", label: "Investments you can liquidate", default: 0 },
      { id: "loan_approved", label: "Business loan (approved or expected)", default: 0 },
      { id: "family_investment", label: "Family / friends investment", default: 0 },
      { id: "other_funds", label: "Other funds", default: 0 },
    ],
  },
  {
    id: "setup",
    title: "One-Time Setup Costs",
    icon: "🏗️",
    color: "#dc2626",
    note: "Based on UK chiropractic clinic data. Room-in-clinic route can halve these.",
    fields: [
      { id: "lease_deposit", label: "Lease deposit + first 2 months' rent", default: 3600, source: "UK treatment rooms: £800–1,500/mo outside London, £1,200–2,500/mo London" },
      { id: "buildout", label: "Clinic buildout / fit-out", default: 8000, source: "Basic renovation: paint, flooring, plumbing — UK avg for small clinic space" },
      { id: "treatment_table", label: "Treatment table (electric hi-lo)", default: 3500, source: "Quality electric hi-lo tables range £2,000–5,000 in the UK" },
      { id: "other_equipment", label: "Other clinical equipment", default: 2000, source: "Goniometer, neuro kit, BP cuff, rehab tools, posture grid" },
      { id: "tech_hardware", label: "Computer, tablet, card terminal", default: 1500, source: "Laptop ~£600, tablet ~£400, SumUp/Square terminal ~£50–100, printer etc." },
      { id: "signage_branding", label: "Signage & branding", default: 2000, source: "External clinic sign, logo design, print materials" },
      { id: "legal_accounting", label: "Legal & accounting setup", default: 1500, source: "Ltd company formation + solicitor lease review + accountant initial setup" },
      { id: "website", label: "Website build", default: 1500, source: "Professional site with booking: £500 DIY to £3,000+ agency" },
      { id: "initial_marketing", label: "Initial marketing push (3 months)", default: 2000, source: "Google Ads launch, printed materials, social media setup" },
      { id: "gcc_registration", label: "GCC registration & BCA membership", default: 800, source: "GCC annual retention ~£800, BCA membership ~£600–900 (includes insurance)" },
      { id: "other_setup", label: "Other setup costs", default: 1000, source: "Contingency — clinical waste contract deposit, fire safety, DBS check" },
    ],
  },
  {
    id: "monthly",
    title: "Monthly Running Costs",
    icon: "📅",
    color: "#ea580c",
    note: "Typical UK solo chiropractic clinic outside London.",
    fields: [
      { id: "rent", label: "Rent", default: 1200, source: "UK avg clinic room/small unit: £800–1,500 outside London, higher in London" },
      { id: "utilities", label: "Utilities (electric, water, internet)", default: 250, source: "Small commercial unit avg ~£200–350/mo" },
      { id: "insurance_monthly", label: "Insurance (all types, monthly)", default: 150, source: "PI via BCA ~£50–75/mo, public liability ~£20–40, contents/cyber ~£30–50" },
      { id: "software", label: "Software & subscriptions", default: 100, source: "PMS like Cliniko ~£45–95/mo, email tool, accounting software" },
      { id: "marketing_monthly", label: "Marketing (ongoing)", default: 400, source: "Google Ads £300–500/mo recommended for new clinics + social/content" },
      { id: "supplies", label: "Clinical supplies & consumables", default: 100, source: "Couch roll, gloves, disinfectant, rehab supplies" },
      { id: "accountant", label: "Accountant / bookkeeper", default: 150, source: "UK avg for small business: £100–250/mo" },
      { id: "cleaning", label: "Cleaning", default: 120, source: "Professional cleaner 3x/week for small clinic" },
      { id: "phone", label: "Phone / comms", default: 50, source: "Business mobile + VoIP/landline" },
      { id: "loan_repayment", label: "Loan repayment (monthly)", default: 0, source: "Depends on borrowing — enter your own figure" },
      { id: "clinical_waste", label: "Clinical waste disposal", default: 40, source: "Monthly collection contract for small clinic" },
      { id: "cpd", label: "CPD & professional development (monthly)", default: 80, source: "GCC requires 30hrs CPD/yr — courses, seminars, materials" },
      { id: "other_monthly", label: "Other monthly costs", default: 100, source: "Contingency — parking, misc subscriptions" },
    ],
  },
  {
    id: "personal",
    title: "Personal Monthly Costs",
    icon: "🏠",
    color: "#7c3aed",
    note: "Your personal burn rate. Be honest — most people underestimate by 20–30%.",
    fields: [
      { id: "personal_rent", label: "Rent / mortgage", default: 0 },
      { id: "personal_bills", label: "Bills & utilities & council tax", default: 0 },
      { id: "personal_food", label: "Food & groceries", default: 0 },
      { id: "personal_transport", label: "Transport (car, fuel, public)", default: 0 },
      { id: "personal_insurance", label: "Personal insurance & pension", default: 0 },
      { id: "personal_other", label: "Everything else (subs, phone, etc.)", default: 0 },
    ],
  },
  {
    id: "revenue",
    title: "Revenue Assumptions",
    icon: "📈",
    color: "#0284c7",
    note: "UK avg: initial consult £65–100, follow-ups £40–65. London: £80–140 / £50–90.",
    fields: [
      { id: "initial_consult_fee", label: "Initial consultation fee (£)", default: 75, source: "UK avg £65–100 for 45–60min initial assessment" },
      { id: "followup_fee", label: "Follow-up visit fee (£)", default: 45, source: "UK avg £35–65 for 15–30min follow-up treatment" },
      { id: "avg_visits_week_m1", label: "Expected visits/week — Month 1", default: 8, source: "Realistic for new clinic: 5–10 visits/wk" },
      { id: "avg_visits_week_m3", label: "Expected visits/week — Month 3", default: 15, source: "Moderate growth: 12–20 visits/wk" },
      { id: "avg_visits_week_m6", label: "Expected visits/week — Month 6", default: 25, source: "Good trajectory: 20–30 visits/wk approaching break-even" },
      { id: "avg_visits_week_m12", label: "Expected visits/week — Month 12", default: 35, source: "Mature solo practice: 30–45 visits/wk" },
    ],
  },
];

function formatCurrency(val) {
  return "£" + Math.round(val).toLocaleString("en-GB");
}

function GaugeBar({ value, max, label, color }) {
  const pct = max > 0 ? Math.min((value / max) * 100, 100) : 0;
  return (
    <div style={{ marginBottom: 12 }}>
      <div style={{ display: "flex", justifyContent: "space-between", fontSize: 13, marginBottom: 4, fontFamily: "'DM Sans', sans-serif" }}>
        <span style={{ color: "#94a3b8" }}>{label}</span>
        <span style={{ color: color, fontWeight: 700 }}>{formatCurrency(value)}</span>
      </div>
      <div style={{ height: 8, background: "#1e293b", borderRadius: 99, overflow: "hidden" }}>
        <div style={{ width: `${pct}%`, height: "100%", background: color, borderRadius: 99, transition: "width 0.5s ease" }} />
      </div>
    </div>
  );
}

function SourceTooltip({ text }) {
  const [show, setShow] = useState(false);
  return (
    <span style={{ position: "relative", display: "inline-block" }}>
      <span
        onMouseEnter={() => setShow(true)}
        onMouseLeave={() => setShow(false)}
        onClick={() => setShow(!show)}
        style={{
          display: "inline-flex", alignItems: "center", justifyContent: "center",
          width: 16, height: 16, borderRadius: 99, background: "#334155", color: "#94a3b8",
          fontSize: 10, cursor: "pointer", marginLeft: 6, fontWeight: 700, flexShrink: 0,
        }}
      >i</span>
      {show && (
        <div style={{
          position: "absolute", bottom: "calc(100% + 6px)", left: "50%", transform: "translateX(-50%)",
          background: "#1e293b", border: "1px solid #475569", borderRadius: 8, padding: "8px 12px",
          fontSize: 11, color: "#cbd5e1", width: 240, zIndex: 100, lineHeight: 1.4,
          boxShadow: "0 4px 20px rgba(0,0,0,0.4)",
        }}>
          {text}
          <div style={{ position: "absolute", bottom: -5, left: "50%", transform: "translateX(-50%) rotate(45deg)", width: 8, height: 8, background: "#1e293b", borderRight: "1px solid #475569", borderBottom: "1px solid #475569" }} />
        </div>
      )}
    </span>
  );
}

function CategorySection({ category, values, onChange, expanded, onToggle }) {
  const total = category.fields.reduce((sum, f) => sum + (values[f.id] || 0), 0);
  return (
    <div style={{
      background: "#0f172a",
      border: "1px solid #1e293b",
      borderRadius: 12,
      marginBottom: 12,
      overflow: "hidden",
    }}>
      <button
        onClick={onToggle}
        style={{
          width: "100%",
          padding: "16px 20px",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          background: "transparent",
          border: "none",
          cursor: "pointer",
          color: "#e2e8f0",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <span style={{ fontSize: 22 }}>{category.icon}</span>
          <span style={{ fontSize: 16, fontWeight: 700, fontFamily: "'DM Sans', sans-serif" }}>{category.title}</span>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <span style={{ fontSize: 16, fontWeight: 700, color: category.color, fontFamily: "'DM Mono', monospace" }}>
            {formatCurrency(total)}
          </span>
          <span style={{ fontSize: 18, color: "#64748b", transform: expanded ? "rotate(180deg)" : "rotate(0)", transition: "transform 0.2s" }}>▾</span>
        </div>
      </button>
      {expanded && (
        <div style={{ padding: "0 20px 20px" }}>
          {category.note && (
            <div style={{ fontSize: 12, color: "#64748b", marginBottom: 14, padding: "8px 12px", background: "#1e293b", borderRadius: 8, lineHeight: 1.5 }}>
              {category.note}
            </div>
          )}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(240px, 1fr))", gap: 10 }}>
            {category.fields.map((field) => (
              <div key={field.id} style={{ display: "flex", flexDirection: "column", gap: 4 }}>
                <label style={{ fontSize: 12, color: "#94a3b8", fontFamily: "'DM Sans', sans-serif", display: "flex", alignItems: "center" }}>
                  {field.label}
                  {field.source && <SourceTooltip text={field.source} />}
                </label>
                <div style={{ position: "relative" }}>
                  <span style={{ position: "absolute", left: 12, top: "50%", transform: "translateY(-50%)", color: "#64748b", fontSize: 14, fontFamily: "'DM Mono', monospace" }}>£</span>
                  <input
                    type="number"
                    value={values[field.id] === 0 && category.id === "personal" ? "" : values[field.id] || ""}
                    placeholder={field.default > 0 ? String(field.default) : "0"}
                    onChange={(e) => onChange(field.id, parseFloat(e.target.value) || 0)}
                    style={{
                      width: "100%",
                      padding: "10px 12px 10px 28px",
                      background: "#1e293b",
                      border: "1px solid #334155",
                      borderRadius: 8,
                      color: "#e2e8f0",
                      fontSize: 15,
                      fontFamily: "'DM Mono', monospace",
                      outline: "none",
                      boxSizing: "border-box",
                    }}
                    onFocus={(e) => e.target.style.borderColor = category.color}
                    onBlur={(e) => e.target.style.borderColor = "#334155"}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export default function ClinicCalculator() {
  const [values, setValues] = useState(() => {
    const init = {};
    CATEGORIES.forEach(c => c.fields.forEach(f => init[f.id] = f.default));
    return init;
  });
  const [expanded, setExpanded] = useState({ savings: true, setup: true, monthly: false, personal: false, revenue: false });
  const [runwayMonths, setRunwayMonths] = useState(6);

  const handleChange = (id, val) => setValues(prev => ({ ...prev, [id]: val }));
  const toggleSection = (id) => setExpanded(prev => ({ ...prev, [id]: !prev[id] }));

  const analysis = useMemo(() => {
    const totalFunds = CATEGORIES.find(c => c.id === "savings").fields.reduce((s, f) => s + (values[f.id] || 0), 0);
    const totalSetup = CATEGORIES.find(c => c.id === "setup").fields.reduce((s, f) => s + (values[f.id] || 0), 0);
    const monthlyBiz = CATEGORIES.find(c => c.id === "monthly").fields.reduce((s, f) => s + (values[f.id] || 0), 0);
    const monthlyPersonal = CATEGORIES.find(c => c.id === "personal").fields.reduce((s, f) => s + (values[f.id] || 0), 0);
    const totalMonthly = monthlyBiz + monthlyPersonal;

    const afterSetup = totalFunds - totalSetup;
    const runwayAfterSetup = totalMonthly > 0 ? Math.floor(afterSetup / totalMonthly) : afterSetup > 0 ? 99 : 0;
    const neededForRunway = totalSetup + (totalMonthly * runwayMonths);
    const shortfall = Math.max(0, neededForRunway - totalFunds);
    const surplus = Math.max(0, totalFunds - neededForRunway);

    const followupFee = values.followup_fee || 0;
    const initialFee = values.initial_consult_fee || 0;
    const m1Weekly = values.avg_visits_week_m1 || 0;
    const m3Weekly = values.avg_visits_week_m3 || 0;
    const m6Weekly = values.avg_visits_week_m6 || 0;
    const m12Weekly = values.avg_visits_week_m12 || 0;

    const blendedRate = (initPct, wkly) => (wkly * initPct * initialFee + wkly * (1 - initPct) * followupFee) * 4.33;
    const m1Revenue = blendedRate(0.3, m1Weekly);
    const m3Revenue = blendedRate(0.2, m3Weekly);
    const m6Revenue = blendedRate(0.12, m6Weekly);
    const m12Revenue = blendedRate(0.08, m12Weekly);

    const breakEvenVisits = followupFee > 0 ? Math.ceil(monthlyBiz / followupFee / 4.33) : 0;
    const breakEvenTotal = totalMonthly > 0 && followupFee > 0 ? Math.ceil(totalMonthly / followupFee / 4.33) : 0;

    let breakEvenMonth = null;
    if (totalMonthly > 0 && m12Revenue > 0) {
      for (let m = 1; m <= 24; m++) {
        let wk, initPct;
        if (m <= 1) { wk = m1Weekly; initPct = 0.3; }
        else if (m <= 3) { wk = m1Weekly + (m3Weekly - m1Weekly) * ((m - 1) / 2); initPct = 0.25; }
        else if (m <= 6) { wk = m3Weekly + (m6Weekly - m3Weekly) * ((m - 3) / 3); initPct = 0.15; }
        else { wk = m6Weekly + (m12Weekly - m6Weekly) * Math.min((m - 6) / 6, 1); initPct = 0.1; }
        const rev = blendedRate(initPct, wk);
        if (rev >= totalMonthly && !breakEvenMonth) { breakEvenMonth = m; }
      }
    }

    let yr1Revenue = 0;
    for (let m = 1; m <= 12; m++) {
      let wk, initPct;
      if (m <= 1) { wk = m1Weekly; initPct = 0.3; }
      else if (m <= 3) { wk = m1Weekly + (m3Weekly - m1Weekly) * ((m - 1) / 2); initPct = 0.25; }
      else if (m <= 6) { wk = m3Weekly + (m6Weekly - m3Weekly) * ((m - 3) / 3); initPct = 0.15; }
      else { wk = m6Weekly + (m12Weekly - m6Weekly) * Math.min((m - 6) / 6, 1); initPct = 0.1; }
      yr1Revenue += blendedRate(initPct, wk);
    }
    const yr1Costs = totalSetup + (monthlyBiz * 12);
    const yr1Profit = yr1Revenue - yr1Costs;

    return {
      totalFunds, totalSetup, monthlyBiz, monthlyPersonal, totalMonthly,
      afterSetup, runwayAfterSetup, neededForRunway, shortfall, surplus,
      m1Revenue, m3Revenue, m6Revenue, m12Revenue,
      breakEvenVisits, breakEvenTotal, breakEvenMonth,
      yr1Revenue, yr1Costs, yr1Profit, followupFee
    };
  }, [values, runwayMonths]);

  const healthScore = useMemo(() => {
    if (analysis.totalFunds === 0) return { label: "Enter your savings to see the analysis", color: "#64748b" };
    if (analysis.shortfall > 0 && analysis.runwayAfterSetup < 3) return { label: "Underfunded — high risk without changes", color: "#dc2626" };
    if (analysis.shortfall > 0) return { label: "Tight — you'll need revenue fast or more capital", color: "#ea580c" };
    if (analysis.runwayAfterSetup < 4) return { label: "Workable — but almost no margin for error", color: "#ea580c" };
    if (analysis.runwayAfterSetup < 7) return { label: "Decent — enough if you execute well", color: "#eab308" };
    if (analysis.runwayAfterSetup < 12) return { label: "Solid — good position to launch", color: "#16a34a" };
    return { label: "Strong — comfortable runway", color: "#059669" };
  }, [analysis]);

  const hasData = analysis.totalFunds > 0;

  return (
    <div style={{
      minHeight: "100vh",
      background: "#020617",
      color: "#e2e8f0",
      fontFamily: "'DM Sans', sans-serif",
      padding: "24px 16px",
    }}>
      <link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;700&family=DM+Mono:wght@400;500&display=swap" rel="stylesheet" />

      <div style={{ maxWidth: 900, margin: "0 auto" }}>
        <div style={{ textAlign: "center", marginBottom: 32 }}>
          <h1 style={{ fontSize: 28, fontWeight: 700, margin: 0, letterSpacing: "-0.5px" }}>Clinic Startup Calculator</h1>
          <p style={{ color: "#64748b", fontSize: 14, marginTop: 6 }}>Defaults are UK market data (2024–25). Hover the <span style={{display:"inline-flex",alignItems:"center",justifyContent:"center",width:16,height:16,borderRadius:99,background:"#334155",color:"#94a3b8",fontSize:10,fontWeight:700}}>i</span> icons for sources. Replace with your real numbers.</p>
        </div>

        {CATEGORIES.map(cat => (
          <CategorySection key={cat.id} category={cat} values={values} onChange={handleChange} expanded={expanded[cat.id]} onToggle={() => toggleSection(cat.id)} />
        ))}

        <div style={{ background: "#0f172a", border: "1px solid #1e293b", borderRadius: 12, padding: 20, marginBottom: 12 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
            <span style={{ fontSize: 14, color: "#94a3b8" }}>Desired months of runway</span>
            <span style={{ fontSize: 20, fontWeight: 700, color: "#e2e8f0", fontFamily: "'DM Mono', monospace" }}>{runwayMonths} months</span>
          </div>
          <input type="range" min={3} max={18} value={runwayMonths} onChange={(e) => setRunwayMonths(parseInt(e.target.value))} style={{ width: "100%", accentColor: "#0284c7" }} />
          <div style={{ display: "flex", justifyContent: "space-between", fontSize: 11, color: "#475569", marginTop: 4 }}>
            <span>3 (risky)</span><span>6 (minimum)</span><span>12 (safe)</span><span>18 (ideal)</span>
          </div>
        </div>

        {hasData && (
          <div style={{ background: "linear-gradient(135deg, #0f172a 0%, #1a1f35 100%)", border: `2px solid ${healthScore.color}40`, borderRadius: 16, padding: 28, marginTop: 24 }}>
            <div style={{ textAlign: "center", marginBottom: 28 }}>
              <div style={{ display: "inline-block", padding: "6px 20px", borderRadius: 99, background: `${healthScore.color}18`, border: `1px solid ${healthScore.color}50`, color: healthScore.color, fontSize: 15, fontWeight: 700 }}>
                {healthScore.label}
              </div>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: 16, marginBottom: 28 }}>
              {[
                { label: "Total Available", value: analysis.totalFunds, color: "#16a34a" },
                { label: "Setup Costs", value: analysis.totalSetup, color: "#dc2626" },
                { label: "Left After Setup", value: analysis.afterSetup, color: analysis.afterSetup >= 0 ? "#16a34a" : "#dc2626" },
                { label: `Need for ${runwayMonths}mo Runway`, value: analysis.neededForRunway, color: "#0284c7" },
              ].map((item, i) => (
                <div key={i} style={{ background: "#020617", borderRadius: 12, padding: 16, textAlign: "center" }}>
                  <div style={{ fontSize: 11, color: "#64748b", textTransform: "uppercase", letterSpacing: "1px", marginBottom: 6 }}>{item.label}</div>
                  <div style={{ fontSize: 24, fontWeight: 700, color: item.color, fontFamily: "'DM Mono', monospace" }}>{formatCurrency(item.value)}</div>
                </div>
              ))}
            </div>

            <GaugeBar value={analysis.totalSetup} max={analysis.totalFunds} label="Setup costs (of total funds)" color="#dc2626" />
            <GaugeBar value={analysis.monthlyBiz} max={analysis.totalMonthly || 1} label="Business costs (of total monthly burn)" color="#ea580c" />
            <GaugeBar value={analysis.monthlyPersonal} max={analysis.totalMonthly || 1} label="Personal costs (of total monthly burn)" color="#7c3aed" />

            <div style={{ background: "#020617", borderRadius: 12, padding: 20, margin: "20px 0", borderLeft: `4px solid ${analysis.runwayAfterSetup >= runwayMonths ? "#16a34a" : "#dc2626"}` }}>
              <div style={{ fontSize: 13, color: "#94a3b8", marginBottom: 4 }}>After setup costs, you can survive for:</div>
              <div style={{ fontSize: 36, fontWeight: 700, fontFamily: "'DM Mono', monospace", color: analysis.runwayAfterSetup >= runwayMonths ? "#16a34a" : "#dc2626" }}>
                {analysis.totalMonthly > 0 ? `${analysis.runwayAfterSetup} months` : "Enter personal costs ↑"}
              </div>
              <div style={{ fontSize: 13, color: "#64748b", marginTop: 4 }}>
                with zero patients ({formatCurrency(analysis.totalMonthly)}/mo burn: {formatCurrency(analysis.monthlyBiz)} business + {formatCurrency(analysis.monthlyPersonal)} personal)
              </div>
            </div>

            {analysis.shortfall > 0 && (
              <div style={{ background: "#dc262615", border: "1px solid #dc262640", borderRadius: 12, padding: 20, marginBottom: 20 }}>
                <div style={{ fontSize: 14, fontWeight: 700, color: "#dc2626", marginBottom: 6 }}>Funding Gap</div>
                <div style={{ fontSize: 13, color: "#e2e8f0", lineHeight: 1.6 }}>
                  You're <strong style={{ color: "#dc2626", fontFamily: "'DM Mono', monospace" }}>{formatCurrency(analysis.shortfall)}</strong> short of setup + {runwayMonths} months.
                  Options: start in a room within an existing clinic (cuts setup ~50%), reduce buildout, secure a startup loan, or save longer before launching.
                </div>
              </div>
            )}
            {analysis.surplus > 0 && (
              <div style={{ background: "#16a34a15", border: "1px solid #16a34a40", borderRadius: 12, padding: 20, marginBottom: 20 }}>
                <div style={{ fontSize: 14, fontWeight: 700, color: "#16a34a", marginBottom: 6 }}>You're Funded</div>
                <div style={{ fontSize: 13, color: "#e2e8f0", lineHeight: 1.6 }}>
                  <strong style={{ color: "#16a34a", fontFamily: "'DM Mono', monospace" }}>{formatCurrency(analysis.surplus)}</strong> buffer beyond setup + {runwayMonths} months. Keep it as emergency reserves.
                </div>
              </div>
            )}

            {analysis.followupFee > 0 && (
              <div style={{ background: "#020617", borderRadius: 12, padding: 20, borderLeft: "4px solid #0284c7" }}>
                <div style={{ fontSize: 14, fontWeight: 700, color: "#0284c7", marginBottom: 16 }}>Revenue Projections & Break-Even</div>
                <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(120px, 1fr))", gap: 12, marginBottom: 20 }}>
                  {[
                    { label: "Month 1", value: analysis.m1Revenue, compare: analysis.monthlyBiz },
                    { label: "Month 3", value: analysis.m3Revenue, compare: analysis.monthlyBiz },
                    { label: "Month 6", value: analysis.m6Revenue, compare: analysis.totalMonthly },
                    { label: "Month 12", value: analysis.m12Revenue, compare: analysis.totalMonthly },
                  ].map((p, i) => (
                    <div key={i} style={{ textAlign: "center" }}>
                      <div style={{ fontSize: 11, color: "#64748b", textTransform: "uppercase", letterSpacing: "1px" }}>{p.label}</div>
                      <div style={{ fontSize: 20, fontWeight: 700, color: p.value >= p.compare ? "#16a34a" : "#ea580c", fontFamily: "'DM Mono', monospace" }}>{formatCurrency(p.value)}</div>
                      <div style={{ fontSize: 11, color: "#64748b" }}>/mo revenue</div>
                    </div>
                  ))}
                </div>
                <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))", gap: 12, marginBottom: 16 }}>
                  <div style={{ background: "#0f172a", borderRadius: 8, padding: 14, textAlign: "center" }}>
                    <div style={{ fontSize: 11, color: "#64748b", textTransform: "uppercase", letterSpacing: "1px" }}>Break-even (biz costs)</div>
                    <div style={{ fontSize: 22, fontWeight: 700, color: "#e2e8f0", fontFamily: "'DM Mono', monospace" }}>{analysis.breakEvenVisits}/wk</div>
                  </div>
                  <div style={{ background: "#0f172a", borderRadius: 8, padding: 14, textAlign: "center" }}>
                    <div style={{ fontSize: 11, color: "#64748b", textTransform: "uppercase", letterSpacing: "1px" }}>Break-even (all costs)</div>
                    <div style={{ fontSize: 22, fontWeight: 700, color: "#e2e8f0", fontFamily: "'DM Mono', monospace" }}>{analysis.breakEvenTotal}/wk</div>
                  </div>
                  <div style={{ background: "#0f172a", borderRadius: 8, padding: 14, textAlign: "center" }}>
                    <div style={{ fontSize: 11, color: "#64748b", textTransform: "uppercase", letterSpacing: "1px" }}>Est. break-even month</div>
                    <div style={{ fontSize: 22, fontWeight: 700, color: analysis.breakEvenMonth && analysis.breakEvenMonth <= 12 ? "#16a34a" : "#ea580c", fontFamily: "'DM Mono', monospace" }}>
                      {analysis.breakEvenMonth ? `Month ${analysis.breakEvenMonth}` : "24+"}
                    </div>
                  </div>
                </div>
                <div style={{ background: "#0f172a", borderRadius: 8, padding: 16, marginTop: 12 }}>
                  <div style={{ fontSize: 13, fontWeight: 700, color: "#94a3b8", marginBottom: 10 }}>Year 1 Projection</div>
                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 12 }}>
                    <div>
                      <div style={{ fontSize: 11, color: "#64748b" }}>Revenue</div>
                      <div style={{ fontSize: 16, fontWeight: 700, color: "#16a34a", fontFamily: "'DM Mono', monospace" }}>{formatCurrency(analysis.yr1Revenue)}</div>
                    </div>
                    <div>
                      <div style={{ fontSize: 11, color: "#64748b" }}>Costs (setup + running)</div>
                      <div style={{ fontSize: 16, fontWeight: 700, color: "#dc2626", fontFamily: "'DM Mono', monospace" }}>{formatCurrency(analysis.yr1Costs)}</div>
                    </div>
                    <div>
                      <div style={{ fontSize: 11, color: "#64748b" }}>Net (before personal)</div>
                      <div style={{ fontSize: 16, fontWeight: 700, color: analysis.yr1Profit >= 0 ? "#16a34a" : "#dc2626", fontFamily: "'DM Mono', monospace" }}>
                        {analysis.yr1Profit >= 0 ? "" : "-"}{formatCurrency(Math.abs(analysis.yr1Profit))}
                      </div>
                    </div>
                  </div>
                </div>
                <div style={{ fontSize: 12, color: "#475569", marginTop: 12, lineHeight: 1.5 }}>
                  Revenue blends initial consultations (~30% month 1, dropping to ~8% by month 12) with follow-ups. Green = covering costs, orange = not yet.
                </div>
              </div>
            )}
          </div>
        )}

        {!hasData && (
          <div style={{ textAlign: "center", padding: 40, color: "#475569" }}>
            <div style={{ fontSize: 40, marginBottom: 12 }}>☝️</div>
            <div style={{ fontSize: 15 }}>Enter your savings in the first section to see the full analysis</div>
          </div>
        )}

        <div style={{ textAlign: "center", marginTop: 24, fontSize: 11, color: "#334155", lineHeight: 1.5 }}>
          Defaults based on UK chiropractic market data (2024–25). Fees reflect national averages outside London. This is a planning tool, not financial advice.
        </div>
      </div>
    </div>
  );
}
