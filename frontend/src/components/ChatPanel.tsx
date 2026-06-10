import { useEffect, useRef, useState } from "react";
import { api } from "../api/client";
import type { ChatMessage, MatchState } from "../types";
import SkeletonLoader from "./SkeletonLoader";

interface Props {
  matchId: number;
  homeTeam: string;
  awayTeam: string;
  matchState: MatchState;
  liveContext?: Record<string, unknown> | null;
  /** When true, panel starts expanded (LIVE state default) */
  defaultExpanded?: boolean;
}

export default function ChatPanel({
  matchId,
  homeTeam,
  awayTeam,
  matchState,
  liveContext,
  defaultExpanded = false,
}: Props) {
  const [expanded, setExpanded] = useState(defaultExpanded);
  const [history, setHistory] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (expanded) {
      bottomRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [history, expanded]);

  async function send() {
    const msg = input.trim();
    if (!msg || loading) return;

    setInput("");
    setError(null);
    setLoading(true);

    const optimisticHistory: ChatMessage[] = [
      ...history,
      { role: "user", content: msg },
    ];
    setHistory(optimisticHistory);

    try {
      const res = await api.postChat(matchId, {
        home_team: homeTeam,
        away_team: awayTeam,
        match_state: matchState,
        message: msg,
        history,
        live_context: liveContext ?? null,
      });
      setHistory(res.data.history);
    } catch (e) {
      setError((e as Error).message);
      setHistory((prev) => [
        ...prev,
        { role: "assistant", content: "⚠ Sorry, I couldn't get a response. Try again." },
      ]);
    } finally {
      setLoading(false);
    }
  }

  function handleKey(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  }

  if (!expanded) {
    return (
      <div style={styles.collapsed} onClick={() => setExpanded(true)}>
        <span style={styles.collapsedIcon}>💬</span>
        <span style={styles.collapsedLabel}>Ask anything about this match…</span>
        <span style={styles.collapsedCta}>Open Chat ↗</span>
      </div>
    );
  }

  return (
    <div style={styles.panel}>
      <div style={styles.header}>
        <span style={styles.headerTitle}>MATCH CHAT</span>
        <button style={styles.closeBtn} onClick={() => setExpanded(false)}>✕</button>
      </div>

      <div style={styles.messages}>
        {history.length === 0 && (
          <p style={styles.hint}>
            Ask me anything about {homeTeam} vs {awayTeam} — history, form, predictions, tactics…
          </p>
        )}

        {history.map((m, i) => (
          <div
            key={i}
            style={{
              ...styles.bubble,
              ...(m.role === "user" ? styles.userBubble : styles.aiBubble),
            }}
          >
            {m.content}
          </div>
        ))}

        {loading && (
          <div style={styles.aiBubbleWrap}>
            <SkeletonLoader lines={2} height={14} />
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {error && (
        <p style={styles.errorMsg}>⚠ {error}</p>
      )}

      <div style={styles.inputRow}>
        <input
          style={styles.input}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKey}
          placeholder="Ask a question…"
          disabled={loading}
        />
        <button
          style={{
            ...styles.sendBtn,
            opacity: !input.trim() || loading ? 0.4 : 1,
          }}
          onClick={send}
          disabled={!input.trim() || loading}
        >
          Send ↗
        </button>
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  collapsed: {
    display: "flex",
    alignItems: "center",
    gap: 10,
    padding: "14px 24px",
    borderTop: "1px solid var(--border-subtle)",
    cursor: "pointer",
    background: "var(--surface-card)",
    transition: "background 0.15s",
  },
  collapsedIcon: {
    fontSize: 16,
  },
  collapsedLabel: {
    flex: 1,
    fontSize: 13,
    color: "var(--text-muted)",
  },
  collapsedCta: {
    fontSize: 12,
    fontWeight: 600,
    color: "var(--accent-primary)",
  },
  panel: {
    borderTop: "1px solid var(--border-subtle)",
    display: "flex",
    flexDirection: "column",
    height: 360,
    background: "var(--surface-card)",
  },
  header: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    padding: "10px 16px",
    borderBottom: "1px solid var(--border-subtle)",
  },
  headerTitle: {
    fontSize: 11,
    fontWeight: 600,
    color: "var(--text-muted)",
    textTransform: "uppercase",
    letterSpacing: "0.8px",
  },
  closeBtn: {
    fontSize: 13,
    color: "var(--text-muted)",
    background: "none",
    border: "none",
    cursor: "pointer",
    padding: "2px 4px",
  },
  messages: {
    flex: 1,
    overflowY: "auto",
    padding: "12px 16px",
    display: "flex",
    flexDirection: "column",
    gap: 8,
  },
  hint: {
    fontSize: 13,
    color: "var(--text-muted)",
    lineHeight: 1.5,
    padding: "8px 0",
  },
  bubble: {
    maxWidth: "80%",
    padding: "8px 12px",
    borderRadius: 10,
    fontSize: 14,
    lineHeight: 1.5,
    whiteSpace: "pre-wrap",
  },
  userBubble: {
    alignSelf: "flex-end",
    background: "rgba(0,255,135,0.12)",
    color: "var(--text-primary)",
    borderBottomRightRadius: 2,
  },
  aiBubble: {
    alignSelf: "flex-start",
    background: "var(--surface-elevated)",
    color: "var(--text-primary)",
    borderBottomLeftRadius: 2,
  },
  aiBubbleWrap: {
    alignSelf: "flex-start",
    width: 160,
    padding: "8px 12px",
    background: "var(--surface-elevated)",
    borderRadius: 10,
  },
  errorMsg: {
    fontSize: 12,
    color: "var(--state-live)",
    padding: "4px 16px",
  },
  inputRow: {
    display: "flex",
    gap: 8,
    padding: "10px 12px",
    borderTop: "1px solid var(--border-subtle)",
  },
  input: {
    flex: 1,
    background: "rgba(255,255,255,0.04)",
    border: "1px solid var(--border-subtle)",
    borderRadius: 8,
    padding: "8px 12px",
    color: "var(--text-primary)",
    fontSize: 14,
    fontFamily: "var(--font-body)",
    outline: "none",
  },
  sendBtn: {
    background: "var(--accent-primary)",
    color: "#0D0F12",
    fontWeight: 700,
    fontSize: 12,
    padding: "8px 14px",
    borderRadius: 8,
    border: "none",
    cursor: "pointer",
    transition: "opacity 0.2s",
    whiteSpace: "nowrap",
  },
};
