import { useEffect, useRef } from "react";
import { gsap } from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";

gsap.registerPlugin(ScrollTrigger);

// Cinematic "fly through the code": real snippets from the OwnVoice source
// drift in from depth as you scroll, each with a plain-English annotation.
// Reduced motion → static, readable cards.

const SCENES: { file: string; title: string; note: string; code: string }[] = [
  {
    file: "src/metrics.py",
    title: "Why tone needs its own metric",
    note: "A tone-only error produces a different word, not an accent. CER counts it as one character; the meaning is completely gone.",
    code: `# 買 (mai3, "buy")  vs  賣 (mai4, "sell")
# One tone apart. Opposite meanings.

def score(reference: str, hypothesis: str) -> Scores:
    ref_syl, hyp_syl = _syllables(reference), _syllables(hypothesis)

    # STER: tone errors ONLY on syllables whose initial+final
    # were already correct, isolating tonal from segmental failure.
    matched = wrong_tone = 0
    for r, h in zip(ref_syl, hyp_syl):
        r_seg, r_tone = _split_tone(r)
        h_seg, h_tone = _split_tone(h)
        if r_seg == h_seg:
            matched += 1
            if r_tone != h_tone:
                wrong_tone += 1`,
  },
  {
    file: "src/dysarthria_sim.py",
    title: "Flattening the contour destroys the word",
    note: "Prosodic flattening is the perturbation that matters in Mandarin: tone lives in the F0 contour, so collapsing it collapses lexical identity.",
    code: `def _compress_f0(f0, strength):
    """Compress F0 toward its voiced mean.
    strength=0 no-op, 1.0 = monotone.

    Mandarin tone lives in this contour, so this converts an
    intelligibility problem into a lexical-identity problem.
    """
    out = f0.copy()
    voiced = out > 0
    mean = out[voiced].mean()
    out[voiced] = mean + (out[voiced] - mean) * (1.0 - strength)
    return out`,
  },
  {
    file: "src/verify_sim.py",
    title: "The metric that caught our own bug",
    note: "Raw F0 variance failed: flattening and jitter push it in opposite directions. Splitting the contour from its residual fixed the measurement.",
    code: `# contour  = medfilt(F0)        -> tone    (falls with severity)
# residual = F0 - medfilt(F0)   -> jitter  (should rise)

def f0_tone_std(y, sr, kernel=7):
    """Std of the SMOOTHED F0 contour — syllable-scale tone only.

    Raw F0 std sums two perturbations moving in opposite
    directions, so it reported a non-monotonic result.
    """
    st = _voiced_semitones(y, sr)
    return float(np.std(medfilt(st, kernel_size=k)))`,
  },
  {
    file: "src/train_asr.py",
    title: "Never split by utterance",
    note: "Splitting by utterance leaks speaker identity into the test set. The model then memorises voices and every reported number is inflated.",
    code: `def build_splits(root, severities, eval_frac, seed,
                 include_clean=True):
    """Split by SPEAKER, never by utterance."""
    speakers = sorted({r["speaker"] for r in rows})
    rng = np.random.default_rng(seed)
    rng.shuffle(speakers)
    eval_speakers = set(speakers[:max(1, int(len(speakers)*eval_frac))])

    train = [r for r in rows if r["speaker"] not in eval_speakers]
    evl   = [r for r in rows if r["speaker"] in eval_speakers]`,
  },
  {
    file: "src/evaluate.py",
    title: "One test set, or it proves nothing",
    note: "Our first result compared two different test sets. That cannot support an improvement claim, however good the numbers look — so we rebuilt it.",
    code: `# Both models scored on the SAME held-out speakers, reusing
# build_splits with the identical seed and eval_frac.
#
# Results are broken out PER CONDITION: a mixed average hides
# where the model actually improved, and severe dysarthria is
# what matters clinically.

for cond in CONDITIONS:            # clean, mild, moderate, severe
    print(f"{cond}: {base[cond].cer:.4f} -> {tuned[cond].cer:.4f}")`,
  },
];

