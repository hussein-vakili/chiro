export const REFERRAL_OPTIONS = [
  "Doctor referral",
  "Friend / Family",
  "Google",
  "Social media",
  "Other",
];

export const VISIT_REASON_OPTIONS = [
  "Pain / discomfort",
  "Headaches / migraines",
  "Injury recovery",
  "Posture concerns",
  "Preventive / wellness",
  "Stiffness / limited motion",
  "Numbness / tingling",
  "Sports performance",
  "Other",
];

export const CAUSE_OPTIONS = [
  "Car accident",
  "Work injury",
  "Sports injury",
  "Fall",
  "Repetitive strain",
  "Pregnancy / postpartum",
  "No specific event",
  "Other",
];

export const PAIN_AREA_OPTIONS = [
  "Head",
  "Neck",
  "Upper back",
  "Mid back",
  "Lower back",
  "Left shoulder",
  "Right shoulder",
  "Left arm / hand",
  "Right arm / hand",
  "Chest / ribs",
  "Hips / pelvis",
  "Left leg",
  "Right leg",
  "Left foot",
  "Right foot",
  "Jaw / TMJ",
];

export const PAIN_TYPE_OPTIONS = [
  "Sharp",
  "Dull / aching",
  "Burning",
  "Shooting",
  "Throbbing",
  "Stiff",
  "Tingling",
  "Numbness",
  "Cramping",
];

export const PAIN_FREQUENCY_OPTIONS = [
  "Constant",
  "Daily",
  "Several times a week",
  "Few times a month",
  "Occasionally",
];

export const PAIN_WORSE_OPTIONS = [
  "Sitting",
  "Standing",
  "Walking",
  "Bending",
  "Lifting",
  "Driving",
  "Sleeping",
  "Exercise",
  "Stress",
  "Morning stiffness",
  "End of day",
];

export const PAIN_BETTER_OPTIONS = [
  "Rest",
  "Heat",
  "Ice",
  "Stretching",
  "Medication",
  "Massage",
  "Movement",
  "Position change",
  "Nothing helps",
];

export const CONDITION_OPTIONS = [
  "Arthritis",
  "Osteoporosis",
  "Disc herniation",
  "Scoliosis",
  "Spinal stenosis",
  "Fibromyalgia",
  "Diabetes",
  "High blood pressure",
  "Heart disease",
  "Stroke",
  "Cancer",
  "Autoimmune",
  "Seizures / epilepsy",
  "Depression / anxiety",
  "Migraines",
  "Currently pregnant",
];

export const PREVIOUS_INJURY_TYPE_OPTIONS = [
  "Car accident",
  "Sports injury",
  "Work injury",
  "Fall",
  "Whiplash",
  "Concussion",
  "Back injury",
  "Neck injury",
  "Shoulder injury",
  "Knee injury",
  "Other",
];

export const PREVIOUS_INJURY_RECOVERY_OPTIONS = [
  "Yes, fully recovered",
  "Mostly recovered",
  "Still have some issues",
  "Never fully recovered",
];

export const PRIOR_CHIROPRACTIC_OPTIONS = [
  "First time",
  "Yes, recently",
  "Yes, a while ago",
];

export const IMAGING_OPTIONS = [
  "X-ray",
  "MRI",
  "CT scan",
  "None",
  "Unsure",
];

export const DAILY_IMPACT_OPTIONS = [
  "Work",
  "Sleep",
  "Exercise",
  "Housework",
  "Childcare",
  "Driving",
  "Social life",
  "Mood",
  "Concentration",
  "None",
];

export const SLEEP_POSITION_OPTIONS = ["Back", "Side", "Stomach", "Varies"];

export const GOAL_OPTIONS = [
  "Reduce pain",
  "Fewer headaches",
  "Better mobility",
  "Improve posture",
  "Return to exercise",
  "Sleep better",
  "Reduce medication",
  "Prevention",
  "Quality of life",
  "Better focus",
  "Return to work",
];

