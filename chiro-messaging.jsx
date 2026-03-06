import { useState, useEffect, useRef } from "react";

const CHIRO_TOPICS = [
  { id: "appointment", label: "Appointment", icon: "📅", color: "#2A9D8F" },
  { id: "treatment", label: "Treatment Query", icon: "🦴", color: "#E76F51" },
  { id: "exercise", label: "Home Exercise", icon: "🏋️", color: "#457B9D" },
  { id: "symptoms", label: "Symptom Update", icon: "📋", color: "#6C5CE7" },
  { id: "billing", label: "Billing / Insurance", icon: "💷", color: "#F4A261" },
];

const QUICK_REPLIES_CHIRO = [
  "I'll review your file and get back to you shortly.",
  "Please come in 10 minutes early for your next appointment.",
  "Continue with the prescribed exercises and report back in 3 days.",
  "We have availability this week — would you like to book?",
  "Your progress looks good. Let's discuss at your next visit.",
];

const QUICK_REPLIES_PATIENT = [
  "Can I reschedule my appointment?",
  "I've been doing the exercises — should I increase reps?",
  "My pain has changed since last visit.",
  "What should I avoid doing before my appointment?",
  "Do you have any earlier availability?",
];

const MOCK_PATIENTS = [
  {
    id: "p1",
    name: "Sarah Mitchell",
    initials: "SM",
    lastVisit: "28 Feb 2026",
    nextAppt: "10 Mar 2026, 09:30",
    condition: "Lumbar disc herniation",
    unread: 2,
    messages: [
      { id: 1, from: "patient", topic: "symptoms", text: "Hi, I've noticed my lower back pain has been radiating down my left leg more since Tuesday. It's worse when sitting. Should I be concerned?", time: "09:14", date: "05 Mar 2026" },
      { id: 2, from: "chiro", topic: "symptoms", text: "Thanks for letting me know, Sarah. The radiating pattern you're describing is consistent with what we've been treating. Are you keeping up with the McKenzie extensions I prescribed?", time: "09:42", date: "05 Mar 2026" },
      { id: 3, from: "patient", topic: "exercise", text: "Yes, doing them 3x daily. The centralisation happens after about 10 reps but the leg symptoms return after sitting for more than 20 mins.", time: "10:05", date: "05 Mar 2026" },
      { id: 4, from: "chiro", topic: "exercise", text: "Good that you're getting centralisation — that's a positive sign. Try breaking up sitting to every 15 minutes with a set of 10 standing extensions. We'll reassess on Monday.", time: "10:18", date: "05 Mar 2026" },
      { id: 5, from: "patient", topic: "appointment", text: "Will do. Also, is there any chance I could move Monday's appointment to the afternoon? I have a work meeting in the morning.", time: "14:30", date: "05 Mar 2026" },
      { id: 6, from: "patient", topic: "appointment", text: "Maybe around 2pm if possible?", time: "14:31", date: "05 Mar 2026" },
    ],
  },
  {
    id: "p2",
    name: "James Cooper",
    initials: "JC",
    lastVisit: "03 Mar 2026",
    nextAppt: "12 Mar 2026, 14:00",
    condition: "Cervicogenic headache",
    unread: 0,
    messages: [
      { id: 1, from: "chiro", topic: "treatment", text: "Hi James, just following up from Monday's session. How's the neck mobility feeling? Any change in headache frequency?", time: "11:00", date: "04 Mar 2026" },
      { id: 2, from: "patient", topic: "treatment", text: "Definitely better! Only had one mild headache since Monday and it resolved within an hour. The neck stretches are helping.", time: "16:22", date: "04 Mar 2026" },
      { id: 3, from: "chiro", topic: "treatment", text: "Excellent progress. Keep up with the deep neck flexor exercises. We'll do a formal reassessment next Thursday using your NDI scores to track improvement.", time: "17:05", date: "04 Mar 2026" },
    ],
  },
  {
    id: "p3",
    name: "Emma Patel",
    initials: "EP",
    lastVisit: "01 Mar 2026",
    nextAppt: "08 Mar 2026, 11:00",
    condition: "Rotator cuff tendinopathy",
    unread: 1,
    messages: [
      { id: 1, from: "patient", topic: "symptoms", text: "Hi, I'm having trouble sleeping on my right side. The shoulder pain wakes me up around 3am most nights.", time: "07:45", date: "06 Mar 2026" },
    ],
  },
];

