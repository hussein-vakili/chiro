import { useState, useMemo } from "react";

// DATA PART 1: NECK + LOW BACK — Regions, Clusters, Tests, Conditions, Treatment Plans

const TX = {
  // ═══ NECK ═══
  cervical_radiculopathy: {
    session: [
      { t: "0–3", p: "Pain Modulation", tasks: ["Supine cervical traction (intermittent 5–10 lbs, 10s × 6)", "Assess irritability — high = Gr I–II only"] },
      { t: "3–8", p: "Manual Therapy", tasks: ["Cervical lateral glide mob (Gr III–IV) away from Sx side", "Thoracic HVLA T1–T4", "Neural mob — ULTT slider (NOT tensioner if acute)"] },
      { t: "8–12", p: "Exercise", tasks: ["Cervical retraction × 10", "DNF activation (CCF 10s × 5)", "Scapular setting / low trap activation"] },
      { t: "12–15", p: "Closure", tasks: ["Reassess Spurling's/ULTT — document", "HEP: retraction hourly, sliders 3×10 daily", "Ice 15 min if irritable"] }
    ],
    freq: "Acute: 3×/wk×2wk → 2×/wk×4wk → 1×/wk×2–4wk\nSubacute/Chronic: 2×/wk×4wk → 1×/wk×4–6wk",
    visits: "Acute: 12–16 visits / 8–10 wk\nChronic: 14–20 visits / 10–12 wk",
    prog: { t: "Nerve recovery is slow. 75–90% improve conservatively but full resolution takes 6–12 weeks.", e: "Acute: radicular reduction 2–4 wk, functional 6–8 wk. Chronic: 50% improvement by 6 wk, plateau by 12 wk. First improvement ~4 days.", f: "Better: <50yo, acute <6wk, single level, centralization. Worse: multilevel, progressive weakness, chronic >3mo." },
    outcomes: ["NDI", "NPRS", "ULTT angle", "Grip strength"],
    contras: [{ t: "Progressive neuro deficit → REFER", l: "r" }, { t: "Myelopathic signs → REFER", l: "r" }, { t: "CES equivalent → EMERGENT", l: "r" }],
    refer: "No improvement 6wk, progressive motor, bilateral → MRI + surgical",
    hep: ["Retraction hourly × 10", "ULTT sliders 3×10, 2×/day", "Scapular retraction iso 10s×10", "Avoid extension & overhead lifting"],
    reexam: {
      schedule: [
        { visit: "Visit 6 (~2 wk)", focus: "Initial response check" },
        { visit: "Visit 12 (~6 wk)", focus: "Formal re-examination" },
        { visit: "Discharge / Visit 16+", focus: "MMI or referral decision" }
      ],
      mcid: [
        { measure: "NDI", threshold: "≥7 points improvement", cite: "Young 2009" },
        { measure: "NPRS", threshold: "≥2 points decrease", cite: "Childs 2005" },
        { measure: "ULTT angle", threshold: "≥10° improvement" },
        { measure: "Grip strength", threshold: "≥20% increase from baseline" }
      ],
      onTrack: "NPRS ↓≥2 by visit 6, ULTT angle improving, radicular symptoms centralizing or retreating. Continue current plan, begin frequency taper.",
      offTrack: "NPRS unchanged or ↑ at visit 6, ULTT angle not improving, peripheralization persisting. Modify: reassess directional preference, consider imaging, change mobilization approach. If no NPRS or NDI change by visit 12 → refer for MRI + surgical consult.",
      warningSign: "Any progressive motor loss between re-exams, new myelopathic signs (gait, clonus), bilateral symptoms developing → STOP current plan, URGENT referral."
    }
  },
  cervicogenic_ha: {
    session: [
      { t: "0–3", p: "Assessment / Suboccipital Release", tasks: ["CFRT retest — document rotation", "SNAG C1–C2 if tolerated", "Suboccipital inhibition 2–3 min"] },
      { t: "3–8", p: "Manual Therapy", tasks: ["C1–C2 lateral glide (Gr III–IV) toward restriction", "UC HVLA (toggle/atlas) if stable", "C2–C3 unilateral PA mob"] },
      { t: "8–12", p: "Motor Control", tasks: ["CCF training (biofeedback 22–30mmHg, 10s × 10)", "Cervical flexor endurance (→30s hold)", "Extensor co-contraction with rotation"] },
      { t: "12–15", p: "Closure", tasks: ["Retest CFRT — document degrees gained", "HEP: CCF 3×/day, self-SNAG with towel", "Headache diary"] }
    ],
    freq: "2×/wk×3–4wk → 1×/wk×2–3wk → PRN",
    visits: "8–12 visits / 5–7 weeks",
    prog: { t: "Fast responder — improvement within 4–6 sessions. Motor control retraining is the longer phase.", e: "Acute: 50–70% HA reduction by 3 wk, near-resolution 5–6 wk. Chronic: 6–8 wk to plateau. CFRT should improve within 2–3 sessions.", f: "Better: isolated C1–C2, + CFRT. Worse: concurrent migraine, MOH, chronic >2yr." },
    outcomes: ["HIT-6", "HA freq/wk", "CFRT degrees", "NDI"],
    contras: [{ t: "UC instability (+ Sharp-Purser/alar)", l: "r" }, { t: "VBI symptoms with rotation", l: "r" }, { t: "Thunderclap onset → EMERGENT", l: "r" }],
    refer: "New HA >50yo, sudden severe, neuro signs, fever+stiffness → immediate medical",
    hep: ["CCF 10s×10, 3×/day", "Self-SNAG C1–C2 with towel 2×/day", "Chin tucks hourly", "Workstation ergonomics"],
    reexam: {
      schedule: [
        { visit: "Visit 4 (~2 wk)", focus: "CFRT + HA frequency response" },
        { visit: "Visit 8 (~4–5 wk)", focus: "Formal re-exam — discharge decision" }
      ],
      mcid: [
        { measure: "HIT-6", threshold: "≥6 points improvement", cite: "Smelt 2014" },
        { measure: "CFRT", threshold: "≥10° improvement toward normal (>33°)" },
        { measure: "HA frequency", threshold: "≥50% reduction from baseline" },
        { measure: "NDI", threshold: "≥7 points improvement" }
      ],
      onTrack: "CFRT improving by visit 4, HA frequency ↓≥30%. This is a fast responder — if CFRT is normalizing, taper quickly. Shift focus to motor control.",
      offTrack: "No CFRT change by visit 4, HA frequency unchanged. Reassess: is this actually migraine with cervical component? Screen for MOH. Consider concurrent migraine management. If no HIT-6 change by visit 8 → reconsider diagnosis.",
      warningSign: "New thunderclap onset, neurological signs developing, worsening with manipulation → STOP, medical referral."
    }
  },
  cervical_facet: {
    session: [
      { t: "0–3", p: "Assessment", tasks: ["Active ROM — restriction pattern", "Prone segmental palpation — fixated levels"] },
      { t: "3–8", p: "Manual Therapy", tasks: ["Cervical HVLA (diversified) at restricted segments", "Unilateral PA mob (Gr IV) at painful facets", "Thoracic HVLA T1–T6 for kinetic chain"] },
      { t: "8–12", p: "Soft Tissue / Exercise", tasks: ["MFR cervical paraspinals, UT", "Cervical iso (4-way) 10s holds", "Thoracic ext mobility (foam roller)"] },
      { t: "12–15", p: "Closure", tasks: ["Re-assess ext-rotation — document", "HEP: iso 3×/day, thoracic ext stretches", "Heat before HEP if chronic"] }
    ],
    freq: "Acute: 2–3×/wk×1–2wk → 1×/wk×2–3wk\nChronic: 2×/wk×3wk → 1×/wk×3–4wk",
    visits: "Acute: 6–8 visits / 3–4 wk\nChronic/DJD: 10–14 visits / 6–7 wk",
    prog: { t: "Fastest cervical responder — manipulation often produces immediate relief. If no response by visit 4, reconsider diagnosis.", e: "Acute: 60–80% pain reduction 1–2 wk, discharge 3–4 wk. Chronic/DJD: 50% by 3–4 wk, may need maintenance. Good first-visit response = best predictor.", f: "Better: acute <2wk, single level, immediate post-adjustment relief. Worse: multilevel DJD, chronic >3mo, prior failed injection." },
    outcomes: ["NDI", "NPRS", "C-ROM", "Ext-rotation test"],
    contras: [{ t: "Cervical instability", l: "y" }, { t: "Active RA with AA involvement", l: "r" }],
    refer: "No improvement 4–6 wk → facet injection or imaging",
    hep: ["Cervical iso (4-way) 3×/day", "Thoracic ext foam roller 2×/day", "Chin tucks hourly", "Avoid sustained flexion"],
    reexam: {
      schedule: [
        { visit: "Visit 3–4 (~1–2 wk)", focus: "Early response — should see change by now" },
        { visit: "Visit 6–8 (~3–4 wk)", focus: "Discharge or maintenance decision" }
      ],
      mcid: [
        { measure: "NDI", threshold: "≥7 points improvement", cite: "Young 2009" },
        { measure: "NPRS", threshold: "≥2 points decrease" },
        { measure: "Cervical ROM", threshold: "≥15° improvement in restricted direction" }
      ],
      onTrack: "NPRS ↓≥2 by visit 3, ext-rotation test improving or resolving, ROM gaining. This condition responds fast — if improving, begin taper immediately.",
      offTrack: "No NPRS or ROM change by visit 4 → this is NOT cervical facet. Reassess: disc? radiculopathy? myofascial? Re-run DDx. If facet is confirmed (imaging) but not responding → facet injection referral.",
      warningSign: "Developing radicular symptoms, increasing neurological signs → upgrade diagnosis. New bilateral symptoms → screen for myelopathy."
    }
  },
  cervical_disc: {
    session: [
      { t: "0–3", p: "Directional Preference", tasks: ["Repeated retraction × 10 — centralization?", "Centralizes → add extension", "Peripheralizes → lateral shift correction"] },
      { t: "3–8", p: "Manual Therapy", tasks: ["Flexion-distraction (decompression)", "Lateral glide if shift present", "Thoracic HVLA T2–T6 (avoid C-HVLA acute)"] },
      { t: "8–12", p: "McKenzie Protocol", tasks: ["End-range loading in DP × 10–15 reps", "DNF activation", "Seated retraction drill"] },
      { t: "12–15", p: "Closure", tasks: ["Re-assess centralization — document", "HEP: retraction q1–2h × 10", "Avoid flexion, pillow advice"] }
    ],
    freq: "Acute: daily or 4–5×/wk×1wk → 3×/wk×1–2wk → 2×/wk×2wk\nTaper aggressively once centralizing",
    visits: "Centralizers: 8–12 visits / 3–5 wk\nNon-centralizers: 10–16 visits / 6 wk max before referral",
    prog: { t: "Driven by centralization. Centralizers respond fast. No centralization by session 5 = image.", e: "Centralizers: 80%+ good outcome, pain reduction week 1, functional 3–5 wk. Antalgic resolving by session 2–3 = good sign.", f: "Better: clear DP, acute <4wk, <45yo, first episode. Worse: no centralization, chronic, prior episodes." },
    outcomes: ["NDI", "NPRS", "Centralization status", "C-ROM"],
    contras: [{ t: "Progressive neuro deficit", l: "r" }, { t: "Myelopathic signs → MRI", l: "r" }],
    refer: "No centralization after 5 sessions, progressive radiculopathy → MRI + surgical",
    hep: ["Retraction q1–2h × 10", "Retraction + ext if DP allows", "Avoid sustained flexion", "Cervical roll pillow"],
    reexam: {
      schedule: [
        { visit: "Visit 5 (~1–2 wk)", focus: "Centralization checkpoint — critical decision point" },
        { visit: "Visit 10 (~3–4 wk)", focus: "Functional re-exam if centralizing" }
      ],
      mcid: [
        { measure: "NDI", threshold: "≥7 points improvement" },
        { measure: "NPRS", threshold: "≥2 points decrease" },
        { measure: "Centralization", threshold: "Symptoms retreating proximally — THE key metric" }
      ],
      onTrack: "Centralizing by visit 3–5, NPRS ↓≥2, antalgic resolving. Taper frequency aggressively — centralization means the disc is loading correctly. Shift to self-management.",
      offTrack: "No centralization by visit 5 = STOP. This is your decision point. Options: (1) imaging, (2) surgical consult, (3) reassess if this is actually discogenic. Do not continue McKenzie without centralization response.",
      warningSign: "Peripheralization worsening despite modifications, new radicular symptoms developing, antalgic worsening → imaging + referral. Bilateral arm symptoms = possible myelopathy → URGENT."
    }
  },
  myofascial_neck: {
    session: [
      { t: "0–3", p: "Assessment", tasks: ["ID active TrPs — UT, levator, SCM, suboccipitals", "Document referral patterns, taut bands"] },
      { t: "3–9", p: "Soft Tissue", tasks: ["Ischemic compression 60–90s × 3–4 points", "IASTM cervical paraspinals", "PIR/MET restricted muscles", "Pin-and-stretch UT & levator"] },
      { t: "9–12", p: "Corrective Exercise", tasks: ["Chin tuck + scapular retraction (FHP)", "Pec minor stretch 30s × 3", "Low trap activation (Y/T raises)"] },
      { t: "12–15", p: "Closure", tasks: ["Re-palpate TrPs — document reduction", "HEP: self-release, stretching", "Address perpetuating factors"] }
    ],
    freq: "Acute: 2×/wk×2wk → 1×/wk×2–3wk\nChronic: 2×/wk×3wk → 1×/wk×3–4wk → biweekly PRN",
    visits: "Acute: 6–8 visits / 4–5 wk\nChronic: 8–12 visits / 6–8 wk",
    prog: { t: "Fast tissue response — pain drops 1–3 sessions. Recurrence is the real issue. Treatment length is about perpetuating factors, not the TrPs.", e: "Acute: resolution 2–3 wk. Chronic: reduction 2–3 wk, long-term = ergonomic correction. 70% recurrence without addressing root cause.", f: "Better: correctable perpetuating factor, acute, good compliance. Worse: chronic stress, uncorrectable ergonomics, fibromyalgia." },
    outcomes: ["NDI", "NPRS", "Active TrP count", "FHP measurement"],
    contras: [{ t: "Local infection", l: "y" }, { t: "Anticoagulation — modify pressure", l: "y" }],
    refer: "Not responding 4 wk → rheumatology or systemic workup",
    hep: ["Self-MFR ball (UT, levator) 2×/day", "Chin tucks + scap squeeze hourly", "Pec stretch 30s×3, 2×/day", "Diaphragmatic breathing"],
    reexam: {
      schedule: [
        { visit: "Visit 4 (~2 wk)", focus: "TrP response + perpetuating factor assessment" },
        { visit: "Visit 8 (~4–5 wk)", focus: "Discharge or maintenance decision" }
      ],
      mcid: [
        { measure: "NDI", threshold: "≥7 points improvement" },
        { measure: "NPRS", threshold: "≥2 points decrease" },
        { measure: "Active TrP count", threshold: "≥50% reduction from baseline" }
      ],
      onTrack: "TrP count reducing, NPRS ↓≥2, FHP improving. Shift focus to self-management and ergonomic correction. If perpetuating factors addressed → taper to discharge.",
      offTrack: "TrPs not reducing despite 4 visits → reassess diagnosis. Is this actually facet or disc with secondary muscle guarding? Are perpetuating factors still present? If systemic symptoms → rheumatology screen.",
      warningSign: "Widespread pain developing, fatigue, multiple regions → screen for fibromyalgia or central sensitization. New neurological symptoms → upgrade Dx."
    }
  },
  uc_instability: {
    session: [
      { t: "0–5", p: "⚠ CAUTION", tasks: ["NO cervical HVLA or end-range mob", "Gentle isometric testing only", "Reassess neuro — CN, DTRs, long tract"] },
      { t: "5–10", p: "Stabilization", tasks: ["DNF iso (low load 22–26mmHg)", "Cervical co-contraction neutral", "Proprioceptive training — laser repositioning"] },
      { t: "10–15", p: "Referral", tasks: ["Explain findings + need for imaging", "REFER neuro/ortho spine", "Collar if indicated", "Document HVLA contraindication"] }
    ],
    freq: "1–2×/wk while awaiting specialist",
    visits: "3–6 visits / 2–4 wk — bridge to specialist, NOT standalone Tx",
    prog: { t: "Not a condition you treat to resolution. Job: identify → stabilize → refer. Timeline = specialist wait time.", e: "Mild laxity without neuro: may stabilize over months. Significant laxity or + neuro: surgical fusion likely.", f: "Worse: ANY + neuro finding, RA, os odontoideum, Down syndrome, significant trauma." },
    outcomes: ["NDI", "Neuro reassessment each visit", "Balance / proprioception"],
    contras: [{ t: "ABSOLUTE: Cervical HVLA", l: "r" }, { t: "End-range passive mob", l: "r" }, { t: "Cervical traction", l: "r" }],
    refer: "IMMEDIATE referral upon suspicion",
    hep: ["Gentle iso chin tucks (NO end-range)", "Postural awareness", "NO self-manipulation"],
    reexam: {
      schedule: [
        { visit: "Every visit", focus: "Neurological reassessment — non-negotiable" },
        { visit: "Post-imaging", focus: "Review specialist findings, adjust plan" }
      ],
      mcid: [
        { measure: "NDI", threshold: "≥7 points (secondary — stability is priority)" },
        { measure: "Neuro exam", threshold: "Stable or improving — any deterioration = escalate" },
        { measure: "Proprioception", threshold: "Improving joint position sense accuracy" }
      ],
      onTrack: "Neuro stable, proprioception improving, patient awaiting specialist. Continue stabilization. Specialist confirms mild laxity → long-term isometric program.",
      offTrack: "ANY new or worsening neurological sign = STOP treatment, URGENT re-referral. Symptoms worsening despite stabilization → expedite specialist appointment.",
      warningSign: "New cranial nerve signs, gait disturbance, clonus, Babinski, drop attacks, vertebrobasilar symptoms → EMERGENT referral. Do not wait."
    }
  },
  // ═══ LOW BACK ═══
  lbp_disc_rad: {
    session: [
      { t: "0–3", p: "Directional Preference", tasks: ["Prone press-ups × 10 — centralization?", "Peripheralizes → lateral shift first", "SLR retest — document angle"] },
      { t: "3–8", p: "Manual Therapy", tasks: ["Flexion-distraction (Cox) 3×20s", "Lateral shift correction if needed", "Lumbar PA mob (Gr II–III) if centralizing only"] },
      { t: "8–12", p: "Exercise / Neural Mob", tasks: ["Repeated ext in DP × 10–15", "Sciatic slider (supine cycling)", "TA draw-in 10s × 10"] },
      { t: "12–15", p: "Closure", tasks: ["Re-assess SLR + centralization", "HEP: press-ups q2h × 10", "Avoid sitting >20 min, lumbar roll"] }
    ],
    freq: "Acute: 4–5×/wk×1wk → 3×/wk×1–2wk → 2×/wk×2–3wk → taper\nSubacute: 3×/wk×2wk → 2×/wk×3wk → 1×/wk×2wk",
    visits: "Centralizers: 10–14 visits / 6–8 wk\nNo centralization by session 5 → image before continuing",
    prog: { t: "85% resolve (mean 9 sessions). First improvement ~4 days. Nerve recovery is slow — don't rush.", e: "Centralizers: leg pain reduction 2–3 wk, functional 6–8 wk. Non-centralizers session 5: 50% need surgical consult.", f: "Better: centralization, acute <6wk, <40yo, single level, leg > back. Worse: no centralization, sequestered, motor >3/5." },
    outcomes: ["ODI", "NPRS", "SLR angle", "Centralization"],
    contras: [{ t: "CES → EMERGENT SURGICAL", l: "r" }, { t: "Progressive motor loss → URGENT", l: "r" }, { t: "Bilateral radiculopathy → escalate", l: "r" }],
    refer: "No centralization session 5, progressive neuro, CES → MRI + surgical",
    hep: ["Press-ups q2h × 10", "Nerve sliders 3×10, 2×/day", "Draw-in 10s×10, 3×/day", "Avoid sitting >20 min, lumbar roll"],
    reexam: {
      schedule: [
        { visit: "Visit 5 (~1–2 wk)", focus: "Centralization checkpoint — THE critical decision" },
        { visit: "Visit 10 (~4 wk)", focus: "Formal re-exam — SLR, neuro, ODI" },
        { visit: "Visit 14 (~6–8 wk)", focus: "Discharge or surgical referral decision" }
      ],
      mcid: [
        { measure: "ODI", threshold: "≥6 points (or 12.8 points for robust change)", cite: "Ostelo 2008" },
        { measure: "NPRS", threshold: "≥2 points decrease", cite: "Childs 2005" },
        { measure: "SLR angle", threshold: "≥10° improvement" },
        { measure: "Centralization", threshold: "Leg pain retreating proximally — most important metric" }
      ],
      onTrack: "Centralizing by visit 5, SLR improving, NPRS ↓≥2. Continue plan, taper frequency. Radicular symptoms should retreat before axial pain resolves — this is normal and expected.",
      offTrack: "No centralization by visit 5 → STOP McKenzie. Image. Non-centralizers have 50% chance of needing surgical consult. If centralizing but slow: continue but extend re-exam interval. ODI not changing by visit 10 → imaging + referral.",
      warningSign: "Saddle anesthesia, bowel/bladder change, bilateral progressive weakness → EMERGENT surgical referral same day. Progressive unilateral motor loss (worsening each visit) → URGENT MRI."
    }
  },
  lbp_stenosis: {
    session: [
      { t: "0–3", p: "Assessment", tasks: ["Walking tolerance — distance/time to Sx", "Lumbar flexion ROM + response"] },
      { t: "3–8", p: "Manual Therapy", tasks: ["Flexion-distraction (sustained + intermittent 3×30s)", "Lumbar flexion mob (Gr III–IV) — open canal", "Hip flexor stretch (Thomas)"] },
      { t: "8–12", p: "Flexion-Bias Exercise", tasks: ["DKC 30s × 5", "Posterior pelvic tilt", "Stationary cycling 3–5 min", "Dead bugs 10 × each"] },
      { t: "12–15", p: "Closure", tasks: ["Re-assess walking tolerance", "HEP: flexion program, walking w/ cart", "Avoid standing & extension"] }
    ],
    freq: "2×/wk×4–6wk → 1×/wk×4wk → biweekly or monthly maintenance",
    visits: "12–20 visits / 8–12 wk + ongoing maintenance. Management, not cure.",
    prog: { t: "Structural & progressive. Goal = maximize walking tolerance, not eliminate stenosis.", e: "Walking tolerance improvement 4–6 wk. Flexion-distraction + cycling adds 30–50% walking distance. Monthly maintenance often needed.", f: "Better: mild single-level, flexion-responsive, good fitness. Worse: severe multilevel, progressive neuro, >75 w/ comorbidities." },
    outcomes: ["ODI", "Walking tolerance", "NPRS", "Swiss Stenosis Q"],
    contras: [{ t: "CES → EMERGENT", l: "r" }, { t: "Avoid ALL lumbar extension", l: "y" }, { t: "Progressive bilateral neuro → URGENT surgical", l: "r" }],
    refer: "Progressive neuro, bowel/bladder, declining walking after 12 wk → surgical decompression",
    hep: ["DKC 30s×5, 3×/day", "Pelvic tilts 10×3×/day", "Cycling 15–20 min daily", "Walking with cart/flexion aid"],
    reexam: {
      schedule: [
        { visit: "Visit 8 (~4 wk)", focus: "Walking tolerance + ODI" },
        { visit: "Visit 16 (~8 wk)", focus: "Maintenance decision" },
        { visit: "Every 8–12 wk ongoing", focus: "Maintenance re-assessment" }
      ],
      mcid: [
        { measure: "ODI", threshold: "≥6 points improvement" },
        { measure: "Walking tolerance", threshold: "≥30% increase in pain-free walking distance" },
        { measure: "NPRS", threshold: "≥2 points decrease" },
        { measure: "Swiss Stenosis Q", threshold: "Improvement in symptom severity subscale" }
      ],
      onTrack: "Walking tolerance improving ≥30% by visit 8, ODI improving, cycling tolerance increasing. Transition to maintenance phase — the goal is sustaining gains, not achieving cure.",
      offTrack: "Walking tolerance declining despite 8 weeks, neurological changes, ODI worsening → surgical decompression referral. This is a progressive condition — decline is expected over years but should not happen rapidly during active care.",
      warningSign: "Rapid neurological decline, bowel/bladder onset, bilateral leg weakness → EMERGENT surgical. New foot drop → URGENT imaging."
    }
  },
  lbp_sij: {
    session: [
      { t: "0–3", p: "Assessment", tasks: ["Retest 2 most + Laslett tests", "Gillet test"] },
      { t: "3–8", p: "Manual Therapy", tasks: ["SIJ HVLA side-lying", "SIJ mob (Gr IV PA or gapping)", "L5–S1 HVLA if concurrent"] },
      { t: "8–12", p: "Stabilization", tasks: ["TA + multifidus co-contraction", "Single-leg bridge 10 × each", "Clamshell 15 × each"] },
      { t: "12–15", p: "Closure", tasks: ["SIJ belt if hypermobile", "HEP: lumbopelvic stab 2×/day", "Avoid asymmetric loading"] }
    ],
    freq: "Acute: 2–3×/wk×1–2wk → 1×/wk×2–3wk\nChronic: 2×/wk×3wk → 1×/wk×3wk → biweekly",
    visits: "Acute: 6–8 visits / 3–5 wk\nChronic: 10–14 visits / 6–8 wk\nPostpartum: may need 8–10 wk",
    prog: { t: "Manipulation response is fast — most improve 4–6 visits. Real work = stabilization to prevent recurrence (30–40% without maintenance).", e: "Acute: 50%+ reduction 1–2 wk, functional 3–4 wk. Chronic: 3–4 wk to significant improvement. Postpartum: months for laxity resolution.", f: "Better: acute, clear provocation, good compliance. Worse: hypermobility, postpartum <6mo, multiple prior episodes." },
    outcomes: ["ODI", "NPRS", "Laslett count", "Active SLR"],
    contras: [{ t: "Sacral fracture", l: "r" }, { t: "AS — active inflammation (modify)", l: "y" }, { t: "Sacral tumor — night pain, weight loss → image", l: "r" }],
    refer: "No improvement 6 wk → SIJ injection. Positive injection + recurrence → RF ablation.",
    hep: ["Draw-in + PF 10s×10, 3×/day", "Bridges 15, 2×/day", "Clamshells 15 each, 2×/day", "SIJ belt during aggravating activities"],
    reexam: {
      schedule: [
        { visit: "Visit 4 (~2 wk)", focus: "Laslett retest — should be converting" },
        { visit: "Visit 8 (~4–5 wk)", focus: "Stabilization assessment + discharge" }
      ],
      mcid: [
        { measure: "ODI", threshold: "≥6 points improvement" },
        { measure: "NPRS", threshold: "≥2 points decrease" },
        { measure: "Laslett cluster", threshold: "Positive tests converting to negative (≥3/5 → ≤1/5)" },
        { measure: "Active SLR", threshold: "Normalizing — indicates motor control improving" }
      ],
      onTrack: "Laslett tests converting negative by visit 4, NPRS ↓≥2, active SLR improving. Shift to stabilization focus — the manipulation worked, now prevent recurrence. If stable → taper + HEP independence.",
      offTrack: "Laslett still 3/5+ positive at visit 4 despite manipulation → reassess. Is it truly SIJ or is it lumbar facet/disc referring? If clearly SIJ but not responding → injection referral (diagnostic + therapeutic). Positive injection confirms SIJ source.",
      warningSign: "Morning stiffness >45 min + age <45 + insidious onset → screen for ankylosing spondylitis (HLA-B27, ESR, CRP, sacroiliac imaging). Night pain, weight loss → sacral pathology screen."
    }
  },
  lbp_facet: {
    session: [
      { t: "0–3", p: "Assessment", tasks: ["Ext-rotation retest — levels/pain", "Prone segmental palpation"] },
      { t: "3–8", p: "Manual Therapy", tasks: ["Lumbar HVLA side-posture at restricted segments", "Unilateral PA mob (Gr IV)", "TL junction mob if T12–L1"] },
      { t: "8–12", p: "Exercise", tasks: ["Flexion stretching (DKC, prayer) 30s×3", "McGill Big 3", "Hip flexor stretch"] },
      { t: "12–15", p: "Closure", tasks: ["Re-assess ext-rotation — document", "HEP: McGill Big 3, HF stretches", "Avoid sustained extension"] }
    ],
    freq: "Acute: 3×/wk×1wk → 2×/wk×1–2wk → 1×/wk×2wk\nChronic: 2×/wk×2–3wk → 1×/wk×3–4wk",
    visits: "Acute: 6–8 visits / 3–4 wk\nChronic/DJD: 10–14 visits / 5–7 wk",
    prog: { t: "Fastest LBP responder. Immediate improvement common. No response by visit 4 = wrong diagnosis.", e: "Acute: 60–80% reduction 1–2 wk, discharge 3–4 wk. Chronic/DJD: 50% by 3–4 wk, may need maintenance. First-visit response = best predictor.", f: "Better: acute <2wk, single level, immediate relief. Worse: multilevel DJD, chronic >3mo, failed injection." },
    outcomes: ["ODI", "NPRS", "Lumbar ROM", "Kemp's response"],
    contras: [{ t: "Spondylolisthesis Gr II+ — modify (flex-distraction)", l: "y" }, { t: "Acute fracture — image first", l: "r" }, { t: "Spondylolysis in adolescent → image", l: "y" }],
    refer: "No improvement 4 wk → MBB / facet injection. Positive injection + recurrence → RF neurotomy.",
    hep: ["McGill Big 3 daily", "DKC 30s×5", "HF stretch 30s×3 each", "Walking 20–30 min daily"],
    reexam: {
      schedule: [
        { visit: "Visit 3–4 (~1–2 wk)", focus: "Should see change — fastest LBP responder" },
        { visit: "Visit 6–8 (~3–4 wk)", focus: "Discharge or maintenance" }
      ],
      mcid: [
        { measure: "ODI", threshold: "≥6 points improvement" },
        { measure: "NPRS", threshold: "≥2 points decrease" },
        { measure: "Lumbar ROM", threshold: "≥15° improvement in extension" },
        { measure: "Kemp's test", threshold: "Reduced provocation or negative" }
      ],
      onTrack: "NPRS ↓≥2 by visit 3, Kemp's improving, ROM gaining. Taper fast — acute facet is the quickest win in LBP. First-visit improvement predicts full resolution.",
      offTrack: "No change by visit 4 → WRONG DIAGNOSIS. Re-examine. Consider: disc (try McKenzie), SIJ (Laslett cluster), myofascial (palpate TrPs). If confirmed facet by imaging but not responding → medial branch block referral.",
      warningSign: "Developing leg pain → disc/radiculopathy emerging. Night pain unrelieved by position → screen for pathology. New neurological signs → imaging."
    }
  },
  lbp_disc_nrad: {
    session: [
      { t: "0–3", p: "McKenzie Assessment", tasks: ["Repeated movements — ext in lying, flex in lying", "ID directional preference", "Document centralization"] },
      { t: "3–8", p: "Manual Therapy", tasks: ["Flexion-distraction 3×20s", "Central PA mob (Gr III)", "Avoid HVLA if very irritable"] },
      { t: "8–12", p: "Exercise", tasks: ["End-range loading in DP × 15", "TA activation", "Prone ext progression (sphinx → press-up → standing)"] },
      { t: "12–15", p: "Closure", tasks: ["HEP: press-ups q2h", "Avoid sitting, lumbar roll", "Disc mechanics education"] }
    ],
    freq: "Acute: 4–5×/wk×1wk → 3×/wk×1wk → 2×/wk×1–2wk\nTaper aggressively once centralizing",
    visits: "Centralizers: 8–10 visits / 3–4 wk\nNon-centralizers: 12–14 visits / 5–6 wk max",
    prog: { t: "Same logic as cervical disc — centralization drives everything. No DP by session 5 = reconsider.", e: "Centralizers: pain reduction week 1, functional 3–4 wk. Monitor for conversion to radiculopathy — upgrade immediately if leg pain.", f: "Better: clear centralization, first episode, acute <4wk. Worse: no DP, chronic, multiple recurrences, heavy manual labor." },
    outcomes: ["ODI", "NPRS", "Centralization", "Sitting tolerance"],
    contras: [{ t: "Developing CES → EMERGENT", l: "r" }, { t: "Conversion to radiculopathy → upgrade plan", l: "y" }],
    refer: "Conversion to radiculopathy, no improvement 5–6 wk, recurrent >3/yr → MRI",
    hep: ["Press-ups q2h × 10", "Lumbar roll ALL seats", "Avoid flexion + lifting", "Walking 20–30 min daily"],
    reexam: {
      schedule: [
        { visit: "Visit 5 (~1–2 wk)", focus: "Centralization checkpoint" },
        { visit: "Visit 10 (~3–4 wk)", focus: "Discharge if centralizing" }
      ],
      mcid: [
        { measure: "ODI", threshold: "≥6 points improvement" },
        { measure: "NPRS", threshold: "≥2 points decrease" },
        { measure: "Centralization", threshold: "Achieving and maintaining centralized position" },
        { measure: "Sitting tolerance", threshold: "≥50% improvement in pain-free sitting time" }
      ],
      onTrack: "Centralizing by visit 5, sitting tolerance improving, NPRS ↓≥2. Centralizers should be close to self-managing by visit 8–10. Teach them to be their own therapist with press-ups.",
      offTrack: "No centralization by visit 5 → image or reassess. No sitting tolerance improvement → is this really discogenic or is it SIJ/facet? Monitor for leg pain development → upgrade to radiculopathy plan immediately.",
      warningSign: "New leg pain developing = disc progressing to radiculopathy → upgrade treatment plan. New bilateral symptoms → screen CES. Recurrent episodes >3/year despite good compliance → imaging + specialist."
    }
  },
  lbp_myofascial: {
    session: [
      { t: "0–3", p: "Assessment", tasks: ["Palpate QL, multifidus, ES, glutes", "Document taut bands, referral patterns"] },
      { t: "3–9", p: "Soft Tissue", tasks: ["Ischemic compression QL, multifidus 60–90s each", "IASTM paraspinals", "PIR/MET QL, hip flexors", "Gluteal release if piriformis/glut med"] },
      { t: "9–12", p: "Exercise", tasks: ["McGill Big 3", "Cat-cow × 10", "Bridges 15"] },
      { t: "12–15", p: "Closure", tasks: ["Re-palpate — document", "HEP: foam roller, core, stretching", "Address perpetuating factors"] }
    ],
    freq: "Acute: 2×/wk×1–2wk → 1×/wk×2wk\nChronic: 2×/wk×2–3wk → 1×/wk×3wk → biweekly PRN",
    visits: "Acute: 4–6 visits / 3–4 wk\nChronic: 8–12 visits / 5–7 wk",
    prog: { t: "Fastest LBP soft tissue response — 1–3 sessions. No change by visit 4 = probably missing the real Dx (screen SIJ/facet).", e: "Acute strain: resolution 2–3 wk. Chronic TrP: reduction 2–3 wk but long-term = deconditioning correction. Most common 'failed' treatment = missed SIJ or facet underneath.", f: "Better: identifiable cause, good compliance, active lifestyle. Worse: sedentary, psychosocial stress, central sensitization, workers comp." },
    outcomes: ["ODI", "NPRS", "Active TrP count", "FMS"],
    contras: [{ t: "Local infection", l: "y" }, { t: "Anticoagulation — modify pressure", l: "y" }, { t: "Not responding → consider visceral referral (kidney, GI)", l: "y" }],
    refer: "Not responding 4 wk → STarT Back screening + reconsider Dx. Night pain + weight loss → urgent imaging.",
    hep: ["Foam roller TL 2×/day", "McGill Big 3 daily", "Bridges 15×2×/day", "Walking 30 min daily"],
    reexam: {
      schedule: [
        { visit: "Visit 4 (~2 wk)", focus: "TrP response — should see change" },
        { visit: "Visit 8 (~4–5 wk)", focus: "Discharge decision" }
      ],
      mcid: [
        { measure: "ODI", threshold: "≥6 points improvement" },
        { measure: "NPRS", threshold: "≥2 points decrease" },
        { measure: "Active TrP count", threshold: "≥50% reduction" }
      ],
      onTrack: "TrPs reducing, NPRS ↓≥2, function improving. Shift to self-management. If perpetuating factors corrected → discharge with HEP.",
      offTrack: "No TrP reduction after 4 visits → you're probably missing the real diagnosis. This is the most common misdiagnosis in LBP — muscle guarding from facet/disc/SIJ is NOT myofascial pain. Re-run DDx. Use STarT Back Tool to screen psychosocial.",
      warningSign: "Widespread pain, fatigue, poor sleep → fibromyalgia/central sensitization screen. Night pain + weight loss → pathology screen. Not responding + psychosocial flags → refer for CBT/pain psychology."
    }
  },
};

