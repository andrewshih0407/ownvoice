import { useEffect, useRef, useState } from "react";

// Ring cursor that trails the pointer and swells over interactive elements.
// Hidden on touch + reduced-motion.
export function CustomCursor() {
  const dot = useRef<HTMLDivElement>(null);
  const ring = useRef<HTMLDivElement>(null);
  const [enabled, setEnabled] = useState(false);

  useEffect(() => {
    const fine = window.matchMedia("(pointer: fine)").matches;
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (!fine || reduced) return;
    setEnabled(true);

    let rx = window.innerWidth / 2;
    let ry = window.innerHeight / 2;
    let mx = rx;
    let my = ry;
    let raf = 0;

    const move = (e: MouseEvent) => {
      mx = e.clientX;
      my = e.clientY;
      if (dot.current) {
        dot.current.style.transform = `translate(${mx}px, ${my}px)`;
      }
      const t = e.target as HTMLElement;
      const interactive = t.closest(
        "a, button, input, label, select, [data-cursor='hover']"
      );
      ring.current?.classList.toggle("cursor-ring--hover", !!interactive);
    };

    const loop = () => {
      rx += (mx - rx) * 0.18;
      ry += (my - ry) * 0.18;
      if (ring.current) {
        ring.current.style.transform = `translate(${rx}px, ${ry}px)`;
      }
      raf = requestAnimationFrame(loop);
    };

    window.addEventListener("mousemove", move);
    raf = requestAnimationFrame(loop);
    return () => {
      window.removeEventListener("mousemove", move);
      cancelAnimationFrame(raf);
    };
  }, []);

  if (!enabled) return null;

  return (
    <>
      <div ref={dot} className="cursor-dot" aria-hidden="true" />
      <div ref={ring} className="cursor-ring" aria-hidden="true" />
      <style>{`
        /* mix-blend-mode: difference keeps the cursor visible on ANY background
           (dark pipeline sections, light hero, colored tiles) by inverting. */
        .cursor-dot, .cursor-ring {
          position: fixed; top: 0; left: 0; pointer-events: none;
          z-index: var(--z-cursor); border-radius: 999px;
          margin-left: -4px; margin-top: -4px;
          mix-blend-mode: difference;
        }
        .cursor-dot { width: 8px; height: 8px; background: #fff; }
        .cursor-ring {
          width: 40px; height: 40px; margin-left: -20px; margin-top: -20px;
          border: 1.5px solid #fff; opacity: 0.8;
          transition: width .25s ease, height .25s ease, background .25s ease,
            opacity .25s ease, margin .25s ease;
        }
        .cursor-ring--hover {
          width: 68px; height: 68px; margin-left: -34px; margin-top: -34px;
          background: rgba(255,255,255,0.15); border-color: #fff;
          opacity: 1;
        }
      `}</style>
    </>
  );
}
