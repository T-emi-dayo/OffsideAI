import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api } from "../api/client";
import type {
  LiveData,
  MatchMetadata,
  MatchPrediction,
  PostMatchData,
  PreMatchData,
} from "../types";
import ChatPanel from "../components/ChatPanel";
import ErrorCard from "../components/ErrorCard";
import EventTimeline from "../components/EventTimeline";
import PredictionWidget from "../components/PredictionWidget";
import SkeletonLoader from "../components/SkeletonLoader";
import StateBadge from "../components/StateBadge";

// ---------------------------------------------------------------------------
// Section config — icon + label for each report section
// ---------------------------------------------------------------------------
const SECTION_CONFIG = [
  { key: "match_overview",       icon: "🏆", label: "MATCH OVERVIEW" },
  { key: "team_analysis",        icon: "📊", label: "TEAM ANALYSIS" },
  { key: "head_to_head",         icon: "⚔️",  label: "HEAD TO HEAD" },
  { key: "prediction_reasoning", icon: "🤖", label: "PREDICTION REASONING" },
  { key: "verdict",              icon: "🎯", label: "VERDICT" },
] as const;

type SectionKey = typeof SECTION_CONFIG[number]["key"];

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------

export default function MatchView() {
  const { id } = useParams<{ id: string }>();
  const matchId = Number(id);
  const navigate = useNavigate();

  const [match, setMatch]               = useState<MatchMetadata | null>(null);
  const [matchError, setMatchError]     = useState<string | null>(null);

  const [preview, setPreview]           = useState<PreMatchData | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewError, setPreviewError] = useState<string | null>(null);

  // Prediction sourced from preview.prediction (set via useEffect below)
  const [prediction, setPrediction]     = useState<MatchPrediction | null>(null);

  const [live, setLive]                 = useState<LiveData | null>(null);
  const [liveLoading, setLiveLoading]   = useState(false);
  const [liveError, setLiveError]       = useState<string | null>(null);

  const [report, setReport]             = useState<PostMatchData | null>(null);
  const [reportLoading, setReportLoading] = useState(false);
  const [reportError, setReportError]   = useState<string | null>(null);

  async function loadMatch() {
    setMatchError(null);
    try {
      const res = await api.getMatch(matchId);
      setMatch(res.data);
      return res.data;
    } catch (e) {
      setMatchError((e as Error).message);
      return null;
    }
  }

  async function loadPreview() {
    setPreviewLoading(true);
    setPreviewError(null);
    try {
      const res = await api.getPreview(matchId);
      setPreview(res.data);
    } catch (e) {
      setPreviewError((e as Error).message);
    } finally {
      setPreviewLoading(false);
    }
  }

  async function loadNarrative() {
    setLiveLoading(true);
    setLiveError(null);
    try {
      const res = await api.getNarrative(matchId);
      setLive(res.data);
    } catch (e) {
      setLiveError((e as Error).message);
    } finally {
      setLiveLoading(false);
    }
  }

  async function loadReport() {
    setReportLoading(true);
    setReportError(null);
    try {
      const res = await api.getReport(matchId);
      setReport(res.data);
    } catch (e) {
      setReportError((e as Error).message);
    } finally {
      setReportLoading(false);
    }
  }

  useEffect(() => {
    async function init() {
      const m = await loadMatch();
      if (!m) return;
      if (m.match_state === "pre")  { loadPreview(); }
      if (m.match_state === "post") { loadReport(); }
    }
    init();
  }, [matchId]);

  // Populate prediction widget from the prematch agent response
  useEffect(() => {
    if (preview?.prediction) {
      setPrediction(preview.prediction);
    }
  }, [preview]);

  if (matchError) {
    return (
      <div style={styles.page}>
        <div style={{ padding: 24 }}>
          <ErrorCard message={`Failed to load match: ${matchError}`} onRetry={loadMatch} />
        </div>
      </div>
    );
  }

  if (!match) {
    return (
      <div style={styles.page}>
        <div style={{ padding: 24, maxWidth: 400 }}>
          <SkeletonLoader lines={2} height={24} />
        </div>
      </div>
    );
  }

  const { home_team, away_team, match_state, stage, group, match_date, score } = match;
  const subtitle = [stage, group].filter(Boolean).join(" · ");

  return (
    <div style={styles.page}>
      {/* ── Match Header ── */}
      <div style={styles.header}>
        <button style={styles.backBtn} onClick={() => navigate("/")}>← Fixtures</button>
        <div style={styles.headerInfo}>
          <div style={styles.headerTop}>
            <StateBadge state={match_state} />
            <h2 style={styles.matchTitle}>
              {home_team}
              {match_state !== "pre"
                ? <span style={styles.scoreInline}> {score.home ?? 0} — {score.away ?? 0} </span>
                : <span style={styles.vsInline}> vs </span>}
              {away_team}
            </h2>
          </div>
          <p style={styles.matchSub}>{subtitle}{match_date ? ` · ${match_date}` : ""}</p>
        </div>
      </div>

      {/* ── Body ── */}
      <div style={styles.body}>
        <div style={styles.main}>
          {match_state === "pre" && (
            <PreMatchMain
              homeTeam={home_team}
              awayTeam={away_team}
              preview={preview}
              loading={previewLoading}
              error={previewError}
              onRetry={loadPreview}
            />
          )}
          {match_state === "live" && (
            <LiveMain
              homeTeam={home_team}
              awayTeam={away_team}
              score={score}
              live={live}
              loading={liveLoading}
              error={liveError}
              onGenerate={loadNarrative}
            />
          )}
          {match_state === "post" && (
            <PostMatchMain
              homeTeam={home_team}
              awayTeam={away_team}
              score={score}
              report={report}
              loading={reportLoading}
              error={reportError}
              onRetry={loadReport}
            />
          )}
        </div>

        <div style={styles.sidebar}>
          {match_state === "pre" && (
            <PreMatchSidebar
              homeTeam={home_team}
              awayTeam={away_team}
              prediction={prediction}
              reasoning={preview?.prediction_reasoning ?? null}
              predLoading={previewLoading}
              predError={previewError}
              onRetry={loadPreview}
            />
          )}
          {match_state === "live" && (
            <ChatPanel
              matchId={matchId}
              homeTeam={home_team}
              awayTeam={away_team}
              matchState={match_state}
              liveContext={live ? { key_moments: live.key_moments, score: live.current_score } : undefined}
              defaultExpanded
            />
          )}
          {match_state === "post" && <PostMatchSidebar report={report} />}
        </div>
      </div>

      {match_state !== "live" && (
        <ChatPanel
          matchId={matchId}
          homeTeam={home_team}
          awayTeam={away_team}
          matchState={match_state}
          defaultExpanded={false}
        />
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// PRE-MATCH
// ---------------------------------------------------------------------------

function ReportSection({
  icon,
  label,
  content,
  accent,
}: {
  icon: string;
  label: string;
  content: string;
  accent?: boolean;
}) {
  return (
    <div style={{ ...sectionCard, ...(accent ? styles.verdictCard : {}) }}>
      <div style={styles.sectionHeader}>
        <span style={styles.sectionIcon}>{icon}</span>
        <span style={{ ...sectionLabel, ...(accent ? styles.verdictLabel : {}) }}>{label}</span>
      </div>
      <p style={{ ...styles.reportText, ...(accent ? styles.verdictText : {}) }}>{content}</p>
    </div>
  );
}

function PreMatchMain({
  homeTeam,
  awayTeam,
  preview,
  loading,
  error,
  onRetry,
}: {
  homeTeam: string;
  awayTeam: string;
  preview: PreMatchData | null;
  loading: boolean;
  error: string | null;
  onRetry: () => void;
}) {
  return (
    <>
      {/* Team comparison strip */}
      <div style={sectionCard}>
        <div style={styles.teamCompare}>
          <div>
            <p style={styles.tcName}>{homeTeam}</p>
            <p style={styles.tcRole}>Home</p>
          </div>
          <span style={styles.tcVs}>VS</span>
          <div style={{ textAlign: "right" }}>
            <p style={styles.tcName}>{awayTeam}</p>
            <p style={styles.tcRole}>Away</p>
          </div>
        </div>
      </div>

      {/* Loading skeleton */}
      {loading && (
        <div style={sectionCard}>
          <div style={styles.sectionHeader}>
            <div style={sectionLabel}>AI PREVIEW REPORT</div>
          </div>
          <SkeletonLoader lines={6} height={16} />
          <div style={{ marginTop: 16 }}>
            <SkeletonLoader lines={4} height={16} />
          </div>
        </div>
      )}

      {/* Error */}
      {!loading && error && (
        <div style={sectionCard}>
          <ErrorCard message={error} onRetry={onRetry} />
        </div>
      )}

      {/* Structured report sections */}
      {!loading && !error && preview && (
        <>
          {SECTION_CONFIG.map(({ key, icon, label }) => {
            const content = preview[key as SectionKey];
            if (!content) return null;
            return (
              <ReportSection
                key={key}
                icon={icon}
                label={label}
                content={content}
                accent={key === "verdict"}
              />
            );
          })}
        </>
      )}

      {!loading && !error && !preview && (
        <div style={sectionCard}>
          <p style={styles.na}>Preview not available.</p>
        </div>
      )}
    </>
  );
}

function PreMatchSidebar({
  homeTeam,
  awayTeam,
  prediction,
  reasoning,
  predLoading,
  predError,
  onRetry,
}: {
  homeTeam: string;
  awayTeam: string;
  prediction: MatchPrediction | null;
  reasoning: string | null;
  predLoading: boolean;
  predError: string | null;
  onRetry: () => void;
}) {
  return (
    <>
      <PredictionWidget
        prediction={prediction}
        homeTeam={homeTeam}
        awayTeam={awayTeam}
        reasoning={reasoning}
        loading={predLoading}
        error={predError}
        onRetry={onRetry}
      />
    </>
  );
}

// ---------------------------------------------------------------------------
// LIVE
// ---------------------------------------------------------------------------

function LiveMain({
  homeTeam,
  awayTeam,
  score,
  live,
  loading,
  error,
  onGenerate,
}: {
  homeTeam: string;
  awayTeam: string;
  score: { home: number | null; away: number | null };
  live: LiveData | null;
  loading: boolean;
  error: string | null;
  onGenerate: () => void;
}) {
  return (
    <>
      <div style={{ ...sectionCard, textAlign: "center" }}>
        <div style={styles.scoreboard}>
          <span style={styles.scoreTeam}>{homeTeam}</span>
          <span style={styles.scoreBig}>
            {live?.current_score.home ?? score.home ?? 0}
            {" — "}
            {live?.current_score.away ?? score.away ?? 0}
          </span>
          <span style={styles.scoreTeam}>{awayTeam}</span>
        </div>
      </div>

      <div style={sectionCard}>
        <div style={styles.sectionHeader}>
          <span style={styles.sectionIcon}>⚡</span>
          <span style={sectionLabel}>MATCH EVENTS</span>
        </div>
        <EventTimeline moments={live?.key_moments ?? []} />
      </div>

      <div style={sectionCard}>
        <div style={styles.sectionHeader}>
          <span style={styles.sectionIcon}>🎙️</span>
          <span style={sectionLabel}>AI NARRATIVE</span>
        </div>
        {!live && !loading && !error && (
          <div style={styles.narrativeCta}>
            <p style={styles.na}>Get an AI-generated story of the match so far.</p>
            <button style={styles.generateBtn} onClick={onGenerate}>
              Generate Narrative ↗
            </button>
          </div>
        )}
        {loading && <SkeletonLoader lines={6} height={16} />}
        {!loading && error && <ErrorCard message={error} onRetry={onGenerate} />}
        {!loading && !error && live?.narrative && (
          <p style={styles.reportText}>{live.narrative}</p>
        )}
      </div>
    </>
  );
}

// ---------------------------------------------------------------------------
// POST-MATCH
// ---------------------------------------------------------------------------

function PostMatchMain({
  homeTeam,
  awayTeam,
  score,
  report,
  loading,
  error,
  onRetry,
}: {
  homeTeam: string;
  awayTeam: string;
  score: { home: number | null; away: number | null };
  report: PostMatchData | null;
  loading: boolean;
  error: string | null;
  onRetry: () => void;
}) {
  return (
    <>
      <div style={{ ...sectionCard, textAlign: "center" }}>
        <div style={sectionLabel}>FINAL SCORE</div>
        <div style={styles.scoreboard}>
          <span style={styles.scoreTeam}>{homeTeam}</span>
          <span style={styles.scoreBig}>{score.home ?? 0} — {score.away ?? 0}</span>
          <span style={styles.scoreTeam}>{awayTeam}</span>
        </div>
      </div>

      {loading && (
        <div style={sectionCard}>
          <SkeletonLoader lines={10} height={16} />
        </div>
      )}
      {!loading && error && (
        <div style={sectionCard}>
          <ErrorCard message={error} onRetry={onRetry} />
        </div>
      )}
      {!loading && !error && report && (
        <>
          {report.match_summary && (
            <div style={sectionCard}>
              <div style={styles.sectionHeader}>
                <span style={styles.sectionIcon}>📝</span>
                <span style={sectionLabel}>MATCH SUMMARY</span>
              </div>
              <p style={styles.reportText}>{report.match_summary}</p>
            </div>
          )}
          {report.key_moments.length > 0 && (
            <div style={sectionCard}>
              <div style={styles.sectionHeader}>
                <span style={styles.sectionIcon}>⚡</span>
                <span style={sectionLabel}>KEY MOMENTS</span>
              </div>
              <EventTimeline moments={report.key_moments} />
            </div>
          )}
          {report.player_highlights.length > 0 && (
            <div style={sectionCard}>
              <div style={styles.sectionHeader}>
                <span style={styles.sectionIcon}>⭐</span>
                <span style={sectionLabel}>PLAYER HIGHLIGHTS</span>
              </div>
              <ul style={styles.highlightList}>
                {report.player_highlights.map((h, i) => (
                  <li key={i} style={styles.highlightItem}>{h}</li>
                ))}
              </ul>
            </div>
          )}
          {report.tactical_analysis && (
            <div style={sectionCard}>
              <div style={styles.sectionHeader}>
                <span style={styles.sectionIcon}>🔎</span>
                <span style={sectionLabel}>TACTICAL ANALYSIS</span>
              </div>
              <p style={styles.reportText}>{report.tactical_analysis}</p>
            </div>
          )}
        </>
      )}
    </>
  );
}

function PostMatchSidebar({ report }: { report: PostMatchData | null }) {
  if (!report) return null;
  const playerOfMatch = report.player_highlights[0] ?? null;
  return (
    <>
      {playerOfMatch && (
        <div style={sectionCard}>
          <div style={styles.sectionHeader}>
            <span style={styles.sectionIcon}>🏅</span>
            <span style={sectionLabel}>PLAYER OF THE MATCH</span>
          </div>
          <p style={styles.reportText}>{playerOfMatch}</p>
        </div>
      )}
      {report.player_highlights.length > 1 && (
        <div style={sectionCard}>
          <div style={sectionLabel}>NOTABLE PERFORMANCES</div>
          <ul style={styles.highlightList}>
            {report.player_highlights.slice(1).map((h, i) => (
              <li key={i} style={styles.highlightItem}>{h}</li>
            ))}
          </ul>
        </div>
      )}
    </>
  );
}

// ---------------------------------------------------------------------------
// Shared styles
// ---------------------------------------------------------------------------

const sectionCard: React.CSSProperties = {
  background: "var(--surface-card)",
  border: "1px solid var(--border-subtle)",
  borderRadius: 12,
  padding: 16,
  marginBottom: 12,
};

const sectionLabel: React.CSSProperties = {
  fontSize: 11,
  fontWeight: 600,
  color: "var(--text-muted)",
  textTransform: "uppercase",
  letterSpacing: "0.8px",
};

const styles: Record<string, React.CSSProperties> = {
  page: {
    flex: 1,
    display: "flex",
    flexDirection: "column",
    minHeight: 0,
  },
  header: {
    padding: "14px 24px",
    borderBottom: "1px solid var(--border-subtle)",
    display: "flex",
    alignItems: "flex-start",
    gap: 16,
  },
  backBtn: {
    fontSize: 13,
    color: "var(--text-muted)",
    background: "none",
    border: "none",
    cursor: "pointer",
    padding: "4px 0",
    whiteSpace: "nowrap",
    marginTop: 2,
  },
  headerInfo: { flex: 1, minWidth: 0 },
  headerTop: {
    display: "flex",
    alignItems: "center",
    gap: 10,
    flexWrap: "wrap",
  },
  matchTitle: {
    fontFamily: "var(--font-display)",
    fontSize: 22,
    fontWeight: 400,
    letterSpacing: "0.5px",
    color: "var(--text-primary)",
  },
  scoreInline: { color: "var(--accent-primary)" },
  vsInline:    { color: "var(--text-muted)" },
  matchSub: {
    fontSize: 12,
    color: "var(--text-muted)",
    marginTop: 4,
  },
  body: {
    flex: 1,
    display: "grid",
    gridTemplateColumns: "1fr 290px",
    overflow: "hidden",
    minHeight: 0,
  },
  main: {
    padding: "16px 20px",
    overflowY: "auto",
    borderRight: "1px solid var(--border-subtle)",
  },
  sidebar: {
    padding: 16,
    overflowY: "auto",
    display: "flex",
    flexDirection: "column",
    gap: 0,
  },
  // Section card header row
  sectionHeader: {
    display: "flex",
    alignItems: "center",
    gap: 8,
    marginBottom: 12,
  },
  sectionIcon: {
    fontSize: 14,
    flexShrink: 0,
  },
  // Verdict card accent
  verdictCard: {
    border: "1px solid rgba(0,255,135,0.2)",
    background: "rgba(0,255,135,0.04)",
  },
  verdictLabel: {
    color: "var(--accent-primary)",
  },
  verdictText: {
    color: "var(--text-primary)",
    fontWeight: 600,
    fontSize: 14,
  },
  // Team compare
  teamCompare: {
    display: "grid",
    gridTemplateColumns: "1fr auto 1fr",
    alignItems: "center",
    gap: 12,
  },
  tcName: {
    fontSize: 16,
    fontWeight: 700,
    color: "var(--text-primary)",
    marginBottom: 2,
  },
  tcRole: {
    fontSize: 11,
    color: "var(--text-muted)",
  },
  tcVs: {
    fontFamily: "var(--font-display)",
    fontSize: 14,
    color: "var(--text-muted)",
    padding: "0 8px",
  },
  // Report text
  reportText: {
    fontSize: 13,
    lineHeight: 1.75,
    color: "#C8CDD5",
  },
  na: {
    fontSize: 13,
    color: "var(--text-muted)",
  },
  // Score display
  scoreboard: {
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    gap: 16,
    padding: "8px 0",
    flexWrap: "wrap",
  },
  scoreBig: {
    fontFamily: "var(--font-display)",
    fontSize: 48,
    color: "var(--text-primary)",
    letterSpacing: 2,
    lineHeight: 1,
  },
  scoreTeam: {
    fontSize: 15,
    fontWeight: 700,
    color: "var(--text-primary)",
  },
  // Narrative CTA
  narrativeCta: {
    display: "flex",
    flexDirection: "column",
    alignItems: "flex-start",
    gap: 12,
  },
  generateBtn: {
    background: "var(--accent-primary)",
    color: "#0D0F12",
    fontWeight: 700,
    fontSize: 13,
    padding: "8px 16px",
    borderRadius: 8,
    border: "none",
    cursor: "pointer",
  },
  // Post-match
  highlightList: {
    listStyle: "none",
    display: "flex",
    flexDirection: "column",
    gap: 8,
  },
  highlightItem: {
    fontSize: 13,
    color: "var(--text-primary)",
    lineHeight: 1.5,
    paddingLeft: 12,
    borderLeft: "2px solid var(--accent-primary)",
  },
};
