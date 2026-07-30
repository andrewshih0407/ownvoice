import { Reveal } from "../components/Reveal";

const REPO = "https://github.com/";

export function Problem() {
  return (
    <section className="section" id="problem">
      <div className="container">
        <Reveal as="p" className="eyebrow">
          The problem
        </Reveal>
        <Reveal as="h2" className="display-lg" delay={60}>
          Losing speech is common. Losing tone makes it worse.
        </Reveal>
        <Reveal as="p" className="lead" delay={120} style={{ marginTop: "1.2em", maxWidth: "62ch" }}>
          Dysarthria follows stroke, Parkinson's, ALS, cerebral palsy, and
          head-and-neck cancer surgery. In Taiwan it lands hard: oral cancer is
          the fourth most common cancer and fourth leading cause of cancer death
          among men, with incidence roughly ten times the female rate, driven
          overwhelmingly by betel nut. Roughly 49,000 strokes a year add more,
          with dysarthria following about a quarter of them.
        </Reveal>
        <Reveal as="p" className="lead" delay={160} style={{ marginTop: "1em", maxWidth: "62ch" }}>
          As interfaces become voice-first, these speakers are excluded twice —
          once by other people, once by every system that expects clear speech.
          And in Mandarin there is a second failure the English-language
          literature does not address: tone is lexically contrastive, so a
          mistoned syllable is not an accent. It is a different word.
        </Reveal>
      </div>
    </section>
  );
}

