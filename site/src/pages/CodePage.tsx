import { PageHeader } from "../components/PageHeader";
import { Reveal } from "../components/Reveal";

const REPO = "https://github.com/andrewshih0407/ownvoice";

const MODULES = [
  { f: "dysarthria_sim.py", d: "Six perturbations over a pyworld source-filter decomposition, with severity presets matching TORGO/UASpeech conventions. Analysis runs once per utterance and is shared across severities — a 25x speedup over the first version.", cls: "tile--cobalt" },
  { f: "verify_sim.py", d: "Acoustic validation of the simulation. Gates the build on three claims: tone-scale F0 variance falls, spectral flux falls, duration rises. Reports jitter as UNVALIDATED rather than quietly passing it.", cls: "tile--violet" },
  { f: "metrics.py", d: "CER, TER and STER. The tone metrics do not exist in the English dysarthria literature, and STER is the one that isolates tonal failure from segmental failure.", cls: "tile--tangerine" },
  { f: "data.py", d: "Builds paired dysarthric/clean corpora from openly licensed sources. Writes the manifest incrementally so an interrupted build stays usable — learned the hard way.", cls: "tile--grass" },
  { f: "baseline.py", d: "Pre-training reference numbers, with hallucination detection. Whisper loops on degraded audio and produced CER above 1.0 until repetition penalties were added.", cls: "tile--sky" },
  { f: "train_asr.py", d: "Whisper fine-tuning with speaker-disjoint splits and clean audio mixed in to limit catastrophic forgetting.", cls: "tile--marigold" },
  { f: "evaluate.py", d: "The matched before/after comparison. Reuses the training split with the same seed so the holdout is reproduced exactly, and reports per condition.", cls: "tile--pink" },
  { f: "speaker_sim.py", d: "WavLM x-vector calibration underpinning the own-voice claim. Establishes same-speaker vs cross-speaker distributions before any restoration is attempted.", cls: "tile--ink" },
];

const NEGATIVE = [
  { t: "vc.py + eval_vc.py", d: "LLE voice conversion with Chinese-HuBERT features and HiFi-GAN vocoding — the architecture the prior art recommends. It degraded intelligibility (CER 0.4048 → 0.4881) and is kept in the repo as a documented negative result." },
  { t: "ablate_vocoder.py", d: "Isolated the vocoder from the conversion step: a mel→waveform round trip on clean speech costs −0.019 CER, i.e. it is transparent. That cleared the vocoder and pointed at the LLE stage." },
  { t: "sweep_vc.py", d: "Layer and k grid search. It caught a sampling-noise trap: one configuration measured −0.0238 at n=8 and +0.0403 at n=24, a sign flip. The script now refuses to declare a win below a 0.05 margin or under n=50." },
];

export function CodePage() {
  return (
    <>
      <PageHeader
        tone="dark"
        eyebrow="The code"
        title="Every module, including the ones that failed."
        intro="Eleven Python modules covering simulation, validation, metrics, training and evaluation. The negative results ship with the positive ones."
      />

      <section className="section">
        <div className="container">
          <Reveal as="p" className="eyebrow">What works</Reveal>
          <Reveal as="h2" className="display-lg" delay={60} style={{ marginBottom: "0.8em" }}>
            The working pipeline.
          </Reveal>
          <div className="grid grid--2">
            {MODULES.map((m, i) => (
              <Reveal key={m.f} className={`tile ${m.cls}`} delay={i * 45}>
                <code style={{
                  fontFamily: "ui-monospace,Menlo,Consolas,monospace",
                  fontSize: "0.82rem", opacity: 0.8, letterSpacing: "0.02em",
                }}>
                  src/{m.f}
                </code>
                <p style={{ marginTop: "0.6em", opacity: 0.94 }}>{m.d}</p>
              </Reveal>
            ))}
          </div>
        </div>
      </section>

      <section className="section" style={{ background: "#0b0a10", color: "var(--cream)" }}>
        <div className="container">
          <Reveal as="p" className="eyebrow" style={{ color: "var(--tangerine)" }}>What did not</Reveal>
          <Reveal as="h2" className="display-lg" delay={60} style={{ marginBottom: "0.6em" }}>
            Negative results, kept in the repo.
          </Reveal>
          <Reveal as="p" className="lead" delay={100} style={{ color: "rgba(244,239,230,0.82)", maxWidth: "64ch", marginBottom: "1.4em" }}>
            The voice-conversion route was the architecture the literature
            recommends. We built it, measured it, and it lost to leaving the
            audio alone. Deleting that would make the project look better and be
            worth less.
          </Reveal>
          <div className="grid grid--3">
            {NEGATIVE.map((n, i) => (
              <Reveal key={n.t} className="tile tile--ink" delay={i * 70}
                style={{ boxShadow: "inset 0 0 0 1px rgba(255,255,255,0.14)" }}>
                <h3 style={{ fontSize: "1.2rem" }}>{n.t}</h3>
                <p style={{ color: "rgba(244,239,230,0.8)", marginTop: "0.4em" }}>{n.d}</p>
              </Reveal>
            ))}
          </div>
        </div>
      </section>

      <section className="section">
        <div className="container">
          <Reveal as="p" className="eyebrow">Stack</Reveal>
          <Reveal as="h2" className="display-lg" delay={60} style={{ marginBottom: "0.6em" }}>
            Open models, open data.
          </Reveal>
          <Reveal as="p" className="lead" delay={100} style={{ maxWidth: "62ch", marginBottom: "1.4em" }}>
            PyTorch 2.11 + CUDA 12.8, transformers 5.x, whisper-small fine-tuned
            on a single RTX 5060. Content features from Chinese-HuBERT (MIT),
            vocoding via SpeechT5 HiFi-GAN (MIT), speaker verification via WavLM
            (MIT). Nothing here is behind an API key.
          </Reveal>
          <Reveal className="code-links" delay={140}>
            <a className="btn btn--ghost" href={REPO} target="_blank" rel="noreferrer">
              Repository ↗
            </a>
          </Reveal>
        </div>
      </section>

      <style>{`.code-links{display:flex;flex-wrap:wrap;gap:12px}`}</style>
    </>
  );
}