export function CodeFlythrough() {
  const root = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const isReduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (isReduced) return;
    const ctx = gsap.context(() => {
      const scenes = gsap.utils.toArray<HTMLElement>(".cf-scene");
      scenes.forEach((scene) => {
        const card = scene.querySelector(".cf-card");
        gsap.fromTo(
          card,
          { z: -560, rotateX: 14, autoAlpha: 0 },
          {
            z: 0,
            rotateX: 0,
            autoAlpha: 1,
            ease: "none",
            scrollTrigger: { trigger: scene, start: "top 88%", end: "top 42%", scrub: true },
          }
        );
        gsap.to(card, {
          z: 240,
          autoAlpha: 0.1,
          ease: "none",
          scrollTrigger: { trigger: scene, start: "bottom 55%", end: "bottom 8%", scrub: true },
        });
      });
    }, root);
    return () => ctx.revert();
  }, []);

  return (
    <section className="cf" id="code" ref={root}>
      <div className="container cf-head">
        <p className="eyebrow" style={{ color: "var(--sky)" }}>
          Inside the code
        </p>
        <h2 className="display-lg">The decisions, in the actual source.</h2>
        <p className="lead" style={{ color: "rgba(244,239,230,0.8)", marginTop: "0.8em" }}>
          Not a diagram — the real modules, including the measurement bug we
          found and the split discipline that keeps the numbers honest.
        </p>
      </div>

      <div className="cf-stage">
        {SCENES.map((s, i) => (
          <div className="cf-scene" key={i}>
            <div className="cf-card">
              <div className="cf-card__bar">
                <span className="cf-dot" />
                <span className="cf-dot" />
                <span className="cf-dot" />
                <span className="cf-file">{s.file}</span>
              </div>
              <pre className="cf-code">
                <code>{s.code}</code>
              </pre>
            </div>
            <div className="cf-note">
              <div className="cf-note__n">{String(i + 1).padStart(2, "0")}</div>
              <h3 className="cf-note__title">{s.title}</h3>
              <p className="cf-note__text">{s.note}</p>
            </div>
          </div>
        ))}
      </div>

      <style>{`
        .cf { position:relative; background:#0b0a10; color:var(--cream);
          padding:clamp(72px,12vh,140px) clamp(20px,5vw,72px) 20vh; perspective:1200px; }
        .cf-head { text-align:center; margin-bottom:14vh; }
        .cf-stage { max-width:1000px; margin:0 auto; transform-style:preserve-3d; }
        .cf-scene { min-height:78vh; display:grid; grid-template-columns:1.3fr 1fr; gap:36px;
          align-items:center; }
        .cf-card { transform-style:preserve-3d; border-radius:16px; overflow:hidden;
          background:#16141f; box-shadow:0 40px 90px rgba(0,0,0,0.55), 0 0 0 1px rgba(138,92,246,0.25);
          will-change:transform,opacity; }
        .cf-card__bar { display:flex; align-items:center; gap:8px; padding:12px 16px;
          background:#1e1b2b; border-bottom:1px solid rgba(255,255,255,0.06); }
        .cf-dot { width:11px; height:11px; border-radius:999px; background:#3a3550; }
        .cf-dot:nth-child(1){ background:#ee6c34; }
        .cf-dot:nth-child(2){ background:#f4b024; }
        .cf-dot:nth-child(3){ background:#3fa85b; }
        .cf-file { margin-left:10px; font-family:ui-monospace,Menlo,Consolas,monospace;
          font-size:0.78rem; color:rgba(244,239,230,0.5); }
        .cf-code { margin:0; padding:20px 22px; overflow-x:auto;
          font-family:ui-monospace,Menlo,Consolas,monospace; font-size:0.8rem; line-height:1.7;
          color:#d7d3e8; }
        .cf-note__n { font-family:var(--font-display); font-weight:900; font-size:2.4rem;
          color:var(--violet); line-height:1; }
        .cf-note__title { font-size:clamp(1.4rem,2.6vw,2.2rem); margin:0.2em 0 0.4em; }
        .cf-note__text { color:rgba(244,239,230,0.78); }

        @media (max-width:820px) {
          .cf-scene { grid-template-columns:1fr; gap:20px; min-height:auto; padding:8vh 0; }
        }
      `}</style>
    </section>
  );
}