export const SEX_OPTIONS = ["Male", "Female", "Other", "Prefer not to say"];
export const PRONOUN_OPTIONS = ["He/Him", "She/Her", "They/Them", "Other"];
export const ONSET_TYPE_OPTIONS = ["Suddenly (specific event)", "Gradually over time", "I'm not sure"];
export const WORK_TYPE_OPTIONS = ["Desk / computer", "Standing / walking", "Manual / physical", "Driving", "Mixed", "Retired", "Student"];
export const EXERCISE_FREQUENCY_OPTIONS = ["Never", "1-2 x /week", "3-4 x /week", "5+ x /week", "Daily"];
export const SLEEP_HOURS_OPTIONS = ["< 5 hours", "5-6 hours", "6-7 hours", "7-8 hours", "8+ hours"];
export const SLEEP_QUALITY_OPTIONS = [
  "Good - I wake rested",
  "Fair - could be better",
  "Poor - I wake tired",
  "Very poor - pain/frequent waking",
];

export const HABIT_OPTIONS = [
  { key: "smoker", label: "I smoke or use tobacco" },
  { key: "alcohol", label: "I drink alcohol regularly" },
  { key: "highCaffeine", label: "3+ caffeinated drinks daily" },
  { key: "prolongedSitting", label: "I sit more than 6 hours a day" },
  { key: "highScreenTime", label: "Screen time 4+ hours daily" },
];

export const SECTION_LINKS = [
  { id: "about", label: "About you" },
  { id: "reason", label: "Reason" },
  { id: "pain", label: "Pain" },
  { id: "medical", label: "Medical" },
  { id: "lifestyle", label: "Lifestyle" },
  { id: "outcomes", label: "Questionnaires" },
  { id: "goals", label: "Goals" },
  { id: "consent", label: "Consent" },
];

export const QUESTIONNAIRE_ROUTES = [
  { match: ["Neck", "Head", "Headaches / migraines", "Jaw / TMJ", "Upper back"], ids: ["ndi"] },
  { match: ["Head", "Headaches / migraines"], ids: ["hit6"] },
  { match: ["Lower back", "Hips / pelvis", "Mid back"], ids: ["odi"] },
  { match: ["Left shoulder", "Right shoulder", "Left arm / hand", "Right arm / hand", "Chest / ribs"], ids: ["qdash"] },
  { match: ["Left leg", "Right leg", "Left foot", "Right foot"], ids: ["odi"] },
];

const ODI_LABEL_POSITIONS = [0, 2, 4, 6, 8, 10];

