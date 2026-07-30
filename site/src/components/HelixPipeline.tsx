import { useEffect, useRef, useState } from "react";
import { scrollToId } from "../lib/scroll";

// The pipeline as an infinite spiral of cards. Rectangular stage cards ride a
// helix, rotating and climbing continuously and wrapping at the top so the
// spiral never ends. The front-most card drives the detail panel; clicking a
// card locks it as the featured stage. Pure CSS-3D (readable, clickable, no
// WebGL clipping). Reduced motion / small screens fall back to a static list.

const STAGES = [
  { n: "01", title: "Source clean speech", desc: "Taiwan-accented Mandarin from Common Voice zh-TW (CC0) and AISHELL-3 (Apache-2.0). Both openly licensed, because improper data acquisition is an explicit disqualification criterion in the competition rules.", target: "problem" },
  { n: "02", title: "Simulate dysarthria", desc: "pyworld decomposes each utterance into F0, spectral envelope and aperiodicity. Six perturbations model documented acoustic correlates: reduced rate, prosodic flattening, formant smearing, breathiness, amplitude instability and jitter.", target: "code" },
  { n: "03", title: "Validate the simulation", desc: "Tone-scale F0 variance must fall monotonically with severity, spectral flux must fall, duration must rise. Measured: 2.545 to 1.173 semitones across severities. The jitter axis failed validation and is documented as unproven.", target: "evidence" },
  { n: "04", title: "Split by speaker", desc: "Train and test never share a speaker. Splitting by utterance would leak speaker identity and let the model memorise voices instead of learning dysarthria — a mistake that inflates every downstream number.", target: "evidence" },
  { n: "05", title: "Encode", desc: "Whisper's log-mel front end at 16 kHz, with clean audio mixed into training alongside dysarthric audio so the model does not forget normal speech — a clinical system hears patients, clinicians and family.", target: "code" },
  { n: "06", title: "Fine-tune", desc: "whisper-small, fp16, gradient checkpointing, on an RTX 5060. Training overfits after a single epoch: train loss 0.0018 while eval error rises. Data scale, not training time, is the binding constraint.", target: "evidence" },
  { n: "07", title: "Score characters", desc: "Character error rate, not word error rate — written Chinese has no word delimiters, so WER depends entirely on an arbitrary segmenter and is not comparable across studies.", target: "evidence" },
  { n: "08", title: "Score tone", desc: "Segmental tone error rate: tone mistakes counted only on syllables whose initial and final were recognised correctly. This isolates tonal failure from ordinary mis-hearing, and no prior dysarthria work reports it.", target: "evidence" },
  { n: "09", title: "Compare, matched", desc: "Baseline and fine-tuned models scored on the identical held-out speakers, broken out per severity. A mixed average would hide where the model actually improved — and severe is what matters clinically.", target: "demo" },
];

const COLORS = ["#3e6be0", "#62c6e8", "#8a5cf6", "#f4b024", "#3fa85b", "#ee6c34", "#f38ab0", "#3e6be0", "#3fa85b"];
const TURNS = 1.9;
const RADIUS = 235;
const RISE = 430;

function transformFor(phase: number, seed = 0) {
  const angle = phase * 360 * TURNS; // degrees around Y
  const rad = (angle * Math.PI) / 180;
  const x = Math.sin(rad) * RADIUS;
  const z = Math.cos(rad) * RADIUS;
  const y = (0.5 - phase) * RISE; // screen-up as phase grows
  const depth = (z + RADIUS) / (2 * RADIUS); // 0 back .. 1 front
  const scale = 0.62 + depth * 0.5;
  // fade near the vertical extremes to hide the wrap, and by depth
  const edge = Math.min(1, Math.min(phase, 1 - phase) * 6);
  const opacity = (0.22 + depth * 0.78) * edge;
  // organic warp: gentle forward/back tilt as the card climbs, plus a fixed
  // per-card lean so the spiral reads as floating graphics.
  const tiltX = Math.sin(phase * Math.PI * 2) * 12;
  const tiltZ = ((seed % 5) - 2) * 5;
  const transform =
    `translate(-50%, -50%) translate3d(${x.toFixed(1)}px, ${y.toFixed(1)}px, 0) ` +
    `rotateY(${(-angle).toFixed(1)}deg) rotateX(${tiltX.toFixed(1)}deg) ` +
    `rotateZ(${tiltZ}deg) scale(${scale.toFixed(3)})`;
  return { transform, opacity, z, depth };
}

