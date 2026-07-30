import { useRef, useMemo } from "react";
import { useFrame, useThree } from "@react-three/fiber";
import * as THREE from "three";

// Fullscreen animated iridescent gradient rendered as a fragment shader, tinted
// to the acrylic palette. Cheap: one plane.
const vertex = /* glsl */ `
  varying vec2 vUv;
  void main() {
    vUv = uv;
    gl_Position = vec4(position, 1.0);
  }
`;

const fragment = /* glsl */ `
  precision highp float;
  varying vec2 vUv;
  uniform float uTime;
  uniform vec2 uRes;

  // palette (acrylic pastels)
  vec3 cream = vec3(0.956, 0.937, 0.902);
  vec3 cobalt = vec3(0.243, 0.419, 0.878);
  vec3 violet = vec3(0.541, 0.361, 0.965);
  vec3 pink   = vec3(0.953, 0.541, 0.690);
  vec3 sky    = vec3(0.384, 0.776, 0.910);
  vec3 marigold = vec3(0.956, 0.690, 0.141);

  float noise(vec2 p) {
    return sin(p.x) * cos(p.y);
  }

  void main() {
    vec2 uv = vUv;
    float t = uTime * 0.06;

    float n1 = noise(uv * 3.0 + vec2(t, t * 0.7));
    float n2 = noise(uv * 5.0 - vec2(t * 0.5, t));
    float n3 = noise(uv * 2.0 + vec2(-t, t * 0.3));
    float m = (n1 + n2 + n3) / 3.0;

    // build a soft, washy mix biased toward cream so dark text stays readable
    vec3 col = mix(cream, sky, smoothstep(-0.6, 0.6, n1) * 0.5);
    col = mix(col, violet, smoothstep(-0.4, 0.8, n2) * 0.35);
    col = mix(col, pink, smoothstep(0.0, 1.0, n3) * 0.28);
    col = mix(col, cobalt, smoothstep(0.3, 1.0, m) * 0.18);
    col = mix(col, marigold, smoothstep(0.6, 1.0, n1 * n3) * 0.10);

    // vignette toward cream at edges
    float d = distance(uv, vec2(0.5));
    col = mix(col, cream, smoothstep(0.35, 0.95, d) * 0.55);

    gl_FragColor = vec4(col, 1.0);
  }
`;

export function GradientPlane() {
  const mat = useRef<THREE.ShaderMaterial>(null);
  const { size } = useThree();

  const uniforms = useMemo(
    () => ({
      uTime: { value: 0 },
      uRes: { value: new THREE.Vector2(size.width, size.height) },
    }),
    []
  );

  useFrame((_, delta) => {
    if (mat.current) {
      mat.current.uniforms.uTime.value += delta;
    }
  });

  return (
    <mesh>
      <planeGeometry args={[2, 2]} />
      <shaderMaterial
        ref={mat}
        vertexShader={vertex}
        fragmentShader={fragment}
        uniforms={uniforms}
        depthWrite={false}
      />
    </mesh>
  );
}
