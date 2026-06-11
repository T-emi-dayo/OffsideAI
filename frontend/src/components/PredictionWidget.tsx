import type { MatchPrediction } from "../types";
import SkeletonLoader from "./SkeletonLoader";
import ErrorCard from "./ErrorCard";

interface Props {
  prediction: MatchPrediction | null;
  homeTeam: string;
  awayTeam: string;
  reasoning?: string | null;
  loading: boolean;
  error: string | null;
  onRetry: () => void;
}

function ProbBar({
  label,
  pct,
  color,
}: {
  label: string;
  pct: number;
  color: string;
}) {
  return (
    <div style={styles.probRow}>
      <span style={styles.probLabel}>{label}</span>
      <div style={styles.probTrack}>
        <div
          style={{
            ...styles.probFill,
            width: `${(pct * 100).toFixed(1)}%`,
            background: color,
          }}
        />
      </div>
      <span style={styles.probPct}>{(pct * 100).toFixed(0)}%</span>
    </div>
  );
}

export default function PredictionWidget({
  prediction,
  homeTeam,
  awayTeam,
  reasoning,
  loading,
  error,
  onRetry,
}: Props) {
  return (
    <div style={styles.card}>
      <div style={styles.label}>WIN PROBABILITIES</div>

      {loading && <SkeletonLoader lines={5} height={14} />}
      {!loading && error && <ErrorCard message={error} onRetry={onRetry} />}

      {!loading && !error && prediction && (
        <>
          <div style={styles.teamNames}>
            <span style={styles.teamName}>{homeTeam}</span>
            <span style={styles.teamName}>{awayTeam}</span>
          </div>

          <ProbBar label="Home" pct={prediction.p_home} color="var(--accent-primary)" />
          <ProbBar label="Draw" pct={prediction.p_draw} color="var(--text-muted)" />
          <ProbBar label="Away" pct={prediction.p_away} color="var(--accent-secondary)" />

          <div style={styles.xgRow}>
            <div>
              <span style={styles.xgVal}>{prediction.lambda_home.toFixed(2)}</span>
              <span style={styles.xgUnit}> xG</span>
            </div>
            <span style={styles.xgSep}>—</span>
            <div style={{ textAlign: "right" }}>
              <span style={styles.xgVal}>{prediction.lambda_away.toFixed(2)}</span>
              <span style={styles.xgUnit}> xG</span>
            </div>
          </div>

          {reasoning && (
            <p style={styles.reasoning}>{reasoning}</p>
          )}
        </>
      )}

      {!loading && !error && !prediction && (
        <p style={styles.na}>Prediction unavailable</p>
      )}
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  card: {
    background: "var(--surface-card)",
    border: "1px solid var(--border-subtle)",
    borderRadius: 12,
    padding: 16,
  },
  label: {
    fontSize: 11,
    fontWeight: 600,
    color: "var(--text-muted)",
    textTransform: "uppercase",
    letterSpacing: "0.8px",
    marginBottom: 12,
  },
  teamNames: {
    display: "flex",
    justifyContent: "space-between",
    marginBottom: 10,
  },
  teamName: {
    fontSize: 11,
    fontWeight: 600,
    color: "var(--text-primary)",
  },
  probRow: {
    display: "flex",
    alignItems: "center",
    gap: 8,
    marginBottom: 8,
  },
  probLabel: {
    fontSize: 11,
    color: "var(--text-muted)",
    width: 36,
    flexShrink: 0,
  },
  probTrack: {
    flex: 1,
    height: 6,
    background: "rgba(255,255,255,0.08)",
    borderRadius: 3,
    overflow: "hidden",
  },
  probFill: {
    height: "100%",
    borderRadius: 3,
    transition: "width 0.8s ease",
  },
  probPct: {
    fontSize: 12,
    fontWeight: 700,
    color: "var(--text-primary)",
    width: 32,
    textAlign: "right",
    flexShrink: 0,
  },
  xgRow: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    marginTop: 10,
    paddingTop: 10,
    borderTop: "1px solid var(--border-subtle)",
  },
  xgVal: {
    fontFamily: "var(--font-display)",
    fontSize: 22,
    color: "var(--text-primary)",
  },
  xgUnit: {
    fontSize: 10,
    color: "var(--text-muted)",
    textTransform: "uppercase",
    letterSpacing: "0.5px",
  },
  xgSep: {
    fontSize: 14,
    color: "var(--text-muted)",
  },
  reasoning: {
    fontSize: 11,
    color: "#8B96A5",
    lineHeight: 1.6,
    fontStyle: "italic",
    marginTop: 10,
    paddingTop: 10,
    borderTop: "1px solid var(--border-subtle)",
  },
  na: {
    fontSize: 13,
    color: "var(--text-muted)",
  },
};
