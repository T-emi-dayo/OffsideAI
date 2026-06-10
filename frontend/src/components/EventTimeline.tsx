interface Props {
  moments: string[];
}

function eventIcon(text: string): string {
  const lower = text.toLowerCase();
  if (lower.includes("goal") || lower.includes("⚽")) return "⚽";
  if (lower.includes("red") || lower.includes("🟥")) return "🟥";
  if (lower.includes("yellow") || lower.includes("🟨")) return "🟨";
  if (lower.includes("pen")) return "⚽";
  return "•";
}

export default function EventTimeline({ moments }: Props) {
  if (moments.length === 0) {
    return <p style={styles.empty}>No events yet</p>;
  }

  return (
    <div style={styles.list}>
      {moments.map((m, i) => (
        <div key={i} style={styles.row}>
          <span style={styles.icon}>{eventIcon(m)}</span>
          <span style={styles.text}>{m}</span>
        </div>
      ))}
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  list: {
    display: "flex",
    flexDirection: "column",
    gap: 8,
  },
  row: {
    display: "flex",
    alignItems: "flex-start",
    gap: 10,
    padding: "8px 0",
    borderBottom: "1px solid var(--border-subtle)",
  },
  icon: {
    fontSize: 15,
    flexShrink: 0,
    marginTop: 1,
  },
  text: {
    fontSize: 13,
    color: "var(--text-primary)",
    lineHeight: 1.5,
  },
  empty: {
    fontSize: 13,
    color: "var(--text-muted)",
  },
};