// DATA PART 2: SHOULDER + HEADACHE Treatment Plans

Object.assign(TX, {
  // ═══ SHOULDER ═══
  rc_tendinopathy: {
    session: [
      { t: "0–3", p: "Assessment", tasks: ["Retest Hawkins, painful arc — irritability", "Active ROM — note arc range"] },
      { t: "3–8", p: "Manual Therapy", tasks: ["GH posterior glide (Gr III–IV) if IR restricted", "Inferior glide if elevation restricted", "Thoracic HVLA T3–T6 (subacromial clearance)", "Cross-fiber friction supraspinatus if chronic"] },
      { t: "8–12", p: "Exercise", tasks: ["Isometric supraspinatus (pain-free arc) 10s×10 if acute", "Eccentric supraspinatus (side-lying ER lowering) if subacute/chronic", "Scapular stab — low trap Y, serratus wall slides"] },
      { t: "12–15", p: "Closure", tasks: ["Re-assess painful arc — document", "HEP: iso/eccentric RC, scapular program", "Avoid overhead repetition, sleep positioning"] }
    ],
    freq: "2×/wk×4–6wk → 1×/wk×3–4wk\nTendinopathy requires progressive loading — don't rush",
    visits: "10–16 visits / 7–10 wk. Eccentric loading takes 6–12 wk for tendon adaptation.",
    prog: { t: "Good with progressive loading but tendinopathy requires patience. Tendon remodeling takes 6–12 weeks — educate patient expectations.", e: "Pain reduction 2–4 wk with isometrics. Functional improvement 6–8 wk with eccentric program. Full return to overhead 10–12 wk. Night pain typically resolves first (2–3 wk).", f: "Better: <50yo, acute, compliant with eccentric program. Worse: full-thickness tear suspected, chronic >6mo, calcific, worker's comp." },
    outcomes: ["QuickDASH", "NPRS", "Shoulder ROM", "Empty can response"],
    contras: [{ t: "Full-thickness tear with significant weakness → surgical consult", l: "r" }, { t: "Avoid painful arc loading in acute phase — isometric only", l: "y" }],
    refer: "No improvement 6–8 wk, suspected tear, acute trauma <40yo → US/MRI + ortho",
    hep: ["Eccentric supraspinatus 3×15 daily (KEY exercise)", "Scapular Y/T/W exercises daily", "Pendulums for pain relief PRN", "Avoid overhead; sleep on unaffected side"],
    reexam: { schedule:[{visit:"Visit 6 (~3 wk)",focus:"Pain response + arc assessment"},{visit:"Visit 12 (~6 wk)",focus:"Functional re-exam + strength"},{visit:"Visit 16 (~8–10 wk)",focus:"Discharge or imaging decision"}], mcid:[{measure:"QuickDASH",threshold:"≥8 points improvement",cite:"Mintken 2009"},{measure:"NPRS",threshold:"≥2 points decrease"},{measure:"Painful arc",threshold:"Arc narrowing or resolving"},{measure:"Shoulder ROM",threshold:"≥15° improvement in restricted plane"}], onTrack:"Night pain resolving by wk 2–3 (first sign of improvement). Painful arc narrowing by visit 6. Eccentric loading should be progressively loaded — if patient tolerating heavier resistance, tendon is remodeling. QuickDASH ↓≥8 by visit 12.", offTrack:"Night pain persisting >4 wk, arc unchanged at visit 6 → suspect full-thickness tear. Order US or MRI. If eccentric loading consistently painful without habituation → modify load or reassess diagnosis. QuickDASH unchanged at visit 12 → imaging + ortho.", warningSign:"Sudden weakness after trauma (even minor) → acute-on-chronic tear. Significant weakness on empty can → full tear likely. Refer ortho." }
  },
  rc_tear: {
    session: [
      { t: "0–3", p: "Assessment", tasks: ["Retest lag signs — weakness grade", "Pain level and functional limitations"] },
      { t: "3–8", p: "Manual Therapy", tasks: ["GH gentle post/inf glide (Gr II–III)", "Thoracic HVLA T3–T8 for kinetic chain", "STM deltoid, remaining RC, periscapular"] },
      { t: "8–12", p: "Compensatory Strengthening", tasks: ["Intact RC strengthening (protect torn tendon)", "Scapular stab priority — low trap, serratus, rhomboids", "Deltoid strengthening in pain-free range"] },
      { t: "12–15", p: "Referral Discussion", tasks: ["DISCUSS imaging referral for tear confirmation", "Acute traumatic: REFER ortho within 2 weeks", "Chronic degenerative: conservative trial 6–12 wk acceptable", "HEP: scapular program, compensatory strengthening"] }
    ],
    freq: "Conservative trial: 2×/wk×6–8wk → 1×/wk×4wk\nPre-surgical bridge: 1–2×/wk until surgery date",
    visits: "Conservative: 14–20 visits / 10–12 wk\nPre-op bridge: 4–6 visits / 2–4 wk",
    prog: { t: "Age and tear type drive everything. Young + acute traumatic = surgical. Older + degenerative = conservative often works.", e: "Partial tears: 60–80% respond conservative with scapular program. Full-thickness degenerative >60yo: many manage well without surgery. Full-thickness <50yo acute: surgical outcomes better if repaired within 3 months.", f: "Better: partial tear, degenerative onset, good scapular control, >60yo. Worse: acute traumatic, massive/retracted tear, young active, fatty infiltration on MRI." },
    outcomes: ["QuickDASH", "Strength (dynamometer)", "NPRS", "Functional outcome"],
    contras: [{ t: "Aggressive stretching in acute full tear", l: "r" }, { t: "High-load resistance through injured tendon", l: "r" }, { t: "Acute traumatic + young = don't delay surgical referral", l: "r" }],
    refer: "Acute traumatic in active patient → URGENT ortho within 2 wk. Progressive weakness at any age → imaging.",
    hep: ["Scapular retraction exercises 3×/day", "Isometric RC (pain-free) 10s×10", "Pendulums for pain relief PRN", "Avoid heavy lifting until cleared"],
    reexam: { schedule:[{visit:"Visit 4 (~2 wk)",focus:"Strength trending — key metric"},{visit:"Visit 10 (~5 wk)",focus:"Conservative trial midpoint"},{visit:"Visit 16 (~8 wk)",focus:"Continue vs surgical decision"}], mcid:[{measure:"QuickDASH",threshold:"≥8 points improvement"},{measure:"Strength",threshold:"Measurable gain on dynamometry"},{measure:"NPRS",threshold:"≥2 points decrease"}], onTrack:"Strength stable/improving, pain decreasing, compensatory muscles taking over. Degenerative >60yo: full strength may not return but function does.", offTrack:"Strength declining, pain unchanged → conservative failing. Acute traumatic <50yo: don't wait >8 wk for repair. Degenerative >60yo: extend to 12 wk if pain improving.", warningSign:"Rapid strength loss → tear propagation. Night pain worsening → inflammation. Catching/locking → labral component. Expedite imaging + ortho." }
  },
  frozen_shoulder: {
    session: [
      { t: "0–3", p: "Assessment / Heat", tasks: ["Measure passive ER, ABD, IR — capsular pattern", "Moist heat 3–5 min if available"] },
      { t: "3–9", p: "Manual Therapy", tasks: ["GH posterior glide (Gr III–IV, sustained 30–60s × 5)", "Inferior glide (sustained, end-range)", "Anterior glide for IR restriction", "Scapulothoracic mob", "Thoracic HVLA T3–T8"] },
      { t: "9–12", p: "ROM / Stretch", tasks: ["Passive ER stretch at 45° ABD 30s×5", "Cross-body adduction 30s×3", "Wall slide (active-assisted elevation)"] },
      { t: "12–15", p: "Closure", tasks: ["Re-measure ER — document degree gains", "HEP: pendulums, ER stretch, wall slides", "Education: 12–18 mo natural history"] }
    ],
    freq: "Freezing phase: 1–2×/wk (gentle, Gr II only)\nFrozen phase: 2–3×/wk×6–8wk → 1–2×/wk×8–12wk\nThawing phase: 1×/wk → taper",
    visits: "20–30 visits over 3–6 months. This is the longest rehab in the shoulder group. Set expectations early.",
    prog: { t: "Natural history 12–18 months (freezing → frozen → thawing). Manual therapy accelerates thawing but doesn't skip phases. Most important thing you can do: set expectations on day 1.", e: "ROM gains 5–10° per month with aggressive mob. Freezing phase (first 3–6mo): pain management only — don't force ROM. Frozen phase: this is where manual therapy has biggest impact. Most recover 90%+ ROM but timeline is 12–18 months total.", f: "Better: early intervention, compliant with daily HEP, no diabetes. Worse: diabetes (DOUBLES recovery time), bilateral, post-surgical, thyroid disease." },
    outcomes: ["QuickDASH", "Passive ROM (ER, ABD, IR)", "NPRS", "SPADI"],
    contras: [{ t: "Aggressive mob in freezing phase — stay Gr II, don't force", l: "y" }, { t: "MUA only via ortho referral", l: "y" }, { t: "Rule out secondary causes: tumor, fracture, infection", l: "r" }],
    refer: "No ROM progress after 3 months of consistent care → hydrodilatation or MUA referral",
    hep: ["Pendulums 5 min, 3×/day (the homework that matters most)", "ER stretch with stick 30s×5, 3×/day", "Wall slides (active-assisted)", "Cross-body stretch 30s×3, 2×/day"],
    reexam: { schedule:[{visit:"Monthly (every 4–6 visits)",focus:"ROM measurement — THE metric"},{visit:"3-month mark",focus:"Continue vs hydrodilatation/MUA decision"}], mcid:[{measure:"Passive ER",threshold:"≥5–10° improvement per month"},{measure:"QuickDASH",threshold:"≥8 points improvement"},{measure:"SPADI",threshold:"≥13 points improvement",cite:"Roy 2009"},{measure:"NPRS",threshold:"≥2 points decrease"}], onTrack:"ER gaining 5–10° monthly, pain decreasing (pain resolves before ROM returns — this is normal). If in thawing phase with consistent gains → continue. Patient compliance with 3×/day HEP is the #1 predictor of outcome.", offTrack:"No ROM change over 2 consecutive months → intervention needed. Options: hydrodilatation (evidence supports), MUA under anesthesia, or corticosteroid injection. If in freezing phase and pain is dominant → injection may help transition to frozen phase faster.", warningSign:"ROM declining (not just plateauing) → rule out secondary cause (tumor, fracture, infection). New neurological symptoms → reassess. Bilateral onset → screen diabetes, thyroid." }
  },
  ac_joint: {
    session: [
      { t: "0–2", p: "Assessment", tasks: ["Retest cross-body adduction, AC shear", "Palpate AC joint — tenderness level"] },
      { t: "2–7", p: "Manual Therapy", tasks: ["AC mob PA + inferior (Gr II–III)", "Thoracic HVLA mid-thoracic", "STM upper trap, deltoid insertion", "Kinesio tape — AC deloading technique"] },
      { t: "7–12", p: "Exercise", tasks: ["Scapular retraction + depression", "RC strengthening pain-free range <90°", "Posterior deltoid, mid-trap strengthening"] },
      { t: "12–15", p: "Closure", tasks: ["HEP: ice post-activity, scapular exercises", "Activity mod — avoid cross-body, end-range elev", "Consider injection referral if OA + not responding"] }
    ],
    freq: "Acute sprain: 2×/wk×2wk → 1×/wk×2wk\nChronic OA: 1–2×/wk×4–6wk",
    visits: "Acute Gr I–II sprain: 4–6 visits / 3–4 wk\nChronic OA: 6–10 visits / 4–6 wk",
    prog: { t: "Acute sprains resolve fast with protection. Chronic OA is management — may ultimately need injection or distal clavicle resection.", e: "Acute sprain: pain resolution 2–3 wk with activity mod. Chronic OA: symptom management 4–6 wk; expect periodic flares. Osteolysis (weightlifters): requires activity modification.", f: "Better: Gr I–II sprain, acute, compliance with activity mod. Worse: Gr III+ (refer), chronic OA, distal clavicle osteolysis." },
    outcomes: ["QuickDASH", "NPRS", "Cross-body test", "Overhead function"],
    contras: [{ t: "Grade III+ AC separation → ortho referral", l: "r" }, { t: "Aggressive mob in acute sprain", l: "y" }],
    refer: "Gr III+ separation, osteolysis, failed 6 wk → ortho. OA not responding → injection.",
    hep: ["Ice 15 min post-activity", "Scapular retraction daily", "Avoid bench/dips/push-ups until pain-free", "Cross-body stretch ONLY if pain-free"],
    reexam: { schedule:[{visit:"Visit 3 (~1–2 wk)",focus:"Acute sprain response"},{visit:"Visit 6 (~3–4 wk)",focus:"Discharge or injection decision"}], mcid:[{measure:"QuickDASH",threshold:"≥8 points improvement"},{measure:"NPRS",threshold:"≥2 points decrease"},{measure:"Cross-body test",threshold:"Reduced provocation or negative"}], onTrack:"Acute sprain: pain ↓≥50% by visit 3 with activity mod + taping. Cross-body test improving. Discharge 3–4 wk.", offTrack:"Pain unchanged at visit 6 → if acute: image for Gr III+. If chronic OA: injection referral. Weightlifters with osteolysis: must modify training permanently.", warningSign:"Step deformity developing → Gr III+ separation, refer ortho. Increasing instability → imaging." }
  },
  biceps_slap: {
    session: [
      { t: "0–3", p: "Assessment", tasks: ["Retest Speed's, Yergason's", "Palpate bicipital groove — tenderness"] },
      { t: "3–8", p: "Manual Therapy", tasks: ["Biceps transverse friction if chronic tendinopathy", "GH posterior glide mob", "Thoracic HVLA for kinetic chain"] },
      { t: "8–12", p: "Exercise", tasks: ["Eccentric biceps curl (slow lowering) 3×15 if chronic", "Scapular stab — serratus, low trap", "RC ER + scapular retraction"] },
      { t: "12–15", p: "Closure", tasks: ["HEP: eccentric biceps, scapular program", "Avoid heavy lifting, overhead", "SLAP + mechanical Sx → REFER MRI arthrogram"] }
    ],
    freq: "Tendinopathy: 2×/wk×3–4wk → 1×/wk×3–4wk\nSuspected SLAP: 2×/wk×4wk trial then reassess",
    visits: "Tendinopathy: 8–12 visits / 6–8 wk\nSLAP suspected: 6–8 visits / 4 wk conservative trial → if mechanical Sx persist, refer",
    prog: { t: "Two different conditions with different timelines. Tendinopathy responds to eccentric loading in 6–12 wk. SLAP is a structural lesion that may need surgery.", e: "Tendinopathy: 70–80% resolve conservatively with eccentric program. SLAP in young overhead athletes: often needs arthroscopic repair. SLAP in >40yo: labral fraying is normal aging — conservative management.", f: "Better: isolated tendinopathy, no mechanical symptoms, >40yo. Worse: SLAP with catching/locking, young overhead athlete, failed conservative." },
    outcomes: ["QuickDASH", "NPRS", "Speed's test response", "Overhead function"],
    contras: [{ t: "Aggressive stretching if labral tear suspected", l: "y" }, { t: "Avoid heavy supination/flexion loading", l: "y" }],
    refer: "Mechanical symptoms (catching/locking), young overhead athlete, failed 6 wk → MRI arthrogram + ortho",
    hep: ["Eccentric biceps curls 3×15 daily", "Scapular retraction daily", "Avoid heavy supination loading", "Ice after activity PRN"],
    reexam: { schedule:[{visit:"Visit 4 (~2 wk)",focus:"Tendinopathy vs SLAP differentiation"},{visit:"Visit 8 (~4 wk)",focus:"Conservative trial endpoint for SLAP"}], mcid:[{measure:"QuickDASH",threshold:"≥8 points improvement"},{measure:"NPRS",threshold:"≥2 points decrease"},{measure:"Speed's test",threshold:"Reduced provocation"}], onTrack:"Tendinopathy: Speed's improving, eccentric loading tolerated, pain ↓. SLAP: if mechanical symptoms resolving → continue. >40yo with labral fraying: conservative is appropriate long-term.", offTrack:"Mechanical symptoms persisting (catching, locking, popping with pain) at visit 8 → MRI arthrogram. Young overhead athlete with no improvement → refer earlier (visit 6).", warningSign:"New instability symptoms → assess for concurrent Bankart. Sudden weakness → RC tear developing. Night pain not resolving → image." }
  },
  gh_instability: {
    session: [
      { t: "0–3", p: "Assessment", tasks: ["Retest apprehension/relocation — document", "Scapular dyskinesis assessment"] },
      { t: "3–7", p: "Manual (Cautious)", tasks: ["Posterior GH mob Gr II–III ONLY", "Thoracic HVLA for kinetic chain", "Scapulothoracic mob", "AVOID: anterior GH glide, excessive ER mob"] },
      { t: "7–12", p: "Stabilization (Priority)", tasks: ["Dynamic RC ER/IR band at 0° ABD", "Rhythmic stabilization (PNF) at 90° ABD if tolerated", "Serratus push-ups, low trap Y raises", "Proprioception — ball wall circles, quadruped"] },
      { t: "12–15", p: "Closure", tasks: ["HEP: RC + scapular 2×/day", "Avoid end-range risk positions", "Recurrent + young → REFER Bankart repair discussion"] }
    ],
    freq: "2–3×/wk×4–6wk → 1×/wk×4wk → sport-specific phase 4 wk",
    visits: "14–20 visits / 10–14 wk (includes sport-specific return phase). Longest shoulder rehab alongside frozen shoulder.",
    prog: { t: "Age is the biggest prognostic factor. <25yo first dislocation: 70–90% redislocation risk without surgery. >30yo: much lower recurrence.", e: "Functional stability achievable 8–12 wk intensive. Non-contact athletes: return to sport 12–16 wk if strength >85% contralateral. Contact athletes <25: strongly consider surgical referral before return.", f: "Better: first episode, >30yo, good muscle control, non-contact sport. Worse: <20yo, contact sport, MDI, >2 dislocations, Hill-Sachs lesion." },
    outcomes: ["QuickDASH", "Apprehension grade", "WOSI score", "Return-to-sport criteria"],
    contras: [{ t: "Anterior GH glide mobilization", l: "r" }, { t: "End-range ER stretching", l: "r" }, { t: "Contact sports until fully cleared", l: "y" }],
    refer: "Recurrent dislocation, young contact athlete, Hill-Sachs/Bankart → ortho for surgical eval",
    hep: ["RC ER/IR band 3×15 each, 2×/day", "Scapular push-ups 3×10 daily", "Ball on wall circles (proprioception)", "Avoid sleeping with arm overhead"],
    reexam: { schedule:[{visit:"Visit 6 (~3 wk)",focus:"Strength + apprehension response"},{visit:"Visit 12 (~6 wk)",focus:"Sport-specific readiness assessment"},{visit:"Visit 16–20 (~10–14 wk)",focus:"Return to sport decision"}], mcid:[{measure:"QuickDASH",threshold:"≥8 points improvement"},{measure:"WOSI",threshold:"≥12% improvement",cite:"Kirkley 1998"},{measure:"Apprehension",threshold:"Reduced or negative"},{measure:"Strength",threshold:"≥85% contralateral for RTS"}], onTrack:"Apprehension reducing, RC strength building, proprioception improving. Non-contact: may return to sport 12 wk if strength >85% contralateral. Contact: 16+ wk minimum.", offTrack:"Apprehension not improving by visit 6, recurrent subluxation episodes during rehab → refer ortho for Bankart discussion. MDI not responding to strengthening → consider prolotherapy or surgical referral.", warningSign:"Redislocation during treatment → STOP, refer immediately. <20yo + contact sport + first dislocation: discuss surgical referral NOW — 70–90% redislocation without repair." }
  },
  // ═══ HEADACHE ═══
  cervicogenic: {
    session: [
      { t: "0–3", p: "Assessment", tasks: ["CFRT retest — document degrees", "HA frequency/intensity this week"] },
      { t: "3–8", p: "Manual Therapy", tasks: ["C1–C2 rotatory mob (Gr III–IV) or SNAG", "UC HVLA (toggle/atlas) if appropriate", "C2–C3 unilateral PA mob", "Suboccipital release 2–3 min"] },
      { t: "8–12", p: "Motor Control", tasks: ["CCF training (biofeedback 22–30mmHg)", "Flexor endurance hold (progress → 30s)", "Eye-neck coordination (smooth pursuit)"] },
      { t: "12–15", p: "Closure", tasks: ["Retest CFRT — document", "HEP: CCF 3×/day, self-SNAG C1–C2", "HA diary for tracking"] }
    ],
    freq: "2×/wk×3–4wk → 1×/wk×2–3wk → PRN",
    visits: "8–12 visits / 5–7 wk",
    prog: { t: "Excellent responder — often 4–6 sessions. Same condition as cervicogenic_ha in neck region; if presenting as primary HA complaint, manage identically.", e: "50–70% HA frequency reduction by 3 wk. Near-complete resolution by 5–6 wk. CFRT should normalize within 2–3 sessions.", f: "Better: + CFRT, isolated C1–C2, acute. Worse: concurrent migraine, MOH, chronic >2yr." },
    outcomes: ["HIT-6", "HA freq/wk", "CFRT degrees", "NDI"],
    contras: [{ t: "UC instability", l: "r" }, { t: "VBI → REFER", l: "r" }],
    refer: "Thunderclap, new >50yo, neuro signs → EMERGENT medical",
    hep: ["CCF 10s×10, 3×/day", "Self-SNAG C1–C2 with towel", "Chin tucks hourly", "Workstation ergonomics"],
    reexam: { schedule:[{visit:"Visit 4 (~2 wk)",focus:"CFRT + HA freq response"},{visit:"Visit 8 (~4–5 wk)",focus:"Discharge decision"}], mcid:[{measure:"HIT-6",threshold:"≥6 points improvement",cite:"Smelt 2014"},{measure:"CFRT",threshold:"≥10° toward normal (>33°)"},{measure:"HA frequency",threshold:"≥50% reduction"}], onTrack:"CFRT improving by visit 4, HA freq ↓≥30%. Fast responder — if CFRT normalizing, taper quickly.", offTrack:"No CFRT change by visit 4, HA unchanged → is this actually migraine? Screen MOH. Reconsider Dx.", warningSign:"Thunderclap, new neuro signs, worsening with manipulation → STOP, medical referral." }
  },
  migraine: {
    session: [
      { t: "0–3", p: "Assessment", tasks: ["HA diary review — freq, triggers, meds", "Cervical palpation — concurrent component?"] },
      { t: "3–8", p: "Manual Therapy", tasks: ["Cervical mob if restrictions (Gr II–III)", "UC STM — suboccipitals, SCM", "Thoracic HVLA T1–T6 (evidence for migraine reduction)"] },
      { t: "8–12", p: "Exercise / Lifestyle", tasks: ["Aerobic Rx (graded: start 50% intensity, progress)", "Relaxation — diaphragmatic breathing, PMR", "Postural correction if applicable"] },
      { t: "12–15", p: "Closure", tasks: ["Trigger ID + avoidance strategies", "HEP: aerobic 30min×5/wk (strongest evidence)", "REFER neuro if >4 migraines/mo for prophylaxis"] }
    ],
    freq: "1–2×/wk×6–8wk\nChiro is complementary — primary focus is lifestyle + aerobic exercise",
    visits: "8–12 visits / 6–8 wk. Longer timeline because aerobic exercise benefits take 6–8 wk to manifest.",
    prog: { t: "Chiropractic role is complementary. You're managing cervical component + coaching lifestyle modification. Aerobic exercise is the strongest evidence-based intervention.", e: "Regular aerobic exercise reduces migraine frequency 40–50%. Thoracic manipulation may add benefit if cervical component. Benefits take 6–8 wk to stabilize — set expectations. Co-management with neuro if >4/mo.", f: "Better: identifiable triggers, cervical component present, exercise compliance. Worse: chronic daily, MOH, strong aura, >15 HA days/mo." },
    outcomes: ["HIT-6", "MIDAS score", "Migraine days/mo", "Medication use"],
    contras: [{ t: "Vigorous cervical manipulation during active migraine attack", l: "y" }, { t: "New aura pattern → urgent medical referral", l: "r" }],
    refer: ">4 migraines/mo → neuro for prophylactic meds. New aura, pattern change → urgent medical.",
    hep: ["Aerobic exercise 30min×5/wk (THE key intervention)", "Diaphragmatic breathing 5min×2/day", "Trigger diary maintenance", "Regular sleep schedule (migraine hygiene)"],
    reexam: { schedule:[{visit:"Visit 6 (~4 wk)",focus:"HA diary review — freq trending"},{visit:"Visit 10 (~6–8 wk)",focus:"Aerobic benefit assessment — full effect takes 6–8 wk"}], mcid:[{measure:"HIT-6",threshold:"≥6 points improvement"},{measure:"MIDAS",threshold:"Grade reduction (e.g. IV→III)"},{measure:"Migraine days/mo",threshold:"≥50% reduction"},{measure:"Med use",threshold:"Reduction in acute medication days"}], onTrack:"Migraine frequency decreasing ≥30% by visit 6, patient adhering to aerobic program. Cervical component improving if present. Taper manual therapy, emphasize lifestyle.", offTrack:"Frequency unchanged at 6 wk despite exercise compliance → REFER neuro for prophylactic meds. If aerobic program not started (non-compliance) → this is the #1 priority to address. Manual therapy alone is insufficient for migraine.", warningSign:"New aura type, aura >60 min, aura without headache (new), frequency escalating rapidly → urgent neurology. ≥15 days/mo → chronic migraine, needs specialist." }
  },
  tension_ha: {
    session: [
      { t: "0–3", p: "Assessment", tasks: ["Pericranial palpation — temporalis, frontalis, suboccipitals, UT", "HA frequency/intensity this week"] },
      { t: "3–9", p: "Manual Therapy", tasks: ["Cervical mob mid-cervical segments", "Suboccipital release 2–3 min", "Temporalis/masseter soft tissue release", "UT trigger point therapy", "C/T HVLA if segmental restriction"] },
      { t: "9–12", p: "Exercise", tasks: ["Chin tucks + scapular retraction", "Cervical iso (4-way) 10s×10", "Progressive relaxation technique teaching"] },
      { t: "12–15", p: "Closure", tasks: ["HEP: stretching, posture, stress management", "Ergonomic assessment if work-related", "Consider psychosocial referral if dominant factor"] }
    ],
    freq: "Episodic: 1–2×/wk×3–4wk → PRN\nChronic: 2×/wk×3wk → 1×/wk×3–4wk",
    visits: "Episodic: 4–6 visits / 3–4 wk\nChronic: 8–12 visits / 5–7 wk",
    prog: { t: "Good multimodal response. Episodic resolves fast. Chronic is about lifestyle — stress reduction, posture, exercise.", e: "Episodic: resolution 3–4 wk. Chronic: 50% frequency reduction by 4 wk, continued improvement with stress management. Pericranial tenderness should decrease within 2–3 sessions.", f: "Better: episodic, identifiable trigger (posture/stress/sleep), good compliance. Worse: chronic daily, dominant psychosocial factors, MOH overlay." },
    outcomes: ["HIT-6", "HA freq/wk", "NPRS", "NDI"],
    contras: [{ t: "None specific — gentle techniques preferred", l: "y" }],
    refer: "New onset, change in character, neuro signs → medical. Chronic daily → screen for MOH.",
    hep: ["Chin tucks hourly", "Self-suboccipital release with ball", "Stress management / relaxation daily", "Physical activity 30 min daily"],
    reexam: { schedule:[{visit:"Visit 4 (~2 wk)",focus:"Pericranial tenderness + freq"},{visit:"Visit 8 (~4–5 wk)",focus:"Discharge or chronic Mx decision"}], mcid:[{measure:"HIT-6",threshold:"≥6 points improvement"},{measure:"HA frequency",threshold:"≥50% reduction"},{measure:"NPRS",threshold:"≥2 points decrease"}], onTrack:"Pericranial tenderness reducing, HA freq ↓. Episodic: should be near-resolution by visit 4–6. Shift to self-management.", offTrack:"Episodic not improving → screen for MOH, cervicogenic component, psychosocial. Chronic daily: if no HIT-6 change by visit 8 → refer for psychosocial assessment, consider amitriptyline referral.", warningSign:"Pattern change, new features, neuro signs → medical workup. >15 days/mo → screen for MOH and chronic migraine." }
  },
  cluster_ha: {
    session: [
      { t: "0–5", p: "Assessment / Education", tasks: ["Confirm cluster: autonomic features, duration 15–180 min, circadian pattern", "This REQUIRES medical referral — chiropractic is adjunctive ONLY", "Primary Mx: neurologist (high-flow O₂, triptans, verapamil)"] },
      { t: "5–10", p: "Supportive Therapy", tasks: ["Cervical mob gentle (Gr II–III)", "Suboccipital + cervical paraspinal STM", "Thoracic mob for cervicogenic overlay"] },
      { t: "10–15", p: "Referral", tasks: ["REFER neurologist urgently", "Education on cluster cycle + management", "Support during active cluster period", "HEP: HA diary for neurologist"] }
    ],
    freq: "1×/wk adjunctive during cluster period\nDo NOT position as primary treatment",
    visits: "4–8 visits as bridge/adjunct to neurology. This is not your condition to manage independently.",
    prog: { t: "Cyclic condition — cluster periods 4–12 wk, then remission. Pharmacological intervention is the primary treatment. Your role: identify, refer, support.", e: "Episodic: good prognosis with proper neuro management (O₂ aborts 78% of attacks within 15 min). Chronic cluster (>1yr without remission): more difficult, requires specialist. Manual therapy may help cervicogenic overlay but does not resolve attacks.", f: "Episodic: better prognosis. Chronic: requires specialist management. Transformation from episodic to chronic: rare but requires aggressive treatment." },
    outcomes: ["HIT-6", "Attack frequency/day", "Attack duration", "Medication response"],
    contras: [{ t: "Do NOT delay medical referral for chiropractic-only trial", l: "r" }, { t: "Avoid aggressive cervical manipulation during active attack", l: "y" }],
    refer: "IMMEDIATE referral to neurologist upon clinical suspicion. Do not wait.",
    hep: ["HA diary (timing, duration, autonomic features, triggers)", "Regular sleep schedule (circadian regulation)", "AVOID alcohol during cluster period", "Relaxation techniques between attacks"],
    reexam: { schedule:[{visit:"Every visit",focus:"Neuro referral status check"},{visit:"Post-neuro appointment",focus:"Collaborative plan adjustment"}], mcid:[{measure:"Attack frequency",threshold:"Reduction with pharmacological Mx"},{measure:"Attack duration",threshold:"Aborting faster with O₂/triptans"},{measure:"HIT-6",threshold:"≥6 points improvement"}], onTrack:"Patient connected with neurology, attacks being managed pharmacologically, chiropractic supporting cervical component. Your role is adjunctive — measure success by referral completion.", offTrack:"Patient refusing neurology referral → educate on cluster severity and pharmacological necessity. O₂ aborts 78% of attacks — this is not optional information. Document refusal.", warningSign:"Cluster transforming to chronic (>1yr without remission) → needs aggressive specialist management. Secondary cluster (structural cause) → imaging indicated." }
  },
  moh: {
    session: [
      { t: "0–5", p: "Education (Most Important Phase)", tasks: ["Document current med use: type, frequency, duration", "Educate on MOH mechanism — medication IS the problem now", "Collaborative Mx with GP/neurologist required"] },
      { t: "5–10", p: "Supportive Therapy", tasks: ["Cervical mob gentle (Gr II–III) for symptom relief", "Suboccipital + pericranial muscle release", "Thoracic mob"] },
      { t: "10–15", p: "Withdrawal Support / Referral", tasks: ["REFER GP for supervised medication withdrawal plan", "Non-pharmacological pain support during withdrawal", "HEP: hydration, regular meals, sleep hygiene, gentle exercise", "Set expectations: worsening 1–2 wk before improvement"] }
    ],
    freq: "Withdrawal phase: 2×/wk×2–4wk (support through worst period)\nPost-withdrawal: 1×/wk×4wk → PRN for underlying HA type",
    visits: "10–14 visits / 6–8 wk total. First 2–4 wk is withdrawal support; remaining is treating the underlying primary HA.",
    prog: { t: "Withdrawal headache peaks 2–10 days after cessation, then gradual improvement 4–8 wk. The underlying primary HA will re-emerge — then treat THAT appropriately.", e: "60–70% improve significantly after successful withdrawal. Triptan overuse recovers fastest (1–2 wk). Combination analgesic: 2–4 wk. Post-withdrawal: identify and treat underlying HA type (migraine, tension, cervicogenic).", f: "Better: triptan overuse (fastest recovery), motivated patient, GP co-management. Worse: opioid overuse (needs addiction medicine), combination analgesics, psychiatric comorbidity, prior failed withdrawal." },
    outcomes: ["HIT-6", "Medication use days/month", "HA frequency/month", "MIDAS"],
    contras: [{ t: "DO NOT manage opioid withdrawal independently → addiction medicine", l: "r" }, { t: "Barbiturate-containing analgesics → medical supervision required", l: "r" }],
    refer: "REFER GP/neurologist for supervised withdrawal plan. Opioid overuse → addiction medicine. Barbiturate-containing → inpatient withdrawal may be needed.",
    hep: ["Hydration 2L daily", "Regular sleep schedule (critical)", "Gentle aerobic exercise 20–30 min daily", "Stress management / relaxation techniques"],
    reexam: { schedule:[{visit:"Weekly during withdrawal (wk 1–4)",focus:"Withdrawal symptom monitoring"},{visit:"Visit 8 (~4 wk post-withdrawal)",focus:"Identify emerging primary HA type"},{visit:"Visit 12 (~6–8 wk)",focus:"Long-term HA management plan"}], mcid:[{measure:"Med use days/mo",threshold:"≥50% reduction (goal: <10 days/mo)"},{measure:"HA frequency",threshold:"Reduction after withdrawal window (4–8 wk)"},{measure:"HIT-6",threshold:"≥6 points improvement"},{measure:"MIDAS",threshold:"Grade reduction"}], onTrack:"Med use decreasing, withdrawal HA peaking then improving (expected 2–10 days). By wk 4 post-withdrawal: underlying primary HA type should be identifiable. Treat THAT appropriately (cervicogenic, migraine, tension).", offTrack:"Unable to reduce medication use → GP/neuro co-management failing or patient non-adherent. Withdrawal attempted but relapsing → need structured withdrawal program. Identify barriers.", warningSign:"Opioid withdrawal without medical supervision → DANGEROUS, refer addiction medicine. Seizure risk with barbiturate withdrawal → inpatient. Post-withdrawal HA worsening beyond expected → screen for secondary cause." }
  },
});