export const QUESTIONNAIRE_DEFS = {
  ndi: {
    id: "ndi",
    name: "Neck Disability Index (NDI)",
    version: "2.0",
    citation: "Vernon H, Mior S. JMPT 1991;14(7):409-415.",
    icon: "🔵",
    color: "sky",
    score: { type: "pct", max: 50 },
    bands: [
      { min: 0, max: 8, label: "No disability", tone: "life" },
      { min: 9, max: 28, label: "Mild disability", tone: "life" },
      { min: 29, max: 48, label: "Moderate disability", tone: "amber" },
      { min: 49, max: 68, label: "Severe disability", tone: "rose" },
      { min: 69, max: 100, label: "Complete disability", tone: "rose" },
    ],
    questions: [
      { prompt: "Pain Intensity", options: ["I have no pain right now", "The pain is very mild", "The pain is moderate", "The pain is fairly severe", "The pain is very severe", "The pain is the worst imaginable"] },
      { prompt: "Personal Care (washing, dressing)", options: ["I can look after myself normally", "I can look after myself but it causes extra pain", "It is painful and I am slow and careful", "I need some help but manage most of it", "I need help every day with most of my care", "I cannot get dressed, I wash with difficulty"] },
      { prompt: "Lifting", options: ["I can lift heavy weights without extra pain", "I can lift heavy weights but it causes extra pain", "Pain prevents heavy weights off the floor", "Pain prevents heavy weights but I manage light-medium", "I can only lift very light weights", "I cannot lift or carry anything"] },
      { prompt: "Reading / Screen Work", options: ["I can do this as long as I want — no problem", "I can do this as long as I want — slight pain", "I can do this as long as I want — moderate pain", "Pain prevents me doing this as long as I want", "I can hardly do this because of pain", "I cannot do this at all"] },
      { prompt: "Headaches", options: ["I have no headaches at all", "Slight headaches, infrequently", "Moderate headaches, infrequently", "Moderate headaches, frequently", "Severe headaches, frequently", "Headaches almost all the time"] },
      { prompt: "Concentration", options: ["I can concentrate fully — no difficulty", "I can concentrate fully — slight difficulty", "Fair degree of difficulty concentrating", "A lot of difficulty concentrating", "Great deal of difficulty concentrating", "I cannot concentrate at all"] },
      { prompt: "Work / Daily Tasks", options: ["I can do as much work as I want", "I can only do my usual work, no more", "I can do most of my usual work, no more", "I cannot do my usual work", "I can hardly do any work", "I cannot do any work"] },
      { prompt: "Driving / Travel", options: ["I can drive/travel with no pain", "I can drive/travel with slight pain", "I can drive/travel with moderate pain", "Pain limits driving to under 1 hour", "I can barely drive at all", "I cannot drive or travel at all"] },
      { prompt: "Sleep", options: ["No trouble sleeping", "Sleep slightly disturbed (< 1 hr)", "Sleep mildly disturbed (1-2 hrs)", "Sleep moderately disturbed (2-3 hrs)", "Sleep greatly disturbed (3-5 hrs)", "Sleep completely disturbed (5+ hrs)"] },
      { prompt: "Recreation / Hobbies", options: ["All activities — no pain", "All activities — some pain", "Most but not all activities — pain", "Only a few activities — pain", "Hardly any activities — pain", "No activities at all"] },
    ],
  },
  odi: {
    id: "odi",
    name: "Oswestry Disability Index (ODI)",
    version: "2.2",
    citation: "Fairbank JCT, Pynsent PB. Spine 2000;25(22):2940-2953.",
    icon: "🟢",
    color: "life",
    score: { type: "odi_slider" },
    bands: [
      { min: 0, max: 20, label: "Minimal Disability", tone: "life" },
      { min: 20.01, max: 40, label: "Moderate Disability", tone: "amber" },
      { min: 40.01, max: 60, label: "Severe Disability", tone: "rose" },
      { min: 60.01, max: 80, label: "Crippled", tone: "rose" },
      { min: 80.01, max: 100, label: "Bed-bound / Exaggerating", tone: "rose" },
    ],
    questions: [
      { prompt: "Pain Intensity", options: ["No pain at the moment", "Very mild pain", "Moderate pain", "Fairly severe pain", "Very severe pain", "Worst imaginable pain"] },
      { prompt: "Personal Care", subtitle: "e.g. washing, dressing", options: ["Normal, no extra pain", "Normal but causes extra pain", "Slow and careful, painful", "Need some help", "Need daily help", "Cannot dress / stay in bed"] },
      { prompt: "Lifting", options: ["Heavy weights, no extra pain", "Heavy weights, extra pain", "No heavy from floor, OK from table", "Light-medium weights only", "Very light weights only", "Cannot lift or carry anything"] },
      { prompt: "Walking", options: ["No limit", "Limited to 2 km", "Limited to 1 km", "Limited to 500 m", "Stick or crutches only", "Bed-bound most of the time"] },
      { prompt: "Sitting", options: ["Any chair, as long as I like", "Favourite chair only, unlimited", "Limited to 1 hour", "Limited to 30 minutes", "Limited to 10 minutes", "Cannot sit at all"] },
      { prompt: "Standing", options: ["Unlimited, no extra pain", "Unlimited but extra pain", "Limited to 1 hour", "Limited to 30 minutes", "Limited to 10 minutes", "Cannot stand at all"] },
      { prompt: "Sleeping", options: ["Never disturbed by pain", "Occasionally disturbed", "Less than 6 hours", "Less than 4 hours", "Less than 2 hours", "Cannot sleep at all"] },
      { prompt: "Sex Life", subtitle: "if applicable", optional: true, options: ["Normal, no extra pain", "Normal, some extra pain", "Nearly normal, very painful", "Severely restricted", "Nearly absent", "Not possible due to pain"] },
      { prompt: "Social Life", options: ["Normal, no extra pain", "Normal but increases pain", "Limited energetic interests only", "Don't go out as often", "Restricted to home", "No social life due to pain"] },
      { prompt: "Travelling", options: ["Anywhere, no pain", "Anywhere, extra pain", "Journeys over 2 hours OK", "Limited to under 1 hour", "Short trips under 30 min only", "Only to receive treatment"] },
    ],
  },
  hit6: {
    id: "hit6",
    name: "Headache Impact Test (HIT-6)",
    version: "1.0",
    citation: "Kosinski M et al. Qual Life Res 2003;12:963-974.",
    icon: "🟣",
    color: "plum",
    score: { type: "hit6", values: [6, 8, 10, 11, 13] },
    bands: [
      { min: 36, max: 49, label: "Little or no impact", tone: "life" },
      { min: 50, max: 55, label: "Some impact", tone: "amber" },
      { min: 56, max: 59, label: "Substantial impact", tone: "amber" },
      { min: 60, max: 78, label: "Severe impact", tone: "rose" },
    ],
    questions: [
      { prompt: "When you have headaches, how often is the pain severe?", options: ["Never", "Rarely", "Sometimes", "Very often", "Always"] },
      { prompt: "How often do headaches limit your ability to do usual daily activities?", options: ["Never", "Rarely", "Sometimes", "Very often", "Always"] },
      { prompt: "When you have a headache, how often do you wish you could lie down?", options: ["Never", "Rarely", "Sometimes", "Very often", "Always"] },
      { prompt: "In the past 4 weeks, how often have you felt too tired to do work or daily activities because of headaches?", options: ["Never", "Rarely", "Sometimes", "Very often", "Always"] },
      { prompt: "In the past 4 weeks, how often have you felt fed up or irritated because of headaches?", options: ["Never", "Rarely", "Sometimes", "Very often", "Always"] },
      { prompt: "In the past 4 weeks, how often did headaches limit your ability to concentrate?", options: ["Never", "Rarely", "Sometimes", "Very often", "Always"] },
    ],
  },
  qdash: {
    id: "qdash",
    name: "QuickDASH",
    version: "1.0",
    citation: "Beaton DE et al. J Hand Ther 2005;18(2):191-199.",
    icon: "🟠",
    color: "amber",
    score: { type: "dash" },
    bands: [
      { min: 0, max: 25, label: "Mild disability", tone: "life" },
      { min: 26, max: 50, label: "Moderate disability", tone: "amber" },
      { min: 51, max: 75, label: "Severe disability", tone: "rose" },
      { min: 76, max: 100, label: "Extreme disability", tone: "rose" },
    ],
    questions: [
      { prompt: "Open a tight or new jar", options: ["No difficulty", "Mild difficulty", "Moderate difficulty", "Severe difficulty", "Unable"] },
      { prompt: "Do heavy household chores (washing walls, floors)", options: ["No difficulty", "Mild difficulty", "Moderate difficulty", "Severe difficulty", "Unable"] },
      { prompt: "Carry a shopping bag or briefcase", options: ["No difficulty", "Mild difficulty", "Moderate difficulty", "Severe difficulty", "Unable"] },
      { prompt: "Wash your back", options: ["No difficulty", "Mild difficulty", "Moderate difficulty", "Severe difficulty", "Unable"] },
      { prompt: "Use a knife to cut food", options: ["No difficulty", "Mild difficulty", "Moderate difficulty", "Severe difficulty", "Unable"] },
      { prompt: "Recreational activities requiring force through arm/shoulder/hand", options: ["No difficulty", "Mild difficulty", "Moderate difficulty", "Severe difficulty", "Unable"] },
      { prompt: "Arm/shoulder/hand interference with social activities this past week?", options: ["Not at all", "Slightly", "Moderately", "Quite a bit", "Extremely"] },
      { prompt: "Limited in work/daily activities due to arm/shoulder/hand this past week?", options: ["Not limited", "Slightly limited", "Moderately limited", "Very limited", "Unable"] },
      { prompt: "Arm/shoulder/hand pain severity this past week", options: ["None", "Mild", "Moderate", "Severe", "Extreme"] },
      { prompt: "Tingling in arm/shoulder/hand this past week", options: ["None", "Mild", "Moderate", "Severe", "Extreme"] },
      { prompt: "Difficulty sleeping from arm/shoulder/hand pain this past week", options: ["No difficulty", "Mild", "Moderate", "Severe", "So much I can't sleep"] },
    ],
  },
};