// --- Utility Components ---

function TopicBadge({ topicId, small = false }) {
  const topic = CHIRO_TOPICS.find((t) => t.id === topicId);
  if (!topic) return null;
  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: small ? 3 : 5,
        background: topic.color + "18",
        color: topic.color,
        padding: small ? "2px 7px" : "3px 10px",
        borderRadius: 20,
        fontSize: small ? 10 : 11,
        fontWeight: 600,
        letterSpacing: 0.3,
        whiteSpace: "nowrap",
      }}
    >
      <span style={{ fontSize: small ? 10 : 12 }}>{topic.icon}</span>
      {topic.label}
    </span>
  );
}

function Avatar({ initials, size = 40, color = "#264653" }) {
  return (
    <div
      style={{
        width: size,
        height: size,
        minWidth: size,
        borderRadius: "50%",
        background: `linear-gradient(135deg, ${color}, ${color}cc)`,
        color: "#fff",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        fontSize: size * 0.36,
        fontWeight: 700,
        letterSpacing: 0.5,
        fontFamily: "'DM Sans', sans-serif",
      }}
    >
      {initials}
    </div>
  );
}

// --- Main App ---

export default function ChiroMessaging() {
  const [role, setRole] = useState("chiro"); // "chiro" or "patient"
  const [patients, setPatients] = useState(MOCK_PATIENTS);
  const [selectedId, setSelectedId] = useState("p1");
  const [input, setInput] = useState("");
  const [selectedTopic, setSelectedTopic] = useState("appointment");
  const [showTopicPicker, setShowTopicPicker] = useState(false);
  const [showQuickReplies, setShowQuickReplies] = useState(false);
  const [showMobileList, setShowMobileList] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  const selected = patients.find((p) => p.id === selectedId);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [selected?.messages?.length]);

  function sendMessage() {
    if (!input.trim()) return;
    setPatients((prev) =>
      prev.map((p) =>
        p.id === selectedId
          ? {
              ...p,
              messages: [
                ...p.messages,
                {
                  id: Date.now(),
                  from: role,
                  topic: selectedTopic,
                  text: input.trim(),
                  time: new Date().toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" }),
                  date: "06 Mar 2026",
                },
              ],
              unread: role === "patient" ? p.unread + 1 : 0,
            }
          : p
      )
    );
    setInput("");
    setShowQuickReplies(false);
    inputRef.current?.focus();
  }

  function handleQuickReply(text) {
    setInput(text);
    setShowQuickReplies(false);
    setTimeout(() => inputRef.current?.focus(), 50);
  }

  const filteredPatients = patients.filter((p) =>
    p.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    p.condition.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const quickReplies = role === "chiro" ? QUICK_REPLIES_CHIRO : QUICK_REPLIES_PATIENT;

  // --- Styles ---
  const palette = {
    bg: "#F0F4F3",
    surface: "#FFFFFF",
    surfaceAlt: "#F7FAF9",
    primary: "#264653",
    accent: "#2A9D8F",
    accentLight: "#2A9D8F22",
    text: "#1A2E35",
    textMuted: "#6B8A8E",
    border: "#E0EAE8",
    chiroMsg: "#264653",
    patientMsg: "#2A9D8F",
  };

  return (
    <div
      style={{
        fontFamily: "'DM Sans', 'Nunito', sans-serif",
        height: "100vh",
        width: "100%",
        background: palette.bg,
        display: "flex",
        flexDirection: "column",
        color: palette.text,
        overflow: "hidden",
      }}
    >
      <link
        href="https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,300;0,9..40,500;0,9..40,700;1,9..40,400&family=Nunito:wght@400;600;700&display=swap"
        rel="stylesheet"
      />

      {/* ===== HEADER ===== */}
      <header
        style={{
          background: palette.primary,
          color: "#fff",
          padding: "0 24px",
          height: 60,
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          boxShadow: "0 2px 12px #26465322",
          zIndex: 10,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          {!showMobileList && (
            <button
              onClick={() => setShowMobileList(true)}
              style={{
                background: "none",
                border: "none",
                color: "#fff",
                fontSize: 22,
                cursor: "pointer",
                display: "none",
                padding: 0,
              }}
              className="mobile-back"
            >
              ←
            </button>
          )}
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <svg width="28" height="28" viewBox="0 0 28 28" fill="none">
              <circle cx="14" cy="14" r="13" stroke="#2A9D8F" strokeWidth="2" fill="none" />
              <path d="M14 6 C14 6 10 10 10 14 C10 18 14 22 14 22 C14 22 18 18 18 14 C18 10 14 6 14 6Z" fill="#2A9D8F" opacity="0.7" />
              <circle cx="14" cy="14" r="2.5" fill="#fff" />
            </svg>
            <span style={{ fontSize: 17, fontWeight: 700, letterSpacing: -0.3 }}>
              Life Chiropractic
            </span>
          </div>
          <span
            style={{
              fontSize: 10,
              fontWeight: 600,
              background: palette.accent,
              padding: "2px 8px",
              borderRadius: 10,
              letterSpacing: 0.5,
              textTransform: "uppercase",
            }}
          >
            Messages
          </span>
        </div>

        {/* Role Switcher */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 4,
            background: "#ffffff18",
            borderRadius: 8,
            padding: 3,
          }}
        >
          {["chiro", "patient"].map((r) => (
            <button
              key={r}
              onClick={() => setRole(r)}
              style={{
                padding: "5px 14px",
                border: "none",
                borderRadius: 6,
                fontSize: 12,
                fontWeight: 600,
                cursor: "pointer",
                background: role === r ? palette.accent : "transparent",
                color: "#fff",
                transition: "all 0.2s",
                fontFamily: "inherit",
              }}
            >
              {r === "chiro" ? "🩺 Practitioner" : "🧑 Patient"}
            </button>
          ))}
        </div>
      </header>

      {/* ===== BODY ===== */}
      <div style={{ flex: 1, display: "flex", overflow: "hidden" }}>
        {/* --- LEFT: Patient List --- */}
        <aside
          style={{
            width: 320,
            minWidth: 280,
            background: palette.surface,
            borderRight: `1px solid ${palette.border}`,
            display: "flex",
            flexDirection: "column",
            overflow: "hidden",
          }}
        >
          {/* Search */}
          <div style={{ padding: "14px 16px 10px" }}>
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: 8,
                background: palette.surfaceAlt,
                borderRadius: 10,
                padding: "8px 12px",
                border: `1px solid ${palette.border}`,
              }}
            >
              <span style={{ color: palette.textMuted, fontSize: 15 }}>🔍</span>
              <input
                type="text"
                placeholder={role === "chiro" ? "Search patients..." : "Search conversations..."}
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                style={{
                  border: "none",
                  outline: "none",
                  background: "transparent",
                  flex: 1,
                  fontSize: 13,
                  fontFamily: "inherit",
                  color: palette.text,
                }}
              />
            </div>
          </div>

          {/* Patient / Conversation List */}
          <div style={{ flex: 1, overflowY: "auto", padding: "0 8px 8px" }}>
            {filteredPatients.map((p) => {
              const isActive = p.id === selectedId;
              const lastMsg = p.messages[p.messages.length - 1];
              return (
                <button
                  key={p.id}
                  onClick={() => {
                    setSelectedId(p.id);
                    setShowMobileList(false);
                    // Mark as read
                    if (role === "chiro") {
                      setPatients((prev) =>
                        prev.map((pt) => (pt.id === p.id ? { ...pt, unread: 0 } : pt))
                      );
                    }
                  }}
                  style={{
                    width: "100%",
                    display: "flex",
                    alignItems: "flex-start",
                    gap: 12,
                    padding: "12px 12px",
                    border: "none",
                    borderRadius: 12,
                    background: isActive ? palette.accentLight : "transparent",
                    cursor: "pointer",
                    textAlign: "left",
                    transition: "all 0.15s",
                    fontFamily: "inherit",
                    marginBottom: 2,
                    borderLeft: isActive ? `3px solid ${palette.accent}` : "3px solid transparent",
                  }}
                >
                  <Avatar
                    initials={p.initials}
                    size={42}
                    color={isActive ? palette.accent : palette.primary}
                  />
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                      <span style={{ fontWeight: 700, fontSize: 13.5, color: palette.text }}>
                        {p.name}
                      </span>
                      <span style={{ fontSize: 10, color: palette.textMuted, whiteSpace: "nowrap" }}>
                        {lastMsg?.time}
                      </span>
                    </div>
                    <div
                      style={{
                        fontSize: 11,
                        color: palette.accent,
                        fontWeight: 600,
                        margin: "2px 0",
                      }}
                    >
                      {p.condition}
                    </div>
                    <div
                      style={{
                        fontSize: 12,
                        color: palette.textMuted,
                        whiteSpace: "nowrap",
                        overflow: "hidden",
                        textOverflow: "ellipsis",
                        maxWidth: 190,
                      }}
                    >
                      {lastMsg?.from === "chiro" ? "You: " : ""}
                      {lastMsg?.text}
                    </div>
                    {p.unread > 0 && role === "chiro" && (
                      <span
                        style={{
                          display: "inline-block",
                          marginTop: 4,
                          background: palette.accent,
                          color: "#fff",
                          fontSize: 10,
                          fontWeight: 700,
                          padding: "1px 7px",
                          borderRadius: 10,
                        }}
                      >
                        {p.unread} new
                      </span>
                    )}
                  </div>
                </button>
              );
            })}
          </div>
        </aside>

        {/* --- RIGHT: Chat Area --- */}
        <main style={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden" }}>
          {selected ? (
            <>
              {/* Chat Header / Patient Info Bar */}
              <div
                style={{
                  padding: "12px 24px",
                  background: palette.surface,
                  borderBottom: `1px solid ${palette.border}`,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  gap: 16,
                }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
                  <Avatar initials={selected.initials} size={38} color={palette.accent} />
                  <div>
                    <div style={{ fontWeight: 700, fontSize: 15 }}>{selected.name}</div>
                    <div style={{ fontSize: 11.5, color: palette.textMuted }}>
                      {selected.condition}
                    </div>
                  </div>
                </div>
                <div
                  style={{
                    display: "flex",
                    gap: 16,
                    fontSize: 11.5,
                    color: palette.textMuted,
                  }}
                >
                  <div>
                    <span style={{ fontWeight: 600, color: palette.text }}>Last visit:</span>{" "}
                    {selected.lastVisit}
                  </div>
                  <div>
                    <span style={{ fontWeight: 600, color: palette.text }}>Next:</span>{" "}
                    {selected.nextAppt}
                  </div>
                </div>
              </div>

              {/* Messages */}
              <div
                style={{
                  flex: 1,
                  overflowY: "auto",
                  padding: "20px 24px",
                  background: palette.bg,
                }}
              >
                {/* Topic-based guideline notice */}
                <div
                  style={{
                    textAlign: "center",
                    margin: "0 auto 20px",
                    maxWidth: 420,
                    padding: "10px 16px",
                    background: "#fff",
                    borderRadius: 12,
                    border: `1px dashed ${palette.border}`,
                    fontSize: 11.5,
                    color: palette.textMuted,
                    lineHeight: 1.5,
                  }}
                >
                  🔒 This channel is for <strong>chiropractic-related</strong> communication only — appointments, treatment queries, symptom updates, home exercises, and billing. Please tag each message with a topic.
                </div>

                {selected.messages.map((msg, i) => {
                  const isChiro = msg.from === "chiro";
                  const showDate =
                    i === 0 || selected.messages[i - 1]?.date !== msg.date;
                  return (
                    <div key={msg.id}>
                      {showDate && (
                        <div
                          style={{
                            textAlign: "center",
                            fontSize: 10.5,
                            fontWeight: 600,
                            color: palette.textMuted,
                            margin: "16px 0 10px",
                            letterSpacing: 0.5,
                          }}
                        >
                          {msg.date}
                        </div>
                      )}
                      <div
                        style={{
                          display: "flex",
                          justifyContent: isChiro ? "flex-end" : "flex-start",
                          marginBottom: 10,
                        }}
                      >
                        <div style={{ maxWidth: "70%", minWidth: 180 }}>
                          <div
                            style={{
                              display: "flex",
                              justifyContent: isChiro ? "flex-end" : "flex-start",
                              marginBottom: 4,
                              gap: 6,
                              alignItems: "center",
                            }}
                          >
                            <TopicBadge topicId={msg.topic} small />
                            <span style={{ fontSize: 10, color: palette.textMuted }}>
                              {msg.time}
                            </span>
                          </div>
                          <div
                            style={{
                              background: isChiro ? palette.chiroMsg : palette.surface,
                              color: isChiro ? "#fff" : palette.text,
                              padding: "11px 16px",
                              borderRadius: isChiro
                                ? "16px 16px 4px 16px"
                                : "16px 16px 16px 4px",
                              fontSize: 13.5,
                              lineHeight: 1.55,
                              boxShadow: "0 1px 4px #00000008",
                              border: isChiro ? "none" : `1px solid ${palette.border}`,
                            }}
                          >
                            {msg.text}
                          </div>
                          <div
                            style={{
                              fontSize: 10,
                              color: palette.textMuted,
                              marginTop: 3,
                              textAlign: isChiro ? "right" : "left",
                              fontWeight: 500,
                            }}
                          >
                            {isChiro ? "🩺 Practitioner" : "🧑 Patient"}
                          </div>
                        </div>
                      </div>
                    </div>
                  );
                })}
                <div ref={messagesEndRef} />
              </div>

              {/* Quick Replies */}
              {showQuickReplies && (
                <div
                  style={{
                    background: palette.surface,
                    borderTop: `1px solid ${palette.border}`,
                    padding: "10px 20px",
                    display: "flex",
                    flexWrap: "wrap",
                    gap: 6,
                  }}
                >
                  {quickReplies.map((qr, i) => (
                    <button
                      key={i}
                      onClick={() => handleQuickReply(qr)}
                      style={{
                        padding: "6px 12px",
                        borderRadius: 20,
                        border: `1px solid ${palette.border}`,
                        background: palette.surfaceAlt,
                        fontSize: 12,
                        color: palette.text,
                        cursor: "pointer",
                        fontFamily: "inherit",
                        transition: "all 0.15s",
                      }}
                      onMouseEnter={(e) => {
                        e.target.style.background = palette.accentLight;
                        e.target.style.borderColor = palette.accent;
                      }}
                      onMouseLeave={(e) => {
                        e.target.style.background = palette.surfaceAlt;
                        e.target.style.borderColor = palette.border;
                      }}
                    >
                      {qr}
                    </button>
                  ))}
                </div>
              )}

              {/* Composer */}
              <div
                style={{
                  background: palette.surface,
                  borderTop: `1px solid ${palette.border}`,
                  padding: "12px 20px 14px",
                }}
              >
                {/* Topic selector row */}
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 8,
                    marginBottom: 10,
                    flexWrap: "wrap",
                  }}
                >
                  <span style={{ fontSize: 11, fontWeight: 600, color: palette.textMuted }}>
                    Topic:
                  </span>
                  {CHIRO_TOPICS.map((t) => (
                    <button
                      key={t.id}
                      onClick={() => setSelectedTopic(t.id)}
                      style={{
                        padding: "4px 10px",
                        borderRadius: 16,
                        border: `1.5px solid ${selectedTopic === t.id ? t.color : palette.border}`,
                        background: selectedTopic === t.id ? t.color + "18" : "transparent",
                        fontSize: 11,
                        fontWeight: 600,
                        color: selectedTopic === t.id ? t.color : palette.textMuted,
                        cursor: "pointer",
                        fontFamily: "inherit",
                        display: "flex",
                        alignItems: "center",
                        gap: 4,
                        transition: "all 0.15s",
                      }}
                    >
                      <span style={{ fontSize: 12 }}>{t.icon}</span>
                      {t.label}
                    </button>
                  ))}
                </div>

                {/* Input Row */}
                <div style={{ display: "flex", gap: 8, alignItems: "flex-end" }}>
                  <button
                    onClick={() => setShowQuickReplies(!showQuickReplies)}
                    title="Quick replies"
                    style={{
                      width: 38,
                      height: 38,
                      borderRadius: 10,
                      border: `1px solid ${palette.border}`,
                      background: showQuickReplies ? palette.accentLight : palette.surfaceAlt,
                      color: showQuickReplies ? palette.accent : palette.textMuted,
                      fontSize: 17,
                      cursor: "pointer",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      flexShrink: 0,
                    }}
                  >
                    ⚡
                  </button>
                  <div
                    style={{
                      flex: 1,
                      display: "flex",
                      alignItems: "flex-end",
                      background: palette.surfaceAlt,
                      borderRadius: 12,
                      border: `1.5px solid ${palette.border}`,
                      padding: "4px 4px 4px 14px",
                      transition: "border-color 0.2s",
                    }}
                  >
                    <textarea
                      ref={inputRef}
                      value={input}
                      onChange={(e) => setInput(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === "Enter" && !e.shiftKey) {
                          e.preventDefault();
                          sendMessage();
                        }
                      }}
                      placeholder={
                        role === "chiro"
                          ? "Type your message to the patient..."
                          : "Type your question or message..."
                      }
                      rows={1}
                      style={{
                        flex: 1,
                        border: "none",
                        outline: "none",
                        background: "transparent",
                        fontSize: 13.5,
                        fontFamily: "inherit",
                        color: palette.text,
                        resize: "none",
                        lineHeight: 1.5,
                        padding: "6px 0",
                        minHeight: 30,
                        maxHeight: 120,
                      }}
                      onInput={(e) => {
                        e.target.style.height = "auto";
                        e.target.style.height = e.target.scrollHeight + "px";
                      }}
                    />
                    <button
                      onClick={sendMessage}
                      disabled={!input.trim()}
                      style={{
                        width: 34,
                        height: 34,
                        borderRadius: 9,
                        border: "none",
                        background: input.trim() ? palette.accent : palette.border,
                        color: "#fff",
                        fontSize: 16,
                        cursor: input.trim() ? "pointer" : "default",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        transition: "all 0.2s",
                        flexShrink: 0,
                      }}
                    >
                      ↑
                    </button>
                  </div>
                </div>
              </div>
            </>
          ) : (
            <div
              style={{
                flex: 1,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                color: palette.textMuted,
                fontSize: 14,
              }}
            >
              Select a conversation to begin
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
