import { useEffect, useRef, useState } from "react";

// Minimal pairs: words identical except for tone. Drag the slider and every
// contour collapses toward its mean — which is what dysarthric prosodic
// flattening does to real speech. At full flattening the pairs become
// indistinguishable, and that is the entire argument for the project in one
// interaction.

type Pair = {
  syllable: string;
  a: { hanzi: string; pinyin: string; tone: number; gloss: string };
  b: { hanzi: string; pinyin: string; tone: number; gloss: string };
  color: string;
};

const PAIRS: Pair[] = [
  {
    syllable: "mai",
    a: { hanzi: "買", pinyin: "mǎi", tone: 3, gloss: "buy" },
    b: { hanzi: "賣", pinyin: "mài", tone: 4, gloss: "sell" },
    color: "#ee6c34",
  },
  {
    syllable: "tong yi",
    a: { hanzi: "統一", pinyin: "tǒng yī", tone: 3, gloss: "unify" },
    b: { hanzi: "同一", pinyin: "tóng yī", tone: 2, gloss: "the same" },
    color: "#3e6be0",
  },
  {
    syllable: "shu",
    a: { hanzi: "書", pinyin: "shū", tone: 1, gloss: "book" },
    b: { hanzi: "樹", pinyin: "shù", tone: 4, gloss: "tree" },
    color: "#3fa85b",
  },
  {
    syllable: "wen",
    a: { hanzi: "問", pinyin: "wèn", tone: 4, gloss: "ask" },
    b: { hanzi: "吻", pinyin: "wěn", tone: 3, gloss: "kiss" },
    color: "#8a5cf6",
  },
];

// Normalized pitch trajectory for each Mandarin tone, t in [0,1] -> [-1,1].
function toneCurve(tone: number, t: number): number {
  switch (tone) {
    case 1:
      return 0.75;
    case 2:
      return -0.45 + 1.25 * t * t;
    case 3:
      return 0.1 - 1.5 * Math.sin(Math.PI * Math.min(t * 1.15, 1)) * (1 - t * 0.35);
    case 4:
      return 0.85 - 1.7 * t;
    default:
      return 0;
  }
}

function contourPath(tone: number, flatten: number, w: number, h: number): string {
  const N = 40;
  const pts: string[] = [];
  let sum = 0;
  const raw: number[] = [];
  for (let i = 0; i <= N; i++) raw.push(toneCurve(tone, i / N));
  sum = raw.reduce((a, b) => a + b, 0) / raw.length;

  for (let i = 0; i <= N; i++) {
    const t = i / N;
    const v = sum + (raw[i] - sum) * (1 - flatten);
    const x = 6 + t * (w - 12);
    const y = h / 2 - v * (h / 2 - 8);
    pts.push(`${i === 0 ? "M" : "L"}${x.toFixed(1)},${y.toFixed(1)}`);
  }
  return pts.join(" ");
}

