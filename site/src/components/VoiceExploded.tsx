import { useEffect, useRef, useState } from "react";
import { gsap } from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { scrollToId } from "../lib/scroll";

gsap.registerPlugin(ScrollTrigger);

// Apple-style exploded view of a spoken word, driven by scroll.
//
// A voice is a stack: a body makes a signal, the signal carries a contour, the
// contour carries meaning. Dysarthria damages the physical layers at the top,
// which destroys the F0 contour in the middle, which changes the word at the
// bottom. Scrolling pulls the stack apart so that causal chain is something you
// watch rather than something you read.
//
// Pinned + scrubbed: progress 0 = assembled (one coherent graphic), progress 1
// = fully separated with every layer labelled. Reduced motion / small screens
// fall back to a readable stacked list.

type Layer = {
  key: string;
  title: string;
  note: string;
  color: string;
  /** Where dysarthria does its damage — these get a warning flag. */
  damaged?: boolean;
};

const LAYERS: Layer[] = [
  {
    key: "speaker",
    title: "The speaker",
    note: "A person with something to say. After a glossectomy, a stroke, or with Parkinson's, everything below this line stops working the way it used to.",
    color: "#3e6be0",
  },
  {
    key: "articulators",
    title: "Articulators",
    note: "Tongue, lips, jaw, soft palate. Surgery removes tissue here; neurological disease weakens the muscles. Consonants blur first.",
    color: "#8a5cf6",
    damaged: true,
  },
  {
    key: "larynx",
    title: "Larynx",
    note: "The vocal folds set fundamental frequency. Lose fine control here and pitch stops moving — which in Mandarin is not a cosmetic problem.",
    color: "#f38ab0",
    damaged: true,
  },
  {
    key: "waveform",
    title: "The signal",
    note: "What a microphone actually receives: slower, breathier, less precisely articulated. This is the only layer a machine ever sees.",
    color: "#62c6e8",
  },
  {
    key: "contour",
    title: "The tone contour",
    note: "F0 over time. In Mandarin this is lexical — it is part of the word, not decoration on top of it. Dysarthric flattening collapses it toward a straight line.",
    color: "#f4b024",
    damaged: true,
  },
  {
    key: "meaning",
    title: "The word",
    note: "統一 (tǒng yī, \"unify\") becomes 同一 (tóng yī, \"the same\"). One tone apart. A different word — not an accent, and no spell-checker can catch it.",
    color: "#ee6c34",
  },
];

/* ------------------------------------------------------------------ */
/* Layer artwork. Stylised and graphic to match the display type — not */
/* medical illustration.                                              */
/* ------------------------------------------------------------------ */