const R = {
  neck: { id:"neck",label:"Neck Pain",icon:"⬡",color:"#2A9D8F",
    clusters:[
      {id:"nc_r",name:"Radiculopathy",desc:"Neural compression",tests:[
        {id:"n_spur",name:"Spurling's",sn:.50,sp:.88,c:"Rubinstein 07"},{id:"n_ultt",name:"ULTT1",sn:.97,sp:.22,c:"Wainner 03"},{id:"n_dist",name:"Distraction",sn:.44,sp:.90},{id:"n_sabd",name:"Shoulder ABD Relief",sn:.46,sp:.85},{id:"n_vals",name:"Valsalva",sn:.22,sp:.94}]},
      {id:"nc_n",name:"Neuro Screen",desc:"DTRs, myotomes, dermatomes",tests:[
        {id:"n_dtr",name:"Diminished DTRs",sn:.50,sp:.85},{id:"n_myo",name:"Myotomal Weakness",sn:.60,sp:.75},{id:"n_derm",name:"Sensory Loss",sn:.45,sp:.80}]},
      {id:"nc_uc",name:"Upper Cervical",desc:"C0–C2 assessment",tests:[
        {id:"n_cfrt",name:"Flex-Rotation Test",sn:.91,sp:.90,c:"Ogince 07"},{id:"n_ucp",name:"C1–C2 Palp",sn:.82,sp:.79},{id:"n_sp",name:"Sharp-Purser",sn:.69,sp:.96},{id:"n_alar",name:"Alar Ligament",sn:.50,sp:.90}]},
      {id:"nc_ml",name:"Mid/Lower Cervical",desc:"Facet, disc",tests:[
        {id:"n_er",name:"Ext-Rotation",sn:.70,sp:.60},{id:"n_fp",name:"PA Glide",sn:.75,sp:.55},{id:"n_ac",name:"Axial Compression",sn:.50,sp:.64}]},
      {id:"nc_st",name:"Soft Tissue",desc:"Trigger points",tests:[
        {id:"n_trp",name:"TrP Palpation",sn:.80,sp:.55},{id:"n_rs",name:"Reverse Spurling",sn:.40,sp:.75}]},
      {id:"nc_hx",name:"History",desc:"Patterns",tests:[
        {id:"n_uha",name:"Unilateral HA",sn:.85,sp:.65},{id:"n_nprov",name:"Neck Provokes HA",sn:.80,sp:.70},{id:"n_ax",name:"Axial Pain",sn:.80,sp:.50},{id:"n_ew",name:"Worse Extension",sn:.72,sp:.60},{id:"n_fw",name:"Worse Flexion",sn:.72,sp:.58},{id:"n_cent",name:"Centralization",sn:.65,sp:.70},{id:"n_trau",name:"Hx Trauma",sn:.70,sp:.60},{id:"n_lher",name:"L'hermitte's +",sn:.35,sp:.95},{id:"n_fhp",name:"FHP",sn:.60,sp:.40}]}
    ],
    conditions:[
      {id:"cervical_radiculopathy",name:"Cervical Radiculopathy",prior:.25,color:"#E63946",desc:"Nerve root compression",tids:["n_spur","n_ultt","n_dist","n_sabd","n_vals","n_dtr","n_myo","n_derm"]},
      {id:"cervicogenic_ha",name:"Cervicogenic HA",prior:.18,color:"#457B9D",desc:"C1–C2 origin headache",tids:["n_cfrt","n_ucp","n_uha","n_nprov"]},
      {id:"cervical_facet",name:"Cervical Facet",prior:.30,color:"#2A9D8F",desc:"Zygapophyseal dysfunction",tids:["n_er","n_fp","n_ax","n_ew"]},
      {id:"cervical_disc",name:"Discogenic Neck",prior:.12,color:"#E9C46A",desc:"Disc-mediated axial pain",tids:["n_ac","n_fw","n_cent"]},
      {id:"myofascial_neck",name:"Myofascial Pain",prior:.35,color:"#F4A261",desc:"Trigger point-driven",tids:["n_trp","n_rs","n_fhp"]},
      {id:"uc_instability",name:"UC Instability",prior:.03,color:"#9B2226",desc:"Ligamentous laxity — REFER",tids:["n_sp","n_alar","n_trau","n_lher"]}
    ]},
  low_back: { id:"low_back",label:"Low Back Pain",icon:"◈",color:"#E76F51",
    clusters:[
      {id:"lc_n",name:"Neural Tension",desc:"SLR, slump",tests:[
        {id:"lb_slr",name:"SLR",sn:.92,sp:.28,c:"vd Windt 10"},{id:"lb_xslr",name:"Crossed SLR",sn:.28,sp:.90},{id:"lb_slump",name:"Slump",sn:.84,sp:.83,c:"Majlesi 08"}]},
      {id:"lc_ne",name:"Neuro Screen",desc:"L4–S1",tests:[
        {id:"lb_dtr",name:"Diminished DTR",sn:.29,sp:.78},{id:"lb_mot",name:"Motor Deficit",sn:.40,sp:.79},{id:"lb_sen",name:"Sensory Deficit",sn:.61,sp:.63}]},
      {id:"lc_sij",name:"SIJ Provocation",desc:"Laslett cluster",tests:[
        {id:"lb_dist",name:"SIJ Distraction",sn:.60,sp:.81,c:"Laslett 05"},{id:"lb_th",name:"Thigh Thrust",sn:.88,sp:.69},{id:"lb_comp",name:"SIJ Compression",sn:.69,sp:.69},{id:"lb_sac",name:"Sacral Thrust",sn:.63,sp:.75}]},
      {id:"lc_fd",name:"Facet / Disc",desc:"Extension-rotation",tests:[
        {id:"lb_er",name:"Ext-Rotation",sn:.72,sp:.58},{id:"lb_kemp",name:"Kemp's",sn:.68,sp:.62}]},
      {id:"lc_hx",name:"History",desc:"Patterns",tests:[
        {id:"lb_leg",name:"Leg > Back Pain",sn:.75,sp:.60},{id:"lb_clau",name:"Neurogenic Claudication",sn:.82,sp:.78},{id:"lb_sit",name:"Relief Sitting/Flex",sn:.80,sp:.70},{id:"lb_fort",name:"Fortin's (PSIS)",sn:.76,sp:.72},{id:"lb_eag",name:"Worse Extension",sn:.75,sp:.55},{id:"lb_fag",name:"Worse Flex/Sit",sn:.80,sp:.55},{id:"lb_cen",name:"Centralization",sn:.70,sp:.68},{id:"lb_norm",name:"Normal Neuro",sn:.90,sp:.25}]}
    ],
    conditions:[
      {id:"lbp_disc_rad",name:"Disc + Radiculopathy",prior:.22,color:"#E63946",desc:"Disc compressing nerve root",tids:["lb_slr","lb_xslr","lb_slump","lb_dtr","lb_mot","lb_sen","lb_leg"]},
      {id:"lbp_stenosis",name:"Lumbar Stenosis",prior:.12,color:"#6D597A",desc:"Canal narrowing",tids:["lb_clau","lb_sit"]},
      {id:"lbp_sij",name:"SIJ Dysfunction",prior:.20,color:"#F4A261",desc:"Sacroiliac joint",tids:["lb_dist","lb_th","lb_comp","lb_sac","lb_fort"]},
      {id:"lbp_facet",name:"Lumbar Facet",prior:.25,color:"#2A9D8F",desc:"Zygapophyseal pain",tids:["lb_er","lb_kemp","lb_eag"]},
      {id:"lbp_disc_nrad",name:"Discogenic LBP",prior:.20,color:"#264653",desc:"Internal disc disruption",tids:["lb_fag","lb_cen"]},
      {id:"lbp_myofascial",name:"Myofascial LBP",prior:.30,color:"#E9C46A",desc:"Muscular origin",tids:["lb_norm"]}
    ]},
  shoulder: { id:"shoulder",label:"Shoulder",icon:"◇",color:"#6D597A",
    clusters:[
      {id:"sc_i",name:"Impingement",desc:"Subacromial",tests:[
        {id:"s_hk",name:"Hawkins-Kennedy",sn:.79,sp:.59,c:"Hegedus 08"},{id:"s_nr",name:"Neer's",sn:.79,sp:.53},{id:"s_arc",name:"Painful Arc",sn:.76,sp:.60},{id:"s_ec",name:"Empty Can",sn:.69,sp:.62},{id:"s_da",name:"Drop Arm",sn:.27,sp:.88}]},
      {id:"sc_rc",name:"RC Integrity",desc:"Lag signs",tests:[
        {id:"s_erl",name:"ER Lag",sn:.70,sp:.89,c:"Hertel 96"},{id:"s_horn",name:"Hornblower's",sn:.55,sp:.93},{id:"s_lo",name:"Lift-Off",sn:.62,sp:.85}]},
      {id:"sc_in",name:"GH Instability",desc:"Apprehension",tests:[
        {id:"s_app",name:"Apprehension",sn:.72,sp:.96,c:"Hegedus 08"},{id:"s_rel",name:"Relocation",sn:.68,sp:.92},{id:"s_sul",name:"Sulcus",sn:.28,sp:.97}]},
      {id:"sc_ac",name:"AC Joint",desc:"Cross-body",tests:[
        {id:"s_cb",name:"Cross-Body",sn:.77,sp:.79},{id:"s_as",name:"AC Shear",sn:.72,sp:.85}]},
      {id:"sc_bi",name:"Biceps/Labrum",desc:"Speed's, Yergason's",tests:[
        {id:"s_sp",name:"Speed's",sn:.69,sp:.56},{id:"s_ye",name:"Yergason's",sn:.43,sp:.79}]},
      {id:"sc_ca",name:"Capsular",desc:"Frozen shoulder",tests:[
        {id:"s_erl2",name:"ER Loss >50%",sn:.90,sp:.85},{id:"s_cor",name:"Coracoid Pain",sn:.96,sp:.87},{id:"s_cap",name:"Capsular Pattern",sn:.85,sp:.80}]},
      {id:"sc_hx",name:"History",desc:"Patterns",tests:[
        {id:"s_ni",name:"Night Pain",sn:.75,sp:.48},{id:"s_wk",name:"Weakness",sn:.78,sp:.72},{id:"s_at",name:"Atrophy",sn:.40,sp:.92},{id:"s_tt",name:"AC TTP",sn:.88,sp:.72},{id:"s_ant",name:"Anterior Pain",sn:.80,sp:.55},{id:"s_hd",name:"Hx Dislocation",sn:.65,sp:.92}]}
    ],
    conditions:[
      {id:"rc_tendinopathy",name:"RC Tendinopathy",prior:.35,color:"#E76F51",desc:"Impingement",tids:["s_hk","s_nr","s_arc","s_ec","s_da","s_ni"]},
      {id:"rc_tear",name:"RC Tear",prior:.12,color:"#9B2226",desc:"Full-thickness tear",tids:["s_erl","s_horn","s_lo","s_da","s_wk","s_at"]},
      {id:"frozen_shoulder",name:"Adhesive Capsulitis",prior:.10,color:"#457B9D",desc:"Capsular restriction",tids:["s_erl2","s_cor","s_cap"]},
      {id:"ac_joint",name:"AC Joint",prior:.15,color:"#2A9D8F",desc:"Sprain/OA",tids:["s_cb","s_as","s_tt"]},
      {id:"biceps_slap",name:"Biceps/SLAP",prior:.10,color:"#E9C46A",desc:"LHB/labral",tids:["s_sp","s_ye","s_ant"]},
      {id:"gh_instability",name:"GH Instability",prior:.08,color:"#264653",desc:"Anterior/MDI",tids:["s_app","s_rel","s_sul","s_hd"]}
    ]},
  headache: { id:"headache",label:"Headache",icon:"◎",color:"#264653",
    clusters:[
      {id:"hc_c",name:"Cervical",desc:"CFRT, UC palp",tests:[
        {id:"h_cfrt",name:"Flex-Rotation",sn:.91,sp:.90,c:"Ogince 07"},{id:"h_ucp",name:"C1–C2 Palp",sn:.82,sp:.79}]},
      {id:"hc_ch",name:"HA Features",desc:"Quality, distribution",tests:[
        {id:"h_np",name:"Neck Precedes HA",sn:.80,sp:.72},{id:"h_sl",name:"Side-Locked",sn:.85,sp:.65},{id:"h_pu",name:"Pulsating",sn:.80,sp:.70},{id:"h_pr",name:"Pressing",sn:.80,sp:.60},{id:"h_bi",name:"Bilateral",sn:.85,sp:.50},{id:"h_orb",name:"Orbital",sn:.92,sp:.65},{id:"h_dur",name:"15–180 min",sn:.88,sp:.75}]},
      {id:"hc_as",name:"Associated Sx",desc:"Autonomic, nausea",tests:[
        {id:"h_na",name:"Nausea",sn:.75,sp:.78},{id:"h_ph",name:"Photo/Phono",sn:.82,sp:.72},{id:"h_au",name:"Autonomic",sn:.90,sp:.88},{id:"h_re",name:"Restless",sn:.82,sp:.80},{id:"h_nn",name:"No Nausea",sn:.82,sp:.60}]},
      {id:"hc_mo",name:"Modifiers",desc:"Activity, meds",tests:[
        {id:"h_aw",name:"Worse Activity",sn:.78,sp:.65},{id:"h_na2",name:"NOT Worse Activity",sn:.75,sp:.62},{id:"h_ci",name:"Circadian",sn:.70,sp:.85},{id:"h_da",name:"≥15d/mo",sn:.90,sp:.70},{id:"h_an",name:"Analgesic >10d/mo",sn:.92,sp:.82},{id:"h_pe",name:"Pericranial TTP",sn:.70,sp:.55}]}
    ],
    conditions:[
      {id:"cervicogenic",name:"Cervicogenic HA",prior:.20,color:"#457B9D",desc:"Cervical origin",tids:["h_cfrt","h_ucp","h_np","h_sl"]},
      {id:"migraine",name:"Migraine",prior:.30,color:"#6D597A",desc:"Pulsating, nausea, photo",tids:["h_pu","h_na","h_ph","h_aw"]},
      {id:"tension_ha",name:"Tension-Type",prior:.35,color:"#E9C46A",desc:"Bilateral pressing",tids:["h_pr","h_bi","h_nn","h_na2","h_pe"]},
      {id:"cluster_ha",name:"Cluster HA",prior:.04,color:"#E63946",desc:"Orbital + autonomic",tids:["h_orb","h_au","h_dur","h_re","h_ci"]},
      {id:"moh",name:"Med Overuse HA",prior:.08,color:"#F4A261",desc:"Analgesic overuse",tids:["h_da","h_an"]}
    ]}
};

