import { Link } from "react-router-dom";
import { PageHeader } from "../components/PageHeader";
import { Reveal } from "../components/Reveal";
import { scrollToId } from "../lib/scroll";

const WHO = [
  { t: "After head-and-neck surgery", d: "Glossectomy, mandibulectomy or laryngectomy. In Taiwan this is a large group — oral cancer is the 4th most common cancer among men, and the surgery is scheduled, so a voice can be banked beforehand.", cls: "tile--cobalt" },
  { t: "After a stroke", d: "Dysarthria follows roughly a quarter of ischaemic strokes. Onset is sudden, so there is usually no banked recording — the hardest case for voice restoration.", cls: "tile--marigold" },
  { t: "Progressive conditions", d: "Parkinson's, ALS, MSA and PSP degrade speech gradually. Gradual means there is time to bank a voice while it is still clear.", cls: "tile--grass" },
];

const STEPS = [
  { n: "01", t: "Bank the voice", d: "Where there is warning — scheduled surgery, or a progressive diagnosis — record the person while their speech is still clear. This is the step that makes restoration possible later, and it costs one session.", cls: "tile--cobalt" },
  { n: "02", t: "Speak normally", d: "No special task, no sustained vowels, no reading list. Ordinary connected speech into an ordinary microphone.", cls: "tile--sky" },
  { n: "03", t: "Recognise", d: "The dysarthria-adapted model transcribes it. On simulated severe dysarthria this recovers 41% of the character errors stock recognition makes.", cls: "tile--violet" },
  { n: "04", t: "Check the tone", d: "Segmental tone error rate flags syllables where the segment was right and the tone was wrong — the errors that silently change meaning.", cls: "tile--tangerine" },
];

const NOTBUILT = [
  { t: "Voice restoration", d: "Synthesising restored speech in the person's banked voice. Attempted via voice conversion; it degraded intelligibility, so it is documented as a negative result rather than shipped." },
  { t: "Real-time conversion", d: "Live phone-call latency. The current pipeline is offline batch inference." },
  { t: "Clinical validation", d: "Everything measured so far uses simulated dysarthria. Real patient speech is required before any clinical claim." },
];

export function Screening() {
  return (
    <>
      <PageHeader
        eyebrow="How it works"
        title="Speak normally. Get understood."
        intro="OwnVoice adapts speech recognition to dysarthric Mandarin and measures the one failure the English-language literature ignores — tone. Here is what a person actually does, and what the system honestly does not do yet."
      />

      <section className="section" style={{ paddingTop: 0 }}>
        <div className="container">
          <Reveal as="h2" className="display-lg" style={{ marginBottom: "0.6em" }}>Who this is for</Reveal>
          <div className="grid grid--3">
            {WHO.map((x, i) => (
              <Reveal key={x.t} className={`tile ${x.cls}`} delay={i * 60}>
                <h3>{x.t}</h3>
                <p style={{ marginTop: "0.4em", opacity: 0.92 }}>{x.d}</p>
              </Reveal>
            ))}
          </div>
        </div>
      </section>

      <section className="section" style={{ background: "#0b0a10", color: "var(--cream)" }}>
        <div className="container">
          <Reveal as="p" className="eyebrow" style={{ color: "var(--sky)" }}>The flow</Reveal>
          <Reveal as="h2" className="display-lg" delay={60} style={{ marginBottom: "0.6em" }}>
            Four steps, one of them before you need it.
          </Reveal>
          <div className="grid grid--2">
            {STEPS.map((x, i) => (
              <Reveal key={x.t} className={`tile ${x.cls}`} delay={i * 70}>
                <div className="stat" style={{ fontSize: "2.2rem" }}>{x.n}</div>
                <h3 style={{ margin: "0.2em 0" }}>{x.t}</h3>
                <p style={{ opacity: 0.94 }}>{x.d}</p>
              </Reveal>
            ))}
          </div>
        </div>
      </section>

      <section className="section">
        <div className="container">
          <Reveal as="p" className="eyebrow">Why banking matters</Reveal>
          <Reveal as="h2" className="display-lg" delay={60} style={{ marginBottom: "0.6em" }}>
            The hardest problem in voice restoration is a scheduling problem.
          </Reveal>
          <Reveal as="p" className="lead" delay={100} style={{ maxWidth: "64ch" }}>
            Restoring someone's own voice needs a recording of that voice from
            before it was lost. A stroke gives no warning, so most stroke
            patients have nothing usable. But a patient scheduled for
            glossectomy next Tuesday can bank their voice on Monday — a defined
            clinical workflow with a defined patient pipeline. That is why the
            oral-cancer population is the right place to start, and it is a
            population Taiwan has far too many of.
          </Reveal>
        </div>
      </section>

      <section className="section" style={{ background: "#0b0a10", color: "var(--cream)" }}>
        <div className="container">
          <Reveal as="p" className="eyebrow" style={{ color: "var(--tangerine)" }}>Not built yet</Reveal>
          <Reveal as="h2" className="display-lg" delay={60} style={{ marginBottom: "0.6em" }}>
            What this cannot do.
          </Reveal>
          <div className="grid grid--3">
            {NOTBUILT.map((x, i) => (
              <Reveal key={x.t} className="tile tile--ink" delay={i * 70}
                style={{ boxShadow: "inset 0 0 0 1px rgba(255,255,255,0.14)" }}>
                <h3>{x.t}</h3>
                <p style={{ color: "rgba(244,239,230,0.8)", marginTop: "0.4em" }}>{x.d}</p>
              </Reveal>
            ))}
          </div>
          <Reveal style={{ marginTop: "2em", display: "flex", gap: "14px", flexWrap: "wrap" }}>
            <Link className="btn" to="/" onClick={() => setTimeout(() => scrollToId("demo"), 450)}>
              Try the live demo
            </Link>
            <Link className="btn btn--ghost" to="/method" style={{ color: "var(--cream)", boxShadow: "inset 0 0 0 2px var(--cream)" }}>
              See the research
            </Link>
          </Reveal>
        </div>
      </section>

      <section className="section">
        <div className="container">
          <Reveal className="tile tile--pink">
            <h3>Please read</h3>
            <p style={{ marginTop: "0.5em" }}>
              OwnVoice is a research prototype built for the 2026 Presidential
              Hackathon on openly licensed public datasets. It is an
              accessibility aid, not a medical device, and it does not diagnose
              anything. Every result published so far is measured on simulated
              dysarthria. Do not upload real patient information.
            </p>
          </Reveal>
        </div>
      </section>
    </>
  );
}
