import { useEffect, useState } from "react";
import { Link, NavLink, useLocation, useNavigate } from "react-router-dom";
import { scrollToId } from "../lib/scroll";

const LINKS = [
  { to: "/how", label: "How it works" },
  { to: "/method", label: "Research" },
  { to: "/code", label: "Code" },
];

// Route-aware floating nav. Translucent, solidifies on scroll. Collapses to
// brand + CTA on small screens. The CTA always lands on the live demo (home).
export function FloatingNav() {
  const [scrolled, setScrolled] = useState(false);
  const { pathname } = useLocation();
  const navigate = useNavigate();

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 40);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  const goDemo = () => {
    if (pathname === "/") {
      scrollToId("demo");
    } else {
      navigate("/");
      window.setTimeout(() => scrollToId("demo"), 450);
    }
  };

  return (
    <nav className={`fnav ${scrolled ? "is-solid" : ""}`} aria-label="Primary">
      <Link className="fnav__brand" to="/" aria-label="OwnVoice home">
        Own<span>Voice</span>
      </Link>
      <div className="fnav__links">
        {LINKS.map((l) => (
          <NavLink
            key={l.to}
            to={l.to}
            className={({ isActive }) => (isActive ? "is-active" : "")}
          >
            {l.label}
          </NavLink>
        ))}
      </div>
      <button className="fnav__cta" onClick={goDemo}>
        Hear the problem
      </button>
      <style>{`
        .fnav { position:fixed; top:0; left:0; right:0; z-index:var(--z-nav);
          display:flex; align-items:center; justify-content:space-between;
          padding:14px clamp(16px,4vw,40px); transition:background .3s ease, box-shadow .3s ease;
          background:transparent; }
        .fnav.is-solid { background:rgba(244,239,230,0.82); backdrop-filter:blur(12px);
          box-shadow:0 1px 0 rgba(20,17,15,0.08); }
        .fnav__brand { background:none; border:none; font-family:var(--font-display);
          font-weight:900; font-size:1.25rem; letter-spacing:-0.02em; color:var(--ink);
          cursor:pointer; text-decoration:none; }
        .fnav__brand span { color:var(--cobalt); }
        .fnav__links { display:flex; gap:6px; }
        .fnav__links a { font-family:var(--font-body); font-weight:600; font-size:0.92rem;
          color:var(--ink-soft); padding:8px 12px; border-radius:999px; text-decoration:none;
          transition:background .2s, color .2s; }
        .fnav__links a:hover { background:rgba(20,17,15,0.07); color:var(--ink); }
        .fnav__links a.is-active { color:var(--ink); background:rgba(62,107,224,0.12); }
        .fnav__cta { background:var(--ink); color:var(--cream); border:none; border-radius:999px;
          font-family:var(--font-body); font-weight:600; font-size:0.9rem; padding:9px 18px;
          cursor:pointer; transition:background .2s; }
        .fnav__cta:hover { background:var(--cobalt); }
        @media (max-width:860px) { .fnav__links { display:none; } }
      `}</style>
    </nav>
  );
}
