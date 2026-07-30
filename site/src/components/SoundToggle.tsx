import { useEffect, useRef, useState } from "react";

// Ambient sound toggle (equalizer button). Browsers block autoplay, so audio
// only starts after a user gesture — the first click acts as the gate. Uses the
// Web Audio API to synthesize a soft evolving pad (no asset files).
export function SoundToggle() {
  const [on, setOn] = useState(false);
  const ctxRef = useRef<AudioContext | null>(null);
  const nodesRef = useRef<any>(null);

  const start = () => {
    const AC =
      (window as any).AudioContext || (window as any).webkitAudioContext;
    const ctx: AudioContext = new AC();
    const master = ctx.createGain();
    master.gain.value = 0.0;
    master.connect(ctx.destination);

    // Two detuned oscillators through a slow lowpass = soft ambient pad.
    const filter = ctx.createBiquadFilter();
    filter.type = "lowpass";
    filter.frequency.value = 520;
    filter.connect(master);

    const freqs = [110, 164.81, 220];
    const oscs = freqs.map((f) => {
      const o = ctx.createOscillator();
      o.type = "sine";
      o.frequency.value = f;
      const g = ctx.createGain();
      g.gain.value = 0.12;
      o.connect(g);
      g.connect(filter);
      o.start();
      return o;
    });

    // Gentle LFO on the filter for slow movement.
    const lfo = ctx.createOscillator();
    lfo.frequency.value = 0.06;
    const lfoGain = ctx.createGain();
    lfoGain.gain.value = 220;
    lfo.connect(lfoGain);
    lfoGain.connect(filter.frequency);
    lfo.start();

    master.gain.linearRampToValueAtTime(0.16, ctx.currentTime + 1.4);
    ctxRef.current = ctx;
    nodesRef.current = { master, oscs, lfo };
  };

  const stop = () => {
    const ctx = ctxRef.current;
    const nodes = nodesRef.current;
    if (!ctx || !nodes) return;
    nodes.master.gain.linearRampToValueAtTime(0.0001, ctx.currentTime + 0.5);
    setTimeout(() => {
      try {
        nodes.oscs.forEach((o: OscillatorNode) => o.stop());
        nodes.lfo.stop();
        ctx.close();
      } catch (e) {
        /* already closed */
      }
      ctxRef.current = null;
      nodesRef.current = null;
    }, 600);
  };

  const toggle = () => {
    if (on) stop();
    else start();
    setOn((v) => !v);
  };

  useEffect(() => () => stop(), []);

  return (
    <button
      className="sound-toggle"
      onClick={toggle}
      aria-pressed={on}
      aria-label={on ? "Mute ambient sound" : "Enable ambient sound"}
      title={on ? "Sound on" : "Sound off"}
    >
      <span className={`eq ${on ? "eq--on" : ""}`} aria-hidden="true">
        <i></i>
        <i></i>
        <i></i>
        <i></i>
      </span>
      <style>{`
        .sound-toggle {
          position: fixed; left: 24px; bottom: 24px; z-index: var(--z-nav);
          width: 56px; height: 56px; border-radius: 999px; border: none;
          background: rgba(20,17,15,0.9); display: grid; place-items: center;
          box-shadow: 0 8px 30px rgba(0,0,0,0.18);
        }
        .eq { display: flex; align-items: flex-end; gap: 3px; height: 20px; }
        .eq i {
          width: 3px; height: 6px; background: var(--cream); border-radius: 2px;
        }
        .eq--on i { animation: eqbar 900ms ease-in-out infinite; }
        .eq--on i:nth-child(1){ animation-delay: 0ms; }
        .eq--on i:nth-child(2){ animation-delay: 150ms; }
        .eq--on i:nth-child(3){ animation-delay: 300ms; }
        .eq--on i:nth-child(4){ animation-delay: 450ms; }
        @keyframes eqbar {
          0%,100% { height: 5px; } 50% { height: 18px; }
        }
        @media (prefers-reduced-motion: reduce) {
          .eq--on i { animation: none; height: 12px; }
        }
      `}</style>
    </button>
  );
}