// ═══ OUTCOME MEASURE DEFINITIONS (scales + MCID for charting) ═══
const OM = {
  NDI:   { name:"NDI", full:"Neck Disability Index", range:[0,50], mcid:7, direction:"lower", cite:"Young 2009", unit:"pts" },
  NPRS:  { name:"NPRS", full:"Numeric Pain Rating", range:[0,10], mcid:2, direction:"lower", cite:"Childs 2005", unit:"/10" },
  ODI:   { name:"ODI", full:"Oswestry Disability Index", range:[0,100], mcid:6, direction:"lower", cite:"Ostelo 2008", unit:"%" },
  "HIT-6": { name:"HIT-6", full:"Headache Impact Test", range:[36,78], mcid:6, direction:"lower", cite:"Smelt 2014", unit:"pts" },
  QuickDASH: { name:"QuickDASH", full:"Quick DASH", range:[0,100], mcid:8, direction:"lower", cite:"Mintken 2009", unit:"pts" },
  SPADI: { name:"SPADI", full:"Shoulder Pain & Disability", range:[0,100], mcid:13, direction:"lower", cite:"Roy 2009", unit:"pts" },
  MIDAS: { name:"MIDAS", full:"Migraine Disability Assessment", range:[0,100], mcid:null, direction:"lower", unit:"pts" },
  WOSI:  { name:"WOSI", full:"Western Ontario Shoulder Instab.", range:[0,2100], mcid:252, direction:"lower", cite:"Kirkley 1998", unit:"pts" },
};

