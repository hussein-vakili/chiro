import { useState, useEffect, useCallback, useRef } from "react";

const BODY_REGIONS = ["Cervical", "Thoracic", "Lumbar", "Sacral/Pelvic", "Upper Extremity", "Lower Extremity", "TMJ", "Cranial"];
const ENTRY_TYPES = ["Clinical Insight", "Case Reflection", "Technique Note", "Learning", "Personal Growth", "Practice Management"];
const MOODS = [
  { emoji: "🔥", label: "Energized", color: "#E85D3A" },
  { emoji: "😊", label: "Good", color: "#4CAF50" },
  { emoji: "😐", label: "Neutral", color: "#9E9E9E" },
  { emoji: "😓", label: "Drained", color: "#7986CB" },
  { emoji: "🤔", label: "Reflective", color: "#AB47BC" },
];

const PROMPTS = {
  "Clinical Insight": [
    "What clinical pattern did you notice today that surprised you?",
    "Describe a patient response that challenged your expectations.",
    "What connection between symptoms did you observe?",
  ],
  "Case Reflection": [
    "Walk through a complex case — what would you do differently?",
    "What outcome made you proud today?",
    "Describe a case where your initial assessment shifted.",
  ],
  "Technique Note": [
    "What adjustment modification worked particularly well?",
    "Describe a technique adaptation you tried and why.",
    "What hands-on discovery did you make during treatment?",
  ],
  "Learning": [
    "What new research or concept are you integrating into practice?",
    "What did a colleague or mentor teach you recently?",
    "What gap in your knowledge became apparent today?",
  ],
  "Personal Growth": [
    "How did you handle a difficult patient interaction?",
    "What boundaries did you set or need to set?",
    "What gave you meaning in your work today?",
  ],
  "Practice Management": [
    "What workflow improvement could save you time?",
    "How did patient flow feel today?",
    "What systems need attention in your practice?",
  ],
};

function generateId() {
  return Date.now().toString(36) + Math.random().toString(36).substr(2, 5);
}

function formatDate(ts) {
  const d = new Date(ts);
  return d.toLocaleDateString("en-US", { weekday: "short", month: "short", day: "numeric", year: "numeric" });
}

function formatTime(ts) {
  return new Date(ts).toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit" });
}

function daysAgo(ts) {
  const now = new Date();
  const then = new Date(ts);
  const diff = Math.floor((now - then) / (1000 * 60 * 60 * 24));
  if (diff === 0) return "Today";
  if (diff === 1) return "Yesterday";
  return `${diff} days ago`;
}

function getStreak(entries) {
  if (!entries.length) return 0;
  const dates = [...new Set(entries.map(e => new Date(e.timestamp).toDateString()))].sort((a, b) => new Date(b) - new Date(a));
  let streak = 0;
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  for (let i = 0; i < dates.length; i++) {
    const d = new Date(dates[i]);
    d.setHours(0, 0, 0, 0);
    const expected = new Date(today);
    expected.setDate(expected.getDate() - i);
    if (d.getTime() === expected.getTime()) {
      streak++;
    } else break;
  }
  return streak;
}

function getWeekActivity(entries) {
  const days = [];
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  for (let i = 6; i >= 0; i--) {
    const d = new Date(today);
    d.setDate(d.getDate() - i);
    const ds = d.toDateString();
    const count = entries.filter(e => new Date(e.timestamp).toDateString() === ds).length;
    days.push({ label: d.toLocaleDateString("en-US", { weekday: "narrow" }), count, isToday: i === 0 });
  }
  return days;
}

// Persistent storage helpers
async function loadEntries() {
  try {
    const result = await window.storage.get("chiro-journal-entries");
    if (result && result.value) return JSON.parse(result.value);
  } catch (e) { /* key doesn't exist */ }
  return [];
}