export function ToneGallery() {
  const [flatten, setFlatten] = useState(0);
  const [auto, setAuto] = useState(true);
  const raf = useRef(0);

  // Gently sweep on its own until the visitor takes the slider.
  useEffect(() => {
    if (!auto) return;
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    const start = performance.now();
    const loop = (now: number) => {
      const s = (now - start) / 1000;
      setFlatten((Math.sin(s * 0.35) * 0.5 + 0.5) * 0.95);
      raf.current = requestAnimationFrame(loop);
    };
    raf.current = requestAnimationFrame(loop);
    return () => cancelAnimationFrame(raf.current);
  }, [auto]);

  const collapsed = flatten > 0.72;

  return (
    <section className="tg section" id="pairs">
      <div className="container">
        <p className="eyebrow">Why tone is not a detail</p>
        <h2 className="display-lg" style={{ marginBottom: "0.5em" }}>
          Four words. One flattened contour.
        </h2>
        <p className="lead" style={{ maxWidth: "62ch", marginBottom: "1.6em" }}>
          Each pair below is the <em>same</em> syllable — the only difference is
          the pitch contour. Dysarthria flattens that contour. Drag the slider
          and watch two different words become the same shape.
        </p>

        <div className="tg__control">
          <label htmlFor="flatten">Prosodic flattening</label>
          <input
            id="flatten"
            type="range"
            min={0}
            max={100}
            value={Math.round(flatten * 100)}
            onChange={(e) => {
              setAuto(false);
              setFlatten(Number(e.target.value) / 100);
            }}
          />
          <span className="tg__pct">{Math.round(flatten * 100)}%</span>
        </div>

        <div className="grid grid--2 tg__grid">
          {PAIRS.map((p) => (
            <div className="tg__card" key={p.syllable}>
              <div className="tg__head">
                <span className="tg__syll">{p.syllable}</span>
                <span className={`tg__verdict ${collapsed ? "is-bad" : ""}`}>
                  {collapsed ? "indistinguishable" : "distinct"}
                </span>
              </div>

              <svg className="tg__svg" viewBox="0 0 260 96" role="img"
                aria-label={`Pitch contours for ${p.a.pinyin} and ${p.b.pinyin}`}>
                <line x1="6" y1="48" x2="254" y2="48" stroke="rgba(20,17,15,0.12)" strokeWidth="1" />
                <path d={contourPath(p.a.tone, flatten, 260, 96)} fill="none"
                  stroke={p.color} strokeWidth="3" strokeLinecap="round" />
                <path d={contourPath(p.b.tone, flatten, 260, 96)} fill="none"
                  stroke="var(--ink)" strokeWidth="3" strokeLinecap="round"
                  strokeDasharray="6 5" />
              </svg>

              <div className="tg__words">
                <div className="tg__word">
                  <span className="tg__hanzi" style={{ color: p.color }}>{p.a.hanzi}</span>
                  <span className="tg__pin">{p.a.pinyin}</span>
                  <span className="tg__gloss">{p.a.gloss}</span>
                </div>
                <div className="tg__vs">vs</div>
                <div className="tg__word">
                  <span className="tg__hanzi">{p.b.hanzi}</span>
                  <span className="tg__pin">{p.b.pinyin}</span>
                  <span className="tg__gloss">{p.b.gloss}</span>
                </div>
              </div>
            </div>
          ))}
        </div>

        <p className="disclaimer" style={{ marginTop: "28px" }}>
          Contours are idealised tone targets for illustration, not measured
          patient F0. The flattening behaviour matches what our simulation does
          to real recordings: tone-scale F0 variance falls from 2.545 to 1.173
          semitones between healthy and severe.
        </p>
      </div>

      <style>{`
        .tg__control { display:flex; align-items:center; gap:14px; flex-wrap:wrap;
          margin-bottom:26px; }
        .tg__control label { font-weight:600; font-size:0.9rem; text-transform:uppercase;
          letter-spacing:0.12em; color:var(--ink-soft); }
        .tg__control input[type=range] { flex:1; min-width:220px; max-width:420px;
          accent-color:var(--tangerine); }
        .tg__pct { font-family:var(--font-display); font-weight:900; font-size:1.3rem;
          font-variant-numeric:tabular-nums; min-width:3.4ch; }

        .tg__card { background:rgba(255,255,255,0.55); border-radius:var(--radius-lg);
          padding:clamp(18px,2.4vw,28px); box-shadow:inset 0 0 0 1px rgba(20,17,15,0.08); }
        .tg__head { display:flex; align-items:center; justify-content:space-between;
          margin-bottom:6px; }
        .tg__syll { font-family:ui-monospace,Menlo,Consolas,monospace; font-size:0.82rem;
          letter-spacing:0.08em; color:var(--ink-soft); }
        .tg__verdict { font-size:0.74rem; font-weight:700; text-transform:uppercase;
          letter-spacing:0.1em; padding:3px 10px; border-radius:999px;
          background:rgba(63,168,91,0.16); color:#256b39; transition:background .3s,color .3s; }
        .tg__verdict.is-bad { background:rgba(238,108,52,0.2); color:#a33d12; }
        .tg__svg { width:100%; height:auto; display:block; margin:4px 0 10px; }
        .tg__words { display:flex; align-items:center; gap:14px; }
        .tg__word { display:flex; flex-direction:column; line-height:1.2; }
        .tg__hanzi { font-family:var(--font-display); font-weight:900;
          font-size:clamp(1.6rem,3vw,2.2rem); }
        .tg__pin { font-size:0.9rem; color:var(--ink-soft); }
        .tg__gloss { font-size:0.8rem; color:var(--ink-soft); opacity:0.8; font-style:italic; }
        .tg__vs { font-size:0.78rem; text-transform:uppercase; letter-spacing:0.14em;
          color:var(--ink-soft); opacity:0.6; }
      `}</style>
    </section>
  );
}