export function HelixPipeline() {
  const cardEls = useRef<(HTMLDivElement | null)[]>([]);
  const progress = useRef(0);
  const paused = useRef(false);
  const featuredRef = useRef<number | null>(null);
  const lastFront = useRef(-1);
  const panelNum = useRef<HTMLDivElement>(null);
  const panelTitle = useRef<HTMLHeadingElement>(null);
  const panelDesc = useRef<HTMLParagraphElement>(null);
  const [featured, setFeatured] = useState<number | null>(null);
  const [reduced, setReduced] = useState(false);

  const n = STAGES.length;

  const paintPanel = (i: number) => {
    if (panelNum.current) {
      panelNum.current.textContent = STAGES[i].n;
      panelNum.current.style.color = COLORS[i];
    }
    if (panelTitle.current) panelTitle.current.textContent = STAGES[i].title;
    if (panelDesc.current) panelDesc.current.textContent = STAGES[i].desc;
  };

  useEffect(() => {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      setReduced(true);
      return;
    }
    let raf = 0;
    let last = performance.now();
    const loop = (now: number) => {
      const dt = Math.min(0.05, (now - last) / 1000);
      last = now;
      if (!paused.current) progress.current = (progress.current + dt * 0.05) % 1;

      let front = 0;
      let frontZ = -Infinity;
      for (let i = 0; i < n; i++) {
        const el = cardEls.current[i];
        if (!el) continue;
        const phase = (i / n + progress.current) % 1;
        const { transform, opacity, z } = transformFor(phase, i);
        el.style.transform = transform;
        el.style.opacity = String(opacity);
        el.style.zIndex = String(Math.round(z + RADIUS));
        if (z > frontZ) {
          frontZ = z;
          front = i;
        }
      }
      const show = featuredRef.current ?? front;
      if (show !== lastFront.current) {
        lastFront.current = show;
        paintPanel(show);
        cardEls.current.forEach((el, i) =>
          el?.classList.toggle("is-active", i === show)
        );
      }
      raf = requestAnimationFrame(loop);
    };
    raf = requestAnimationFrame(loop);
    return () => cancelAnimationFrame(raf);
  }, [n]);

  const onCardEnter = () => {
    if (featuredRef.current === null) paused.current = true;
  };
  const onCardLeave = () => {
    if (featuredRef.current === null) paused.current = false;
  };
  const onCardClick = (i: number) => {
    if (featured === i) {
      setFeatured(null);
      featuredRef.current = null;
      paused.current = false;
    } else {
      setFeatured(i);
      featuredRef.current = i;
      paused.current = true;
      lastFront.current = -1; // force panel repaint
    }
  };

  if (reduced) {
    return (
      <section className="helix" id="how">
        <div className="helix__head container">
          <p className="eyebrow" style={{ color: "var(--sky)" }}>The pipeline</p>
          <h2 className="display-lg">Nine steps, measured at every one.</h2>
        </div>
        <div className="container" style={{ display: "grid", gap: "16px", paddingBottom: "12vh" }}>
          {STAGES.map((s, i) => (
            <div key={s.title} className="helix__flat">
              <div className="helix__n" style={{ color: COLORS[i] }}>{s.n}</div>
              <h3 className="helix__title">{s.title}</h3>
              <p className="helix__desc">{s.desc}</p>
            </div>
          ))}
        </div>
      </section>
    );
  }

  return (
    <section className="helix" id="how">
      <div className="helix__head container">
        <p className="eyebrow" style={{ color: "var(--sky)" }}>The pipeline</p>
        <h2 className="display-lg">Nine steps, measured at every one.</h2>
      </div>

      <div className="helix__scene">
        <div className="helix__panel">
          <div className="helix__n" ref={panelNum} style={{ color: COLORS[0] }}>{STAGES[0].n}</div>
          <h3 className="helix__title" ref={panelTitle}>{STAGES[0].title}</h3>
          <p className="helix__desc" ref={panelDesc}>{STAGES[0].desc}</p>
          <button
            className="helix__explore"
            onClick={() => scrollToId(STAGES[featured ?? 0].target)}
          >
            Explore this step
          </button>
          <p className="helix__hint">
            {featured !== null ? "Click the card again to resume the spiral" : "Click a card to hold it"}
          </p>
        </div>

        <div className="helix__stage" role="list" aria-label="Pipeline stages">
          {STAGES.map((s, i) => {
            const init = transformFor((i / n) % 1, i);
            return (
              <button
                key={s.title}
                role="listitem"
                className={`helix__card ${featured === i ? "is-featured" : ""}`}
                ref={(el) => { cardEls.current[i] = el as unknown as HTMLDivElement; }}
                style={{ transform: init.transform, opacity: init.opacity, borderColor: COLORS[i] }}
                onMouseEnter={onCardEnter}
                onMouseLeave={onCardLeave}
                onClick={() => onCardClick(i)}
                aria-label={`Stage ${s.n}: ${s.title}. ${s.desc}`}
              >
                <span
                  className="helix__card-graphic"
                  style={{ background: `linear-gradient(135deg, ${COLORS[i]}, ${COLORS[(i + 2) % COLORS.length]})` }}
                  aria-hidden="true"
                >
                  <span className="helix__card-n">{s.n}</span>
                </span>
                <span className="helix__card-t">{s.title}</span>
              </button>
            );
          })}
        </div>
      </div>

      <style>{`
        .helix { position:relative; color:var(--cream); overflow:hidden;
          background-color:#0b0a10;
          background-image:
            linear-gradient(rgba(255,255,255,0.035) 1px, transparent 1px),
            linear-gradient(90deg, rgba(255,255,255,0.035) 1px, transparent 1px);
          background-size:48px 48px; }
        .helix__head { position:relative; z-index:3; text-align:center;
          padding:clamp(72px,12vh,130px) clamp(20px,5vw,72px) 0; }
        .helix__scene { position:relative; display:grid; grid-template-columns:1fr 1fr;
          align-items:center; gap:24px; max-width:var(--maxw); margin:0 auto;
          padding:4vh clamp(20px,5vw,72px) 12vh; min-height:86vh; }

        .helix__panel { position:relative; z-index:3; max-width:440px; }
        .helix__n { font-family:var(--font-display); font-weight:900;
          font-size:clamp(2.4rem,5vw,3.6rem); line-height:1; }
        .helix__title { font-size:clamp(2rem,4vw,3.2rem); margin:0.1em 0 0.4em; }
        .helix__desc { color:rgba(244,239,230,0.82); font-size:clamp(1rem,1.4vw,1.2rem);
          min-height:7.4em; }
        .helix__explore { margin-top:1.2em; background:var(--cream); color:var(--ink);
          border:none; border-radius:999px; font-family:var(--font-body); font-weight:600;
          font-size:0.95rem; padding:10px 20px; cursor:pointer; transition:background .2s,color .2s; }
        .helix__explore:hover { background:var(--sky); }
        .helix__hint { margin-top:1em; font-size:0.82rem; color:rgba(244,239,230,0.45); }

        .helix__stage { position:relative; height:min(72vh,620px);
          transform-style:preserve-3d; perspective:1500px; }
        .helix__card {
          position:absolute; left:50%; top:50%; width:194px; min-height:150px;
          display:flex; flex-direction:column; overflow:hidden;
          padding:0; border-radius:16px; cursor:pointer;
          background:rgba(18,16,28,0.96); border:1.5px solid; color:var(--cream);
          box-shadow:0 26px 64px rgba(0,0,0,0.55); will-change:transform,opacity;
          text-align:left; transition:box-shadow .3s ease; }
        .helix__card.is-active { box-shadow:0 34px 90px rgba(0,0,0,0.7); }
        .helix__card.is-featured { box-shadow:0 0 0 2px var(--cream), 0 34px 90px rgba(0,0,0,0.7); }
        .helix__card-graphic { position:relative; flex:1; min-height:94px;
          display:grid; place-items:start; padding:12px 14px; }
        .helix__card-graphic::after { content:""; position:absolute; inset:0;
          background:radial-gradient(120% 80% at 80% 0%, rgba(255,255,255,0.28), transparent 60%);
          mix-blend-mode:screen; }
        .helix__card-n { font-family:var(--font-display); font-weight:900;
          font-size:1.9rem; line-height:1; color:#fff; position:relative; z-index:1;
          text-shadow:0 1px 6px rgba(0,0,0,0.35); }
        .helix__card-t { font-family:var(--font-display); font-weight:800; font-size:1.25rem;
          letter-spacing:-0.02em; padding:10px 16px 14px; }

        .helix__flat { border-left:3px solid var(--sky); padding:6px 0 6px 18px; }

        @media (max-width:900px) {
          .helix__scene { grid-template-columns:1fr; gap:8px; }
          .helix__stage { display:none; }
        }
      `}</style>
    </section>
  );
}
