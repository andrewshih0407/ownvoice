import { useEffect, useRef, useState } from "react";
import { scrollToId } from "../lib/scroll";

// Interactive intro: a living web of signal nodes that fires around the cursor.
// Each labelled node reveals a piece of the project when hovered/focused — the
// "basic tour". The canvas animation never touches React state (mouse only), so
// no render loops. Reduced motion → a static, fully readable version.

type Info = {
  label: string;
  title: string;
  text: string;
  target: string; // section id to jump to on click
  x: number; // % of section
  y: number;
};

const INFO: Info[] = [
  { label: "Tone", title: "Tone is the word", text: "In Mandarin, tone is lexically contrastive. 統一 (tǒng yī, \"unify\") and 同一 (tóng yī, \"the same\") differ by one tone — and mean different things.", target: "problem", x: 20, y: 30 },
  { label: "STER", title: "A metric that isolates it", text: "Segmental tone error rate counts tone mistakes only on syllables the model already got right — separating tonal failure from ordinary mis-hearing.", target: "evidence", x: 79, y: 27 },
  { label: "+27.7%", title: "Measured, not claimed", text: "Fine-tuning cut character error rate 27.7% relative on a matched test set — and severe dysarthria improved most, by 41%.", target: "evidence", x: 50, y: 14 },
  { label: "The gap", title: "Tone did not follow", text: "Character accuracy improved. Tone accuracy did not move. Generic ASR fine-tuning does not fix tone — that is the gap this project exists in.", target: "evidence", x: 14, y: 66 },
  { label: "Taiwan", title: "Why here", text: "Oral cancer is the 4th most common cancer among Taiwanese men. Surgery is scheduled — so a voice can be banked before it is lost.", target: "problem", x: 86, y: 64 },
  { label: "Open source", title: "Fully public", text: "Simulation, metrics, training and evaluation are all open, including the negative results.", target: "code", x: 33, y: 84 },
  { label: "Honest", title: "Limits stated first", text: "Everything so far runs on simulated dysarthria. We say so on every number, because a screening claim needs real patient speech.", target: "limitations", x: 69, y: 85 },
];

