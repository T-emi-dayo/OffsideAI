import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api/client";
import FixtureCard from "../components/FixtureCard";
import SkeletonLoader from "../components/SkeletonLoader";
import ErrorCard from "../components/ErrorCard";
import type { FixtureItem } from "../types";

type Tab = "today" | "upcoming" | "completed";

function todayISO(): string {
  return new Date().toISOString().slice(0, 10);
}

function classifyTab(fixture: FixtureItem, today: string): Tab {
  const fixtureDate = fixture.utc_date.slice(0, 10);
  if (fixture.match_state === "post") return "completed";
  if (fixtureDate === today || fixture.match_state === "live") return "today";
  return "upcoming";
}

const TAB_LABELS: Record<Tab, string> = {
  today: "TODAY",
  upcoming: "UPCOMING",
  completed: "COMPLETED",
};


export default function FixtureHub() {
  const navigate = useNavigate();
  const [tab, setTab] = useState<Tab>("today");
  const [allFixtures, setAllFixtures] = useState<FixtureItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const today = todayISO();

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const res = await api.getFixtures();
      setAllFixtures(res.data.fixtures);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, []);

  const todayFixtures  = allFixtures.filter(f => classifyTab(f, today) === "today");
  const upcomingFixtures = allFixtures.filter(f => {
    const d = f.utc_date.slice(0, 10);
    return f.match_state === "pre" && d > today;
  });
  const completedFixtures = allFixtures.filter(f => f.match_state === "post");

  const displayed: FixtureItem[] = tab === "today" ? todayFixtures
    : tab === "upcoming" ? upcomingFixtures
    : completedFixtures;

  const todayCount = todayFixtures.length;

  const nextMatch = tab === "today" && displayed.length === 0
    ? upcomingFixtures[0]
    : null;

  return (
    <div style={styles.page}>
      <div style={styles.hero}>
        <h1 style={styles.heroTitle}>2026 FIFA WORLD CUP</h1>
        <p style={styles.heroSub}>
          {todayCount > 0
            ? `${todayCount} match${todayCount > 1 ? "es" : ""} today · AI-powered intelligence for every fixture`
            : "AI-powered intelligence for every World Cup fixture"}
        </p>
      </div>

      <div style={styles.tabBar}>
        {(["today", "upcoming", "completed"] as Tab[]).map((t) => (
          <button
            key={t}
            style={{ ...styles.tab, ...(tab === t ? styles.tabActive : {}) }}
            onClick={() => setTab(t)}
          >
            {TAB_LABELS[t]}
            {t === "today" && todayCount > 0 && (
              <span style={styles.tabCount}>{todayCount}</span>
            )}
          </button>
        ))}
      </div>

      <div style={styles.content}>
        {loading && (
          <div style={styles.skeletonGrid}>
            {[1, 2, 3, 4, 5, 6].map((n) => (
              <div key={n} style={styles.skeletonCard}>
                <SkeletonLoader lines={3} height={20} />
              </div>
            ))}
          </div>
        )}

        {!loading && error && (
          <div style={styles.errorWrap}>
            <ErrorCard message={`Failed to load fixtures: ${error}`} onRetry={load} />
          </div>
        )}

        {!loading && !error && displayed.length === 0 && (
          <div style={styles.empty}>
            <p style={styles.emptyTitle}>
              {tab === "today"
                ? "No matches scheduled today"
                : tab === "upcoming"
                ? "No upcoming matches"
                : "No completed matches yet"}
            </p>
            {nextMatch && (
              <p style={styles.emptySub}>
                Next match: {nextMatch.home_team.name} vs {nextMatch.away_team.name}
                {" · "}{new Date(nextMatch.utc_date).toLocaleDateString("en-GB", { day: "numeric", month: "long" })}
              </p>
            )}
          </div>
        )}

        {!loading && !error && displayed.length > 0 && (
          <div style={styles.grid}>
            {displayed.map((f) => (
              <FixtureCard
                key={f.id}
                fixture={f}
                onClick={() => navigate(`/match/${f.id}`)}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  page: {
    flex: 1,
    display: "flex",
    flexDirection: "column",
  },
  hero: {
    padding: "28px 24px 20px",
    borderBottom: "1px solid var(--border-subtle)",
  },
  heroTitle: {
    fontFamily: "var(--font-display)",
    fontSize: 32,
    letterSpacing: 1,
    color: "var(--text-primary)",
    fontWeight: 400,
  },
  heroSub: {
    color: "var(--text-muted)",
    fontSize: 13,
    marginTop: 4,
  },
  tabBar: {
    display: "flex",
    gap: 0,
    padding: "0 24px",
    borderBottom: "1px solid var(--border-subtle)",
  },
  tab: {
    padding: "12px 16px",
    fontSize: 12,
    fontWeight: 600,
    color: "var(--text-muted)",
    background: "none",
    border: "none",
    borderBottom: "2px solid transparent",
    cursor: "pointer",
    transition: "color 0.2s",
    display: "flex",
    alignItems: "center",
    gap: 6,
    letterSpacing: "0.5px",
  },
  tabActive: {
    color: "var(--accent-primary)",
    borderBottomColor: "var(--accent-primary)",
  },
  tabCount: {
    background: "var(--accent-primary)",
    color: "#0D0F12",
    fontSize: 10,
    fontWeight: 700,
    padding: "1px 6px",
    borderRadius: 100,
  },
  content: {
    flex: 1,
    padding: "20px 24px",
  },
  grid: {
    display: "grid",
    gridTemplateColumns: "repeat(3, 1fr)",
    gap: 12,
  },
  skeletonGrid: {
    display: "grid",
    gridTemplateColumns: "repeat(3, 1fr)",
    gap: 12,
  },
  skeletonCard: {
    background: "var(--surface-card)",
    border: "1px solid var(--border-subtle)",
    borderRadius: 12,
    padding: 16,
    minHeight: 140,
  },
  errorWrap: {
    maxWidth: 480,
  },
  empty: {
    padding: "48px 0",
    textAlign: "center",
  },
  emptyTitle: {
    fontSize: 15,
    color: "var(--text-muted)",
    marginBottom: 8,
  },
  emptySub: {
    fontSize: 13,
    color: "var(--text-muted)",
  },
};