// ═══ BAYESIAN ENGINE ═══
function bMap(r){const m={};r.clusters.forEach(c=>c.tests.forEach(t=>{m[t.id]=t}));return m}
function bayes(reg,res){
  const m=bMap(reg);
  return reg.conditions.map(c=>{
    let odds=c.prior/(1-c.prior);const ap=[];
    c.tids.forEach(tid=>{const r2=res[tid];if(!r2)return;const t=m[tid];if(!t)return;
      const lr=r2==="+"?t.sn/(1-t.sp):(1-t.sn)/t.sp;odds*=lr;ap.push({n:t.name,r:r2,lr})});
    return{...c,post:Math.min(Math.max(odds/(1+odds),.001),.999),ap}
  }).sort((a,b)=>b.post-a.post);
}

// ═══ UI COMPONENTS ═══
const Tri=({v,set})=>(
  <div style={{display:"flex",borderRadius:5,overflow:"hidden",border:"1px solid #2a2a3a",flexShrink:0}}>
    {[{k:"+",c:"#2A9D8F"},{k:null,c:"#1a1a2e"},{k:"-",c:"#E63946"}].map((o,i)=>
      <button key={i} onClick={()=>set(o.k)} style={{padding:"4px 10px",border:"none",cursor:"pointer",fontSize:13,fontWeight:v===o.k?700:400,background:v===o.k&&o.k?o.c:v===o.k?"#1a1a2e":"transparent",color:v===o.k&&o.k?"#fff":v===o.k?"#666":"#444"}}>{o.k||"○"}</button>)}
  </div>
);