export function Science() {
  const stats: {
    figure: string;
    label: string;
    cls: string;
    span?: string;
  }[] = [
    {
      figure: "80.9 → 86.2%",
      label: "intelligibility after fine-tuning, measured on a matched test set with both models scored on identical held-out speakers",
      cls: "tile--cobalt",
      span: "col-span-2",
    },
    { figure: "−27.7%", label: "relative character error rate, 0.1908 → 0.1380", cls: "tile--marigold" },
    { figure: "−41%", label: "on severe dysarthria — the gain scales with severity", cls: "tile--tangerine" },
    { figure: "91", label: "unique speakers, train and test strictly disjoint", cls: "tile--grass" },
    { figure: "−0.004", label: "change in tone error rate — essentially nothing. The gap this project targets", cls: "tile--violet" },
    {
      figure: "Simulated, and we say so",
      label: "every number here comes from perturbation-simulated dysarthria, valid for architecture work and not yet a clinical claim",
      cls: "tile--ink",
      span: "col-span-2",
    },
  ];
  return (
    <section className="section" id="science">
      <div className="container">
        <Reveal as="p" className="eyebrow">
          The results
        </Reveal>
        <Reveal as="h2" className="display-lg" delay={60} style={{ marginBottom: "0.8em" }}>
          Measured on a matched test set — including what did not work.
        </Reveal>
        <div className="grid grid--bento">
          {stats.map((s, i) => (
            <Reveal key={i} className={`tile ${s.cls} ${s.span || ""}`} delay={i * 60}>
              <div className="stat">{s.figure}</div>
              <p style={{ marginTop: "0.5em", opacity: 0.92 }}>{s.label}</p>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  );
}

export function Confidentiality() {
  return (
    <section className="section" id="privacy">
      <div className="container">
        <Reveal as="p" className="eyebrow">Confidentiality</Reveal>
        <Reveal as="h2" className="display-lg" delay={60} style={{ marginBottom: "0.8em" }}>
          Voice is medical data. We treat it that way.
        </Reveal>
        <div className="grid grid--2">
          <Reveal className="tile tile--sky">
            <h3>What actually happens</h3>
            <p style={{ marginTop: "0.5em" }}>
              Audio is processed in memory and discarded immediately after
              inference. No database, no logging of file contents, no
              third-party storage. A banked voice, when that feature exists,
              belongs to the person who banked it and to nobody else.
            </p>
          </Reveal>
          <Reveal className="tile tile--pink" delay={80}>
            <h3>On training data</h3>
            <p style={{ marginTop: "0.5em" }}>
              Every corpus used here is openly licensed — Common Voice zh-TW
              (CC0) and AISHELL-3 (Apache-2.0). We deliberately did not use the
              unlicensed re-uploads of restricted patient corpora circulating on
              dataset hubs, both because it is wrong and because improper data
              acquisition is an explicit disqualification criterion.
            </p>
          </Reveal>
        </div>
      </div>
    </section>
  );
}

export function Limitations() {
  return (
    <section className="section" id="limitations">
      <div className="container">
        <Reveal as="p" className="eyebrow">Limitations</Reveal>
        <Reveal as="h2" className="display-lg" delay={60} style={{ marginBottom: "0.6em" }}>
          What this does not do yet.
        </Reveal>
        <div className="grid grid--3" style={{ marginTop: "1.4em" }}>
          <Reveal className="tile tile--ink">
            <h3>It is simulated</h3>
            <p style={{ color: "rgba(244,239,230,0.82)", marginTop: "0.4em" }}>
              The model trained on perturbations we designed, so part of the
              gain may be learning to invert our own simulation rather than
              learning dysarthria. Real patient speech is the next test.
            </p>
          </Reveal>
          <Reveal className="tile tile--ink" delay={70}>
            <h3>There is no audio output</h3>
            <p style={{ color: "rgba(244,239,230,0.82)", marginTop: "0.4em" }}>
              Voice restoration is not built. A voice-conversion route was
              implemented and <em>degraded</em> intelligibility, so it is
              documented as a negative result rather than shipped.
            </p>
          </Reveal>
          <Reveal className="tile tile--ink" delay={140}>
            <h3>Tone is not solved</h3>
            <p style={{ color: "rgba(244,239,230,0.82)", marginTop: "0.4em" }}>
              We can measure the tonal failure and show fine-tuning does not fix
              it. That is motivating evidence for the approach, not a solution
              to the problem.
            </p>
          </Reveal>
        </div>
        <Reveal as="p" className="lead" delay={180} style={{ maxWidth: "64ch", marginTop: "1.6em" }}>
          One perturbation axis — jitter — failed its own validation and shows no
          graded effect, so we make no claim about modelling voice quality.
          Reporting that is cheaper than having a judge find it.
        </Reveal>
      </div>
    </section>
  );
}

export function Team() {
  return (
    <section className="section" id="team">
      <div className="container">
        <Reveal as="p" className="eyebrow">The team</Reveal>
        <Reveal as="h2" className="display-lg" delay={60} style={{ marginBottom: "0.6em" }}>
          Built for the Presidential Hackathon.
        </Reveal>
        <Reveal as="p" className="lead" delay={100} style={{ maxWidth: "62ch" }}>
          2026 Presidential Hackathon International Track — theme, Digital
          Inclusion in the AI Era. Supervised by the Office of the President,
          organised by the Executive Yuan, implemented by the Ministry of
          Digital Affairs.
          {" "}
          <span className="muted">[team roster to add]</span>
        </Reveal>
      </div>
    </section>
  );
}

export function Footer() {
  return (
    <footer className="section" style={{ paddingBottom: "48px" }}>
      <div className="container">
        <div className="footer__row">
          <div className="footer__brand">OwnVoice</div>
          <a className="btn btn--ghost" href={REPO} target="_blank" rel="noreferrer">
            GitHub ↗
          </a>
        </div>
        <p className="muted" style={{ marginTop: "1em", maxWidth: "58ch" }}>
          Open-source tone-aware speech restoration for Mandarin speakers with
          dysarthria. Research prototype — not a medical device, and not a
          diagnosis.
        </p>
      </div>
      <style>{`
        .footer__row{display:flex;align-items:center;justify-content:space-between;
          border-top:2px solid var(--ink);padding-top:24px;gap:20px;flex-wrap:wrap}
        .footer__brand{font-family:var(--font-display);font-weight:900;
          font-size:clamp(2rem,6vw,4rem);letter-spacing:-0.03em}
      `}</style>
    </footer>
  );
}
