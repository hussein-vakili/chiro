import React, { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { fetchJson } from "../../../shared/api";
import { useApiMutation, useApiResource } from "../../../shared/hooks";
import { ErrorState, LoadingState, StatusPill } from "../../../shared/ui";

export default function MessagesPage({ config }) {
  const queryClient = useQueryClient();
  const resource = useApiResource(() => fetchJson(config.messagesEndpoint), [config.messagesEndpoint]);
  const [topic, setTopic] = useState("appointment");
  const [body, setBody] = useState("");
  const [notice, setNotice] = useState("");
  const [errorNotice, setErrorNotice] = useState("");
  const sendMutation = useApiMutation(
    ({ nextTopic, nextBody }) =>
      fetchJson(config.messagesEndpoint, {
        method: "POST",
        body: JSON.stringify({ topic: nextTopic, body: nextBody }),
      }),
    {
      onSuccess: async (data) => {
        setBody("");
        setNotice(data.message || "Message sent.");
        setErrorNotice("");
        await queryClient.invalidateQueries({ queryKey: resource.queryKey });
      },
      onError: (error) => {
        setErrorNotice(error.message || "Message failed.");
      },
    }
  );

  const sendMessage = async (event) => {
    event.preventDefault();
    setNotice("");
    setErrorNotice("");
    await sendMutation.mutateAsync({ nextTopic: topic, nextBody: body });
  };

  if (resource.loading) {
    return <LoadingState title="Loading messages" detail="Opening your secure thread." />;
  }
  if (resource.error) {
    return <ErrorState detail={resource.error} onRetry={resource.reload} />;
  }

  const messages = resource.data.messages;
  const topics = resource.data.message_topics;

  return (
    <div className="rp-two-column">
      <section className="rp-card">
        <div className="rp-section-head">
          <div>
            <span className="rp-eyebrow">Messages</span>
            <h2>Your chiropractic thread</h2>
          </div>
          <StatusPill tone={resource.data.unread_before_open ? "rose" : "life"}>
            {resource.data.unread_before_open ? `${resource.data.unread_before_open} unread` : "Up to date"}
          </StatusPill>
        </div>
        <div className="rp-message-stream">
          {messages.length ? (
            messages.map((message) => (
              <article key={message.id} className={`rp-message ${message.sender_role === "client" ? "is-client" : "is-staff"}`.trim()}>
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
            <div className="rp-empty-inline">No messages yet. Send your first secure update to the clinic.</div>
          )}
        </div>
      </section>

      <section className="rp-card">
        <div className="rp-section-head">
          <div>
            <span className="rp-eyebrow">Send message</span>
            <h2>Write to your care team</h2>
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
            <textarea rows="6" value={body} onChange={(event) => setBody(event.target.value)} placeholder="Write your update, question, or booking request..." />
          </label>
          <button type="submit" className="rp-button rp-button-primary" disabled={sendMutation.isPending}>
            {sendMutation.isPending ? "Sending..." : "Send message"}
          </button>
        </form>
      </section>
    </div>
  );
}