export function SignalWeb() {
  const sectionRef = useRef<HTMLElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const mouse = useRef({ x: -9999, y: -9999 });
  const [active, setActive] = useState<number | null>(null);
  const [reduced, setReduced] = useState(false);

  useEffect(() => {
    const isReduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (isReduced) {
      setReduced(true);
      return;
    }
    const canvas = canvasRef.current!;
    const section = sectionRef.current!;
    const ctx = canvas.getContext("2d")!;
    let raf = 0;
    let w = 0;
    let h = 0;
    let dpr = Math.min(window.devicePixelRatio || 1, 2);

    type N = { x: number; y: number; vx: number; vy: number; hue: number };
    let nodes: N[] = [];

    const build = () => {
      const rect = section.getBoundingClientRect();
      w = rect.width;
      h = rect.height;
      canvas.width = w * dpr;
      canvas.height = h * dpr;
      canvas.style.width = w + "px";
      canvas.style.height = h + "px";
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      const count = Math.min(52, Math.floor((w * h) / 24000));
      nodes = Array.from({ length: count }, () => ({
        x: Math.random() * w,
        y: Math.random() * h,
        vx: (Math.random() - 0.5) * 0.25,
        vy: (Math.random() - 0.5) * 0.25,
        hue: Math.random() * 360,
      }));
    };
    build();

    const ro = new ResizeObserver(build);
    ro.observe(section);

    const LINK = 150;
    const MOUSE_R = 240;

    const draw = (t: number) => {
      ctx.clearRect(0, 0, w, h);
      const mx = mouse.current.x;
      const my = mouse.current.y;

      for (const n of nodes) {
        n.x += n.vx;
        n.y += n.vy;
        if (n.x < 0 || n.x > w) n.vx *= -1;
        if (n.y < 0 || n.y > h) n.vy *= -1;
        // gentle attraction toward cursor
        const dxm = mx - n.x;
        const dym = my - n.y;
        const dm = Math.hypot(dxm, dym);
        if (dm < MOUSE_R) {
          n.x += (dxm / dm) * 0.4;
          n.y += (dym / dm) * 0.4;
        }
      }

      // edges
      for (let i = 0; i < nodes.length; i++) {
        for (let j = i + 1; j < nodes.length; j++) {
          const a = nodes[i];
          const b = nodes[j];
          const d = Math.hypot(a.x - b.x, a.y - b.y);
          if (d < LINK) {
            const near = Math.min(
              Math.hypot(mx - a.x, my - a.y),
              Math.hypot(mx - b.x, my - b.y)
            );
            const lit = near < MOUSE_R ? 1 - near / MOUSE_R : 0;
            const alpha = (1 - d / LINK) * (0.12 + lit * 0.5);
            const hue = (a.hue + t * 0.02) % 360;
            ctx.strokeStyle = `hsla(${hue}, 85%, 68%, ${alpha})`;
            ctx.lineWidth = 0.6 + lit * 1.2;
            ctx.beginPath();
            ctx.moveTo(a.x, a.y);
            ctx.lineTo(b.x, b.y);
            ctx.stroke();
            // spark travelling along lit edges
            if (lit > 0.35) {
              const p = (t * 0.0009 + i * 0.13) % 1;
              const sx = a.x + (b.x - a.x) * p;
              const sy = a.y + (b.y - a.y) * p;
              ctx.fillStyle = `hsla(${(hue + 40) % 360}, 90%, 75%, ${lit})`;
              ctx.beginPath();
              ctx.arc(sx, sy, 1.8, 0, Math.PI * 2);
              ctx.fill();
            }
          }
        }
      }

      // nodes + mouse links
      for (const n of nodes) {
        const dm = Math.hypot(mx - n.x, my - n.y);
        const lit = dm < MOUSE_R ? 1 - dm / MOUSE_R : 0;
        const hue = (n.hue + t * 0.03) % 360;
        const r = 1.6 + lit * 2.6;
        const g = ctx.createRadialGradient(n.x, n.y, 0, n.x, n.y, r * 4);
        g.addColorStop(0, `hsla(${hue}, 90%, 75%, ${0.5 + lit * 0.5})`);
        g.addColorStop(1, `hsla(${hue}, 90%, 60%, 0)`);
        ctx.fillStyle = g;
        ctx.beginPath();
        ctx.arc(n.x, n.y, r * 4, 0, Math.PI * 2);
        ctx.fill();
        if (lit > 0) {
          ctx.strokeStyle = `hsla(${hue}, 90%, 78%, ${lit * 0.6})`;
          ctx.lineWidth = 0.7;
          ctx.beginPath();
          ctx.moveTo(n.x, n.y);
          ctx.lineTo(mx, my);
          ctx.stroke();
        }
      }

      raf = requestAnimationFrame(draw);
    };
    raf = requestAnimationFrame(draw);

    const onMove = (e: MouseEvent) => {
      const rect = section.getBoundingClientRect();
      mouse.current.x = e.clientX - rect.left;
      mouse.current.y = e.clientY - rect.top;
    };
    const onLeave = () => {
      mouse.current.x = -9999;
      mouse.current.y = -9999;
    };
    section.addEventListener("mousemove", onMove);
    section.addEventListener("mouseleave", onLeave);

    return () => {
      cancelAnimationFrame(raf);
      ro.disconnect();
      section.removeEventListener("mousemove", onMove);
      section.removeEventListener("mouseleave", onLeave);
    };
  }, []);

  const activeInfo = active !== null ? INFO[active] : null;

  return (
    <section className="nw" id="tour" ref={sectionRef}>
      {!reduced && <canvas className="nw__canvas" ref={canvasRef} aria-hidden="true" />}

      <div className="nw__center">
        <p className="eyebrow nw__eyebrow">{activeInfo ? activeInfo.label : "Start here"}</p>
        <h2 className="display-lg nw__title">
          {activeInfo ? activeInfo.title : "A living map of the project."}
        </h2>
        <p className="lead nw__lead">
          {activeInfo
            ? activeInfo.text
            : "Hover a node to explore what OwnVoice does — then click to jump straight there."}
        </p>
      </div>

      {INFO.map((info, i) => (
        <button
          key={info.label}
          className={`nw__node ${active === i ? "is-on" : ""}`}
          style={{ left: `${info.x}%`, top: `${info.y}%` }}
          onMouseEnter={() => setActive(i)}
          onFocus={() => setActive(i)}
          onMouseLeave={() => setActive(null)}
          onBlur={() => setActive(null)}
          onClick={() => scrollToId(info.target)}
          aria-label={`${info.label}: ${info.text}. Jump to section.`}
        >
          <span className="nw__node-dot" aria-hidden="true" />
          <span className="nw__node-label">{info.label}</span>
        </button>
      ))}

      <style>{`
        .nw { position:relative; min-height:100vh; background:
          radial-gradient(120% 90% at 50% 40%, #1c1830 0%, #100e18 55%, #0b0a10 100%);
          overflow:hidden; display:grid; place-items:center; }
        .nw__canvas { position:absolute; inset:0; z-index:1; }
        .nw__center { position:relative; z-index:3; text-align:center; color:var(--cream);
          max-width:640px; padding:0 clamp(20px,5vw,60px); pointer-events:none;
          text-shadow:0 2px 26px rgba(6,4,14,0.85); }
        .nw__eyebrow { color:var(--sky); }
        .nw__title { margin:0.25em 0 0.4em; }
        .nw__lead { color:rgba(244,239,230,0.9); margin-left:auto; margin-right:auto;
          transition:opacity .3s; min-height:4.6em; }

        .nw__node { position:absolute; z-index:4; transform:translate(-50%,-50%);
          display:flex; flex-direction:column; align-items:center; gap:8px;
          background:none; border:none; color:var(--cream); cursor:pointer; }
        .nw__node-dot { width:16px; height:16px; border-radius:999px;
          background:conic-gradient(from 0deg, #62c6e8, #8a5cf6, #f38ab0, #f4b024, #3fa85b, #62c6e8);
          box-shadow:0 0 0 6px rgba(138,92,246,0.16), 0 0 20px 4px rgba(98,198,232,0.35);
          transition:transform .25s ease, box-shadow .25s ease; }
        .nw__node-label { font-size:0.82rem; font-weight:600; letter-spacing:0.02em;
          opacity:0.8; text-shadow:0 1px 8px rgba(6,4,14,0.9); transition:opacity .25s; }
        .nw__node:hover .nw__node-dot, .nw__node.is-on .nw__node-dot,
        .nw__node:focus-visible .nw__node-dot {
          transform:scale(1.5); box-shadow:0 0 0 10px rgba(138,92,246,0.22), 0 0 34px 8px rgba(98,198,232,0.55); }
        .nw__node:hover .nw__node-label, .nw__node.is-on .nw__node-label,
        .nw__node:focus-visible .nw__node-label { opacity:1; }
        .nw__node:focus-visible { outline:2px solid var(--sky); outline-offset:8px; border-radius:12px; }

        @media (max-width:760px) {
          .nw__node-label { display:none; }
        }
      `}</style>
    </section>
  );
}
