import type { FixtureItem } from "../types";
import StateBadge from "./StateBadge";

const COUNTRY_FLAGS: Record<string, string> = {
  "Argentina": "🇦🇷", "Australia": "🇦🇺", "Belgium": "🇧🇪", "Brazil": "🇧🇷",
  "Cameroon": "🇨🇲", "Canada": "🇨🇦", "Chile": "🇨🇱", "Colombia": "🇨🇴",
  "Costa Rica": "🇨🇷", "Croatia": "🇭🇷", "Denmark": "🇩🇰", "Ecuador": "🇪🇨",
  "Egypt": "🇪🇬", "England": "🏴󠁧󠁢󠁥󠁮󠁧󠁿", "France": "🇫🇷", "Germany": "🇩🇪",
  "Ghana": "🇬🇭", "IR Iran": "🇮🇷", "Italy": "🇮🇹", "Japan": "🇯🇵",
  "Mexico": "🇲🇽", "Morocco": "🇲🇦", "Netherlands": "🇳🇱", "Nigeria": "🇳🇬",
  "Panama": "🇵🇦", "Peru": "🇵🇪", "Poland": "🇵🇱", "Portugal": "🇵🇹",
  "Qatar": "🇶🇦", "Saudi Arabia": "🇸🇦", "Senegal": "🇸🇳", "Serbia": "🇷🇸",
  "South Korea": "🇰🇷", "Spain": "🇪🇸", "Switzerland": "🇨🇭", "Tunisia": "🇹🇳",
  "United States": "🇺🇸", "USA": "🇺🇸", "Uruguay": "🇺🇾", "Wales": "🏴󠁧󠁢󠁷󠁬󠁳󠁿",
  "Algeria": "🇩🇿", "Bolivia": "🇧🇴", "Ivory Coast": "🇨🇮", "Greece": "🇬🇷",
  "Hungary": "🇭🇺", "Indonesia": "🇮🇩", "Israel": "🇮🇱", "Jamaica": "🇯🇲",
  "Kenya": "🇰🇪", "New Zealand": "🇳🇿", "Norway": "🇳🇴", "Paraguay": "🇵🇾",
  "Scotland": "🏴󠁧󠁢󠁳󠁣󠁴󠁿", "Sweden": "🇸🇪", "Turkey": "🇹🇷", "Ukraine": "🇺🇦",
  "Venezuela": "🇻🇪", "Zambia": "🇿🇲", "Austria": "🇦🇹", "Czech Republic": "🇨🇿",
  "Slovenia": "🇸🇮", "Albania": "🇦🇱", "Honduras": "🇭🇳", "Guatemala": "🇬🇹",
  "DR Congo": "🇨🇩", "Burkina Faso": "🇧🇫", "Mali": "🇲🇱", "Sudan": "🇸🇩",
  "Iraq": "🇮🇶", "Syria": "🇸🇾", "Jordan": "🇯🇴", "United Arab Emirates": "🇦🇪",
  "Uzbekistan": "🇺🇿", "South Africa": "🇿🇦",
};

function getFlag(name: string): string {
  return COUNTRY_FLAGS[name] ?? "🏳";
}

function formatDate(utcDate: string): string {
  if (!utcDate) return "";
  try {
    return new Date(utcDate).toLocaleDateString("en-GB", {
      day: "numeric",
      month: "short",
      hour: "2-digit",
      minute: "2-digit",
      timeZone: "UTC",
    });
  } catch {
    return utcDate.slice(0, 10);
  }
}

interface Props {
  fixture: FixtureItem;
  onClick: () => void;
}

export default function FixtureCard({ fixture, onClick }: Props) {
  const { home_team, away_team, score, match_state, utc_date, stage } = fixture;
  const showScore = match_state !== "pre";

  return (
    <div style={styles.card} onClick={onClick} role="button" tabIndex={0}
      onKeyDown={(e) => e.key === "Enter" && onClick()}
      onMouseEnter={(e) => { (e.currentTarget as HTMLDivElement).style.background = "var(--surface-elevated)"; }}
      onMouseLeave={(e) => { (e.currentTarget as HTMLDivElement).style.background = "var(--surface-card)"; }}
    >
      <div style={styles.badgeWrap}>
        <StateBadge state={match_state} />
      </div>

      <div style={styles.teams}>
        <div style={styles.teamSide}>
          <span style={styles.flag}>{getFlag(home_team.name)}</span>
          <span style={styles.teamName}>{home_team.name}</span>
        </div>

        <div style={styles.center}>
          {showScore ? (
            <span style={styles.score}>
              {score.home ?? 0} — {score.away ?? 0}
            </span>
          ) : (
            <span style={styles.vs}>vs</span>
          )}
        </div>

        <div style={{ ...styles.teamSide, alignItems: "flex-end" }}>
          <span style={styles.flag}>{getFlag(away_team.name)}</span>
          <span style={styles.teamName}>{away_team.name}</span>
        </div>
      </div>

      <div style={styles.meta}>
        <span style={styles.metaText}>{formatDate(utc_date)}</span>
        <span style={styles.metaText}>{stage}</span>
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  card: {
    background: "var(--surface-card)",
    border: "1px solid var(--border-subtle)",
    borderRadius: 12,
    padding: "16px 16px 12px",
    cursor: "pointer",
    position: "relative",
    minHeight: 140,
    display: "flex",
    flexDirection: "column",
    justifyContent: "space-between",
    transition: "background 0.15s",
    userSelect: "none",
  },
  badgeWrap: {
    position: "absolute",
    top: 12,
    right: 12,
  },
  teams: {
    display: "grid",
    gridTemplateColumns: "1fr auto 1fr",
    alignItems: "center",
    gap: 8,
    marginTop: 8,
  },
  teamSide: {
    display: "flex",
    flexDirection: "column",
    alignItems: "flex-start",
    gap: 4,
  },
  flag: {
    fontSize: 22,
    lineHeight: 1,
  },
  teamName: {
    fontSize: 12,
    fontWeight: 600,
    color: "var(--text-primary)",
    lineHeight: 1.2,
  },
  center: {
    textAlign: "center",
  },
  score: {
    fontFamily: "var(--font-display)",
    fontSize: 26,
    color: "var(--text-primary)",
    letterSpacing: 1,
  },
  vs: {
    fontSize: 12,
    color: "var(--text-muted)",
  },
  meta: {
    marginTop: 12,
    paddingTop: 10,
    borderTop: "1px solid var(--border-subtle)",
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
  },
  metaText: {
    fontSize: 11,
    color: "var(--text-muted)",
  },
};