function buildDefaultQuestionnaireState(questionnaireId) {
  const definition = QUESTIONNAIRE_DEFS[questionnaireId];
  if (!definition) {
    return null;
  }
  if (definition.score.type === "odi_slider") {
    return {
      ans: new Array(definition.questions.length).fill(0),
      skipped: new Array(definition.questions.length).fill(false),
      done: null,
      archived: false,
    };
  }
  return {
    ans: new Array(definition.questions.length).fill(-1),
    done: null,
    archived: false,
  };
}

function normalizeQuestionnaireId(value) {
  return String(value || "").trim().toLowerCase();
}

export function deriveQuestionnaireIds(payload) {
  const reasonTags = payload?.reasonForVisit?.reasons || [];
  const painAreas = payload?.pain?.areas || [];
  const all = [...reasonTags, ...painAreas];
  const ids = new Set();
  QUESTIONNAIRE_ROUTES.forEach((route) => {
    if (route.match.some((item) => all.includes(item))) {
      route.ids.forEach((questionnaireId) => ids.add(questionnaireId));
    }
  });
  if (!ids.size && all.length) {
    ids.add("ndi");
    ids.add("odi");
  }
  return [...ids];
}

export function hydrateQuestionnaireState(functional) {
  const byId = {};
  const archived = Array.isArray(functional?.archived) ? functional.archived : [];
  (functional?.questionnaires || []).forEach((questionnaire) => {
    const questionnaireId = normalizeQuestionnaireId(questionnaire.questionnaireId);
    const definition = QUESTIONNAIRE_DEFS[questionnaireId];
    if (!definition) {
      return;
    }
    const state = buildDefaultQuestionnaireState(questionnaireId);
    state.done = questionnaire.completedAt || null;
    if (definition.score.type === "odi_slider") {
      (questionnaire.responses || []).forEach((response, index) => {
        if (index >= state.ans.length) {
          return;
        }
        if (response?.skipped) {
          state.skipped[index] = true;
          state.ans[index] = 0;
          return;
        }
        const value = Number(response?.selectedValue);
        state.ans[index] = Number.isFinite(value) ? Math.max(0, Math.min(10, Math.round(value * 10) / 10)) : 0;
      });
    } else {
      (questionnaire.responses || []).forEach((response, index) => {
        if (index >= state.ans.length) {
          return;
        }
        const value = Number(response?.selectedValue);
        state.ans[index] = Number.isFinite(value) ? value : -1;
      });
    }
    byId[questionnaireId] = state;
  });
  return { byId, archived };
}