function Art({ layer }: { layer: string }) {
  const c = "currentColor";
  switch (layer) {
    case "speaker":
      return (
        <svg viewBox="0 0 320 200" className="vx-art">
          {/* head profile, facing right */}
          <path
            d="M112 178 C86 168 70 142 70 112 C70 74 98 44 136 40 C170 36 198 54 208 82
               L228 106 L206 116 L204 132 L186 134 L184 152 C184 166 172 176 156 176 Z"
            fill="none" stroke={c} strokeWidth="3" strokeLinejoin="round"
          />
          {/* mouth */}
          <path d="M186 134 L214 130" stroke={c} strokeWidth="3" strokeLinecap="round" />
          {/* sound radiating out */}
          <g opacity="0.75">
            <path d="M236 112 Q248 130 236 148" fill="none" stroke={c} strokeWidth="2.5" strokeLinecap="round" />
            <path d="M254 100 Q274 130 254 160" fill="none" stroke={c} strokeWidth="2.5" strokeLinecap="round" opacity="0.7" />
            <path d="M272 88 Q300 130 272 172" fill="none" stroke={c} strokeWidth="2.5" strokeLinecap="round" opacity="0.4" />
          </g>
        </svg>
      );
    case "articulators":
      return (
        <svg viewBox="0 0 320 200" className="vx-art">
          {/* hard palate */}
          <path d="M96 82 Q150 66 214 78" fill="none" stroke={c} strokeWidth="3" strokeLinecap="round" />
          {/* tongue body */}
          <path
            d="M92 148 Q112 108 150 106 Q192 104 208 126"
            fill="none" stroke={c} strokeWidth="7" strokeLinecap="round" opacity="0.85"
          />
          {/* jaw line */}
          <path d="M86 160 Q150 182 216 156" fill="none" stroke={c} strokeWidth="3" strokeLinecap="round" opacity="0.6" />
          {/* lips */}
          <path d="M214 96 L238 104 M214 132 L238 124" stroke={c} strokeWidth="4" strokeLinecap="round" />
          {/* constriction markers */}
          <circle cx="150" cy="106" r="5" fill={c} />
          <circle cx="208" cy="126" r="5" fill={c} opacity="0.7" />
        </svg>
      );
    case "larynx":
      return (
        <svg viewBox="0 0 320 200" className="vx-art">
          {/* vocal folds, open */}
          <path d="M120 60 Q152 100 120 140" fill="none" stroke={c} strokeWidth="6" strokeLinecap="round" />
          <path d="M200 60 Q168 100 200 140" fill="none" stroke={c} strokeWidth="6" strokeLinecap="round" />
          {/* glottal airflow */}
          <path d="M160 74 L160 126" stroke={c} strokeWidth="2.5" strokeDasharray="5 6" strokeLinecap="round" opacity="0.8" />
          {/* vibration */}
          <g opacity="0.55">
            <path d="M104 78 Q94 100 104 122" fill="none" stroke={c} strokeWidth="2" strokeLinecap="round" />
            <path d="M216 78 Q226 100 216 122" fill="none" stroke={c} strokeWidth="2" strokeLinecap="round" />
          </g>
          {/* F0 label tick */}
          <path d="M244 100 L282 100" stroke={c} strokeWidth="2.5" strokeLinecap="round" opacity="0.7" />
        </svg>
      );
    case "waveform":
      return (
        <svg viewBox="0 0 320 200" className="vx-art">
          <path
            d="M20 100
               Q32 62 44 100 T68 100 Q80 48 92 100 T116 100
               Q128 70 140 100 T164 100 Q176 40 188 100 T212 100
               Q224 74 236 100 T260 100 Q272 66 284 100 T300 100"
            fill="none" stroke={c} strokeWidth="3" strokeLinecap="round"
          />
          <line x1="20" y1="100" x2="300" y2="100" stroke={c} strokeWidth="1" opacity="0.28" />
        </svg>
      );
    case "contour":
      return (
        <svg viewBox="0 0 320 200" className="vx-art">
          {/* tone 3 (dipping) — solid, the correct contour */}
          <path d="M40 78 Q104 172 160 150 Q216 130 280 62" fill="none"
            stroke={c} strokeWidth="5" strokeLinecap="round" />
          {/* flattened version — dashed, what dysarthria produces */}
          <path d="M40 112 L280 112" fill="none" stroke={c} strokeWidth="3"
            strokeDasharray="8 8" strokeLinecap="round" opacity="0.55" />
          <line x1="40" y1="40" x2="40" y2="170" stroke={c} strokeWidth="1.5" opacity="0.3" />
        </svg>
      );
    case "meaning":
      return (
        <svg viewBox="0 0 320 200" className="vx-art">
          <text x="160" y="88" textAnchor="middle" className="vx-hanzi" fill={c}>統一</text>
          <path d="M132 108 L188 108" stroke={c} strokeWidth="2" opacity="0.5" />
          <text x="160" y="108" textAnchor="middle" className="vx-arrow" fill={c}>▼</text>
          <text x="160" y="168" textAnchor="middle" className="vx-hanzi" fill={c} opacity="0.75">同一</text>
        </svg>
      );
    default:
      return null;
  }
}