const Bar=({c,i})=>{
  const p=(c.post*100).toFixed(1),top=i===0;
  return <div style={{marginBottom:6,background:top?c.color+"0a":"transparent",borderRadius:8,padding:"9px 12px",border:`1px solid ${top?c.color+"44":"#1a1a2e"}`}}>
    <div style={{display:"flex",justifyContent:"space-between",alignItems:"center",marginBottom:4}}>
      <div style={{display:"flex",alignItems:"center",gap:5,minWidth:0}}>
        {top&&<span style={{fontSize:8,background:c.color,color:"#fff",padding:"1px 5px",borderRadius:3,fontFamily:"mono",fontWeight:700}}>TOP</span>}
        <span style={{fontSize:12.5,fontWeight:top?700:500,color:top?"#e8e8ff":"#999",overflow:"hidden",textOverflow:"ellipsis",whiteSpace:"nowrap"}}>{c.name}</span>
      </div>
      <span style={{fontSize:16,fontWeight:800,color:c.color,fontFamily:"mono"}}>{p}%</span>
    </div>
    <div style={{width:"100%",height:4,background:"#0d0d1a",borderRadius:3,overflow:"hidden",position:"relative"}}>
      <div style={{width:`${p}%`,height:"100%",background:`linear-gradient(90deg,${c.color}88,${c.color})`,borderRadius:3,transition:"width .4s"}}/>
      <div style={{position:"absolute",left:`${c.prior*100}%`,top:0,width:1.5,height:"100%",background:"#fff3"}}/>
    </div>
    <div style={{display:"flex",justifyContent:"space-between",marginTop:2}}>
      <span style={{fontSize:8,color:"#444",fontFamily:"mono"}}>Prior {(c.prior*100).toFixed(0)}%</span>
      <span style={{fontSize:8,color:"#444",fontFamily:"mono"}}>{c.ap.length} tests</span>
    </div>
  </div>;
};

// ═══ TREATMENT PLAN VIEW ═══
const TxPlan=({cid,color,onBack})=>{
  const tx=TX[cid];
  const[op,setOp]=useState({session:true,freq:false,prog:false,reexam:false,outcomes:false,contras:false,hep:false});
  if(!tx) return <div style={{padding:20,textAlign:"center",color:"#555",fontSize:11,fontFamily:"mono"}}>No Tx plan for this condition yet.</div>;
  const Sec=({k,title,children})=>(
    <div style={{marginBottom:6}}>
      <button onClick={()=>setOp(p=>({...p,[k]:!p[k]}))} style={{width:"100%",padding:"8px 10px",background:op[k]?color+"0c":"transparent",border:`1px solid ${op[k]?color+"33":"#1a1a2e"}`,borderRadius:op[k]?"6px 6px 0 0":6,cursor:"pointer",textAlign:"left"}}>
        <span style={{fontSize:12,fontWeight:600,color:op[k]?"#e8e8ff":"#888"}}>{op[k]?"▾":"▸"} {title}</span>
      </button>
      {op[k]&&<div style={{border:`1px solid ${color}22`,borderTop:"none",borderRadius:"0 0 6px 6px",padding:"10px 12px",background:"#0c0c1a"}}>{children}</div>}
    </div>
  );
  return <div>
    <button onClick={onBack} style={{padding:"4px 10px",border:"1px solid #2a2a3a",borderRadius:5,background:"transparent",color:"#666",fontSize:10,fontFamily:"mono",cursor:"pointer",marginBottom:10}}>← DDx Results</button>
    <Sec k="session" title="15-Minute Session Protocol">
      {tx.session.map((s,i)=><div key={i} style={{marginBottom:i<tx.session.length-1?10:0}}>
        <div style={{display:"flex",gap:8,alignItems:"baseline",marginBottom:3}}>
          <span style={{fontSize:10,color,fontFamily:"mono",fontWeight:700,whiteSpace:"nowrap",minWidth:50}}>{s.t} min</span>
          <span style={{fontSize:12.5,fontWeight:700,color:"#e8e8ff"}}>{s.p}</span>
        </div>
        {s.tasks.map((t,j)=><div key={j} style={{fontSize:11,color:"#aaa",paddingLeft:58,marginBottom:2,lineHeight:1.4}}>• {t}</div>)}
      </div>)}
    </Sec>
    <Sec k="freq" title="Frequency & Duration">
      {tx.freq.split("\n").map((l,i)=><div key={i} style={{fontSize:11.5,color:"#ccc",marginBottom:3}}>{l}</div>)}
      <div style={{fontSize:11.5,color:"#e8e8ff",marginTop:6,fontWeight:600}}>{tx.visits}</div>
    </Sec>
    <Sec k="prog" title="Prognosis">
      <div style={{marginBottom:6}}><div style={{fontSize:9,fontFamily:"mono",color,textTransform:"uppercase",letterSpacing:1,marginBottom:2}}>Timeline</div><div style={{fontSize:11.5,color:"#ccc",lineHeight:1.45}}>{tx.prog.t}</div></div>
      <div style={{marginBottom:6}}><div style={{fontSize:9,fontFamily:"mono",color,textTransform:"uppercase",letterSpacing:1,marginBottom:2}}>Expected</div><div style={{fontSize:11.5,color:"#ccc",lineHeight:1.45}}>{tx.prog.e}</div></div>
      <div><div style={{fontSize:9,fontFamily:"mono",color:"#555",textTransform:"uppercase",letterSpacing:1,marginBottom:2}}>Factors</div><div style={{fontSize:10.5,color:"#888",lineHeight:1.45}}>{tx.prog.f}</div></div>
    </Sec>
    {tx.reexam&&<Sec k="reexam" title="Re-Exam Decision Rules">
      <div style={{marginBottom:10}}>
        <div style={{fontSize:9,fontFamily:"mono",color,textTransform:"uppercase",letterSpacing:1,marginBottom:4}}>Schedule</div>
        {tx.reexam.schedule.map((s,i)=><div key={i} style={{display:"flex",gap:8,marginBottom:4,alignItems:"baseline"}}>
          <span style={{fontSize:10,fontFamily:"mono",color,fontWeight:700,minWidth:90,flexShrink:0}}>{s.visit}</span>
          <span style={{fontSize:11,color:"#bbb"}}>{s.focus}</span>
        </div>)}
      </div>
      <div style={{marginBottom:10}}>
        <div style={{fontSize:9,fontFamily:"mono",color,textTransform:"uppercase",letterSpacing:1,marginBottom:4}}>MCID Thresholds</div>
        {tx.reexam.mcid.map((m,i)=><div key={i} style={{display:"flex",gap:6,marginBottom:3,alignItems:"baseline"}}>
          <span style={{fontSize:10,fontFamily:"mono",color:"#e8e8ff",fontWeight:600,minWidth:80,flexShrink:0}}>{m.measure}</span>
          <span style={{fontSize:11,color:"#aaa"}}>{m.threshold}</span>
          {m.cite&&<span style={{fontSize:8,color:"#555",fontFamily:"mono",flexShrink:0}}>{m.cite}</span>}
        </div>)}
      </div>
      <div style={{padding:"8px 10px",background:"#2A9D8F08",border:"1px solid #2A9D8F22",borderRadius:5,marginBottom:6}}>
        <div style={{fontSize:9,fontFamily:"mono",color:"#2A9D8F",textTransform:"uppercase",letterSpacing:1,marginBottom:2}}>✓ On Track</div>
        <div style={{fontSize:11,color:"#bbb",lineHeight:1.45}}>{tx.reexam.onTrack}</div>
      </div>
      <div style={{padding:"8px 10px",background:"#F4A26108",border:"1px solid #F4A26122",borderRadius:5,marginBottom:6}}>
        <div style={{fontSize:9,fontFamily:"mono",color:"#F4A261",textTransform:"uppercase",letterSpacing:1,marginBottom:2}}>✗ Off Track</div>
        <div style={{fontSize:11,color:"#bbb",lineHeight:1.45}}>{tx.reexam.offTrack}</div>
      </div>
      <div style={{padding:"8px 10px",background:"#E6394608",border:"1px solid #E6394622",borderRadius:5}}>
        <div style={{fontSize:9,fontFamily:"mono",color:"#E63946",textTransform:"uppercase",letterSpacing:1,marginBottom:2}}>⚠ Warning Signs</div>
        <div style={{fontSize:11,color:"#bbb",lineHeight:1.45}}>{tx.reexam.warningSign}</div>
      </div>
    </Sec>}
    <Sec k="outcomes" title="Outcome Measures">
      <div style={{display:"flex",flexWrap:"wrap",gap:5}}>{tx.outcomes.map((o,i)=><span key={i} style={{fontSize:10,padding:"3px 8px",background:color+"12",border:`1px solid ${color}33`,borderRadius:4,color,fontFamily:"mono"}}>{o}</span>)}</div>
    </Sec>
    <Sec k="contras" title="Contraindications & Red Flags">
      {tx.contras.map((c2,i)=><div key={i} style={{fontSize:11.5,color:c2.l==="r"?"#E63946":"#F4A261",marginBottom:3}}>⚠ {c2.t}</div>)}
      <div style={{marginTop:8,padding:"6px 8px",background:"#E6394608",border:"1px solid #E6394622",borderRadius:5}}>
        <div style={{fontSize:9,fontFamily:"mono",color:"#E63946",textTransform:"uppercase",letterSpacing:1,marginBottom:2}}>Referral</div>
        <div style={{fontSize:10.5,color:"#ccc",lineHeight:1.4}}>{tx.refer}</div>
      </div>
    </Sec>
    <Sec k="hep" title="Home Exercise Program">
      {tx.hep.map((h,i)=><div key={i} style={{fontSize:11.5,color:"#ccc",marginBottom:3,lineHeight:1.4}}>→ {h}</div>)}
    </Sec>
  </div>;
};