export function reconcileQuestionnaireState(activeIds, state) {
  const activeSet = new Set(activeIds);
  const nextById = { ...(state?.byId || {}) };
  const nextArchived = Array.isArray(state?.archived) ? [...state.archived] : [];
  let changed = false;

  Object.entries(nextById).forEach(([questionnaireId, current]) => {
    if (activeSet.has(questionnaireId)) {
      return;
    }
    if (!current?.archived) {
      nextArchived.push({ ...current, qId: questionnaireId, at: new Date().toISOString() });
      nextById[questionnaireId] = { ...current, archived: true };
      changed = true;
    }
  });

  activeIds.forEach((questionnaireId) => {
    const current = nextById[questionnaireId];
    if (!current) {
      nextById[questionnaireId] = buildDefaultQuestionnaireState(questionnaireId);
      changed = true;
      return;
    }
    if (current.archived) {
      nextById[questionnaireId] = { ...current, archived: false };
      changed = true;
    }
  });

  return changed ? { byId: nextById, archived: nextArchived } : state;
}

export function nearestOdiLabelIndex(value) {
  let nearest = 0;
  let distance = Infinity;
  ODI_LABEL_POSITIONS.forEach((position, index) => {
    const nextDistance = Math.abs(value - position);
    if (nextDistance < distance) {
      distance = nextDistance;
      nearest = index;
    }
  });
  return nearest;
}