async function saveEntries(entries) {
  try {
    await window.storage.set("chiro-journal-entries", JSON.stringify(entries));
  } catch (e) {
    console.error("Failed to save:", e);
  }
}

// ─── COMPONENTS ───

function Tag({ label, active, onClick, color }) {
  return (
    <button
      onClick={onClick}
      style={{
        padding: "4px 12px",
        borderRadius: "100px",
        border: active ? "none" : "1px solid #3a3a3a",
        background: active ? (color || "#E85D3A") : "transparent",
        color: active ? "#fff" : "#aaa",
        fontSize: "12px",
        fontFamily: "'DM Sans', sans-serif",
        cursor: "pointer",
        transition: "all 0.2s",
        whiteSpace: "nowrap",
      }}
    >
      {label}
    </button>
  );
}

function EntryCard({ entry, onClick, isExpanded }) {
  const typeColor = {
    "Clinical Insight": "#E85D3A",
    "Case Reflection": "#4CAF50",
    "Technique Note": "#2196F3",
    "Learning": "#FF9800",
    "Personal Growth": "#AB47BC",
    "Practice Management": "#00BCD4",
  };

  return (
    <div
      onClick={onClick}
      style={{
        background: "#1a1a1a",
        borderRadius: "12px",
        padding: "20px",
        cursor: "pointer",
        borderLeft: `3px solid ${typeColor[entry.type] || "#555"}`,
        transition: "all 0.25s ease",
        marginBottom: "12px",
        transform: isExpanded ? "scale(1)" : "scale(1)",
      }}
      onMouseEnter={e => { e.currentTarget.style.background = "#222"; }}
      onMouseLeave={e => { e.currentTarget.style.background = "#1a1a1a"; }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "8px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <span style={{ fontSize: "11px", color: typeColor[entry.type], fontFamily: "'DM Mono', monospace", textTransform: "uppercase", letterSpacing: "0.5px" }}>
            {entry.type}
          </span>
          {entry.mood && (
            <span style={{ fontSize: "14px" }}>{MOODS.find(m => m.label === entry.mood)?.emoji}</span>
          )}
        </div>
        <span style={{ fontSize: "11px", color: "#666", fontFamily: "'DM Mono', monospace" }}>
          {daysAgo(entry.timestamp)}
        </span>
      </div>

      <h3 style={{
        fontFamily: "'Instrument Serif', serif",
        fontSize: "18px",
        color: "#e8e4df",
        margin: "0 0 8px 0",
        fontWeight: 400,
        lineHeight: 1.3,
      }}>
        {entry.title || "Untitled Entry"}
      </h3>

      <p style={{
        fontFamily: "'DM Sans', sans-serif",
        fontSize: "13px",
        color: "#888",
        margin: 0,
        lineHeight: 1.5,
        display: "-webkit-box",
        WebkitLineClamp: isExpanded ? 999 : 2,
        WebkitBoxOrient: "vertical",
        overflow: "hidden",
      }}>
        {entry.content}
      </p>

      {entry.bodyRegions?.length > 0 && (
        <div style={{ display: "flex", gap: "4px", marginTop: "10px", flexWrap: "wrap" }}>
          {entry.bodyRegions.map(r => (
            <span key={r} style={{
              fontSize: "10px",
              padding: "2px 8px",
              borderRadius: "100px",
              background: "rgba(232, 93, 58, 0.1)",
              color: "#E85D3A",
              fontFamily: "'DM Mono', monospace",
            }}>{r}</span>
          ))}
        </div>
      )}

      {isExpanded && (
        <div style={{
          marginTop: "16px",
          paddingTop: "16px",
          borderTop: "1px solid #2a2a2a",
          display: "flex",
          gap: "16px",
          fontSize: "11px",
          color: "#666",
          fontFamily: "'DM Mono', monospace",
        }}>
          <span>{formatDate(entry.timestamp)}</span>
          <span>{formatTime(entry.timestamp)}</span>
          {entry.technique && <span>Technique: {entry.technique}</span>}
        </div>
      )}
    </div>
  );
}

// ─── MAIN APP ───

export default function ChiroJournal() {
  const [entries, setEntries] = useState([]);
  const [view, setView] = useState("home"); // home, compose, detail
  const [loading, setLoading] = useState(true);
  const [selectedEntry, setSelectedEntry] = useState(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [filterType, setFilterType] = useState(null);
  const [filterRegion, setFilterRegion] = useState(null);

  // Compose state
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [entryType, setEntryType] = useState("Clinical Insight");
  const [selectedMood, setSelectedMood] = useState(null);
  const [selectedRegions, setSelectedRegions] = useState([]);
  const [technique, setTechnique] = useState("");
  const [activePrompt, setActivePrompt] = useState(null);
  const [editingId, setEditingId] = useState(null);

  const textareaRef = useRef(null);

  useEffect(() => {
    loadEntries().then(e => { setEntries(e); setLoading(false); });
  }, []);

  const persist = useCallback(async (updated) => {
    setEntries(updated);
    await saveEntries(updated);
  }, []);

  const resetCompose = () => {
    setTitle(""); setContent(""); setEntryType("Clinical Insight");
    setSelectedMood(null); setSelectedRegions([]); setTechnique("");
    setActivePrompt(null); setEditingId(null);
  };

  const handleSave = async () => {
    if (!content.trim()) return;
    const entry = {
      id: editingId || generateId(),
      title: title.trim() || content.trim().split("\n")[0].substring(0, 60),
      content: content.trim(),
      type: entryType,
      mood: selectedMood,
      bodyRegions: selectedRegions,
      technique: technique.trim(),
      timestamp: editingId ? entries.find(e => e.id === editingId)?.timestamp || Date.now() : Date.now(),
      updatedAt: Date.now(),
    };
    let updated;
    if (editingId) {
      updated = entries.map(e => e.id === editingId ? entry : e);
    } else {
      updated = [entry, ...entries];
    }
    await persist(updated);
    resetCompose();
    setView("home");
  };

  const handleDelete = async (id) => {
    const updated = entries.filter(e => e.id !== id);
    await persist(updated);
    setSelectedEntry(null);
    setView("home");
  };

  const handleEdit = (entry) => {
    setEditingId(entry.id);
    setTitle(entry.title);
    setContent(entry.content);
    setEntryType(entry.type);
    setSelectedMood(entry.mood);
    setSelectedRegions(entry.bodyRegions || []);
    setTechnique(entry.technique || "");
    setView("compose");
  };

  const toggleRegion = (r) => {
    setSelectedRegions(prev => prev.includes(r) ? prev.filter(x => x !== r) : [...prev, r]);
  };

  const filtered = entries.filter(e => {
    if (filterType && e.type !== filterType) return false;
    if (filterRegion && !(e.bodyRegions || []).includes(filterRegion)) return false;
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      return (
        (e.title || "").toLowerCase().includes(q) ||
        e.content.toLowerCase().includes(q) ||
        e.type.toLowerCase().includes(q) ||
        (e.technique || "").toLowerCase().includes(q) ||
        (e.bodyRegions || []).some(r => r.toLowerCase().includes(q))
      );
    }
    return true;
  });

  const streak = getStreak(entries);
  const weekActivity = getWeekActivity(entries);
  const totalEntries = entries.length;

  // On this day
  const today = new Date();
  const onThisDay = entries.filter(e => {
    const d = new Date(e.timestamp);
    return d.getMonth() === today.getMonth() && d.getDate() === today.getDate() && d.getFullYear() !== today.getFullYear();
  });

  if (loading) {
    return (
      <div style={{ background: "#111", minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center" }}>
        <div style={{ color: "#E85D3A", fontFamily: "'Instrument Serif', serif", fontSize: "24px" }}>Loading journal...</div>
      </div>
    );
  }

  return (
    <div style={{ background: "#111", minHeight: "100vh", color: "#e8e4df", fontFamily: "'DM Sans', sans-serif" }}>
      <link href="https://fonts.googleapis.com/css2?family=Instrument+Serif:ital@0;1&family=DM+Sans:wght@300;400;500&family=DM+Mono:wght@300;400&display=swap" rel="stylesheet" />

      <style>{`
        * { box-sizing: border-box; }
        ::selection { background: #E85D3A; color: #fff; }
        textarea:focus, input:focus { outline: none; }
        ::-webkit-scrollbar { width: 4px; }
        ::-webkit-scrollbar-track { background: transparent; }
        ::-webkit-scrollbar-thumb { background: #333; border-radius: 4px; }
        @keyframes fadeUp { from { opacity: 0; transform: translateY(12px); } to { opacity: 1; transform: translateY(0); } }
        @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.5; } }
        .fade-up { animation: fadeUp 0.4s ease forwards; }
        .stagger-1 { animation-delay: 0.05s; opacity: 0; }
        .stagger-2 { animation-delay: 0.1s; opacity: 0; }
        .stagger-3 { animation-delay: 0.15s; opacity: 0; }
        .stagger-4 { animation-delay: 0.2s; opacity: 0; }
      `}</style>

      {/* ─── HEADER ─── */}
      <div style={{
        padding: "24px 24px 0",
        maxWidth: "640px",
        margin: "0 auto",
      }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "4px" }}>
          {view !== "home" ? (
            <button
              onClick={() => { setView("home"); resetCompose(); setSelectedEntry(null); }}
              style={{
                background: "none", border: "none", color: "#888", cursor: "pointer",
                fontFamily: "'DM Sans', sans-serif", fontSize: "13px", padding: 0,
                display: "flex", alignItems: "center", gap: "4px",
              }}
            >
              ← Back
            </button>
          ) : (
            <div>
              <h1 style={{
                fontFamily: "'Instrument Serif', serif",
                fontSize: "28px",
                fontWeight: 400,
                margin: 0,
                color: "#e8e4df",
                letterSpacing: "-0.5px",
              }}>
                Spine & Mind
              </h1>
              <p style={{ fontSize: "12px", color: "#666", margin: "2px 0 0", fontFamily: "'DM Mono', monospace" }}>
                Your chiropractic experience journal
              </p>
            </div>
          )}

          {view === "home" && (
            <button
              onClick={() => { resetCompose(); setView("compose"); }}
              style={{
                background: "#E85D3A",
                border: "none",
                color: "#fff",
                width: "40px",
                height: "40px",
                borderRadius: "50%",
                fontSize: "22px",
                cursor: "pointer",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                transition: "transform 0.2s",
                boxShadow: "0 4px 16px rgba(232, 93, 58, 0.3)",
              }}
              onMouseEnter={e => e.currentTarget.style.transform = "scale(1.1)"}
              onMouseLeave={e => e.currentTarget.style.transform = "scale(1)"}
            >
              +
            </button>
          )}
        </div>
      </div>

      <div style={{ maxWidth: "640px", margin: "0 auto", padding: "16px 24px 100px" }}>

        {/* ─── HOME VIEW ─── */}
        {view === "home" && (
          <div>
            {/* Stats Row */}
            <div className="fade-up stagger-1" style={{
              display: "grid",
              gridTemplateColumns: "1fr 1fr 1fr",
              gap: "12px",
              marginBottom: "20px",
              marginTop: "16px",
            }}>
              <div style={{ background: "#1a1a1a", borderRadius: "12px", padding: "16px", textAlign: "center" }}>
                <div style={{ fontSize: "28px", fontFamily: "'Instrument Serif', serif", color: "#E85D3A" }}>{streak}</div>
                <div style={{ fontSize: "10px", color: "#666", fontFamily: "'DM Mono', monospace", textTransform: "uppercase", letterSpacing: "1px" }}>Day Streak</div>
              </div>
              <div style={{ background: "#1a1a1a", borderRadius: "12px", padding: "16px", textAlign: "center" }}>
                <div style={{ fontSize: "28px", fontFamily: "'Instrument Serif', serif", color: "#e8e4df" }}>{totalEntries}</div>
                <div style={{ fontSize: "10px", color: "#666", fontFamily: "'DM Mono', monospace", textTransform: "uppercase", letterSpacing: "1px" }}>Entries</div>
              </div>
              <div style={{ background: "#1a1a1a", borderRadius: "12px", padding: "16px", textAlign: "center" }}>
                <div style={{ display: "flex", justifyContent: "center", gap: "3px", alignItems: "flex-end", height: "32px" }}>
                  {weekActivity.map((d, i) => (
                    <div key={i} style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "2px" }}>
                      <div style={{
                        width: "6px",
                        height: Math.max(4, d.count * 10),
                        background: d.count > 0 ? "#E85D3A" : "#2a2a2a",
                        borderRadius: "2px",
                        transition: "height 0.3s",
                        maxHeight: "28px",
                      }} />
                    </div>
                  ))}
                </div>
                <div style={{ fontSize: "10px", color: "#666", fontFamily: "'DM Mono', monospace", textTransform: "uppercase", letterSpacing: "1px", marginTop: "4px" }}>This Week</div>
              </div>
            </div>

            {/* On This Day */}
            {onThisDay.length > 0 && (
              <div className="fade-up stagger-2" style={{
                background: "linear-gradient(135deg, rgba(232,93,58,0.08), rgba(171,71,188,0.06))",
                borderRadius: "12px",
                padding: "16px",
                marginBottom: "20px",
                border: "1px solid rgba(232,93,58,0.15)",
              }}>
                <div style={{ fontSize: "11px", color: "#E85D3A", fontFamily: "'DM Mono', monospace", textTransform: "uppercase", letterSpacing: "1px", marginBottom: "8px" }}>
                  📅 On This Day
                </div>
                {onThisDay.slice(0, 2).map(e => (
                  <div key={e.id} style={{ marginBottom: "4px" }}>
                    <span style={{ fontFamily: "'Instrument Serif', serif", fontSize: "14px", color: "#e8e4df" }}>
                      {e.title}
                    </span>
                    <span style={{ fontSize: "11px", color: "#666", marginLeft: "8px" }}>
                      {new Date(e.timestamp).getFullYear()}
                    </span>
                  </div>
                ))}
              </div>
            )}

            {/* Search */}
            <div className="fade-up stagger-2" style={{ marginBottom: "16px" }}>
              <input
                value={searchQuery}
                onChange={e => setSearchQuery(e.target.value)}
                placeholder="Search entries..."
                style={{
                  width: "100%",
                  padding: "12px 16px",
                  background: "#1a1a1a",
                  border: "1px solid #2a2a2a",
                  borderRadius: "10px",
                  color: "#e8e4df",
                  fontSize: "14px",
                  fontFamily: "'DM Sans', sans-serif",
                }}
              />
            </div>

            {/* Filters */}
            <div className="fade-up stagger-3" style={{ display: "flex", gap: "6px", flexWrap: "wrap", marginBottom: "20px" }}>
              <Tag label="All" active={!filterType} onClick={() => setFilterType(null)} />
              {ENTRY_TYPES.map(t => (
                <Tag key={t} label={t} active={filterType === t} onClick={() => setFilterType(filterType === t ? null : t)} />
              ))}
            </div>
            {filterType && (
              <div style={{ display: "flex", gap: "6px", flexWrap: "wrap", marginBottom: "16px" }}>
                {BODY_REGIONS.map(r => (
                  <Tag key={r} label={r} active={filterRegion === r} onClick={() => setFilterRegion(filterRegion === r ? null : r)} color="#2196F3" />
                ))}
              </div>
            )}

            {/* Entries */}
            <div className="fade-up stagger-4">
              {filtered.length === 0 ? (
                <div style={{ textAlign: "center", padding: "60px 20px" }}>
                  <div style={{ fontSize: "48px", marginBottom: "16px" }}>🦴</div>
                  <h3 style={{ fontFamily: "'Instrument Serif', serif", fontSize: "22px", fontWeight: 400, color: "#e8e4df", marginBottom: "8px" }}>
                    {entries.length === 0 ? "Start Your Journal" : "No matches found"}
                  </h3>
                  <p style={{ fontSize: "13px", color: "#666", maxWidth: "280px", margin: "0 auto", lineHeight: 1.6 }}>
                    {entries.length === 0
                      ? "Capture your clinical experiences, technique insights, and professional reflections."
                      : "Try adjusting your search or filters."}
                  </p>
                  {entries.length === 0 && (
                    <button
                      onClick={() => { resetCompose(); setView("compose"); }}
                      style={{
                        marginTop: "20px",
                        background: "#E85D3A",
                        border: "none",
                        color: "#fff",
                        padding: "10px 24px",
                        borderRadius: "8px",
                        fontSize: "14px",
                        cursor: "pointer",
                        fontFamily: "'DM Sans', sans-serif",
                      }}
                    >
                      Write First Entry
                    </button>
                  )}
                </div>
              ) : (
                filtered.map(entry => (
                  <EntryCard
                    key={entry.id}
                    entry={entry}
                    onClick={() => { setSelectedEntry(entry); setView("detail"); }}
                  />
                ))
              )}
            </div>
          </div>
        )}

        {/* ─── DETAIL VIEW ─── */}
        {view === "detail" && selectedEntry && (
          <div className="fade-up" style={{ marginTop: "16px" }}>
            <div style={{ display: "flex", gap: "8px", marginBottom: "20px" }}>
              <button
                onClick={() => handleEdit(selectedEntry)}
                style={{
                  background: "#1a1a1a", border: "1px solid #333", color: "#aaa",
                  padding: "6px 16px", borderRadius: "6px", fontSize: "12px",
                  cursor: "pointer", fontFamily: "'DM Sans', sans-serif",
                }}
              >
                Edit
              </button>
              <button
                onClick={() => { if (confirm("Delete this entry?")) handleDelete(selectedEntry.id); }}
                style={{
                  background: "#1a1a1a", border: "1px solid #333", color: "#E85D3A",
                  padding: "6px 16px", borderRadius: "6px", fontSize: "12px",
                  cursor: "pointer", fontFamily: "'DM Sans', sans-serif",
                }}
              >
                Delete
              </button>
            </div>

            <div style={{ marginBottom: "12px", display: "flex", alignItems: "center", gap: "10px" }}>
              <span style={{
                fontSize: "11px",
                padding: "3px 10px",
                borderRadius: "100px",
                background: "rgba(232,93,58,0.12)",
                color: "#E85D3A",
                fontFamily: "'DM Mono', monospace",
                textTransform: "uppercase",
              }}>
                {selectedEntry.type}
              </span>
              {selectedEntry.mood && (
                <span style={{ fontSize: "18px" }}>{MOODS.find(m => m.label === selectedEntry.mood)?.emoji} <span style={{ fontSize: "12px", color: "#888" }}>{selectedEntry.mood}</span></span>
              )}
            </div>

            <h2 style={{
              fontFamily: "'Instrument Serif', serif",
              fontSize: "28px",
              fontWeight: 400,
              margin: "0 0 8px 0",
              lineHeight: 1.2,
              color: "#e8e4df",
            }}>
              {selectedEntry.title}
            </h2>

            <div style={{ fontSize: "12px", color: "#666", fontFamily: "'DM Mono', monospace", marginBottom: "24px" }}>
              {formatDate(selectedEntry.timestamp)} · {formatTime(selectedEntry.timestamp)}
              {selectedEntry.technique && <span> · {selectedEntry.technique}</span>}
            </div>

            {selectedEntry.bodyRegions?.length > 0 && (
              <div style={{ display: "flex", gap: "6px", flexWrap: "wrap", marginBottom: "20px" }}>
                {selectedEntry.bodyRegions.map(r => (
                  <span key={r} style={{
                    fontSize: "11px", padding: "4px 12px", borderRadius: "100px",
                    background: "rgba(33,150,243,0.1)", color: "#2196F3",
                    fontFamily: "'DM Mono', monospace",
                  }}>{r}</span>
                ))}
              </div>
            )}

            <div style={{
              fontFamily: "'DM Sans', sans-serif",
              fontSize: "15px",
              lineHeight: 1.8,
              color: "#ccc",
              whiteSpace: "pre-wrap",
            }}>
              {selectedEntry.content}
            </div>
          </div>
        )}

        {/* ─── COMPOSE VIEW ─── */}
        {view === "compose" && (
          <div className="fade-up" style={{ marginTop: "16px" }}>
            <h2 style={{
              fontFamily: "'Instrument Serif', serif",
              fontSize: "24px",
              fontWeight: 400,
              marginBottom: "20px",
              color: "#e8e4df",
            }}>
              {editingId ? "Edit Entry" : "New Entry"}
            </h2>

            {/* Entry Type */}
            <div style={{ marginBottom: "20px" }}>
              <label style={{ fontSize: "11px", color: "#666", fontFamily: "'DM Mono', monospace", textTransform: "uppercase", letterSpacing: "1px", display: "block", marginBottom: "8px" }}>
                Type
              </label>
              <div style={{ display: "flex", gap: "6px", flexWrap: "wrap" }}>
                {ENTRY_TYPES.map(t => (
                  <Tag key={t} label={t} active={entryType === t} onClick={() => { setEntryType(t); setActivePrompt(null); }} />
                ))}
              </div>
            </div>

            {/* Mood */}
            <div style={{ marginBottom: "20px" }}>
              <label style={{ fontSize: "11px", color: "#666", fontFamily: "'DM Mono', monospace", textTransform: "uppercase", letterSpacing: "1px", display: "block", marginBottom: "8px" }}>
                How are you feeling?
              </label>
              <div style={{ display: "flex", gap: "8px" }}>
                {MOODS.map(m => (
                  <button
                    key={m.label}
                    onClick={() => setSelectedMood(selectedMood === m.label ? null : m.label)}
                    style={{
                      background: selectedMood === m.label ? `${m.color}22` : "#1a1a1a",
                      border: selectedMood === m.label ? `1px solid ${m.color}` : "1px solid #2a2a2a",
                      borderRadius: "10px",
                      padding: "10px 12px",
                      cursor: "pointer",
                      display: "flex",
                      flexDirection: "column",
                      alignItems: "center",
                      gap: "4px",
                      transition: "all 0.2s",
                      minWidth: "56px",
                    }}
                  >
                    <span style={{ fontSize: "20px" }}>{m.emoji}</span>
                    <span style={{ fontSize: "9px", color: selectedMood === m.label ? m.color : "#888", fontFamily: "'DM Mono', monospace" }}>{m.label}</span>
                  </button>
                ))}
              </div>
            </div>

            {/* Title */}
            <div style={{ marginBottom: "16px" }}>
              <input
                value={title}
                onChange={e => setTitle(e.target.value)}
                placeholder="Entry title (optional)"
                style={{
                  width: "100%",
                  padding: "12px 0",
                  background: "transparent",
                  border: "none",
                  borderBottom: "1px solid #2a2a2a",
                  color: "#e8e4df",
                  fontSize: "20px",
                  fontFamily: "'Instrument Serif', serif",
                }}
              />
            </div>

            {/* Writing Prompt */}
            <div style={{ marginBottom: "12px" }}>
              <button
                onClick={() => {
                  const prompts = PROMPTS[entryType];
                  const idx = activePrompt === null ? 0 : (activePrompt + 1) % prompts.length;
                  setActivePrompt(idx);
                }}
                style={{
                  background: "none", border: "none", color: "#E85D3A", cursor: "pointer",
                  fontSize: "12px", fontFamily: "'DM Mono', monospace", padding: 0,
                  display: "flex", alignItems: "center", gap: "4px",
                }}
              >
                ✦ {activePrompt !== null ? "Next prompt" : "Need a prompt?"}
              </button>
              {activePrompt !== null && (
                <p style={{
                  fontSize: "14px",
                  color: "#AB47BC",
                  fontStyle: "italic",
                  margin: "8px 0 0",
                  fontFamily: "'Instrument Serif', serif",
                  lineHeight: 1.5,
                }}>
                  "{PROMPTS[entryType][activePrompt]}"
                </p>
              )}
            </div>

            {/* Content */}
            <div style={{ marginBottom: "20px" }}>
              <textarea
                ref={textareaRef}
                value={content}
                onChange={e => {
                  setContent(e.target.value);
                  e.target.style.height = "auto";
                  e.target.style.height = e.target.scrollHeight + "px";
                }}
                placeholder="Write about your experience..."
                style={{
                  width: "100%",
                  minHeight: "180px",
                  padding: "16px",
                  background: "#1a1a1a",
                  border: "1px solid #2a2a2a",
                  borderRadius: "10px",
                  color: "#e8e4df",
                  fontSize: "15px",
                  fontFamily: "'DM Sans', sans-serif",
                  lineHeight: 1.7,
                  resize: "none",
                  overflow: "hidden",
                }}
              />
            </div>

            {/* Body Regions */}
            <div style={{ marginBottom: "20px" }}>
              <label style={{ fontSize: "11px", color: "#666", fontFamily: "'DM Mono', monospace", textTransform: "uppercase", letterSpacing: "1px", display: "block", marginBottom: "8px" }}>
                Body Regions
              </label>
              <div style={{ display: "flex", gap: "6px", flexWrap: "wrap" }}>
                {BODY_REGIONS.map(r => (
                  <Tag key={r} label={r} active={selectedRegions.includes(r)} onClick={() => toggleRegion(r)} color="#2196F3" />
                ))}
              </div>
            </div>

            {/* Technique */}
            <div style={{ marginBottom: "28px" }}>
              <label style={{ fontSize: "11px", color: "#666", fontFamily: "'DM Mono', monospace", textTransform: "uppercase", letterSpacing: "1px", display: "block", marginBottom: "8px" }}>
                Technique (optional)
              </label>
              <input
                value={technique}
                onChange={e => setTechnique(e.target.value)}
                placeholder="e.g., Diversified, Gonstead, Activator..."
                style={{
                  width: "100%",
                  padding: "12px 16px",
                  background: "#1a1a1a",
                  border: "1px solid #2a2a2a",
                  borderRadius: "10px",
                  color: "#e8e4df",
                  fontSize: "14px",
                  fontFamily: "'DM Sans', sans-serif",
                }}
              />
            </div>

            {/* Save */}
            <button
              onClick={handleSave}
              disabled={!content.trim()}
              style={{
                width: "100%",
                padding: "14px",
                background: content.trim() ? "#E85D3A" : "#333",
                border: "none",
                borderRadius: "10px",
                color: content.trim() ? "#fff" : "#666",
                fontSize: "15px",
                fontFamily: "'DM Sans', sans-serif",
                fontWeight: 500,
                cursor: content.trim() ? "pointer" : "default",
                transition: "all 0.2s",
                boxShadow: content.trim() ? "0 4px 16px rgba(232,93,58,0.25)" : "none",
              }}
            >
              {editingId ? "Update Entry" : "Save Entry"}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
