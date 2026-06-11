interface Props {
  message: string;
  onRetry?: () => void;
}

export default function ErrorCard({ message, onRetry }: Props) {
  return (
    <div style={styles.wrap}>
      <span style={styles.icon}>⚠</span>
      <p style={styles.msg}>{message}</p>
      {onRetry && (
        <button style={styles.btn} onClick={onRetry}>
          Retry
        </button>
      )}
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  wrap: {
    display: "flex",
    alignItems: "center",
    gap: 10,
    padding: "12px 14px",
    borderRadius: 8,
    border: "1px solid rgba(255,69,69,0.3)",
    background: "rgba(255,69,69,0.07)",
  },
  icon: {
    color: "var(--state-live)",
    fontSize: 14,
    flexShrink: 0,
  },
  msg: {
    flex: 1,
    fontSize: 13,
    color: "var(--text-primary)",
    lineHeight: 1.4,
  },
  btn: {
    fontSize: 12,
    fontWeight: 600,
    color: "var(--state-live)",
    background: "rgba(255,69,69,0.15)",
    border: "1px solid rgba(255,69,69,0.3)",
    borderRadius: 6,
    padding: "4px 10px",
    cursor: "pointer",
    flexShrink: 0,
  },
};