export function scoreQuestionnaire(questionnaireId, questionnaireState) {
  const definition = QUESTIONNAIRE_DEFS[questionnaireId];
  const state = questionnaireState?.[questionnaireId] || buildDefaultQuestionnaireState(questionnaireId);
  if (!definition || !state) {
    return { raw: 0, pct: 0, ok: false, answered: 0, max: 0 };
  }

  if (definition.score.type === "odi_slider") {
    let total = 0;
    let activeCount = 0;
    definition.questions.forEach((question, index) => {
      if (state.skipped?.[index]) {
        return;
      }
      const value = Number(state.ans[index]);
      total += Number.isFinite(value) ? Math.max(0, Math.min(10, value)) : 0;
      activeCount += 1;
    });
    if (!activeCount) {
      return { raw: 0, pct: 0, ok: false, answered: 0, max: 0 };
    }
    return {
      raw: Math.round(total * 10) / 10,
      pct: Math.round((total / (activeCount * 10)) * 1000) / 10,
      ok: true,
      answered: activeCount,
      max: activeCount,
    };
  }

  const answered = state.ans.filter((value) => value >= 0).length;
  if (!answered) {
    return { raw: 0, pct: 0, ok: false, answered: 0, max: definition.questions.length };
  }

  if (definition.score.type === "hit6") {
    const raw = state.ans.reduce((sum, value) => sum + (value >= 0 ? definition.score.values[value] : 6), 0);
    return {
      raw,
      pct: Math.round(((raw - 36) / 42) * 100),
      ok: answered === definition.questions.length,
      answered,
      max: definition.questions.length,
    };
  }

  if (definition.score.type === "dash") {
    const values = state.ans.filter((value) => value >= 0).map((value) => value + 1);
    const mean = values.reduce((sum, value) => sum + value, 0) / values.length;
    return {
      raw: values.reduce((sum, value) => sum + value, 0),
      pct: Math.round(((mean - 1) / 4) * 100),
      ok: answered === definition.questions.length,
      answered,
      max: definition.questions.length,
    };
  }

  const raw = state.ans.reduce((sum, value) => sum + (value >= 0 ? value : 0), 0);
  return {
    raw,
    pct: Math.round((raw / definition.score.max) * 100),
    ok: answered === definition.questions.length,
    answered,
    max: definition.questions.length,
  };
}

export function questionnaireBand(questionnaireId, score) {
  const definition = QUESTIONNAIRE_DEFS[questionnaireId];
  if (!definition) {
    return { label: "Incomplete", tone: "muted" };
  }
  const comparisonValue = definition.score.type === "hit6" ? score.raw : score.pct;
  return definition.bands.find((band) => comparisonValue >= band.min && comparisonValue <= band.max) || definition.bands[definition.bands.length - 1];
}