// ═══ OUTCOME TRACKER ═══
const Tracker=({cid,color})=>{
  const tx=TX[cid];
  const[scores,setScores]=useState({});
  const[addingTo,setAddingTo]=useState(null);
  const[inputVal,setInputVal]=useState("");
  const[inputLabel,setInputLabel]=useState("");

  if(!tx) return null;
  // Get trackable measures (ones that exist in OM lookup)
  const measures=tx.outcomes.filter(o=>OM[o]);
  if(!measures.length) return <div style={{padding:16,textAlign:"center",color:"#555",fontSize:11,fontFamily:"mono"}}>No trackable outcome measures for this condition.</div>;

  const addScore=(measure)=>{
    const val=parseFloat(inputVal);
    if(isNaN(val)) return;
    const label=inputLabel||`Visit ${(scores[measure]||[]).length+1}`;
    setScores(p=>({...p,[measure]:[...(p[measure]||[]),{v:val,label,ts:Date.now()}]}));
    setInputVal("");setInputLabel("");setAddingTo(null);
  };
  const removeScore=(measure,idx)=>{
    setScores(p=>({...p,[measure]:(p[measure]||[]).filter((_,i)=>i!==idx)}));
  };

  // SVG Chart
  const Chart=({measure})=>{
    const om=OM[measure];
    const data=scores[measure]||[];
    if(data.length<1) return <div style={{padding:12,textAlign:"center",color:"#333",fontSize:10,fontFamily:"mono"}}>No data yet — add first score below</div>;
    const W=320,H=140,PAD={t:18,r:14,b:28,l:36};
    const cw=W-PAD.l-PAD.r,ch=H-PAD.t-PAD.b;
    const yMin=om.range[0],yMax=om.range[1];
    const xPts=data.map((_,i)=>PAD.l+(i/(Math.max(data.length-1,1)))*cw);
    const yPts=data.map(d=>PAD.t+ch-(((d.v-yMin)/(yMax-yMin))*ch));
    const mcidY=om.mcid&&data.length>0?PAD.t+ch-((((data[0].v-om.mcid)-yMin)/(yMax-yMin))*ch):null;
    // Line path
    const linePath=data.length>1?xPts.map((x,i)=>`${i===0?"M":"L"}${x},${yPts[i]}`).join(" "):"";
    // MCID target line (baseline minus MCID for "lower is better")
    const mcidTarget=om.mcid&&data.length>0?(om.direction==="lower"?data[0].v-om.mcid:data[0].v+om.mcid):null;
    const mcidTargetY=mcidTarget!==null?PAD.t+ch-(((mcidTarget-yMin)/(yMax-yMin))*ch):null;
    // Status
    const latest=data[data.length-1].v;
    const baseline=data[0].v;
    const change=om.direction==="lower"?baseline-latest:latest-baseline;
    const metMCID=om.mcid?change>=om.mcid:false;

    return <svg width="100%" viewBox={`0 0 ${W} ${H}`} style={{display:"block"}}>
      {/* Grid lines */}
      {[0,.25,.5,.75,1].map(f=>{const y=PAD.t+ch*(1-f);return <g key={f}><line x1={PAD.l} x2={W-PAD.r} y1={y} y2={y} stroke="#1a1a2e" strokeWidth={.5}/><text x={PAD.l-4} y={y+3} textAnchor="end" fill="#333" fontSize={7} fontFamily="monospace">{Math.round(yMin+f*(yMax-yMin))}</text></g>})}
      {/* MCID target line */}
      {mcidTargetY!==null&&mcidTargetY>=PAD.t&&mcidTargetY<=PAD.t+ch&&<>
        <line x1={PAD.l} x2={W-PAD.r} y1={mcidTargetY} y2={mcidTargetY} stroke="#2A9D8F" strokeWidth={1} strokeDasharray="4,3" opacity={.7}/>
        <text x={W-PAD.r+2} y={mcidTargetY+3} fill="#2A9D8F" fontSize={6} fontFamily="monospace">MCID</text>
      </>}
      {/* Data line */}
      {data.length>1&&<path d={linePath} fill="none" stroke={color} strokeWidth={2} strokeLinejoin="round"/>}
      {/* Data points */}
      {data.map((d,i)=><g key={i}>
        <circle cx={xPts[i]} cy={yPts[i]} r={4} fill={color} stroke="#0a0a16" strokeWidth={2}/>
        <text x={xPts[i]} y={H-PAD.b+14} textAnchor="middle" fill="#555" fontSize={7} fontFamily="monospace">{d.label.replace("Visit ","V")}</text>
      </g>)}
      {/* Status badge */}
      {data.length>=2&&<g>
        <rect x={PAD.l} y={2} width={metMCID?80:90} height={14} rx={3} fill={metMCID?"#2A9D8F22":"#F4A26122"} stroke={metMCID?"#2A9D8F44":"#F4A26144"} strokeWidth={.5}/>
        <text x={PAD.l+4} y={11} fill={metMCID?"#2A9D8F":"#F4A261"} fontSize={7} fontFamily="monospace" fontWeight="bold">{metMCID?"✓ MCID MET":"✗ Below MCID"} ({change>0?"+":""}{change.toFixed(1)})</text>
      </g>}
    </svg>;
  };

  return <div>
    {measures.map(measure=>{
      const om=OM[measure];
      const data=scores[measure]||[];
      return <div key={measure} style={{marginBottom:12,border:"1px solid #1a1a2e",borderRadius:8,overflow:"hidden"}}>
        <div style={{padding:"8px 10px",background:"#0d0d1a",display:"flex",justifyContent:"space-between",alignItems:"center"}}>
          <div>
            <div style={{fontSize:12,fontWeight:600,color:"#e8e8ff"}}>{om.name}</div>
            <div style={{fontSize:9,color:"#555",fontFamily:"mono"}}>{om.full} · Range {om.range[0]}–{om.range[1]} · MCID {om.mcid||"N/A"}{om.cite?` · ${om.cite}`:""}</div>
          </div>
          <button onClick={()=>setAddingTo(addingTo===measure?null:measure)} style={{padding:"3px 8px",border:`1px solid ${color}44`,borderRadius:4,background:"transparent",color,fontSize:9,fontFamily:"mono",cursor:"pointer"}}>{addingTo===measure?"Cancel":"+ Add"}</button>
        </div>
        <div style={{padding:"6px 10px",background:"#0a0a16"}}>
          <Chart measure={measure}/>
          {/* Score entry */}
          {addingTo===measure&&<div style={{display:"flex",gap:4,marginTop:6,alignItems:"center"}}>
            <input value={inputLabel} onChange={e=>setInputLabel(e.target.value)} placeholder="Visit #" style={{width:60,padding:"4px 6px",background:"#12122a",border:"1px solid #2a2a3a",borderRadius:4,color:"#e8e8ff",fontSize:10,fontFamily:"mono"}}/>
            <input value={inputVal} onChange={e=>setInputVal(e.target.value)} placeholder="Score" type="number" style={{width:55,padding:"4px 6px",background:"#12122a",border:"1px solid #2a2a3a",borderRadius:4,color:"#e8e8ff",fontSize:10,fontFamily:"mono"}}/>
            <button onClick={()=>addScore(measure)} style={{padding:"4px 8px",border:`1px solid ${color}`,borderRadius:4,background:color+"18",color,fontSize:10,fontFamily:"mono",cursor:"pointer",fontWeight:700}}>Save</button>
          </div>}
          {/* Data table */}
          {data.length>0&&<div style={{marginTop:6}}>
            {data.map((d,i)=><div key={i} style={{display:"flex",justifyContent:"space-between",alignItems:"center",padding:"2px 0",borderBottom:i<data.length-1?"1px solid #1a1a2e":"none"}}>
              <span style={{fontSize:10,color:"#888",fontFamily:"mono"}}>{d.label}</span>
              <div style={{display:"flex",gap:6,alignItems:"center"}}>
                <span style={{fontSize:11,color:"#e8e8ff",fontWeight:600,fontFamily:"mono"}}>{d.v}{om.unit}</span>
                {i>0&&<span style={{fontSize:9,color:((om.direction==="lower"&&d.v<data[0].v)||(om.direction==="higher"&&d.v>data[0].v))?"#2A9D8F":"#E63946",fontFamily:"mono"}}>
                  {om.direction==="lower"?(data[0].v-d.v>0?"+":"")+(data[0].v-d.v).toFixed(1):(d.v-data[0].v>0?"+":"")+(d.v-data[0].v).toFixed(1)}
                </span>}
                <button onClick={()=>removeScore(measure,i)} style={{padding:"1px 4px",border:"none",background:"transparent",color:"#333",fontSize:9,cursor:"pointer"}}>×</button>
              </div>
            </div>)}
          </div>}
        </div>
      </div>
    })}
  </div>;
};

// ═══ SPINE DIAGRAM ═══
const SPINE_SEGS = [
  { id:"C0",label:"Occiput",region:"cervical",y:0 },
  { id:"C1",label:"Atlas",region:"cervical",y:1 },
  { id:"C2",label:"Axis",region:"cervical",y:2 },
  { id:"C3",label:"C3",region:"cervical",y:3 },
  { id:"C4",label:"C4",region:"cervical",y:4 },
  { id:"C5",label:"C5",region:"cervical",y:5 },
  { id:"C6",label:"C6",region:"cervical",y:6 },
  { id:"C7",label:"C7",region:"cervical",y:7 },
  { id:"T1",label:"T1",region:"thoracic",y:8 },
  { id:"T2",label:"T2",region:"thoracic",y:9 },
  { id:"T3",label:"T3",region:"thoracic",y:10 },
  { id:"T4",label:"T4",region:"thoracic",y:11 },
  { id:"T5",label:"T5",region:"thoracic",y:12 },
  { id:"T6",label:"T6",region:"thoracic",y:13 },
  { id:"T7",label:"T7",region:"thoracic",y:14 },
  { id:"T8",label:"T8",region:"thoracic",y:15 },
  { id:"T9",label:"T9",region:"thoracic",y:16 },
  { id:"T10",label:"T10",region:"thoracic",y:17 },
  { id:"T11",label:"T11",region:"thoracic",y:18 },
  { id:"T12",label:"T12",region:"thoracic",y:19 },
  { id:"L1",label:"L1",region:"lumbar",y:20 },
  { id:"L2",label:"L2",region:"lumbar",y:21 },
  { id:"L3",label:"L3",region:"lumbar",y:22 },
  { id:"L4",label:"L4",region:"lumbar",y:23 },
  { id:"L5",label:"L5",region:"lumbar",y:24 },
  { id:"S1",label:"Sacrum",region:"sacral",y:25 },
  { id:"SI",label:"SI Joint",region:"sacral",y:26 },
];
const REGION_COLORS = { cervical:"#2A9D8F", thoracic:"#457B9D", lumbar:"#E76F51", sacral:"#F4A261" };

const SpineDiagram=({selected,onToggle,regionFilter})=>{
  const W=300,H=520;
  const segs=SPINE_SEGS;
  const segH=H/(segs.length+1);
  // Vertebra widths by region (mimics anatomy)
  const getW=(s)=>s.region==="cervical"?28+s.y*2.5:s.region==="thoracic"?48+Math.sin((s.y-8)/11*Math.PI)*8:s.region==="lumbar"?62-(s.y-20)*2:s.id==="S1"?58:50;
  // Curvature offset (lordosis/kyphosis)
  const getX=(s)=>{
    if(s.region==="cervical") return 150+Math.sin((s.y/7)*Math.PI)*12; // lordosis
    if(s.region==="thoracic") return 150-Math.sin(((s.y-8)/11)*Math.PI)*14; // kyphosis
    if(s.region==="lumbar") return 150+Math.sin(((s.y-20)/4)*Math.PI)*10; // lordosis
    return 150;
  };

  return <svg width="100%" viewBox={`0 0 ${W} ${H}`} style={{display:"block",maxHeight:420}}>
    {/* Spinal cord line */}
    <path d={segs.map((s,i)=>`${i===0?"M":"L"}${getX(s)},${(s.y+1)*segH}`).join(" ")} fill="none" stroke="#1a1a2e" strokeWidth={3} strokeLinecap="round"/>
    {/* Region labels */}
    {["cervical","thoracic","lumbar","sacral"].map(r=>{
      const rSegs=segs.filter(s=>s.region===r);
      const midY=((rSegs[0].y+1+rSegs[rSegs.length-1].y+1)/2)*segH;
      return <text key={r} x={12} y={midY} fill={REGION_COLORS[r]+"66"} fontSize={8} fontFamily="monospace" textAnchor="start" transform={`rotate(-90,12,${midY})`} style={{textTransform:"uppercase",letterSpacing:2}}>{r}</text>;
    })}
    {/* Vertebrae */}
    {segs.map(s=>{
      const cx=getX(s), cy=(s.y+1)*segH;
      const w=getW(s), h=segH*0.7;
      const isSel=selected.includes(s.id);
      const isRegion=!regionFilter||
        (regionFilter==="neck"&&s.region==="cervical")||
        (regionFilter==="low_back"&&(s.region==="lumbar"||s.region==="sacral"))||
        (regionFilter==="shoulder"&&(s.region==="cervical"||s.region==="thoracic"))||
        (regionFilter==="headache"&&s.region==="cervical");
      const col=REGION_COLORS[s.region];
      return <g key={s.id} onClick={()=>onToggle(s.id)} style={{cursor:"pointer"}}>
        {/* Vertebra body */}
        <rect x={cx-w/2} y={cy-h/2} width={w} height={h} rx={s.region==="sacral"?6:4}
          fill={isSel?col+"33":"#0d0d1a"} stroke={isSel?col:isRegion?"#2a2a3a":"#181828"} strokeWidth={isSel?2:1}
          style={{transition:"all .15s"}}/>
        {/* Spinous process */}
        {s.id!=="SI"&&<line x1={cx} y1={cy} x2={cx-(s.region==="thoracic"?18:12)} y2={cy+3}
          stroke={isSel?col+"88":"#1a1a2e"} strokeWidth={isSel?1.5:1} strokeLinecap="round"/>}
        {/* Transverse processes */}
        {s.id!=="SI"&&s.id!=="S1"&&<>
          <line x1={cx-w/2} y1={cy} x2={cx-w/2-8} y2={cy-1} stroke={isSel?col+"66":"#1a1a2e"} strokeWidth={1} strokeLinecap="round"/>
          <line x1={cx+w/2} y1={cy} x2={cx+w/2+8} y2={cy-1} stroke={isSel?col+"66":"#1a1a2e"} strokeWidth={1} strokeLinecap="round"/>
        </>}
        {/* Label */}
        <text x={cx+w/2+14} y={cy+3} fill={isSel?col:isRegion?"#555":"#2a2a3a"} fontSize={isSel?9:8} fontFamily="monospace" fontWeight={isSel?700:400}>{s.label}</text>
        {/* Selection dot */}
        {isSel&&<circle cx={cx+w/2+8} cy={cy} r={2.5} fill={col}/>}
      </g>;
    })}
  </svg>;
};

