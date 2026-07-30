import { useRef, useMemo } from "react";
import { useFrame } from "@react-three/fiber";
import { Line } from "@react-three/drei";
import * as THREE from "three";

// The four Mandarin tone contours — the actual thing this project is about.
// Tone is an F0 trajectory over a syllable, and it carries lexical meaning:
// mā (flat), má (rising), mǎ (dip), mà (falling) are four different words.
//
// `flatten` collapses each contour toward its mean, which is exactly what
// dysarthric prosodic flattening does. At flatten=1 all four tones become the
// same horizontal line — four different words rendered indistinguishable. The
// hero animates this back and forth so the problem is visible before a single
// word of copy is read.

const TONES: { name: string; f: (t: number) => number; color: string }[] = [
  // t in [0,1] -> normalized pitch in [-1,1]
  { name: "1 high level", f: () => 0.75, color: "#3e6be0" },
  { name: "2 rising", f: (t) => -0.45 + 1.25 * t * t, color: "#3fa85b" },
  {
    name: "3 dipping",
    f: (t) => 0.1 - 1.5 * Math.sin(Math.PI * Math.min(t * 1.15, 1)) * (1 - t * 0.35),
    color: "#f4b024",
  },
  { name: "4 falling", f: (t) => 0.85 - 1.7 * t, color: "#ee6c34" },
];

const SEGMENTS = 72;

export function ToneContour({
  flatten = 0,
  spacing = 0.62,
  width = 1.6,
  animate = true,
}: {
  flatten?: number;
  spacing?: number;
  width?: number;
  animate?: boolean;
}) {
  const group = useRef<THREE.Group>(null);
  const lines = useRef<(any | null)[]>([]);

  // Base (unflattened) point sets, one per tone.
  const base = useMemo(
    () =>
      TONES.map((tone) => {
        const pts: [number, number, number][] = [];
        for (let i = 0; i <= SEGMENTS; i++) {
          const t = i / SEGMENTS;
          pts.push([(t - 0.5) * width, tone.f(t) * 0.42, 0]);
        }
        return pts;
      }),
    [width]
  );

  useFrame((state) => {
    if (!group.current) return;
    // Breathe the whole stack gently.
    const s = 1 + Math.sin(state.clock.elapsedTime * 0.6) * 0.015;
    group.current.scale.set(s, s, s);

    if (!animate) return;
    // Oscillate flattening: 0 (healthy) -> ~0.92 (severe) and back. Slow, so it
    // reads as a demonstration rather than a decoration.
    const k =
      flatten ||
      (Math.sin(state.clock.elapsedTime * 0.28) * 0.5 + 0.5) * 0.92;

    base.forEach((pts, ti) => {
      const line = lines.current[ti];
      if (!line?.geometry) return;
      const mean =
        pts.reduce((acc, p) => acc + p[1], 0) / pts.length;
      const flat = pts.map(
        ([x, y, z]) => new THREE.Vector3(x, mean + (y - mean) * (1 - k), z)
      );
      line.geometry.setFromPoints(flat);
    });
  });

  return (
    <group ref={group}>
      {TONES.map((tone, i) => (
        <group key={tone.name} position={[0, (1.5 - i) * spacing * 0.42, 0]}>
          <Line
            ref={(el: any) => (lines.current[i] = el)}
            points={base[i]}
            color={tone.color}
            lineWidth={2.6}
            transparent
            opacity={0.92}
          />
          <Line
            points={base[i]}
            color={tone.color}
            lineWidth={8}
            transparent
            opacity={0.1}
          />
        </group>
      ))}
    </group>
  );
}
