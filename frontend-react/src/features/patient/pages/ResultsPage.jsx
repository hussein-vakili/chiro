import React from "react";
import { fetchJson } from "../../../shared/api";
import { useApiResource } from "../../../shared/hooks";
import { ErrorState, LoadingState, StatusPill } from "../../../shared/ui";

export default function ResultsPage({ config }) {
  const resource = useApiResource(() => fetchJson(config.resultsEndpoint), [config.resultsEndpoint]);

  if (resource.loading) {
    return <LoadingState title="Loading results" detail="Pulling your latest published findings." />;
  }
  if (resource.error) {
    if (resource.errorPayload?.redirect) {
      return (
        <section className="rp-empty-card">
          <span className="rp-eyebrow">Results</span>
          <h2>Results are not ready yet</h2>
          <p>{resource.error}</p>
          <a className="rp-button rp-button-primary" href={resource.errorPayload.redirect}>
            Open intake form
          </a>
        </section>
      );
    }
    return <ErrorState detail={resource.error} onRetry={resource.reload} />;
  }

  const summary = resource.data.results.summary;
  const report = summary.visit_report || null;
  const questionnaires = summary.questionnaires || [];
  const journey = resource.data.journey_summary;

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
          <span>Results</span>
          <strong>{report ? "Published" : "Pending review"}</strong>
          <small>Updated {summary.updated_at || "today"}</small>
          <small>{summary.full_name}</small>
        </div>
      </section>

      <section className="rp-two-column">
        <article className="rp-card">
          <div className="rp-section-head">
            <div>
              <span className="rp-eyebrow">Current focus</span>
              <h2>What matters now</h2>
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
              <h2>Results-related next steps</h2>
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

      <section className="rp-two-column">
        <article className="rp-card">
          <div className="rp-section-head">
            <div>
              <span className="rp-eyebrow">Patient summary</span>
              <h2>{report?.patient_summary || summary.reason?.chiefComplaint || "Not recorded yet"}</h2>
            </div>
          </div>
          <div className="rp-chip-row">
            {(summary.reason_tags || []).map((tag) => (
              <StatusPill key={tag} tone="life">{tag}</StatusPill>
            ))}
          </div>
          <div className="rp-key-value-list">
            <div><span>Current pain</span><strong>{summary.pain?.currentLevel ?? "-"}/10</strong></div>
            <div><span>Worst pain</span><strong>{summary.pain?.worstLevel ?? "-"}/10</strong></div>
            <div><span>Commitment</span><strong>{summary.goals?.commitmentLevel || "-"}/10</strong></div>
            <div><span>Submitted</span><strong>{summary.submitted_at || "Not recorded"}</strong></div>
          </div>
        </article>

        <article className="rp-card">
          <div className="rp-section-head">
            <div>
              <span className="rp-eyebrow">Recommendations</span>
              <h2>What to focus on</h2>
            </div>
          </div>
          <div className="rp-text-stack">
            <p>{report?.patient_key_findings || report?.assessment || "Your findings will appear here after the assessment is published."}</p>
            <p>{report?.patient_recommendations || report?.care_plan || "Recommendations have not been published yet."}</p>
            {report?.follow_up_plan ? <p>{report.follow_up_plan}</p> : null}
          </div>
        </article>
      </section>

      <section className="rp-card">
        <div className="rp-section-head">
          <div>
            <span className="rp-eyebrow">Outcome scores</span>
            <h2>Questionnaires</h2>
          </div>
        </div>
        {questionnaires.length ? (
          <div className="rp-history-grid">
            {questionnaires.map((questionnaire) => (
              <div key={questionnaire.questionnaireId} className="rp-history-card">
                <strong>{questionnaire.displayName}</strong>
                <p>{questionnaire.percent ?? questionnaire.rawScore}%</p>
                <small>{questionnaire.interpretation || "No interpretation"}</small>
              </div>
            ))}
          </div>
        ) : (
          <div className="rp-empty-inline">No questionnaire scores have been saved yet.</div>
        )}
      </section>

      <section className="rp-two-column">
        <article className="rp-card">
          <div className="rp-section-head">
            <div>
              <span className="rp-eyebrow">Pain areas</span>
              <h2>Reported regions</h2>
            </div>
          </div>
          <div className="rp-chip-row">
            {(summary.pain_areas || []).map((area) => (
              <StatusPill key={area} tone="rose">{area}</StatusPill>
            ))}
          </div>
        </article>

        <article className="rp-card">
          <div className="rp-section-head">
            <div>
              <span className="rp-eyebrow">Goals</span>
              <h2>Patient priorities</h2>
            </div>
          </div>
          <div className="rp-chip-row">
            {(summary.goal_tags || []).map((goal) => (
              <StatusPill key={goal} tone="warm">{goal}</StatusPill>
            ))}
          </div>
          {summary.next_steps?.length ? (
            <ul className="rp-bullet-list">
              {summary.next_steps.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          ) : null}
        </article>
      </section>
    </div>
  );
}