export function VoiceExploded() {
  const root = useRef<HTMLDivElement>(null);
  const stage = useRef<HTMLDivElement>(null);
  const layerEls = useRef<(HTMLDivElement | null)[]>([]);
  const [stageIdx, setStageIdx] = useState(0);
  const [reduced, setReduced] = useState(false);

  const n = LAYERS.length;

  useEffect(() => {
    const isReduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (isReduced || window.innerWidth < 900) {
      setReduced(true);
      return;
    }

    const ctx = gsap.context(() => {
      // Drive one value 0 -> 1 and derive every layer's transform from it, so
      // the whole assembly stays in lockstep with the scrub.
      const state = { p: 0 };

      const apply = () => {
        const p = state.p;
        const eased = gsap.parseEase("power2.inOut")(p);
        layerEls.current.forEach((el, i) => {
          if (!el) return;
          const mid = (n - 1) / 2;
          const offset = i - mid;
          // Spread along Y and push apart in Z for depth.
          const y = offset * 148 * eased;
          const z = offset * -120 * eased;
          const rot = 52 * eased; // tilt into an isometric plate view
          el.style.transform =
            `translate(-50%,-50%) translateY(${y.toFixed(1)}px) ` +
            `translateZ(${z.toFixed(1)}px) rotateX(${rot.toFixed(1)}deg)`;
          // Labels only make sense once the stack has opened up.
          const label = el.querySelector<HTMLElement>(".vx-label");
          if (label) {
            const a = gsap.utils.clamp(0, 1, (eased - 0.28) / 0.3);
            label.style.opacity = String(a);
            label.style.transform = `translateX(${(1 - a) * 26}px)`;
          }
        });
      };

      gsap.to(state, {
        p: 1,
        ease: "none",
        scrollTrigger: {
          trigger: root.current,
          pin: true,
          scrub: 1,
          start: "top top",
          end: "+=2600",
          invalidateOnRefresh: true,
          onUpdate: (self) => {
            state.p = self.progress;
            apply();
            const i = Math.min(n - 1, Math.floor(self.progress * n * 0.999));
            setStageIdx((prev) => (prev !== i ? i : prev));
          },
        },
      });

      apply();
    }, root);

    return () => ctx.revert();
  }, [n]);

  if (reduced) {
    return (
      <section className="vx vx--flat" id="tour">
        <div className="container">
          <p className="eyebrow" style={{ color: "var(--sky)" }}>Anatomy of a word</p>
          <h2 className="display-lg" style={{ marginBottom: "0.7em" }}>
            Six layers between a person and a word.
          </h2>
          <div style={{ display: "grid", gap: "18px" }}>
            {LAYERS.map((l) => (
              <div key={l.key} className="vx-flat" style={{ borderColor: l.color }}>
                <div className="vx-flat__art" style={{ color: l.color }}>
                  <Art layer={l.key} />
                </div>
                <div>
                  <h3 className="vx-flat__title">
                    {l.title}
                    {l.damaged && <span className="vx-tag">dysarthria hits here</span>}
                  </h3>
                  <p className="vx-flat__note">{l.note}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
        <style>{VX_CSS}</style>
      </section>
    );
  }

  const cur = LAYERS[stageIdx];

  return (
    <section className="vx" id="tour" ref={root}>
      <div className="vx-head">
        <p className="eyebrow" style={{ color: "var(--sky)" }}>Anatomy of a word</p>
        <h2 className="display-lg">Six layers between a person and a word.</h2>
      </div>

      <div className="vx-scene">
        <div className="vx-stage" ref={stage}>
          {LAYERS.map((l, i) => (
            <div
              key={l.key}
              className="vx-layer"
              ref={(el) => { layerEls.current[i] = el; }}
              style={{ color: l.color, zIndex: n - i }}
            >
              <div className="vx-plate" style={{ borderColor: l.color }}>
                <Art layer={l.key} />
              </div>
              <div className="vx-label">
                <span className="vx-label__n">{String(i + 1).padStart(2, "0")}</span>
                <span className="vx-label__t">{l.title}</span>
                {l.damaged && <span className="vx-tag">damaged</span>}
              </div>
            </div>
          ))}
        </div>

        <aside className="vx-panel">
          <div className="vx-panel__n" style={{ color: cur.color }}>
            {String(stageIdx + 1).padStart(2, "0")}
          </div>
          <h3 className="vx-panel__title">{cur.title}</h3>
          <p className="vx-panel__note">{cur.note}</p>
          {cur.damaged && (
            <p className="vx-panel__flag">This layer is what dysarthria damages.</p>
          )}
          <div className="vx-progress" aria-hidden="true">
            {LAYERS.map((l, i) => (
              <span
                key={l.key}
                className={`vx-progress__dot ${i <= stageIdx ? "is-on" : ""}`}
                style={{ background: i <= stageIdx ? l.color : undefined }}
              />
            ))}
          </div>
          <button className="vx-cta" onClick={() => scrollToId("pairs")}>
            See it break
          </button>
        </aside>
      </div>

      <style>{VX_CSS}</style>
    </section>
  );
}

const VX_CSS = `
  .vx { position:relative; height:100vh; overflow:hidden; color:var(--cream);
    background:radial-gradient(120% 90% at 50% 35%, #1c1830 0%, #100e18 55%, #0b0a10 100%); }
  .vx--flat { height:auto; padding:clamp(72px,12vh,140px) clamp(20px,5vw,72px); }

  .vx-head { position:absolute; top:0; left:0; right:0; z-index:6; text-align:center;
    padding:clamp(28px,6vh,64px) clamp(20px,5vw,72px) 0; pointer-events:none; }
  .vx-head h2 { margin-top:0.25em; }

  .vx-scene { position:relative; height:100%; display:grid;
    grid-template-columns:1.15fr 0.85fr; align-items:center; gap:20px;
    max-width:var(--maxw); margin:0 auto; padding:0 clamp(20px,5vw,72px); }

  .vx-stage { position:relative; height:100%; perspective:1500px;
    transform-style:preserve-3d; }
  .vx-layer { position:absolute; left:50%; top:50%; width:min(430px,42vw);
    transform-style:preserve-3d; will-change:transform;
    display:flex; align-items:center; gap:16px; }
  .vx-plate { flex:1; border:1.5px solid; border-radius:18px;
    background:rgba(16,14,24,0.72); backdrop-filter:blur(2px);
    box-shadow:0 30px 70px rgba(0,0,0,0.5); padding:10px 14px; }
  .vx-art { width:100%; height:auto; display:block; }
  .vx-hanzi { font-family:var(--font-display); font-weight:900; font-size:46px; }
  .vx-arrow { font-size:15px; opacity:0.65; }

  .vx-label { position:absolute; left:calc(100% + 14px); top:50%;
    transform:translateY(-50%); display:flex; align-items:center; gap:8px;
    white-space:nowrap; opacity:0; pointer-events:none; }
  .vx-label__n { font-family:var(--font-display); font-weight:900; font-size:0.9rem; opacity:0.7; }
  .vx-label__t { font-weight:600; font-size:0.92rem; }
  .vx-tag { font-size:0.62rem; font-weight:700; text-transform:uppercase;
    letter-spacing:0.1em; padding:2px 7px; border-radius:999px;
    background:rgba(238,108,52,0.22); color:#ff9d6e; }

  .vx-panel { position:relative; z-index:6; max-width:420px; }
  .vx-panel__n { font-family:var(--font-display); font-weight:900;
    font-size:clamp(2.2rem,4.4vw,3.2rem); line-height:1; }
  .vx-panel__title { font-size:clamp(1.8rem,3.4vw,2.8rem); margin:0.1em 0 0.35em; }
  .vx-panel__note { color:rgba(244,239,230,0.82); font-size:clamp(0.98rem,1.3vw,1.15rem);
    min-height:7.2em; }
  .vx-panel__flag { margin-top:0.5em; font-size:0.85rem; color:#ff9d6e; font-weight:600; }
  .vx-progress { display:flex; gap:7px; margin:1.3em 0 1.1em; }
  .vx-progress__dot { width:26px; height:4px; border-radius:999px;
    background:rgba(244,239,230,0.2); transition:background .35s ease; }
  .vx-cta { background:var(--cream); color:var(--ink); border:none; border-radius:999px;
    font-family:var(--font-body); font-weight:600; font-size:0.95rem;
    padding:10px 20px; cursor:pointer; transition:background .2s; }
  .vx-cta:hover { background:var(--sky); }

  .vx-flat { display:grid; grid-template-columns:150px 1fr; gap:20px;
    align-items:center; border-left:3px solid; padding:10px 0 10px 18px; }
  .vx-flat__art { width:150px; }
  .vx-flat__title { font-size:1.4rem; display:flex; align-items:center; gap:10px;
    flex-wrap:wrap; }
  .vx-flat__note { color:rgba(244,239,230,0.8); margin-top:0.3em; }

  @media (max-width:1080px) {
    .vx-scene { grid-template-columns:1fr; }
    .vx-panel { position:absolute; bottom:6vh; left:clamp(20px,5vw,72px); right:auto; }
  }
`;
