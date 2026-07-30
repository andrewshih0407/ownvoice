import { PageHeader } from "../components/PageHeader";
import { Reveal } from "../components/Reveal";

const DATA = [
  { t: "Common Voice zh-TW", d: "CC0. Taiwan-accented Mandarin — chosen deliberately, because the Mandarin dysarthria corpora that exist are PRC-recorded and accent mismatch degrades conversion.", cls: "tile--grass" },
  { t: "AISHELL-3", d: "Apache-2.0. 85 hours, 218 speakers, studio quality. High per-speaker volume, which matters for the voice-cloning side.", cls: "tile--sky" },
  { t: "EasyCall", d: "CC-BY-NC-2.0. 21,386 real dysarthric utterances with clinical severity labels. Italian, so it cannot test tone — but it can test whether the approach works on authentic pathology.", cls: "tile--marigold" },
];

const RESTRICTED = [
  { t: "MDSC / AISHELL-6B", d: "Mandarin, 17 h, 21 dysarthric speakers, with intelligibility ratings. The corpus we actually need.", },
  { t: "CDSD", d: "Mandarin, 133 h, 44 speakers. Largest Chinese dysarthria corpus; signed licence via the Institute of Psychology, CAS.", },
  { t: "CUDYS", d: "Cantonese, 27 impaired speakers, CUHK. Cantonese is tonal with six tones — the best available test of the tone hypothesis on real patient speech.", },
  { t: "TORGO / UASpeech", d: "English, LDC and UIUC licences. Useful for architecture work and the ALS/CP expansion population.", },
];

const MATCHED = [
  { cond: "clean", base: "0.1076", tuned: "0.1155", delta: "+0.0078", bad: true },
  { cond: "mild", base: "0.1605", tuned: "0.1370", delta: "−0.0235", bad: false },
  { cond: "moderate", base: "0.2074", tuned: "0.1311", delta: "−0.0763", bad: false },
  { cond: "severe", base: "0.2877", tuned: "0.1683", delta: "−0.1194", bad: false },
  { cond: "overall", base: "0.1908", tuned: "0.1380", delta: "−0.0528", bad: false },
];