function questionnaireResponses(questionnaireId, questionnaireState) {
  const definition = QUESTIONNAIRE_DEFS[questionnaireId];
  const state = questionnaireState?.[questionnaireId] || buildDefaultQuestionnaireState(questionnaireId);
  if (definition.score.type === "odi_slider") {
    return definition.questions.map((question, index) => {
      const skipped = Boolean(state.skipped?.[index]);
      const valueNumber = Number(state.ans[index]);
      const value = Number.isFinite(valueNumber) ? Math.max(0, Math.min(10, Math.round(valueNumber * 10) / 10)) : 0;
      const nearestIndex = nearestOdiLabelIndex(value);
      return {
        questionId: `${definition.id}_q${index}`,
        prompt: question.prompt,
        subtitle: question.subtitle || "",
        skipped,
        responseType: "slider",
        scaleMin: 0,
        scaleMax: 10,
        selectedValue: skipped ? null : value,
        selectedLabel: skipped ? null : question.options[nearestIndex],
      };
    });
  }

  return definition.questions.map((question, index) => ({
    questionId: `${definition.id}_q${index}`,
    prompt: question.prompt,
    selectedValue: state.ans[index] >= 0 ? state.ans[index] : null,
    selectedLabel: state.ans[index] >= 0 ? question.options[state.ans[index]] : null,
  }));
}

export function buildFunctionalOutcomeMeasures(payload, questionnaireState, activeIds) {
  const selectedComplaints = [
    ...(payload?.reasonForVisit?.reasons || []),
    ...(payload?.pain?.areas || []),
  ];

  return {
    schemaVersion: "2026-03-odi-slider",
    routing: {
      selectedComplaints,
      questionnairesShown: activeIds,
    },
    questionnaireSchemas: activeIds.reduce((schemas, questionnaireId) => {
      const definition = QUESTIONNAIRE_DEFS[questionnaireId];
      if (!definition) {
        return schemas;
      }
      if (definition.score.type === "odi_slider") {
        schemas[questionnaireId] = {
          responseModel: "continuous_0_to_10",
          scaleMin: 0,
          scaleMax: 10,
          optionalSectionTitles: definition.questions.filter((question) => question.optional).map((question) => question.prompt),
          version: definition.version,
        };
      } else {
        const scaleMax = (definition.questions[0]?.options?.length || 1) - 1;
        schemas[questionnaireId] = {
          responseModel: "ordinal_0_to_n",
          scaleMin: 0,
          scaleMax,
          version: definition.version,
        };
      }
      return schemas;
    }, {}),
    questionnaires: activeIds.map((questionnaireId) => {
      const definition = QUESTIONNAIRE_DEFS[questionnaireId];
      const score = scoreQuestionnaire(questionnaireId, questionnaireState.byId);
      const band = score.ok ? questionnaireBand(questionnaireId, score) : { label: "Incomplete", tone: "muted" };
      return {
        questionnaireId: definition.id,
        displayName: definition.name,
        version: definition.version,
        citationText: definition.citation,
        completedAt: questionnaireState.byId[questionnaireId]?.done,
        rawScore: score.raw,
        percent: score.pct,
        interpretation: band.label,
        missingItems: definition.score.type === "odi_slider" ? 0 : Math.max(0, definition.questions.length - score.answered),
        responseModel: definition.score.type === "odi_slider" ? "continuous_0_to_10" : "ordinal_0_to_n",
        responses: questionnaireResponses(questionnaireId, questionnaireState.byId),
      };
    }),
    archived: questionnaireState.archived || [],
  };
}

export function questionnaireDisplayValue(questionnaireId, score) {
  const definition = QUESTIONNAIRE_DEFS[questionnaireId];
  if (!definition) {
    return "Incomplete";
  }
  if (!score.ok) {
    return `${score.answered} / ${definition.questions.length} answered`;
  }
  if (definition.score.type === "hit6") {
    return `${score.raw} / 78`;
  }
  if (definition.score.type === "odi_slider") {
    return `${score.pct}% (${score.raw.toFixed(1)} / ${(score.max || 0) * 10})`;
  }
  return `${score.pct}%`;
}
