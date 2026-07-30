import { Canvas } from "@react-three/fiber";
import { Suspense } from "react";
import { GradientPlane } from "../three/GradientPlane";
import { ToneContour } from "../three/ToneContour";

// Hero: WebGL iridescent gradient + the four Mandarin tone contours, which
// slowly flatten and recover — the failure this project measures, shown before
// it is described.
export function Hero() {
  return (
    <header className="hero">
      <div className="hero__canvas" aria-hidden="true">
        <Canvas
          camera={{ position: [0, 0, 3], fov: 50 }}
          gl={{ antialias: true, alpha: false }}
          dpr={[1, 1.8]}
        >
          <Suspense fallback={null}>
            <GradientPlane />
            <group position={[1.15, -0.05, 0]}>
              <ToneContour />
            </group>
          </Suspense>
        </Canvas>
      </div>

      <div className="hero__content container">
        <p className="eyebrow reveal is-in">
          Presidential Hackathon 2026 · Digital Inclusion in the AI Era
        </p>
        <h1 className="hero__title display-xl">
          When speech fails, <em>tone</em> fails first.
          <br />
          And in Mandarin, tone <em>is</em> the word.
        </h1>
        <p className="lead hero__lead">
          An open-source speech pipeline for Mandarin speakers with dysarthria —
          the first to measure tone as a failure mode of its own.
        </p>
        <div className="hero__cta">
          <a className="btn" href="#demo">
            Hear the problem
          </a>
          <a className="btn btn--ghost" href="#code">
            View the code
          </a>
        </div>
      </div>

      <div className="hero__scroll" aria-hidden="true">
        <span>Scroll</span>
        <span className="hero__scroll-line" />
      </div>

      <style>{`
        .hero {
          position: relative; min-height: 100vh; display: flex;
          align-items: flex-start; overflow: hidden;
        }
        .hero__canvas { position: absolute; inset: 0; z-index: 0; }
        .hero__content { position: relative; z-index: 2;
          padding: clamp(118px, 19vh, 200px) clamp(20px,5vw,72px) 90px; }
        .hero__title { margin: 0.3em 0 0.5em; max-width: 17ch; }
        .hero__title em {
          font-family: var(--font-display); font-style: italic; font-weight: 800;
          letter-spacing: -0.02em;
        }
        .hero__lead { margin-bottom: 2em; }
        .hero__cta { display: flex; gap: 14px; flex-wrap: wrap; }
        .hero__scroll {
          position: absolute; bottom: 28px; left: 50%; transform: translateX(-50%);
          z-index: 2; display: flex; flex-direction: column; align-items: center;
          gap: 8px; font-size: 0.75rem; letter-spacing: 0.2em; text-transform: uppercase;
          color: var(--ink-soft);
        }
        .hero__scroll-line {
          width: 1px; height: 42px;
          background: linear-gradient(var(--ink), transparent);
          animation: scrollpulse 1.8s ease-in-out infinite;
        }
        @keyframes scrollpulse { 0%,100%{opacity:.3} 50%{opacity:1} }
        @media (prefers-reduced-motion: reduce) {
          .hero__scroll-line { animation: none; }
        }
      `}</style>
    </header>
  );
}