export function Method() {
  return (
    <>
      <PageHeader
        tone="dark"
        eyebrow="The research"
        title="How every number on this site was produced."
        intro="Simulation validated acoustically, speaker-disjoint splits, a matched before/after comparison, and the results that did not go our way."
      />

      <section className="section">
        <div className="container">
          <Reveal as="p" className="eyebrow">Metrics</Reveal>
          <Reveal as="h2" className="display-lg" delay={60} style={{ marginBottom: "0.6em" }}>
            Why not word error rate.
          </Reveal>
          <Reveal as="p" className="lead" delay={100} style={{ maxWidth: "64ch", marginBottom: "1.4em" }}>
            Written Chinese has no word delimiters, so WER depends entirely on an
            arbitrary segmenter and is not comparable across studies. We report
            character error rate — and alongside it, two tone metrics that do not
            appear in the English dysarthria literature.
          </Reveal>
          <div className="grid grid--3">
            <Reveal className="tile tile--cobalt">
              <h3>CER</h3>
              <p style={{ marginTop: "0.4em" }}>Character error rate. The primary intelligibility number.</p>
            </Reveal>
            <Reveal className="tile tile--violet" delay={70}>
              <h3>TER</h3>
              <p style={{ marginTop: "0.4em" }}>Tone error rate over the whole pinyin tone sequence. Inherits every character error, so it cannot isolate tone on its own.</p>
            </Reveal>
            <Reveal className="tile tile--tangerine" delay={140}>
              <h3>STER</h3>
              <p style={{ marginTop: "0.4em" }}>Tone errors counted <em>only</em> on syllables whose initial and final were already correct. This is the one that isolates tonal failure — and the metric the project turns on.</p>
            </Reveal>
          </div>
        </div>
      </section>

      <section className="section" style={{ background: "#0b0a10", color: "var(--cream)" }}>
        <div className="container">
          <Reveal as="p" className="eyebrow" style={{ color: "var(--sky)" }}>The matched comparison</Reveal>
          <Reveal as="h2" className="display-lg" delay={60} style={{ marginBottom: "0.6em" }}>
            Both models, one test set.
          </Reveal>
          <Reveal as="p" className="lead" delay={100} style={{ color: "rgba(244,239,230,0.82)", maxWidth: "64ch", marginBottom: "1.4em" }}>
            An earlier version of this table compared two <em>different</em> test
            sets, which cannot support an improvement claim however good it
            looks. It was rebuilt so baseline and fine-tuned models are scored on
            identical held-out speakers, broken out per condition.
          </Reveal>

          <Reveal className="mtable-wrap">
            <table className="mtable">
              <thead>
                <tr>
                  <th>Condition</th>
                  <th>CER base</th>
                  <th>CER tuned</th>
                  <th>Δ</th>
                </tr>
              </thead>
              <tbody>
                {MATCHED.map((r) => (
                  <tr key={r.cond} className={r.cond === "overall" ? "is-total" : ""}>
                    <td>{r.cond}</td>
                    <td>{r.base}</td>
                    <td>{r.tuned}</td>
                    <td className={r.bad ? "is-bad" : "is-good"}>{r.delta}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Reveal>

          <Reveal as="p" delay={80} style={{ color: "rgba(244,239,230,0.75)", marginTop: "1.2em", maxWidth: "64ch" }}>
            Clean speech regressed slightly even though clean audio was mixed
            into training specifically to prevent it — the mitigation was partial,
            not sufficient. We report it rather than dropping the row.
          </Reveal>
        </div>
      </section>

      <section className="section">
        <div className="container">
          <Reveal as="p" className="eyebrow">Data</Reveal>
          <Reveal as="h2" className="display-lg" delay={60} style={{ marginBottom: "0.6em" }}>
            Openly licensed, on purpose.
          </Reveal>
          <div className="grid grid--3">
            {DATA.map((d, i) => (
              <Reveal key={d.t} className={`tile ${d.cls}`} delay={i * 60}>
                <h3>{d.t}</h3>
                <p style={{ marginTop: "0.4em", opacity: 0.94 }}>{d.d}</p>
              </Reveal>
            ))}
          </div>

          <Reveal as="h3" delay={60} style={{ margin: "2em 0 0.6em", fontSize: "clamp(1.4rem,3vw,2rem)" }}>
            Requires a signed licence
          </Reveal>
          <div className="grid grid--2">
            {RESTRICTED.map((d, i) => (
              <Reveal key={d.t} className="tile tile--ink" delay={i * 50}>
                <h3 style={{ fontSize: "1.3rem" }}>{d.t}</h3>
                <p style={{ color: "rgba(244,239,230,0.8)", marginTop: "0.3em" }}>{d.d}</p>
              </Reveal>
            ))}
          </div>

          <Reveal className="tile tile--tangerine" delay={120} style={{ marginTop: "18px" }}>
            <h3>What we would not use</h3>
            <p style={{ marginTop: "0.4em" }}>
              Unlicensed re-uploads of TORGO and UASpeech circulate freely on
              dataset hubs. They are restricted patient medical data
              redistributed without authorisation. Publicly accessible is not
              publicly licensed — and improper data acquisition is an explicit
              disqualification criterion in the competition rules.
            </p>
          </Reveal>
        </div>
      </section>

      <section className="section" style={{ background: "#0b0a10", color: "var(--cream)" }}>
        <div className="container">
          <Reveal as="p" className="eyebrow" style={{ color: "var(--tangerine)" }}>Prior art</Reveal>
          <Reveal as="h2" className="display-lg" delay={60} style={{ marginBottom: "0.6em" }}>
            What is already published.
          </Reveal>
          <Reveal as="p" className="lead" delay={100} style={{ color: "rgba(244,239,230,0.82)", maxWidth: "64ch" }}>
            Academia Sinica, with Chi Mei Hospital, has published two-stage voice
            conversion for dysarthric speech reconstruction <em>with speaker
            identity preservation</em>. Restoring speech in a patient's own voice
            is therefore not a novel claim, and we do not make one.
          </Reveal>
          <Reveal as="p" className="lead" delay={140} style={{ color: "rgba(244,239,230,0.82)", maxWidth: "64ch", marginTop: "1em" }}>
            What their paper does not contain, anywhere in its full text, is the
            word <strong>tone</strong> — zero occurrences, against 23 mentions of
            CER, on a Mandarin corpus. That absence is the space this project
            occupies: tone-aware restoration for tonal languages, and a metric
            that makes the failure visible.
          </Reveal>
        </div>
      </section>

      <style>{`
        .mtable-wrap { overflow-x:auto; }
        .mtable { width:100%; border-collapse:collapse; font-variant-numeric:tabular-nums;
          min-width:520px; }
        .mtable th, .mtable td { text-align:left; padding:12px 16px;
          border-bottom:1px solid rgba(255,255,255,0.12); }
        .mtable th { font-family:var(--font-body); font-size:0.78rem; text-transform:uppercase;
          letter-spacing:0.12em; color:rgba(244,239,230,0.6); font-weight:700; }
        .mtable td { font-size:1rem; }
        .mtable tr.is-total td { font-weight:700; border-top:2px solid rgba(255,255,255,0.3);
          border-bottom:none; }
        .mtable .is-good { color:#7ee0a0; }
        .mtable .is-bad { color:#ff9d6e; }
      `}</style>
    </>
  );
}
