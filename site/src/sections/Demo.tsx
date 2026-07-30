import { useEffect, useRef, useState } from "react";
import { API_BASE, checkHealth, simulate, transcribe } from "../lib/api";
import { Reveal } from "../components/Reveal";

// The live demo does two things the model can actually do today:
//
//   1. SIMULATE — degrade a clean clip so a visitor HEARS the condition.
//   2. TRANSCRIBE — run the fine-tuned ASR and show it beside stock Whisper.
//
// It deliberately does NOT offer voice restoration. Stage 2 is unbuilt and the
// voice-conversion attempt degraded intelligibility, so promising restored
// audio here would be a claim the system cannot honour.

const SEVERITIES = ["mild", "moderate", "severe"] as const;
type Severity = (typeof SEVERITIES)[number];

// Shipped so the demo works for a visitor with no Mandarin audio to hand — which
// is most of them. CC0, from Common Voice zh-TW.
//
// Chosen from the HELD-OUT speakers, deliberately. Picking from the head of the
// manifest gave clips where the fine-tuned model scored CER 0.000 nine times
// out of ten — but those were training clips, and this model overfits hard, so
// the demo would have been showing memorisation rather than generalisation.
//
// On this unseen clip at severe: stock Whisper renders 溝通 (gōu tōng,
// "communicate") as 構同 (gòu tóng) — tone errors on BOTH syllables, which is
// precisely the failure this project measures. Our model recovers the word but
// still misses 良性 -> 人性, so the demo shows a real improvement rather than a
// perfect one. CER 0.444 -> 0.111.
const SAMPLE = {
  url: "/samples/sample-clean.wav",
  text: "與地主做良性的溝通",
  gloss: "“to communicate constructively with the landowner”",
};

