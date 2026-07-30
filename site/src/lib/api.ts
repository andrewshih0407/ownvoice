// Backend base URL. Point this at the deployed FastAPI (Hugging Face Space)
// via a .env file: VITE_API_BASE=https://<your-space>.hf.space
// In production the site is served from the same origin as the API (one HF
// Space), so VITE_API_BASE is "" and requests go to relative paths.
// `??` (not `||`) keeps the empty string instead of falling back to localhost.
export const API_BASE: string =
  (import.meta as any).env?.VITE_API_BASE ?? "http://localhost:7860";

export interface ToneScores {
  cer: number;
  ster: number;
  intelligibility_pct: number;
}

export interface TranscribeResult {
  /** Transcript from the dysarthria-adapted model. */
  transcript: string;
  /** Transcript from stock Whisper, for side-by-side comparison. */
  baseline_transcript?: string;
  /** Scores, only present when a reference transcript was supplied. */
  scores?: ToneScores;
  baseline_scores?: ToneScores;
  /** Per-syllable tone comparison, when available. */
  tone_diff?: {
    syllable: string;
    ref_tone: string;
    hyp_tone: string;
    ok: boolean;
  }[];
}

export async function checkHealth(): Promise<any> {
  const res = await fetch(`${API_BASE}/health`, { method: "GET" });
  if (!res.ok) throw new Error(`Health check failed: ${res.status}`);
  return res.json();
}

/** Send an audio clip to the fine-tuned ASR. `reference` enables scoring. */
export async function transcribe(
  file: File | Blob,
  reference?: string
): Promise<TranscribeResult> {
  const fd = new FormData();
  fd.append("file", file, (file as File).name || "clip.wav");
  if (reference) fd.append("reference", reference);
  const res = await fetch(`${API_BASE}/transcribe`, {
    method: "POST",
    body: fd,
  });
  if (!res.ok) {
    const detail = await res.text().catch(() => "");
    throw new Error(`Transcription failed (${res.status}): ${detail}`);
  }
  return res.json();
}

/**
 * Apply the dysarthria simulation to a clean clip, so a visitor can HEAR the
 * condition the model is built for. Returns audio bytes.
 */
export async function simulate(
  file: File | Blob,
  severity: "mild" | "moderate" | "severe"
): Promise<Blob> {
  const fd = new FormData();
  fd.append("file", file, (file as File).name || "clip.wav");
  fd.append("severity", severity);
  const res = await fetch(`${API_BASE}/simulate`, { method: "POST", body: fd });
  if (!res.ok) {
    const detail = await res.text().catch(() => "");
    throw new Error(`Simulation failed (${res.status}): ${detail}`);
  }
  return res.blob();
}
