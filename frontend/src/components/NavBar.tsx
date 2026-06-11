import { Link, useLocation } from "react-router-dom";

export default function NavBar() {
  const { pathname } = useLocation();

  return (
    <nav style={styles.nav}>
      <Link to="/" style={styles.wordmark}>OFFSIDE AI</Link>
      <div style={styles.links}>
        <Link
          to="/"
          style={{
            ...styles.link,
            ...(pathname === "/" ? styles.linkActive : {}),
          }}
        >
          Fixtures
        </Link>
        <a href="#" style={styles.link}>About</a>
      </div>
    </nav>
  );
}

const styles: Record<string, React.CSSProperties> = {
  nav: {
    height: 56,
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    padding: "0 24px",
    borderBottom: "1px solid var(--border-subtle)",
    background: "rgba(13,15,18,0.97)",
    position: "sticky",
    top: 0,
    zIndex: 100,
    flexShrink: 0,
  },
  wordmark: {
    fontFamily: "var(--font-display)",
    fontSize: 22,
    color: "var(--accent-primary)",
    letterSpacing: 1,
    textDecoration: "none",
  },
  links: {
    display: "flex",
    gap: 24,
    alignItems: "center",
  },
  link: {
    fontSize: 13,
    color: "var(--text-muted)",
    textDecoration: "none",
    paddingBottom: 2,
    borderBottom: "2px solid transparent",
    transition: "color 0.2s",
  },
  linkActive: {
    color: "var(--text-primary)",
    borderBottomColor: "var(--accent-primary)",
  },
};