export function Demo() {
  const [health, setHealth] = useState<"loading" | "ok" | "down">("loading");

  const [severity, setSeverity] = useState<Severity>("severe");
  const [reference, setReference] = useState("");
  const [busy, setBusy] = useState<null | "simulate" | "transcribe">(null);
  const [err, setErr] = useState<string | null>(null);
  const [simUrl, setSimUrl] = useState<string | null>(null);
  const [result, setResult] = useState<any>(null);
  const [fileName, setFileName] = useState<string | null>(null);
  // Which audio /transcribe should receive. Once a simulation exists this
  // defaults to it: transcribing the clean original would demonstrate nothing,
  // since the whole claim is about degraded speech.
  const [useSimulated, setUseSimulated] = useState(true);
  const fileRef = useRef<File | null>(null);
  const simFileRef = useRef<File | null>(null);

  useEffect(() => {
    checkHealth()
      .then(() => setHealth("ok"))
      .catch(() => setHealth("down"));
  }, []);

  // Revoke the object URL when it is replaced or the component unmounts.
  useEffect(() => {
    return () => {
      if (simUrl) URL.revokeObjectURL(simUrl);
    };
  }, [simUrl]);

  const clearOutputs = () => {
    setResult(null);
    setErr(null);
    simFileRef.current = null;
    if (simUrl) {
      URL.revokeObjectURL(simUrl);
      setSimUrl(null);
    }
  };

  const onFile = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (!f) return;
    fileRef.current = f;
    setFileName(f.name);
    clearOutputs();
  };

  const loadSample = async () => {
    setErr(null);
    try {
      const res = await fetch(SAMPLE.url);
      if (!res.ok) throw new Error(`Sample not found (${res.status})`);
      const blob = await res.blob();
      fileRef.current = new File([blob], "sample-clean.wav", { type: "audio/wav" });
      setFileName("sample-clean.wav");
      setReference(SAMPLE.text);
      clearOutputs();
    } catch (e: any) {
      setErr(e.message || "Could not load the sample");
    }
  };

  const runSimulate = async () => {
    if (!fileRef.current) return setErr("Choose an audio file first.");
    setBusy("simulate");
    setErr(null);
    try {
      const blob = await simulate(fileRef.current, severity);
      if (simUrl) URL.revokeObjectURL(simUrl);
      setSimUrl(URL.createObjectURL(blob));
      simFileRef.current = new File([blob], `simulated_${severity}.wav`, {
        type: "audio/wav",
      });
      setUseSimulated(true);
      setResult(null); // any previous transcript was of different audio
    } catch (e: any) {
      setErr(e.message || "Simulation failed");
    } finally {
      setBusy(null);
    }
  };

  const runTranscribe = async () => {
    const sim = simFileRef.current;
    const target = useSimulated && sim ? sim : fileRef.current;
    if (!target) return setErr("Choose an audio file first.");
    setBusy("transcribe");
    setErr(null);
    try {
      const r = await transcribe(target, reference || undefined);
      setResult({ ...r, _source: target === sim ? "simulated" : "original" });
    } catch (e: any) {
      setErr(e.message || "Transcription failed");
    } finally {
      setBusy(null);
    }
  };

  return (
    <section className="section" id="demo">
      <div className="container">
        <Reveal as="p" className="eyebrow">Try it live</Reveal>
        <Reveal as="h2" className="display-lg" delay={60} style={{ marginBottom: "0.5em" }}>
          Hear the problem. Then read the transcript.
        </Reveal>
        <Reveal as="p" className="lead" delay={90} style={{ maxWidth: "62ch", marginBottom: "0.6em" }}>
          Upload a short clip of clear Mandarin. The simulator degrades it the
          way dysarthria does, so you can hear what the model is up against —
          then the fine-tuned recogniser transcribes it beside stock Whisper.
        </Reveal>

        <Reveal className={`health health--${health}`}>
          <span className="health__dot" />
          {health === "loading" && "Checking model server…"}
          {health === "ok" && "Model server online — ASR ready"}
          {health === "down" && (
            <>
              Model server not reachable at <code>{API_BASE || "same origin"}</code>. It may be
              waking up (free tier sleeps after inactivity) — reload in ~30s.
            </>
          )}
        </Reveal>

        <div className="grid grid--2" style={{ marginTop: "28px", alignItems: "start" }}>
          <Reveal className="tile tile--cobalt demo-card">
            <h3>1 · Hear it</h3>
            <label className="demo-file">
              <input type="file" accept="audio/*" onChange={onFile} />
              <span>{fileName || "Choose a Mandarin audio clip"}</span>
            </label>

            <button className="demo-sample" onClick={loadSample} type="button">
              No clip to hand? Use our sample →
            </button>
            {fileName === "sample-clean.wav" && (
              <p className="demo-sample__note">
                {SAMPLE.text} &nbsp;<span>{SAMPLE.gloss}</span>
              </p>
            )}

            <label className="demo-label" htmlFor="sev">Severity</label>
            <select
              id="sev"
              className="demo-select"
              value={severity}
              onChange={(e) => setSeverity(e.target.value as Severity)}
            >
              {SEVERITIES.map((s) => (
                <option key={s} value={s}>{s}</option>
              ))}
            </select>

            <button className="demo-btn" onClick={runSimulate} disabled={busy !== null}>
              {busy === "simulate" ? "Degrading…" : "Simulate dysarthria"}
            </button>

            {simUrl && (
              <div className="demo-result">
                <div className="demo-result__name">Simulated · {severity}</div>
                <audio controls src={simUrl} style={{ width: "100%" }} />
              </div>
            )}
          </Reveal>

          <Reveal className="tile tile--violet demo-card" delay={80}>
            <h3>2 · Read it</h3>
            <label className="demo-label" htmlFor="ref">
              Reference text (optional — enables scoring)
            </label>
            <input
              id="ref"
              className="demo-select"
              placeholder="就是以武力統一中國"
              value={reference}
              onChange={(e) => setReference(e.target.value)}
            />

            {simFileRef.current && (
              <div className="demo-source">
                <span className="demo-label" style={{ margin: "0 0 6px" }}>
                  Transcribe which audio
                </span>
                <div className="demo-toggle">
                  <button
                    type="button"
                    className={useSimulated ? "is-on" : ""}
                    onClick={() => { setUseSimulated(true); setResult(null); }}
                  >
                    Simulated ({severity})
                  </button>
                  <button
                    type="button"
                    className={!useSimulated ? "is-on" : ""}
                    onClick={() => { setUseSimulated(false); setResult(null); }}
                  >
                    Original
                  </button>
                </div>
              </div>
            )}

            <button className="demo-btn" onClick={runTranscribe} disabled={busy !== null}>
              {busy === "transcribe" ? "Transcribing…" : "Transcribe"}
            </button>

            {result && (
              <div className="demo-result">
                {result._source && (
                  <div className="demo-src-tag">
                    transcribed the {result._source} audio
                  </div>
                )}
                {result.baseline_transcript && (
                  <>
                    <div className="demo-result__name">
                      Stock Whisper
                      {result.baseline_scores && (
                        <em className="demo-cer">
                          CER {result.baseline_scores.cer.toFixed(3)}
                        </em>
                      )}
                    </div>
                    <p className="demo-hyp">{result.baseline_transcript}</p>
                  </>
                )}
                <div className="demo-result__name">
                  OwnVoice (fine-tuned)
                  {result.scores && (
                    <em className="demo-cer demo-cer--ours">
                      CER {result.scores.cer.toFixed(3)}
                    </em>
                  )}
                </div>
                <p className="demo-hyp demo-hyp--ours">{result.transcript}</p>

                {result.scores && (
                  <div className="demo-scores">
                    <div>
                      <span>CER</span>
                      <strong>{result.scores.cer.toFixed(3)}</strong>
                    </div>
                    <div>
                      <span>STER</span>
                      <strong>{result.scores.ster.toFixed(3)}</strong>
                    </div>
                    <div>
                      <span>Intelligible</span>
                      <strong>{result.scores.intelligibility_pct.toFixed(1)}%</strong>
                    </div>
                  </div>
                )}
              </div>
            )}
          </Reveal>
        </div>

        {err && <p className="demo-err">{err}</p>}

        <p className="disclaimer" style={{ marginTop: "28px" }}>
          Audio is processed in memory and discarded immediately after inference —
          never stored, logged, or shared. Research prototype; do not upload real
          patient data. This system outputs <strong>text, not restored speech</strong> —
          voice restoration is not built yet.
        </p>
      </div>

      <style>{`
        .health {
          display:flex;align-items:flex-start;gap:10px;margin-top:6px;
          padding:12px 18px;border-radius:14px;font-size:0.9rem;line-height:1.5;
          background:rgba(20,17,15,0.06);max-width:640px;
        }
        .health code{background:rgba(0,0,0,0.12);padding:1px 6px;border-radius:6px;font-size:0.85em}
        .health__dot{width:10px;height:10px;border-radius:999px;background:var(--marigold);margin-top:6px;flex-shrink:0}
        .health--ok .health__dot{background:var(--grass)}
        .health--down .health__dot{background:var(--tangerine)}

        .demo-card h3{margin-bottom:0.4em}
        .demo-label{display:block;font-size:0.8rem;text-transform:uppercase;
          letter-spacing:0.12em;opacity:0.85;margin:0.9em 0 0.3em}
        .demo-select{
          width:100%;padding:0.7em 0.9em;border-radius:12px;border:none;
          font-family:var(--font-body);font-size:1rem;background:rgba(255,255,255,0.92);
          color:var(--ink);
        }
        .demo-file{
          display:flex;align-items:center;justify-content:center;margin-top:6px;
          padding:1.1em;border-radius:14px;border:2px dashed rgba(255,255,255,0.6);
          cursor:pointer;text-align:center;font-weight:600;overflow:hidden;
        }
        .demo-file input{display:none}
        .demo-sample{
          margin-top:10px;width:100%;padding:0.55em 1em;border:none;border-radius:999px;
          background:rgba(255,255,255,0.18);color:inherit;font-family:var(--font-body);
          font-weight:600;font-size:0.85rem;cursor:pointer;transition:background .2s;
        }
        .demo-sample:hover{background:rgba(255,255,255,0.3)}
        .demo-sample__note{margin-top:8px;font-size:0.9rem;font-weight:600;text-align:center}
        .demo-sample__note span{font-weight:400;opacity:0.8;font-style:italic}
        .demo-source{margin-top:14px}
        .demo-toggle{display:flex;gap:6px;background:rgba(0,0,0,0.16);
          padding:4px;border-radius:999px}
        .demo-toggle button{flex:1;border:none;background:transparent;color:inherit;
          font-family:var(--font-body);font-weight:600;font-size:0.82rem;
          padding:0.5em 0.4em;border-radius:999px;cursor:pointer;transition:background .2s}
        .demo-toggle button.is-on{background:rgba(255,255,255,0.9);color:var(--ink)}
        .demo-src-tag{font-size:0.7rem;text-transform:uppercase;letter-spacing:0.1em;
          opacity:0.75;margin-bottom:6px}
        .demo-cer{margin-left:8px;font-style:normal;font-weight:700;
          font-variant-numeric:tabular-nums;padding:1px 7px;border-radius:999px;
          background:rgba(238,108,52,0.28);letter-spacing:0.02em;text-transform:none}
        .demo-cer--ours{background:rgba(63,168,91,0.32)}
        .demo-btn{
          margin-top:14px;width:100%;padding:0.85em 1.2em;border:none;border-radius:999px;
          background:rgba(255,255,255,0.94);color:var(--ink);font-family:var(--font-body);
          font-weight:600;font-size:0.95rem;cursor:pointer;transition:background .2s,opacity .2s;
        }
        .demo-btn:hover:not(:disabled){background:#fff}
        .demo-btn:disabled{opacity:0.55;cursor:default}
        .demo-err{margin-top:16px;background:rgba(238,108,52,0.18);
          padding:10px 14px;border-radius:10px;font-size:0.85rem;max-width:640px}
        .demo-result{margin-top:16px;background:rgba(255,255,255,0.16);
          padding:14px;border-radius:14px}
        .demo-result__name{font-weight:700;margin:6px 0 4px;font-size:0.78rem;
          text-transform:uppercase;letter-spacing:0.1em;opacity:0.85}
        .demo-hyp{font-size:1.05rem;line-height:1.5;margin:0 0 8px}
        .demo-hyp--ours{font-weight:600}
        .demo-scores{display:flex;gap:18px;flex-wrap:wrap;margin-top:10px;
          padding-top:10px;border-top:1px solid rgba(255,255,255,0.25)}
        .demo-scores div{display:flex;flex-direction:column}
        .demo-scores span{font-size:0.72rem;text-transform:uppercase;letter-spacing:0.1em;opacity:0.8}
        .demo-scores strong{font-family:var(--font-display);font-size:1.3rem;
          font-variant-numeric:tabular-nums}
      `}</style>
    </section>
  );
}
