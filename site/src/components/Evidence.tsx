import { useEffect, useRef, useState } from "react";
import { gsap } from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";

gsap.registerPlugin(ScrollTrigger);

// Horizontal-slide "journey" through the measured evidence, pinned and scrubbed
// by scroll. Reduced motion / small screens → stacked cards.
//
// Every figure here comes from data/train/matched_eval.json — baseline and
// fine-tuned models scored on the SAME held-out speakers. Panel 05 is a
// negative result and stays in deliberately.
const PANELS = [
  { n: "01", key: "The gap to close", metric: "89.3 → 52.6%", note: "Stock Whisper on Taiwan-accented Mandarin: 89.3% intelligible on clean speech, 52.6% under severe dysarthria. That collapse is the problem.", cls: "g--cobalt" },
  { n: "02", key: "After fine-tuning", metric: "86.2%", note: "Overall intelligibility on a matched test set — character error rate down 27.7% relative, from 0.1908 to 0.1380.", cls: "g--violet" },
  { n: "03", key: "Severe improves most", metric: "−41%", note: "Severe dysarthria: CER 0.2877 → 0.1683. Moderate −37%, mild −15%. Gains scale with severity, which is the clinically correct shape.", cls: "g--tangerine" },
  { n: "04", key: "Speaker-disjoint", metric: "91 speakers", note: "Train and test never share a voice. Splitting by utterance instead would leak speaker identity and inflate every number on this page.", cls: "g--marigold" },
  { n: "05", key: "But tone did not move", metric: "−0.004", note: "Segmental tone error rate barely changed while character accuracy improved 27.7%. Generic ASR fine-tuning does not fix tone. That negative result is the reason this project exists.", cls: "g--grass" },
];

export function Evidence() {
  const root = useRef<HTMLDivElement>(null);
  const track = useRef<HTMLDivElement>(null);
  const [stage, setStage] = useState(0);
  const [reduced, setReduced] = useState(false);

  useEffect(() => {
    const isReduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (isReduced || window.innerWidth < 820 || window.innerWidth === 0) {
      setReduced(true);
      return;
    }
    const ctx = gsap.context(() => {
      const panels = PANELS.length;
      const distance = () =>
        track.current ? track.current.scrollWidth - window.innerWidth : 0;
      gsap.to(track.current, {
        x: () => -distance(),
        ease: "none",
        scrollTrigger: {
          trigger: root.current,
          pin: true,
          scrub: 1,
          start: "top top",
          end: () => "+=" + distance(),
          invalidateOnRefresh: true,
          onUpdate: (self) => {
            const i = Math.min(panels - 1, Math.round(self.progress * (panels - 1)));
            setStage((prev) => (prev !== i ? i : prev));
          },
        },
      });
    }, root);
    return () => ctx.revert();
  }, []);

  if (reduced) {
    return (
      <section className="section" id="evidence">
        <div className="container">
          <p className="eyebrow" style={{ color: "var(--cobalt)" }}>The evidence</p>
          <h2 className="display-lg" style={{ marginBottom: "0.7em" }}>
            What the numbers say.
          </h2>
          <div className="grid grid--2">
            {PANELS.map((p) => (
              <div key={p.key} className={`tile ${p.cls}`}>
                <div className="stat">{p.metric}</div>
                <h3 style={{ margin: "0.2em 0" }}>{p.key}</h3>
                <p style={{ opacity: 0.92 }}>{p.note}</p>
              </div>
            ))}
          </div>
        </div>
      </section>
    );
  }

  return (
    <section id="evidence" ref={root} className="ev-root">
      <div className="ev-nav" aria-hidden="true">
        {PANELS.map((p, i) => (
          <div key={p.key} className={`ev-nav__item ${i === stage ? "is-on" : ""}`}>
            <span className="ev-nav__n">{p.n}</span>
            <span className="ev-nav__k">{p.key}</span>
          </div>
        ))}
        <div className="ev-nav__bar">
          <div className="ev-nav__fill" style={{ width: `${(stage / (PANELS.length - 1)) * 100}%` }} />
        </div>
      </div>

      <div className="ev-track" ref={track}>
        {PANELS.map((p) => (
          <div className={`ev-panel ${p.cls}`} key={p.key}>
            <div className="ev-panel__inner">
              <div className="ev-panel__n">{p.n}</div>
              <div className="ev-panel__metric">{p.metric}</div>
              <h3 className="ev-panel__title">{p.key}</h3>
              <p className="ev-panel__note">{p.note}</p>
            </div>
          </div>
        ))}
      </div>

      <style>{`
        .ev-root { position:relative; height:100vh; overflow:hidden; }
        .ev-nav { position:absolute; top:0; left:0; right:0; z-index:5;
          display:flex; gap:8px; padding:20px clamp(20px,5vw,72px); align-items:center; flex-wrap:wrap; }
        .ev-nav__item { display:flex; align-items:center; gap:6px; opacity:0.4;
          transition:opacity .3s; font-family:var(--font-body); }
        .ev-nav__item.is-on { opacity:1; }
        .ev-nav__n { font-family:var(--font-display); font-weight:900; font-size:0.9rem; }
        .ev-nav__k { font-weight:600; }
        .ev-nav__bar { position:absolute; left:0; bottom:0; height:3px; width:100%; background:rgba(20,17,15,0.12); }
        .ev-nav__fill { height:100%; background:var(--ink); transition:width .4s ease; }

        .ev-track { display:flex; height:100vh; width:500vw; }
        .ev-panel { width:100vw; height:100vh; flex-shrink:0; display:grid; place-items:center;
          padding:0 clamp(20px,6vw,90px); }
        .ev-panel.g--cobalt { background:var(--cobalt); }
        .ev-panel.g--violet { background:var(--violet); }
        .ev-panel.g--tangerine { background:var(--tangerine); }
        .ev-panel.g--marigold { background:var(--marigold); }
        .ev-panel.g--grass { background:var(--grass); }
        .ev-panel.g--sky { background:var(--sky); }
        .ev-panel.g--sky, .ev-panel.g--marigold { color:var(--ink); }
        .ev-panel:not(.g--sky):not(.g--marigold) { color:#fff; }
        .ev-panel__inner { width:100%; max-width:760px; text-align:center; }
        .ev-panel__n { font-family:var(--font-display); font-weight:900; font-size:clamp(1.4rem,3vw,2rem); opacity:0.5; }
        .ev-panel__metric { font-family:var(--font-display); font-weight:900;
          font-size:clamp(3rem,10vw,7rem); line-height:0.95; letter-spacing:-0.03em; margin:0.05em 0; }
        .ev-panel__title { font-size:clamp(1.6rem,4vw,3rem); margin:0.1em 0 0.5em; }
        .ev-panel__note { font-size:clamp(1rem,1.6vw,1.35rem); max-width:46ch; margin:0 auto; opacity:0.95; }
      `}</style>
    </section>
  );
}
