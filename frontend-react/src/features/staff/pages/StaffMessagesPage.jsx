import React, { useCallback, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { buildUrl, fetchJson } from "../../../shared/api";
import { useApiResource } from "../../../shared/hooks";
import { ErrorState, LoadingState, StatusPill } from "../../../shared/ui";

export default function StaffMessagesPage({ config }) {
  const [searchParams, setSearchParams] = useSearchParams();
  const selectedPatientId = searchParams.get("patient_id") || "";
  const currentSearch = searchParams.get("q") || "";
  const [searchDraft, setSearchDraft] = useState(currentSearch);
  const [topic, setTopic] = useState("appointment");
  const [body, setBody] = useState("");
  const [notice, setNotice] = useState("");
  const [errorNotice, setErrorNotice] = useState("");
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    setSearchDraft(currentSearch);
  }, [currentSearch]);

  const endpoint = useMemo(
    () => buildUrl(config.staffMessagesEndpoint, { patient_id: selectedPatientId, q: currentSearch }),
    [config.staffMessagesEndpoint, selectedPatientId, currentSearch]
  );
  const resource = useApiResource(() => fetchJson(endpoint), [endpoint]);

  const updateQuery = useCallback((nextSearch, nextPatientId) => {
    const next = new URLSearchParams();
    if (nextSearch) {
      next.set("q", nextSearch);
    }
    if (nextPatientId) {
      next.set("patient_id", String(nextPatientId));
    }
    setSearchParams(next);
  }, [setSearchParams]);

  const openThread = useCallback((patientId) => {
    setNotice("");
    setErrorNotice("");
    updateQuery(currentSearch, patientId);
  }, [currentSearch, updateQuery]);

  const submitSearch = (event) => {
    event.preventDefault();
    setNotice("");
    setErrorNotice("");
    updateQuery(searchDraft.trim(), selectedPatientId);
  };

  const clearSearch = () => {
    setSearchDraft("");
    setNotice("");
    setErrorNotice("");
    updateQuery("", selectedPatientId);
  };

  const sendMessage = async (event) => {
    event.preventDefault();
    if (!resource.data?.selected_patient) {
      return;
    }
    setSubmitting(true);
    setNotice("");
    setErrorNotice("");
    const { response, data } = await fetchJson(
      buildUrl(`${config.staffMessagesEndpoint}/${resource.data.selected_patient.id}`, { q: currentSearch }),
      {
        method: "POST",
        body: JSON.stringify({ topic, body }),
      }
    );
    setSubmitting(false);
    if (!response.ok || data.ok === false) {
      setErrorNotice(data.errors ? data.errors.join(" ") : data.error || "Message failed.");
      return;
    }
    setBody("");
    setNotice(data.message || "Message sent.");
    resource.reload();
  };

  if (resource.loading) {
    return <LoadingState title="Loading staff messaging" detail="Opening patient-specific message threads." />;
  }
  if (resource.error) {
    return <ErrorState detail={resource.error} onRetry={resource.reload} />;
  }

  const threads = resource.data.threads || [];
  const selectedPatient = resource.data.selected_patient;
  const messages = resource.data.messages || [];
  const topics = resource.data.message_topics || [];

  return (
    <div className="rp-page-grid">
      <section className="rp-card rp-hero-card">
        <div>
          <div className="rp-eyebrow">Staff messaging</div>
          <h2>Individual patient conversations</h2>
          <p>Each thread is isolated to one patient so the clinic team can respond without exposing another patient’s messages.</p>
        </div>
        <div className="rp-header-card">
          <span>Coverage</span>
          <strong>{threads.length} patient threads</strong>
          <small>{selectedPatient ? selectedPatient.full_name : "No patient selected"}</small>
          <small>{resource.data.unread_before_open ? `${resource.data.unread_before_open} unread opened` : "Thread up to date"}</small>
        </div>
      </section>

      <section className="rp-thread-layout">
        <aside className="rp-card rp-thread-sidebar">
          <div className="rp-section-head">
            <div>
              <span className="rp-eyebrow">Patients</span>
              <h2>Conversation list</h2>
            </div>
          </div>
          <form className="rp-form-stack" onSubmit={submitSearch}>
            <label>
              <span>Search</span>
              <input
                type="text"
                value={searchDraft}
                onChange={(event) => setSearchDraft(event.target.value)}
                placeholder="Name, email, or message text"
              />
            </label>
            <div className="rp-inline-actions">
              <button type="submit" className="rp-button rp-button-primary">Filter</button>
              {currentSearch ? (
                <button type="button" className="rp-button rp-button-secondary" onClick={clearSearch}>
                  Clear
                </button>
              ) : null}
            </div>
          </form>

          <div className="rp-thread-list">
            {threads.length ? threads.map((thread) => (
              <button
                key={thread.patient_user_id}
                type="button"
                className={`rp-thread-link ${selectedPatient?.id === thread.patient_user_id ? "active" : ""}`.trim()}
                onClick={() => openThread(thread.patient_user_id)}
              >
                <div className="rp-thread-link-head">
                  <div>
                    <strong>{thread.patient_name}</strong>
                    <small>{thread.patient_email}</small>
                  </div>
                  {thread.unread_for_staff ? <StatusPill tone="rose">{thread.unread_for_staff} unread</StatusPill> : null}
                </div>
                <div className="rp-inline-actions rp-inline-actions-tight">
                  <StatusPill tone={thread.last_topic_tone}>{thread.last_topic_label}</StatusPill>
                  <small>{thread.last_created_label}</small>
                </div>
                <p>{thread.last_body || "No messages yet."}</p>
              </button>
            )) : <div className="rp-empty-inline">No patient threads matched your search.</div>}
          </div>
        </aside>

        <section className="rp-card">
          <div className="rp-section-head">
            <div>
              <span className="rp-eyebrow">Conversation</span>
              <h2>{selectedPatient ? selectedPatient.full_name : "Select a patient thread"}</h2>
            </div>
            {selectedPatient ? <StatusPill tone="life">{selectedPatient.email}</StatusPill> : null}
          </div>

          {selectedPatient ? (
            <>
              <div className="rp-message-stream">
                {messages.length ? (
                  messages.map((message) => (
                    <article key={message.id} className={`rp-message ${message.sender_role === "client" ? "is-inbound" : "is-outbound"}`.trim()}>
                      <div className="rp-message-bubble">
                        <div className="rp-list-head">
                          <div>
                            <StatusPill tone={message.topic_tone}>{message.topic_label}</StatusPill>
                            <strong>{message.sender_name}</strong>
                          </div>
                        </div>
                        <p>{message.body}</p>
                        <small>{message.created_label}</small>
                      </div>
                    </article>
                  ))
                ) : (
                  <div className="rp-empty-inline">No messages yet. Send the first patient-specific message to start this thread.</div>
                )}
              </div>

              <div className="rp-card rp-subcard">
                <div className="rp-section-head">
                  <div>
                    <span className="rp-eyebrow">Reply</span>
                    <h2>Send message</h2>
                  </div>
                </div>
                {notice ? <div className="rp-alert rp-alert-success">{notice}</div> : null}
                {errorNotice ? <div className="rp-alert rp-alert-error">{errorNotice}</div> : null}
                <form className="rp-form-stack" onSubmit={sendMessage}>
                  <label>
                    <span>Topic</span>
                    <select value={topic} onChange={(event) => setTopic(event.target.value)}>
                      {topics.map((item) => (
                        <option key={item.value} value={item.value}>
                          {item.label}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label>
                    <span>Message</span>
                    <textarea
                      rows="5"
                      value={body}
                      onChange={(event) => setBody(event.target.value)}
                      placeholder="Write a patient-specific message..."
                    />
                  </label>
                  <button type="submit" className="rp-button rp-button-primary" disabled={submitting}>
                    {submitting ? "Sending..." : "Send message"}
                  </button>
                </form>
              </div>
            </>
          ) : (
            <div className="rp-empty-inline">Select a patient thread from the left to open the conversation.</div>
          )}
        </section>
      </section>
    </div>
  );
}
