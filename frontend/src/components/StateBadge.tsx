import type { MatchState } from "../types";

interface Props {
  state: MatchState;
}

const CONFIG = {
  pre: {
    label: "PREVIEW",
    bg: "rgba(79,158,255,0.15)",
    color: "var(--state-preview)",
  },
  live: {
    label: "LIVE",
    bg: "rgba(255,69,69,0.15)",
    color: "var(--state-live)",
  },
  post: {
    label: "FULL TIME",
    bg: "rgba(107,114,128,0.15)",
    color: "var(--state-fulltime)",
  },
} as const;

export default function StateBadge({ state }: Props) {
  const { label, bg, color } = CONFIG[state];

  return (
    <span style={{ ...styles.badge, background: bg, color }}>
      {state === "live" && <span style={styles.dot} />}
      {label}
    </span>
  );
}

const styles: Record<string, React.CSSProperties> = {
  badge: {
    display: "inline-flex",
    alignItems: "center",
    gap: 5,
    fontSize: 10,
    fontWeight: 700,
    padding: "3px 9px",
    borderRadius: 100,
    textTransform: "uppercase",
    letterSpacing: "0.6px",
    whiteSpace: "nowrap",
  },
  dot: {
    width: 6,
    height: 6,
    borderRadius: "50%",
    background: "var(--state-live)",
    animation: "pulse 1.4s infinite",
    flexShrink: 0,
  },
};
