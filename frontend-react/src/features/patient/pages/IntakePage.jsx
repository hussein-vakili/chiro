import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { fetchJson } from "../../../shared/api";
import { useApiResource } from "../../../shared/hooks";
import { StatusPill } from "../../../shared/ui";
import {
  CONDITION_OPTIONS,
  DAILY_IMPACT_OPTIONS,
  deriveQuestionnaireIds,
  EXERCISE_FREQUENCY_OPTIONS,
  GOAL_OPTIONS,
  HABIT_OPTIONS,
  hydrateQuestionnaireState,
  IMAGING_OPTIONS,
  ONSET_TYPE_OPTIONS,
  PAIN_AREA_OPTIONS,
  PAIN_BETTER_OPTIONS,
  PAIN_FREQUENCY_OPTIONS,
  PAIN_TYPE_OPTIONS,
  PAIN_WORSE_OPTIONS,
  PREVIOUS_INJURY_RECOVERY_OPTIONS,
  PREVIOUS_INJURY_TYPE_OPTIONS,
  PRIOR_CHIROPRACTIC_OPTIONS,
  QUESTIONNAIRE_DEFS,
  questionnaireBand,
  questionnaireDisplayValue,
  reconcileQuestionnaireState,
  REFERRAL_OPTIONS,
  SECTION_LINKS,
  SEX_OPTIONS,
  SLEEP_HOURS_OPTIONS,
  SLEEP_POSITION_OPTIONS,
  SLEEP_QUALITY_OPTIONS,
  scoreQuestionnaire,
  buildFunctionalOutcomeMeasures,
  VISIT_REASON_OPTIONS,
  CAUSE_OPTIONS,
  WORK_TYPE_OPTIONS,
  PRONOUN_OPTIONS,
} from "../intakeConfig";