// ═══ MAIN APP ═══
export default function App(){
  const[rId,setRId]=useState("neck");
  const[res,setRes]=useState({});
  const[op,setOp]=useState({});
  const[view,setView]=useState("assess");
  const[expDx,setExpDx]=useState(null);
  const[txCond,setTxCond]=useState(null);
  const[spineSegs,setSpineSegs]=useState([]);
  const[showSpine,setShowSpine]=useState(false);
  const toggleSeg=id=>setSpineSegs(p=>p.includes(id)?p.filter(s=>s!==id):[...p,id]);

  const reg=R[rId];
  const results=useMemo(()=>bayes(reg,res),[reg,res]);
  const tested=Object.values(res).filter(Boolean).length;
  const switchReg=r=>{setRId(r);setRes({});setOp({});setView("assess");setExpDx(null);setTxCond(null);setSpineSegs([]);setShowSpine(false)};

  return <div style={{minHeight:"100vh",background:"#0a0a16",color:"#e8e8ff",fontFamily:"'Source Sans 3',sans-serif"}}>
    <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700;800&family=Source+Sans+3:wght@300;400;500;600;700;800&display=swap" rel="stylesheet"/>
    <div style={{background:"linear-gradient(180deg,#12122a,#0a0a16)",borderBottom:"1px solid #1a1a2e",padding:"16px 16px 12px"}}>
      <div style={{maxWidth:640,margin:"0 auto"}}>
        <div style={{display:"flex",alignItems:"center",gap:6,marginBottom:2}}>
          <div style={{width:6,height:6,borderRadius:"50%",background:reg.color,boxShadow:`0 0 8px ${reg.color}88`}}/>
          <span style={{fontSize:9,fontFamily:"mono",color:reg.color,textTransform:"uppercase",letterSpacing:2}}>DDx + Treatment · Life Chiropractic</span>
        </div>
        <h1 style={{fontSize:21,fontWeight:800,margin:"2px 0",background:"linear-gradient(135deg,#e8e8ff,#888)",WebkitBackgroundClip:"text",WebkitTextFillColor:"transparent"}}>{reg.label}</h1>
        <p style={{fontSize:10,color:"#444",margin:0,fontFamily:"mono"}}>{tested} findings{results[0]?.ap.length>0?` · Leading: ${results[0].name}`:""}</p>
      </div>
    </div>
    <div style={{maxWidth:640,margin:"0 auto",padding:"10px 16px"}}>
      <div style={{display:"flex",gap:4,marginBottom:8,flexWrap:"wrap"}}>
        {Object.values(R).map(r=><button key={r.id} onClick={()=>switchReg(r.id)} style={{padding:"5px 9px",border:`1px solid ${rId===r.id?r.color:"#1a1a2e"}`,borderRadius:5,cursor:"pointer",fontSize:10,fontFamily:"mono",fontWeight:rId===r.id?700:400,background:rId===r.id?r.color+"18":"transparent",color:rId===r.id?r.color:"#555"}}>{r.icon} {r.label}</button>)}
      </div>
      <div style={{display:"flex",gap:3,marginBottom:12}}>
        {[{k:"assess",l:"Assessment"},{k:"ddx",l:`DDx${tested?` (${tested})`:""}`},{k:"tx",l:"Tx Plan"},{k:"track",l:"Track"}].map(t=>
          <button key={t.k} onClick={()=>setView(t.k)} style={{flex:1,padding:"7px",border:"none",borderRadius:5,cursor:"pointer",fontSize:10,fontFamily:"mono",fontWeight:view===t.k?700:400,background:view===t.k?"#1a1a2e":"transparent",color:view===t.k?"#e8e8ff":"#555",textTransform:"uppercase",letterSpacing:.5}}>{t.l}</button>)}
      </div>

      {view==="assess"&&<div>
        <div style={{fontSize:10,color:"#555",fontFamily:"mono",marginBottom:10}}>Open clusters based on clinical suspicion. Mark tests + or −.</div>
        {reg.clusters.map(cl=>{const isOp=op[cl.id],ct=cl.tests.filter(t=>res[t.id]).length;
          return <div key={cl.id} style={{marginBottom:6}}>
            <button onClick={()=>setOp(p=>({...p,[cl.id]:!p[cl.id]}))} style={{width:"100%",display:"flex",justifyContent:"space-between",alignItems:"center",padding:"9px 10px",border:`1px solid ${isOp?reg.color+"44":"#1a1a2e"}`,borderRadius:isOp?"7px 7px 0 0":7,cursor:"pointer",background:isOp?reg.color+"0c":"transparent",textAlign:"left"}}>
              <div><div style={{fontSize:12.5,fontWeight:600,color:isOp?"#e8e8ff":"#999"}}>{isOp?"▾":"▸"} {cl.name}</div><div style={{fontSize:9,color:"#555",fontFamily:"mono",marginTop:1}}>{cl.desc}</div></div>
              <div style={{display:"flex",gap:5,alignItems:"center",flexShrink:0}}>
                {ct>0&&<span style={{fontSize:9,color:reg.color,fontFamily:"mono",fontWeight:700}}>{ct}/{cl.tests.length}</span>}
                <span style={{fontSize:9,color:"#444",fontFamily:"mono"}}>{cl.tests.length}</span>
              </div>
            </button>
            {isOp&&<div style={{border:`1px solid ${reg.color}22`,borderTop:"none",borderRadius:"0 0 7px 7px",padding:"8px 10px",background:"#0c0c1a"}}>
              {cl.tests.map(t=><div key={t.id} style={{marginBottom:8}}>
                <div style={{display:"flex",alignItems:"center",gap:7,marginBottom:1}}>
                  <Tri v={res[t.id]||null} set={v=>setRes(p=>({...p,[t.id]:v}))}/>
                  <span style={{fontSize:12,color:res[t.id]?"#e8e8ff":"#aaa"}}>{t.name}</span>
                </div>
                {t.c&&<div style={{marginLeft:85,fontSize:8,color:reg.color+"77",fontFamily:"mono"}}>Sn={t.sn} Sp={t.sp} · {t.c}</div>}
              </div>)}
            </div>}
          </div>})}
        <button onClick={()=>setView("ddx")} style={{width:"100%",padding:"10px",marginTop:8,border:`1px solid ${reg.color}`,borderRadius:7,background:reg.color+"11",color:reg.color,fontSize:12,fontWeight:700,fontFamily:"mono",cursor:"pointer"}}>View DDx Results →</button>
      </div>}

      {view==="ddx"&&<div>
        {tested>0&&results[0]&&<div style={{background:results[0].color+"0c",border:`1px solid ${results[0].color}33`,borderRadius:8,padding:"10px 12px",marginBottom:12}}>
          <div style={{fontSize:8,fontFamily:"mono",color:results[0].color,textTransform:"uppercase",letterSpacing:1.5,marginBottom:2}}>Leading Diagnosis</div>
          <div style={{fontSize:17,fontWeight:800,color:"#e8e8ff",marginBottom:1}}>{results[0].name}</div>
          <div style={{fontSize:10.5,color:"#666",lineHeight:1.3}}>{results[0].desc}</div>
          <div style={{marginTop:5,display:"flex",justifyContent:"space-between",alignItems:"center"}}>
            <span style={{fontSize:10,fontFamily:"mono",color:"#555"}}>Post: <span style={{color:results[0].color,fontWeight:700}}>{(results[0].post*100).toFixed(1)}%</span></span>
            <button onClick={()=>{setTxCond(results[0].id);setView("tx")}} style={{padding:"4px 10px",border:`1px solid ${results[0].color}`,borderRadius:4,background:results[0].color+"18",color:results[0].color,fontSize:10,fontWeight:700,fontFamily:"mono",cursor:"pointer"}}>Tx Plan →</button>
          </div>
        </div>}
        {tested===0&&<div style={{padding:16,textAlign:"center",color:"#555",fontSize:11,border:"1px dashed #2a2a3a",borderRadius:8,fontFamily:"mono",marginBottom:10}}>Priors only — go back to record findings.</div>}
        {results.map((c,i)=><div key={c.id}>
          <div onClick={()=>setExpDx(expDx===c.id?null:c.id)} style={{cursor:"pointer"}}><Bar c={c} i={i}/></div>
          {expDx===c.id&&<div style={{margin:"-2px 0 6px",padding:"7px 9px",background:"#0d0d1a",borderRadius:5,border:"1px solid #1a1a2e"}}>
            {c.ap.length>0?<>{c.ap.map((a,j)=><div key={j} style={{display:"flex",justifyContent:"space-between",padding:"2px 0",borderBottom:j<c.ap.length-1?"1px solid #1a1a2e":"none"}}>
              <div style={{display:"flex",gap:4,alignItems:"center"}}><span style={{fontSize:9,fontWeight:700,color:a.r==="+"?"#2A9D8F":"#E63946",fontFamily:"mono"}}>{a.r}</span><span style={{fontSize:10,color:"#888"}}>{a.n}</span></div>
              <span style={{fontSize:10,fontWeight:700,color:a.lr>1?"#2A9D8F":"#E63946",fontFamily:"mono"}}>LR={a.lr.toFixed(2)}</span>
            </div>)}</>:<div style={{fontSize:10,color:"#555"}}>No tests — prior only</div>}
            <button onClick={()=>{setTxCond(c.id);setView("tx")}} style={{marginTop:6,padding:"4px 8px",border:`1px solid ${c.color}44`,borderRadius:4,background:"transparent",color:c.color,fontSize:9,fontFamily:"mono",cursor:"pointer",width:"100%"}}>View Treatment Plan →</button>
          </div>}
        </div>)}
        <div style={{marginTop:12,padding:"8px 10px",background:"#0d0d1a",borderRadius:6,border:"1px solid #1a1a2e"}}>
          <div style={{fontSize:9,fontFamily:"mono",color:"#444",letterSpacing:1,marginBottom:2}}>METHOD</div>
          <div style={{fontSize:10,color:"#555"}}>Bayes' — LR+=Sn/(1−Sp), LR−=(1−Sn)/Sp. Post-test odds = prior × ΠLR. Decision support only.</div>
        </div>
        <button onClick={()=>setView("assess")} style={{width:"100%",padding:"8px",marginTop:8,border:"1px solid #2a2a3a",borderRadius:6,background:"transparent",color:"#666",fontSize:11,fontFamily:"mono",cursor:"pointer"}}>← Assessment</button>
      </div>}

      {view==="tx"&&<div>
        {!txCond?<div>
          <div style={{fontSize:10,color:"#555",fontFamily:"mono",marginBottom:10}}>Select a condition:</div>
          {results.map(c=><button key={c.id} onClick={()=>setTxCond(c.id)} style={{width:"100%",padding:"10px 12px",marginBottom:5,border:`1px solid ${c.color}33`,borderRadius:7,background:"transparent",cursor:"pointer",display:"flex",justifyContent:"space-between",alignItems:"center",textAlign:"left"}}>
            <div><div style={{fontSize:13,fontWeight:600,color:"#e8e8ff"}}>{c.name}</div><div style={{fontSize:9,color:"#555"}}>{c.desc}</div></div>
            <span style={{fontSize:12,fontWeight:700,color:c.color,fontFamily:"mono"}}>{(c.post*100).toFixed(1)}%</span>
          </button>)}
        </div>
        :<TxPlan cid={txCond} color={reg.conditions.find(c=>c.id===txCond)?.color||reg.color} onBack={()=>{setTxCond(null);setView("ddx")}}/>}
      </div>}

      {view==="track"&&<div>
        {!txCond?<div>
          <div style={{fontSize:10,color:"#555",fontFamily:"mono",marginBottom:10}}>Select a condition to track outcomes:</div>
          {results.map(c=>{
            const tx2=TX[c.id];
            const trackable=tx2?.outcomes?.filter(o=>OM[o])?.length||0;
            return <button key={c.id} onClick={()=>setTxCond(c.id)} style={{width:"100%",padding:"10px 12px",marginBottom:5,border:`1px solid ${c.color}33`,borderRadius:7,background:"transparent",cursor:"pointer",display:"flex",justifyContent:"space-between",alignItems:"center",textAlign:"left"}}>
              <div><div style={{fontSize:13,fontWeight:600,color:"#e8e8ff"}}>{c.name}</div><div style={{fontSize:9,color:"#555",fontFamily:"mono"}}>{trackable} trackable measures</div></div>
              <span style={{fontSize:12,fontWeight:700,color:c.color,fontFamily:"mono"}}>{(c.post*100).toFixed(1)}%</span>
            </button>
          })}
        </div>:<div>
          <div style={{display:"flex",alignItems:"center",gap:8,marginBottom:12}}>
            <button onClick={()=>setTxCond(null)} style={{padding:"4px 10px",border:"1px solid #2a2a3a",borderRadius:5,background:"transparent",color:"#666",fontSize:10,fontFamily:"mono",cursor:"pointer"}}>← Back</button>
            <div>
              <div style={{fontSize:15,fontWeight:700,color:"#e8e8ff"}}>{reg.conditions.find(c=>c.id===txCond)?.name} — Outcomes</div>
              <div style={{fontSize:9,color:"#555",fontFamily:"mono"}}>Enter scores at intake, re-exam, discharge · MCID threshold shown on chart</div>
            </div>
          </div>
          <Tracker cid={txCond} color={reg.conditions.find(c=>c.id===txCond)?.color||reg.color}/>
          <div style={{marginTop:8,padding:"8px 10px",background:"#0d0d1a",borderRadius:6,border:"1px solid #1a1a2e"}}>
            <div style={{fontSize:9,fontFamily:"mono",color:"#444",letterSpacing:1,marginBottom:2}}>INTERPRETATION</div>
            <div style={{fontSize:10,color:"#555",lineHeight:1.5}}>Green "MCID MET" = clinically meaningful change achieved from baseline. Dashed line = MCID target. Change above MCID supports continued care. Change below MCID at re-exam → reassess plan (see Re-Exam Decision Rules in Tx Plan).</div>
          </div>
        </div>}
      </div>}
    </div>
    <div style={{maxWidth:640,margin:"14px auto 0",padding:"8px 16px 20px",borderTop:"1px solid #1a1a2e",textAlign:"center"}}>
      <div style={{fontSize:7,color:"#1a1a2e",fontFamily:"mono"}}>Life Chiropractic · Bayesian DDx + Tx · Decision Support Only</div>
    </div>
  </div>;
}
