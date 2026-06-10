interface Props {
  lines?: number;
  height?: number;
}

export default function SkeletonLoader({ lines = 4, height = 18 }: Props) {
  return (
    <div style={styles.wrap}>
      {Array.from({ length: lines }).map((_, i) => (
        <div
          key={i}
          style={{
            ...styles.line,
            height,
            width: i === lines - 1 ? "65%" : "100%",
          }}
        />
      ))}
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  wrap: {
    display: "flex",
    flexDirection: "column",
    gap: 10,
  },
  line: {
    borderRadius: 6,
    background:
      "linear-gradient(90deg, var(--surface-card) 0%, var(--surface-elevated) 50%, var(--surface-card) 100%)",
    backgroundSize: "600px 100%",
    animation: "shimmer 1.6s infinite linear",
  },
};