function formatSavedAt(value) {
  try {
    return new Date(value).toLocaleString([], { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" });
  } catch (_error) {
    return "just now";
  }
}

function ChipGroup({ options, values, onToggle, multi = true }) {
  return (
    <div className="rp-intake-chip-grid">
      {options.map((option) => {
        const active = values.includes(option);
        return (
          <button
            key={option}
            type="button"
            className={`rp-chip-toggle ${active ? "is-active" : ""}`.trim()}
            onClick={() => onToggle(option, multi)}
          >
            {option}
          </button>
        );
      })}
    </div>
  );
}

function RatingGroup({ value, onChange }) {
  return (
    <div className="rp-rating-grid">
      {Array.from({ length: 10 }, (_item, index) => {
        const nextValue = index + 1;
        return (
          <button
            key={nextValue}
            type="button"
            className={`rp-rating-button ${value === nextValue ? "is-active" : ""}`.trim()}
            onClick={() => onChange(nextValue)}
          >
            {nextValue}
          </button>
        );
      })}
    </div>
  );
}

function SliderField({ label, hint, value, min = 0, max = 10, onChange }) {
  return (
    <label className="rp-form-stack">
      <span>{label}</span>
      {hint ? <small>{hint}</small> : null}
      <div className="rp-intake-slider-row">
        <input type="range" min={min} max={max} value={value} onChange={(event) => onChange(Number(event.target.value))} />
        <strong className="rp-intake-slider-value">{value}</strong>
      </div>
    </label>
  );
}

function QuestionnaireCard({ questionnaireId, state, onPick, onSetSlider, onToggleSkip }) {
  const definition = QUESTIONNAIRE_DEFS[questionnaireId];
  const score = scoreQuestionnaire(questionnaireId, { [questionnaireId]: state });
  const band = score.ok ? questionnaireBand(questionnaireId, score) : { label: "Incomplete", tone: "muted" };

  return (
    <article className="rp-card rp-intake-questionnaire-card">
      <div className="rp-section-head">
        <div>
          <span className="rp-eyebrow">Outcome measure</span>
          <h2>{definition.name}</h2>
        </div>
        <div className="rp-inline-actions rp-inline-actions-tight">
          <StatusPill tone={band.tone}>{band.label}</StatusPill>
          <strong className="rp-intake-score-value">{questionnaireDisplayValue(questionnaireId, score)}</strong>
        </div>
      </div>
      <p>{definition.citation}</p>
      <div className="rp-stack-list">
        {definition.questions.map((question, questionIndex) => {
          if (definition.score.type === "odi_slider") {
            const skipped = Boolean(state.skipped?.[questionIndex]);
            const value = Number(state.ans?.[questionIndex] ?? 0);
            return (
              <section key={`${questionnaireId}-${questionIndex}`} className={`rp-intake-odi-card ${skipped ? "is-skipped" : ""}`.trim()}>
                <div className="rp-list-head">
                  <div>
                    <strong>{questionIndex + 1}. {question.prompt}</strong>
                    {question.subtitle ? <small>{question.subtitle}</small> : null}
                  </div>
                  <strong className="rp-intake-score-value">{skipped ? "N/A" : value.toFixed(1)}</strong>
                </div>
                {question.optional ? (
                  <div className="rp-inline-actions rp-inline-actions-tight">
                    <button type="button" className="rp-button rp-button-secondary" onClick={() => onToggleSkip(questionnaireId, questionIndex)}>
                      {skipped ? "Include" : "N/A - Skip"}
                    </button>
                  </div>
                ) : null}
                {!skipped ? (
                  <>
                    <div className="rp-intake-odi-labels">
                      {question.options.map((option, optionIndex) => (
                        <span key={option} className={optionIndex === Math.round(value / 2) ? "is-active" : ""}>
                          {option}
                        </span>
                      ))}
                    </div>
                    <input
                      type="range"
                      min="0"
                      max="10"
                      step="0.1"
                      value={value}
                      onChange={(event) => onSetSlider(questionnaireId, questionIndex, Number(event.target.value))}
                    />
                    <div className="rp-intake-slider-hint"><span>0</span><span>10</span></div>
                  </>
                ) : null}
              </section>
            );
          }

          return (
            <section key={`${questionnaireId}-${questionIndex}`} className="rp-intake-question-block">
              <strong>{questionIndex + 1}. {question.prompt}</strong>
              <div className="rp-stack-list">
                {question.options.map((option, optionIndex) => {
                  const active = state.ans?.[questionIndex] === optionIndex;
                  return (
                    <button
                      key={option}
                      type="button"
                      className={`rp-intake-option ${active ? "is-active" : ""}`.trim()}
                      onClick={() => onPick(questionnaireId, questionIndex, optionIndex)}
                    >
                      <span className={`rp-intake-option-radio ${active ? "is-active" : ""}`.trim()} />
                      <span>{option}</span>
                    </button>
                  );
                })}
              </div>
            </section>
          );
        })}
      </div>
    </article>
  );
}

export default function IntakePage({ config }) {
  const resource = useApiResource(() => fetchJson(config.intakeEndpoint), [config.intakeEndpoint]);
  const [payload, setPayload] = useState(null);
  const [submissionStatus, setSubmissionStatus] = useState("draft");
  const [questionnaireState, setQuestionnaireState] = useState({ byId: {}, archived: [] });
  const [saveMeta, setSaveMeta] = useState({ message: "", tone: "" });
  const [notice, setNotice] = useState("");
  const [errorNotice, setErrorNotice] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const hydratedRef = useRef(false);
  const saveTimerRef = useRef(null);
  const lastPersistedRef = useRef("");

  const activeQuestionnaireIds = useMemo(() => (payload ? deriveQuestionnaireIds(payload) : []), [payload]);

  useEffect(() => {
    if (!resource.data?.payload) {
      return;
    }
    const seededPayload = resource.data.payload;
    const seededQuestionnaires = hydrateQuestionnaireState(seededPayload.functionalOutcomeMeasures);
    setPayload(seededPayload);
    setSubmissionStatus(resource.data.status || "draft");
    setQuestionnaireState(seededQuestionnaires);
    const seededFunctional = buildFunctionalOutcomeMeasures(seededPayload, seededQuestionnaires, deriveQuestionnaireIds(seededPayload));
    lastPersistedRef.current = JSON.stringify({ ...seededPayload, functionalOutcomeMeasures: seededFunctional, submittedAt: seededPayload.submittedAt || new Date().toISOString() });
    hydratedRef.current = true;
    setSaveMeta({
      message: resource.data.status === "submitted" ? "Submitted to your portal" : "Draft ready",
      tone: resource.data.status === "submitted" ? "ok" : "",
    });
  }, [resource.data]);

  useEffect(() => {
    if (!hydratedRef.current) {
      return;
    }
    setQuestionnaireState((current) => reconcileQuestionnaireState(activeQuestionnaireIds, current));
  }, [activeQuestionnaireIds]);

  const buildSubmissionPayload = useCallback(() => {
    if (!payload) {
      return null;
    }
    const submittedAt = payload.submittedAt || new Date().toISOString();
    return {
      ...payload,
      submittedAt,
      functionalOutcomeMeasures: buildFunctionalOutcomeMeasures({ ...payload, submittedAt }, questionnaireState, activeQuestionnaireIds),
    };
  }, [payload, questionnaireState, activeQuestionnaireIds]);

  const persist = useCallback(async (status, { silent = false, redirectOnSubmit = false } = {}) => {
    const nextPayload = buildSubmissionPayload();
    if (!nextPayload) {
      return null;
    }
    setErrorNotice("");
    setNotice("");
    setSaveMeta({ message: status === "submitted" ? "Submitting to portal..." : "Saving draft...", tone: "" });
    const { response, data } = await fetchJson(config.saveIntakeEndpoint, {
      method: "POST",
      body: JSON.stringify({ status, payload: nextPayload }),
    });

    if (!response.ok || data.ok === false) {
      const message = (data.errors || [data.error || "Unable to save intake right now."]).join(" ");
      setSaveMeta({ message, tone: "error" });
      setErrorNotice(message);
      if (!silent) {
        setNotice("");
      }
      return null;
    }

    lastPersistedRef.current = JSON.stringify(nextPayload);
    setPayload(nextPayload);
    setSubmissionStatus(data.status);
    setSaveMeta({
      message: data.status === "submitted" ? "Submitted to your portal" : `Saved ${formatSavedAt(data.updatedAt)}`,
      tone: "ok",
    });
    if (silent) {
      return data;
    }
    setNotice(data.status === "submitted" ? "Intake submitted successfully." : "Draft saved.");
    if (redirectOnSubmit && data.status === "submitted") {
      window.location.assign(`${config.spaRoot}/results`);
    }
    return data;
  }, [buildSubmissionPayload, config.saveIntakeEndpoint, config.spaRoot]);

  useEffect(() => {
    if (!hydratedRef.current || !payload) {
      return undefined;
    }
    const nextPayload = buildSubmissionPayload();
    if (!nextPayload) {
      return undefined;
    }
    const snapshot = JSON.stringify(nextPayload);
    if (snapshot === lastPersistedRef.current) {
      return undefined;
    }
    setSaveMeta({ message: "Unsaved changes", tone: "" });
    window.clearTimeout(saveTimerRef.current);
    saveTimerRef.current = window.setTimeout(() => {
      persist(submissionStatus === "submitted" ? "submitted" : "draft", { silent: true });
    }, 1200);
    return () => window.clearTimeout(saveTimerRef.current);
  }, [payload, questionnaireState, submissionStatus, buildSubmissionPayload, persist]);

  const updatePayload = useCallback((updater) => {
    setPayload((current) => updater(current));
  }, []);

  const updateSectionField = useCallback((section, field, value) => {
    updatePayload((current) => ({
      ...current,
      [section]: {
        ...(current?.[section] || {}),
        [field]: value,
      },
    }));
  }, [updatePayload]);

  const updateNestedField = useCallback((section, parentKey, field, value) => {
    updatePayload((current) => ({
      ...current,
      [section]: {
        ...(current?.[section] || {}),
        [parentKey]: {
          ...(current?.[section]?.[parentKey] || {}),
          [field]: value,
        },
      },
    }));
  }, [updatePayload]);

  const toggleArrayValue = useCallback((section, field, value, multi = true) => {
    updatePayload((current) => {
      const currentValues = current?.[section]?.[field] || [];
      const hasValue = currentValues.includes(value);
      const nextValues = multi
        ? (hasValue ? currentValues.filter((item) => item !== value) : [...currentValues, value])
        : (hasValue ? [] : [value]);
      return {
        ...current,
        [section]: {
          ...(current?.[section] || {}),
          [field]: nextValues,
        },
      };
    });
  }, [updatePayload]);

  const toggleHabit = useCallback((key) => {
    updatePayload((current) => ({
      ...current,
      lifestyle: {
        ...(current?.lifestyle || {}),
        habits: {
          ...(current?.lifestyle?.habits || {}),
          [key]: !(current?.lifestyle?.habits?.[key]),
        },
      },
    }));
  }, [updatePayload]);

  const toggleNullableField = useCallback((field) => {
    updatePayload((current) => ({
      ...current,
      medicalHistory: {
        ...(current?.medicalHistory || {}),
        [field]: current?.medicalHistory?.[field] == null ? "" : null,
      },
    }));
  }, [updatePayload]);

  const togglePreviousInjuries = useCallback(() => {
    updatePayload((current) => ({
      ...current,
      medicalHistory: {
        ...(current?.medicalHistory || {}),
        previousInjuries: current?.medicalHistory?.previousInjuries
          ? null
          : { types: [], details: "", recoveryStatus: [] },
      },
    }));
  }, [updatePayload]);

  const updatePreviousInjuries = useCallback((field, value) => {
    updatePayload((current) => ({
      ...current,
      medicalHistory: {
        ...(current?.medicalHistory || {}),
        previousInjuries: {
          ...(current?.medicalHistory?.previousInjuries || { types: [], details: "", recoveryStatus: [] }),
          [field]: value,
        },
      },
    }));
  }, [updatePayload]);

  const togglePreviousInjuryChip = useCallback((field, value, multi = true) => {
    updatePayload((current) => {
      const previous = current?.medicalHistory?.previousInjuries || { types: [], details: "", recoveryStatus: [] };
      const currentValues = previous[field] || [];
      const hasValue = currentValues.includes(value);
      const nextValues = multi
        ? (hasValue ? currentValues.filter((item) => item !== value) : [...currentValues, value])
        : (hasValue ? [] : [value]);
      return {
        ...current,
        medicalHistory: {
          ...(current?.medicalHistory || {}),
          previousInjuries: {
            ...previous,
            [field]: nextValues,
          },
        },
      };
    });
  }, [updatePayload]);

  const pickQuestionnaireOption = useCallback((questionnaireId, questionIndex, optionIndex) => {
    setQuestionnaireState((current) => {
      const next = { ...current, byId: { ...current.byId } };
      const state = next.byId[questionnaireId] || { ans: [], done: null, archived: false };
      const answers = [...(state.ans || [])];
      answers[questionIndex] = optionIndex;
      next.byId[questionnaireId] = { ...state, ans: answers, done: new Date().toISOString(), archived: false };
      return next;
    });
  }, []);

  const setQuestionnaireSlider = useCallback((questionnaireId, questionIndex, value) => {
    setQuestionnaireState((current) => {
      const next = { ...current, byId: { ...current.byId } };
      const state = next.byId[questionnaireId] || { ans: [], skipped: [], done: null, archived: false };
      const answers = [...(state.ans || [])];
      answers[questionIndex] = Math.round(Math.max(0, Math.min(10, value)) * 10) / 10;
      next.byId[questionnaireId] = {
        ...state,
        ans: answers,
        skipped: [...(state.skipped || [])],
        done: new Date().toISOString(),
        archived: false,
      };
      return next;
    });
  }, []);

  const toggleQuestionnaireSkip = useCallback((questionnaireId, questionIndex) => {
    setQuestionnaireState((current) => {
      const next = { ...current, byId: { ...current.byId } };
      const state = next.byId[questionnaireId] || { ans: [], skipped: [], done: null, archived: false };
      const skipped = [...(state.skipped || [])];
      skipped[questionIndex] = !skipped[questionIndex];
      const answers = [...(state.ans || [])];
      if (skipped[questionIndex]) {
        answers[questionIndex] = 0;
      }
      next.byId[questionnaireId] = {
        ...state,
        ans: answers,
        skipped,
        done: new Date().toISOString(),
        archived: false,
      };
      return next;
    });
  }, []);

  if (resource.loading || !payload) {
    return (
      <div className="rp-page-grid">
        <section className="rp-card rp-hero-card">
          <div>
            <div className="rp-eyebrow">Intake</div>
            <h2>Loading your intake</h2>
            <p>Preparing your patient history, consent, and questionnaire workspace.</p>
          </div>
        </section>
      </div>
    );
  }

  if (resource.error) {
    return (
      <div className="rp-page-grid">
        <section className="rp-empty-card">
          <span className="rp-eyebrow">Intake</span>
          <h2>Intake could not be loaded</h2>
          <p>{resource.error}</p>
        </section>
      </div>
    );
  }

  const patient = payload.patient || {};
  const reason = payload.reasonForVisit || {};
  const pain = payload.pain || {};
  const medical = payload.medicalHistory || {};
  const lifestyle = payload.lifestyle || {};
  const goals = payload.goals || {};
  const consent = payload.consent || {};
  const reviewQuestionnaires = activeQuestionnaireIds.map((questionnaireId) => {
    const score = scoreQuestionnaire(questionnaireId, questionnaireState.byId);
    return {
      questionnaireId,
      score,
      band: score.ok ? questionnaireBand(questionnaireId, score) : { label: "Incomplete", tone: "muted" },
    };
  });

  return (
    <div className="rp-page-grid">
      <section className="rp-card rp-hero-card">
        <div>
          <div className="rp-eyebrow">Intake</div>
          <h2>Complete your onboarding form</h2>
          <p>The patient intake is now native React. Drafts auto-save to the same secure portal record and still feed the clinic's assessment and results workflow.</p>
        </div>
        <div className="rp-header-card">
          <span>Status</span>
          <strong>{submissionStatus === "submitted" ? "Submitted" : "Draft in progress"}</strong>
          <small>{activeQuestionnaireIds.length} questionnaires active</small>
          <small className={`rp-inline-status ${saveMeta.tone ? `is-${saveMeta.tone}` : ""}`.trim()}>{saveMeta.message || "Ready"}</small>
        </div>
      </section>

      <section className="rp-card">
        <div className="rp-section-head">
          <div>
            <span className="rp-eyebrow">Sections</span>
            <h2>Navigate the intake</h2>
          </div>
        </div>
        <div className="rp-chip-row">
          {SECTION_LINKS.map((section) => (
            <a key={section.id} className="rp-top-link" href={`#section-${section.id}`}>{section.label}</a>
          ))}
        </div>
      </section>

      {notice ? <div className="rp-alert rp-alert-success">{notice}</div> : null}
      {errorNotice ? <div className="rp-alert rp-alert-error">{errorNotice}</div> : null}

      <section id="section-about" className="rp-card rp-section-stack">
        <div className="rp-section-head">
          <div>
            <span className="rp-eyebrow">About you</span>
            <h2>Personal and contact details</h2>
          </div>
        </div>
        <div className="rp-form-grid">
          <label><span>First name</span><input type="text" value={patient.firstName || ""} onChange={(event) => updateSectionField("patient", "firstName", event.target.value)} /></label>
          <label><span>Last name</span><input type="text" value={patient.lastName || ""} onChange={(event) => updateSectionField("patient", "lastName", event.target.value)} /></label>
          <label><span>Date of birth</span><input type="date" value={patient.dob || ""} onChange={(event) => updateSectionField("patient", "dob", event.target.value)} /></label>
          <label><span>Sex</span><select value={patient.sex || ""} onChange={(event) => updateSectionField("patient", "sex", event.target.value)}><option value="">Select...</option>{SEX_OPTIONS.map((option) => <option key={option} value={option}>{option}</option>)}</select></label>
          <label><span>Pronoun</span><select value={patient.pronoun || ""} onChange={(event) => updateSectionField("patient", "pronoun", event.target.value)}><option value="">Optional</option>{PRONOUN_OPTIONS.map((option) => <option key={option} value={option}>{option}</option>)}</select></label>
          <label><span>Email</span><input type="email" value={patient.email || ""} onChange={(event) => updateSectionField("patient", "email", event.target.value)} /></label>
          <label><span>Phone</span><input type="tel" value={patient.phone || ""} onChange={(event) => updateSectionField("patient", "phone", event.target.value)} /></label>
          <label><span>Height (ft)</span><input type="number" min="1" max="8" value={patient.heightFt ?? ""} onChange={(event) => updateSectionField("patient", "heightFt", event.target.value === "" ? null : Number(event.target.value))} /></label>
          <label><span>Height (in)</span><input type="number" min="0" max="11" value={patient.heightIn ?? ""} onChange={(event) => updateSectionField("patient", "heightIn", event.target.value === "" ? null : Number(event.target.value))} /></label>
          <label><span>Weight</span><input type="text" value={patient.weight || ""} onChange={(event) => updateSectionField("patient", "weight", event.target.value)} placeholder="e.g. 75 kg or 165 lbs" /></label>
        </div>
        <label className="rp-form-stack"><span>Address</span><input type="text" value={patient.address || ""} onChange={(event) => updateSectionField("patient", "address", event.target.value)} placeholder="Street, City, State, Zip" /></label>
        <div className="rp-form-grid">
          <label><span>Emergency contact name</span><input type="text" value={patient.emergencyContact?.name || ""} onChange={(event) => updateNestedField("patient", "emergencyContact", "name", event.target.value)} /></label>
          <label><span>Relationship</span><input type="text" value={patient.emergencyContact?.relationship || ""} onChange={(event) => updateNestedField("patient", "emergencyContact", "relationship", event.target.value)} /></label>
          <label><span>Emergency contact phone</span><input type="tel" value={patient.emergencyContact?.phone || ""} onChange={(event) => updateNestedField("patient", "emergencyContact", "phone", event.target.value)} /></label>
        </div>
        <div className="rp-form-stack">
          <span>How did you hear about us?</span>
          <ChipGroup options={REFERRAL_OPTIONS} values={patient.referralSource || []} onToggle={(value, multi) => toggleArrayValue("patient", "referralSource", value, multi)} multi={false} />
        </div>
        <label className="rp-form-stack"><span>Referring provider</span><input type="text" value={patient.referringProvider || ""} onChange={(event) => updateSectionField("patient", "referringProvider", event.target.value)} placeholder="Dr. ..." /></label>
      </section>

      <section id="section-reason" className="rp-card rp-section-stack">
        <div className="rp-section-head">
          <div>
            <span className="rp-eyebrow">Reason for visiting</span>
            <h2>Chief complaint and onset</h2>
          </div>
        </div>
        <div className="rp-form-stack">
          <span>Main reason for seeking care</span>
          <ChipGroup options={VISIT_REASON_OPTIONS} values={reason.reasons || []} onToggle={(value, multi) => toggleArrayValue("reasonForVisit", "reasons", value, multi)} />
        </div>
        <label className="rp-form-stack"><span>Chief complaint</span><textarea value={reason.chiefComplaint || ""} onChange={(event) => updateSectionField("reasonForVisit", "chiefComplaint", event.target.value)} placeholder="Describe the main issue, where you feel it, and how it affects your day." /></label>
        <div className="rp-form-grid">
          <label><span>When did it start?</span><input type="text" value={reason.onset || ""} onChange={(event) => updateSectionField("reasonForVisit", "onset", event.target.value)} placeholder="e.g. 6 months" /></label>
          <label><span>Started how?</span><select value={reason.onsetType || ""} onChange={(event) => updateSectionField("reasonForVisit", "onsetType", event.target.value)}><option value="">Select...</option>{ONSET_TYPE_OPTIONS.map((option) => <option key={option} value={option}>{option}</option>)}</select></label>
        </div>
        <div className="rp-form-stack">
          <span>Was there a specific event or cause?</span>
          <ChipGroup options={CAUSE_OPTIONS} values={reason.cause || []} onToggle={(value, multi) => toggleArrayValue("reasonForVisit", "cause", value, multi)} />
        </div>
        <label className="rp-form-stack"><span>Cause details</span><input type="text" value={reason.causeDetail || ""} onChange={(event) => updateSectionField("reasonForVisit", "causeDetail", event.target.value)} placeholder="What happened..." /></label>
      </section>

      <section id="section-pain" className="rp-card rp-section-stack">
        <div className="rp-section-head">
          <div>
            <span className="rp-eyebrow">Pain profile</span>
            <h2>Problem areas and symptom behaviour</h2>
          </div>
        </div>
        <div className="rp-form-stack">
          <span>Select your problem areas</span>
          <ChipGroup options={PAIN_AREA_OPTIONS} values={pain.areas || []} onToggle={(value, multi) => toggleArrayValue("pain", "areas", value, multi)} />
        </div>
        <div className="rp-form-grid">
          <SliderField label="Pain right now" hint="0 = none, 10 = worst imaginable" value={Number(pain.currentLevel ?? 5)} onChange={(value) => updateSectionField("pain", "currentLevel", value)} />
          <SliderField label="At its worst" hint="0 = none, 10 = worst imaginable" value={Number(pain.worstLevel ?? 7)} onChange={(value) => updateSectionField("pain", "worstLevel", value)} />
        </div>
        <div className="rp-form-stack">
          <span>What does the pain feel like?</span>
          <ChipGroup options={PAIN_TYPE_OPTIONS} values={pain.type || []} onToggle={(value, multi) => toggleArrayValue("pain", "type", value, multi)} />
        </div>
        <div className="rp-form-stack">
          <span>How often?</span>
          <ChipGroup options={PAIN_FREQUENCY_OPTIONS} values={pain.frequency || []} onToggle={(value, multi) => toggleArrayValue("pain", "frequency", value, multi)} multi={false} />
        </div>
        <div className="rp-form-stack">
          <span>What makes it worse?</span>
          <ChipGroup options={PAIN_WORSE_OPTIONS} values={pain.aggravating || []} onToggle={(value, multi) => toggleArrayValue("pain", "aggravating", value, multi)} />
        </div>
        <div className="rp-form-stack">
          <span>What makes it better?</span>
          <ChipGroup options={PAIN_BETTER_OPTIONS} values={pain.relieving || []} onToggle={(value, multi) => toggleArrayValue("pain", "relieving", value, multi)} />
        </div>
      </section>

      <section id="section-medical" className="rp-card rp-section-stack">
        <div className="rp-section-head">
          <div>
            <span className="rp-eyebrow">Medical history</span>
            <h2>Safety and background</h2>
          </div>
        </div>
        <div className="rp-form-stack">
          <span>Conditions</span>
          <ChipGroup options={CONDITION_OPTIONS} values={medical.conditions || []} onToggle={(value, multi) => toggleArrayValue("medicalHistory", "conditions", value, multi)} />
        </div>
        <label className="rp-form-stack"><span>Other conditions</span><input type="text" value={medical.conditionsOther || ""} onChange={(event) => updateSectionField("medicalHistory", "conditionsOther", event.target.value)} /></label>

        <div className="rp-intake-toggle-card">
          <label className="rp-toggle-row"><input type="checkbox" checked={medical.surgeries != null} onChange={() => toggleNullableField("surgeries")} /><span>I have had surgeries</span></label>
          {medical.surgeries != null ? <textarea value={medical.surgeries || ""} onChange={(event) => updateSectionField("medicalHistory", "surgeries", event.target.value)} placeholder="List surgeries and dates" /> : null}
        </div>
        <div className="rp-intake-toggle-card">
          <label className="rp-toggle-row"><input type="checkbox" checked={medical.fractures != null} onChange={() => toggleNullableField("fractures")} /><span>I have had fractures or broken bones</span></label>
          {medical.fractures != null ? <textarea value={medical.fractures || ""} onChange={(event) => updateSectionField("medicalHistory", "fractures", event.target.value)} placeholder="Which bones and when" /> : null}
        </div>
        <div className="rp-intake-toggle-card">
          <label className="rp-toggle-row"><input type="checkbox" checked={Boolean(medical.previousInjuries)} onChange={togglePreviousInjuries} /><span>I have had previous injuries</span></label>
          {medical.previousInjuries ? (
            <div className="rp-stack-list">
              <div className="rp-form-stack">
                <span>Previous injury types</span>
                <ChipGroup options={PREVIOUS_INJURY_TYPE_OPTIONS} values={medical.previousInjuries.types || []} onToggle={(value, multi) => togglePreviousInjuryChip("types", value, multi)} />
              </div>
              <label className="rp-form-stack"><span>Injury details</span><textarea value={medical.previousInjuries.details || ""} onChange={(event) => updatePreviousInjuries("details", event.target.value)} placeholder="Describe each injury, when it happened, and how it was treated" /></label>
              <div className="rp-form-stack">
                <span>Recovery status</span>
                <ChipGroup options={PREVIOUS_INJURY_RECOVERY_OPTIONS} values={medical.previousInjuries.recoveryStatus || []} onToggle={(value, multi) => togglePreviousInjuryChip("recoveryStatus", value, multi)} multi={false} />
              </div>
            </div>
          ) : null}
        </div>
        <div className="rp-intake-toggle-card">
          <label className="rp-toggle-row"><input type="checkbox" checked={medical.medications != null} onChange={() => toggleNullableField("medications")} /><span>I take medications or supplements</span></label>
          {medical.medications != null ? <textarea value={medical.medications || ""} onChange={(event) => updateSectionField("medicalHistory", "medications", event.target.value)} placeholder="Medication and what it's for" /> : null}
        </div>
        <div className="rp-intake-toggle-card">
          <label className="rp-toggle-row"><input type="checkbox" checked={medical.allergies != null} onChange={() => toggleNullableField("allergies")} /><span>I have allergies</span></label>
          {medical.allergies != null ? <input type="text" value={medical.allergies || ""} onChange={(event) => updateSectionField("medicalHistory", "allergies", event.target.value)} placeholder="e.g. Penicillin, Latex" /> : null}
        </div>
        <div className="rp-form-stack">
          <span>Previous chiropractic care</span>
          <ChipGroup options={PRIOR_CHIROPRACTIC_OPTIONS} values={medical.priorChiropractic || []} onToggle={(value, multi) => toggleArrayValue("medicalHistory", "priorChiropractic", value, multi)} multi={false} />
        </div>
        <label className="rp-form-stack"><span>Other treatments tried for this issue</span><input type="text" value={medical.priorTreatments || ""} onChange={(event) => updateSectionField("medicalHistory", "priorTreatments", event.target.value)} placeholder="e.g. Physio, acupuncture, massage" /></label>
        <div className="rp-form-stack">
          <span>Imaging on file</span>
          <ChipGroup options={IMAGING_OPTIONS} values={medical.imaging || []} onToggle={(value, multi) => toggleArrayValue("medicalHistory", "imaging", value, multi)} />
        </div>
      </section>

      <section id="section-lifestyle" className="rp-card rp-section-stack">
        <div className="rp-section-head">
          <div>
            <span className="rp-eyebrow">Lifestyle</span>
            <h2>Daily life and contributing factors</h2>
          </div>
        </div>
        <div className="rp-form-grid">
          <label><span>Occupation</span><input type="text" value={lifestyle.occupation || ""} onChange={(event) => updateSectionField("lifestyle", "occupation", event.target.value)} /></label>
          <label><span>Work type</span><select value={lifestyle.workType || ""} onChange={(event) => updateSectionField("lifestyle", "workType", event.target.value)}><option value="">Select...</option>{WORK_TYPE_OPTIONS.map((option) => <option key={option} value={option}>{option}</option>)}</select></label>
          <label><span>Work hours per day</span><input type="text" value={lifestyle.workHours || ""} onChange={(event) => updateSectionField("lifestyle", "workHours", event.target.value)} /></label>
        </div>
        <div className="rp-form-stack">
          <span>How does this affect daily life?</span>
          <ChipGroup options={DAILY_IMPACT_OPTIONS} values={lifestyle.dailyImpact || []} onToggle={(value, multi) => toggleArrayValue("lifestyle", "dailyImpact", value, multi)} />
        </div>
        <div className="rp-form-grid">
          <label><span>Exercise frequency</span><select value={lifestyle.exerciseFrequency || ""} onChange={(event) => updateSectionField("lifestyle", "exerciseFrequency", event.target.value)}><option value="">Select...</option>{EXERCISE_FREQUENCY_OPTIONS.map((option) => <option key={option} value={option}>{option}</option>)}</select></label>
          <label><span>Exercise type</span><input type="text" value={lifestyle.exerciseType || ""} onChange={(event) => updateSectionField("lifestyle", "exerciseType", event.target.value)} placeholder="Walking, gym, yoga..." /></label>
          <label><span>Sleep hours</span><select value={lifestyle.sleepHours || ""} onChange={(event) => updateSectionField("lifestyle", "sleepHours", event.target.value)}><option value="">Select...</option>{SLEEP_HOURS_OPTIONS.map((option) => <option key={option} value={option}>{option}</option>)}</select></label>
          <label><span>Sleep quality</span><select value={lifestyle.sleepQuality || ""} onChange={(event) => updateSectionField("lifestyle", "sleepQuality", event.target.value)}><option value="">Select...</option>{SLEEP_QUALITY_OPTIONS.map((option) => <option key={option} value={option}>{option}</option>)}</select></label>
        </div>
        <div className="rp-form-stack">
          <span>Sleep position</span>
          <ChipGroup options={SLEEP_POSITION_OPTIONS} values={lifestyle.sleepPosition || []} onToggle={(value, multi) => toggleArrayValue("lifestyle", "sleepPosition", value, multi)} multi={false} />
        </div>
        <SliderField label="Stress level" hint="1 = very relaxed, 10 = extremely stressed" value={Number(lifestyle.stressLevel ?? 5)} min={1} max={10} onChange={(value) => updateSectionField("lifestyle", "stressLevel", value)} />
        <div className="rp-intake-toggle-list">
          {HABIT_OPTIONS.map((habit) => (
            <label key={habit.key} className="rp-toggle-row rp-intake-habit-row">
              <input type="checkbox" checked={Boolean(lifestyle.habits?.[habit.key])} onChange={() => toggleHabit(habit.key)} />
              <span>{habit.label}</span>
            </label>
          ))}
        </div>
      </section>

      <section id="section-outcomes" className="rp-page-grid">
        <section className="rp-card">
          <div className="rp-section-head">
            <div>
              <span className="rp-eyebrow">Outcome questionnaires</span>
              <h2>How symptoms affect daily life</h2>
            </div>
          </div>
          <p>Questionnaires are selected automatically from your pain areas and visit reasons. They are saved into the same schema the clinic already uses for results and reassessments.</p>
        </section>
        {activeQuestionnaireIds.length ? activeQuestionnaireIds.map((questionnaireId) => (
          <QuestionnaireCard
            key={questionnaireId}
            questionnaireId={questionnaireId}
            state={questionnaireState.byId[questionnaireId] || { ans: [], skipped: [], done: null }}
            onPick={pickQuestionnaireOption}
            onSetSlider={setQuestionnaireSlider}
            onToggleSkip={toggleQuestionnaireSkip}
          />
        )) : (
          <section className="rp-empty-card">
            <span className="rp-eyebrow">Questionnaires</span>
            <h2>No questionnaires selected yet</h2>
            <p>Choose a visit reason or pain area above and the matching outcome measures will appear automatically.</p>
          </section>
        )}
      </section>

      <section id="section-goals" className="rp-card rp-section-stack">
        <div className="rp-section-head">
          <div>
            <span className="rp-eyebrow">Goals</span>
            <h2>What success looks like for you</h2>
          </div>
        </div>
        <div className="rp-form-stack">
          <span>What do you hope to achieve?</span>
          <ChipGroup options={GOAL_OPTIONS} values={goals.goals || []} onToggle={(value, multi) => toggleArrayValue("goals", "goals", value, multi)} />
        </div>
        <label className="rp-form-stack"><span>One thing you would love to be able to do again</span><textarea value={goals.activityGoal || ""} onChange={(event) => updateSectionField("goals", "activityGoal", event.target.value)} placeholder="e.g. Play with my kids without pain, run a 5K, sit through a movie comfortably" /></label>
        <div className="rp-form-stack">
          <span>How committed are you to following a care plan?</span>
          <RatingGroup value={goals.commitmentLevel || null} onChange={(value) => updateSectionField("goals", "commitmentLevel", value)} />
        </div>
        <label className="rp-form-stack"><span>Anything else you'd like us to know?</span><textarea value={goals.additionalNotes || ""} onChange={(event) => updateSectionField("goals", "additionalNotes", event.target.value)} placeholder="Concerns, fears about treatment, questions for the chiropractor..." /></label>
      </section>

      <section id="section-consent" className="rp-card rp-section-stack">
        <div className="rp-section-head">
          <div>
            <span className="rp-eyebrow">Review and consent</span>
            <h2>Check the summary and submit</h2>
          </div>
        </div>
        <div className="rp-review-grid">
          <article className="rp-review-card">
            <span>Patient</span>
            <strong>{[patient.firstName, patient.lastName].filter(Boolean).join(" ") || "Not completed"}</strong>
            <small>{patient.email || "No email"}</small>
            <small>{patient.phone || "No phone"}</small>
          </article>
          <article className="rp-review-card">
            <span>Chief complaint</span>
            <strong>{reason.chiefComplaint || "Not completed"}</strong>
            <small>{reason.onset || "Onset not recorded"}</small>
          </article>
          <article className="rp-review-card">
            <span>Pain areas</span>
            <strong>{(pain.areas || []).length}</strong>
            <small>{(pain.areas || []).join(", ") || "None selected"}</small>
          </article>
          <article className="rp-review-card">
            <span>Questionnaires</span>
            <strong>{activeQuestionnaireIds.length}</strong>
            <small>{reviewQuestionnaires.map((item) => `${QUESTIONNAIRE_DEFS[item.questionnaireId].name}: ${item.band.label}`).join(" · ") || "None selected"}</small>
          </article>
        </div>

        <div className="rp-card rp-subcard">
          <div className="rp-section-head">
            <div>
              <span className="rp-eyebrow">Consent</span>
              <h2>Required confirmations</h2>
            </div>
          </div>
          <div className="rp-stack-list">
            <label className="rp-toggle-row rp-intake-habit-row"><input type="checkbox" checked={Boolean(consent.chiropracticCare)} onChange={() => updateSectionField("consent", "chiropracticCare", !consent.chiropracticCare)} /><span>I understand and consent to chiropractic care.</span></label>
            <label className="rp-toggle-row rp-intake-habit-row"><input type="checkbox" checked={Boolean(consent.privacyNotice)} onChange={() => updateSectionField("consent", "privacyNotice", !consent.privacyNotice)} /><span>I acknowledge the privacy notice and consent to use of my information for treatment.</span></label>
            <label className="rp-toggle-row rp-intake-habit-row"><input type="checkbox" checked={Boolean(consent.accuracyConfirmation)} onChange={() => updateSectionField("consent", "accuracyConfirmation", !consent.accuracyConfirmation)} /><span>I confirm the information in this form is accurate to the best of my knowledge.</span></label>
          </div>
          <div className="rp-form-grid">
            <label><span>Digital signature</span><input type="text" value={consent.signature || ""} onChange={(event) => updateSectionField("consent", "signature", event.target.value)} placeholder="Your full legal name" /></label>
            <label><span>Signature date</span><input type="date" value={consent.signatureDate || ""} onChange={(event) => updateSectionField("consent", "signatureDate", event.target.value)} /></label>
          </div>
        </div>

        <div className="rp-inline-actions">
          <button type="button" className="rp-button rp-button-secondary" onClick={() => persist(submissionStatus === "submitted" ? "submitted" : "draft", { silent: false })} disabled={submitting}>
            Save draft now
          </button>
          <button type="button" className="rp-button rp-button-primary" onClick={async () => { setSubmitting(true); await persist("submitted", { silent: false, redirectOnSubmit: true }); setSubmitting(false); }} disabled={submitting}>
            {submitting ? "Submitting..." : "Submit intake"}
          </button>
        </div>
      </section>
    </div>
  );
}
