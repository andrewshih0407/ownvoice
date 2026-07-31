# OwnVoice — Tone-Aware Speech Recognition for Dysarthria

**2026 Presidential Hackathon International Track**
Theme: *Digital Inclusion in the AI Era*

🌐 https://anonymous6623-ownvoice.static.hf.space
💻 https://github.com/andrewshih0407/ownvoice
🤖 https://huggingface.co/anonymous6623/ownvoice-asr

> Every figure below is measured, not projected. Sources:
> `docs/results.md`, `data/train/matched_eval.json`.

---

# 1. Application Scenario & Problem Statement

## The scenario

A man in Tainan is 48. He chewed betel nut for twenty years, as most of his
co-workers did. He has just had a glossectomy for oral cancer. The surgery
saved his life and took his speech. His family struggles to understand him. So
does his phone, his bank's voice menu, and every device his grandchildren use
without thinking.

He is not an edge case. He is a large and growing population in Taiwan.

## Why it matters here

- Oral cancer is the **4th most common cancer and the 4th leading cause of
  cancer death among Taiwanese men**, at roughly **29.8 cases per 100,000 —
  about ten times the female rate**. Around **86% of the variance in incidence
  is explained by betel-nut consumption**.
- It strikes **working age**, in the 40s and 50s, ending careers that depend on
  speaking.
- The affected population skews toward labourers, drivers, and Indigenous
  communities — people already underserved, now cut off from digital services
  as well.
- **Stroke** adds ~210 cases per 100,000 person-years (≈49,000 strokes a year);
  dysarthria follows roughly a quarter of ischaemic strokes.
- **Parkinson's** age-standardised prevalence rose **394% between 2000 and
  2021**, and Taiwan became a super-aged society in 2025.

## The exclusion is doubling, not shrinking

Dysarthric speakers have always faced difficulty being understood by people.
What is new is that they are now also excluded by *machines*. As interfaces
become voice-first — assistants, phone menus, dictation, accessibility tools —
every system that assumes clear speech quietly removes this population from the
digital economy. The technology that was supposed to help is widening the gap.

## The problem nobody is measuring

**In Mandarin, tone is part of the word.**

統一 (tǒng yī, *"unify"*) and 同一 (tóng yī, *"the same"*) differ by exactly one
tone. So do 買 (mǎi, *buy*) and 賣 (mài, *sell*) — opposite meanings, one tone
apart.

Dysarthria flattens the pitch contour that carries tone. A mistoned syllable is
therefore **not an accent — it is a different word**, and no spell-checker,
grammar model, or human listener can reliably recover the intent.

The dysarthria research literature is overwhelmingly English-first, and English
is not tonal. We surveyed the closest prior work — including a two-stage voice
conversion paper from **Academia Sinica with Chi Mei Hospital**, working on
*Mandarin* — and searched its full text: the word "tone" appears **zero times**,
against 23 mentions of character error rate.

**Nobody is measuring the failure mode that matters most for a quarter of the
world's population.** That is the gap this project addresses.

---

# 2. Proposed Solution & Technical Overview

## What it does

1. **The person speaks normally.** No sustained vowels, no reading list, no
   clinical protocol — ordinary connected speech into an ordinary microphone.
2. **A dysarthria-adapted model transcribes it.** On simulated severe
   dysarthria this recovers **41% of the character errors** stock recognition
   makes.
3. **A tone check runs alongside.** Our metric flags syllables where the
   segment was recognised correctly but the *tone* was wrong — precisely the
   errors that silently change meaning.
4. **Voice banking**, where there is warning. Scheduled surgery or a
   progressive diagnosis both give time to record the person while speech is
   still clear, which is what makes later restoration possible at all.

## Technical innovation: a metric that did not exist

Our central contribution is **STER — Segmental Tone Error Rate**.

Character error rate cannot distinguish "the model misheard the syllable" from
"the model heard the syllable and got the tone wrong." Those are different
failures requiring different fixes. STER counts tone errors **only on syllables
whose initial and final were already recognised correctly**, isolating the
tonal signal.

Building it correctly took two iterations, and the second one matters:

> Our first implementation compared syllables **by position**. A single
> inserted word shifted the alignment and hid every tone error after it — a
> real tone error scored 0.000. We caught this while testing the live demo,
> rebuilt STER on edit-distance alignment over syllable *segments*, and locked
> the behaviour in with regression tests. Re-running the full evaluation, the
> conclusion held.

## Open data — the entire pipeline

**Every corpus is openly licensed.** This was a deliberate constraint, not a
convenience.

| dataset | licence | role |
|---|---|---|
| Common Voice zh-TW | **CC0-1.0** | Taiwan-accented Mandarin training corpus |
| AISHELL-3 | **Apache-2.0** | multi-speaker Mandarin |
| LibriSpeech | **CC-BY-4.0** | English extension |
| HPA cancer registry, MOHW mortality statistics | Taiwan open data | epidemiology and needs assessment |

**What we refused to use, and why it matters.** Repackaged copies of the TORGO
and UASpeech patient corpora circulate freely on dataset hubs — including one
9.34 GB collection published under CC BY 4.0 whose own documentation says it
combines "TORGO, UASPEECH, Ultrax, EasyCall." Those source corpora require
signed institutional agreements and cannot be relicensed by a third party.
Beyond the ethics of redistributing patient medical data without
authorisation, the competition handbook makes improper data acquisition an
explicit disqualification criterion. We used none of them.

## AI models — all open, no paid APIs

| component | model | licence | role |
|---|---|---|---|
| Recognition | **Whisper-small**, fine-tuned by us | MIT | dysarthric speech → text |
| Simulation | **pyworld** (WORLD vocoder) | MIT | source-filter decomposition |
| Speaker verification | **WavLM x-vector** | MIT | voice-identity measurement |
| Content features | **Chinese-HuBERT** | MIT | voice-conversion experiments |

No proprietary or paid API is used at any stage. The full pipeline is
reproducible on a single consumer GPU.

## Solving the data scarcity problem

Real dysarthric speech is scarce and licence-gated — the closest prior work
trained on **one patient reading 320 sentences**. We built a validated
**dysarthria simulator** instead: pyworld decomposes clean speech into pitch,
spectral envelope and aperiodicity, and six perturbations model documented
acoustic correlates of dysarthria — reduced rate, prosodic flattening, formant
smearing, breathiness, amplitude instability, jitter.

Critically, **we validated that it does what it claims** rather than assuming
it. Tone-scale F0 variance must fall monotonically with severity; it does
(2.545 → 1.173 semitones). Spectral flux must fall; it does. Duration must
rise; it does. **The jitter axis failed validation and shows no graded effect,
so we make no claim about voice-quality modelling.** That axis is documented as
unproven rather than quietly reported.

## Results — measured on a matched test set

Both models scored on the **same held-out speakers**, speaker-disjoint splits
(train and test never share a voice), broken out per condition:

| condition | CER before | CER after | change |
|---|---|---|---|
| clean | 0.1076 | 0.1155 | +0.0078 |
| mild | 0.1605 | 0.1370 | −0.0235 |
| moderate | 0.2074 | 0.1311 | −0.0763 |
| severe | 0.2877 | 0.1683 | **−0.1194** |
| **overall** | 0.1908 | 0.1380 | **−0.0528** |

**Intelligibility 80.9% → 86.2%, a 27.7% relative reduction in character error
rate.** Gains scale with severity — the model helps most where speech is least
intelligible, which is the clinically correct shape.

## The finding that defines the project

**Tone did not improve.** STER moved −0.004: nothing.

Character accuracy rose 27.7% while tone accuracy stood still. **Generic ASR
fine-tuning does not fix tone.** It is a distinct failure mode requiring
explicit modelling — which is exactly why a tone-aware system is needed, and
exactly what no existing dysarthria system provides.

We report this because it is the most important thing we learned.

## What we tried that failed

We implemented the voice-conversion architecture the literature recommends
(Chinese-HuBERT content features, LLE reconstruction, HiFi-GAN vocoding). **It
degraded intelligibility** (CER 0.4048 → 0.4881). We diagnosed it properly —
an ablation cleared the vocoder, and we found and fixed a genuine bug in our
layer selection — and it still lost to leaving the audio alone. It ships in the
repository as a documented negative result. Deleting it would make the project
look better and be worth less.

---

# 3. Development Plan

## Completed

| milestone | evidence |
|---|---|
| Dysarthria simulator, acoustically validated | 3 of 4 axes pass; jitter documented as failing |
| Tone metric suite (CER / TER / **STER**) | regression-tested, alignment bug found and fixed |
| Corpus pipeline over openly licensed sources | 1,000 utterances, 91 speakers, reproducible by one command |
| Baseline measurement | 89.3% clean → 52.6% severe intelligibility |
| Mandarin model fine-tuned and published | `anonymous6623/ownvoice-asr` |
| Matched per-condition evaluation | 80.9% → 86.2%, −41% on severe |
| Voice conversion investigated | negative result, diagnosed and documented |
| FastAPI backend + public website | live and deployed |

## In progress

| milestone | estimate |
|---|---|
| English second model (LibriSpeech, CC-BY-4.0) | 1 week |

Measurement already established that this must be a **separate model**: the
Mandarin fine-tune left English essentially unchanged (+0.01 WER) but its
dysarthria gain **did not transfer** (severe English WER 0.290 stock vs 0.295
tuned). We tested before claiming.

## Not started — with honest timelines

| milestone | estimate | why it matters |
|---|---|---|
| Validation on **real patient speech** (MDSC, CC BY-NC 4.0, 21 dysarthric speakers) | 3 weeks | the single most important open task |
| Scale the training corpus 10× | 2 weeks | the model overfits after one epoch; data is the binding constraint |
| Fix clean-speech regression | 1 week | clean input degraded slightly (+0.0078 CER) |
| Voice restoration (Chinese-HuBERT + Seed-VC) | 6 weeks | the "own voice" capability |
| Clinical pilot with a partner hospital | 3 months | pre-operative voice banking workflow |

## Long-term strategy

**Phase 1 — validate on real patients (Sept).** MDSC is the only obtainable
corpus of real Mandarin dysarthric speech (CC BY-NC 4.0, 21 patients, cerebral
palsy and Wilson's disease). It is the only way to test whether the tone
finding survives outside simulation. Everything else is secondary to this.

**Phase 2 — tone-aware modelling (Oct).** Having *measured* that generic
fine-tuning fails on tone, build the explicit tone objective. This is the
research contribution.

**Phase 3 — clinical partnership (Nov onward).** Approach **Academia Sinica**
and **Chi Mei Hospital**, who already collaborate on dysarthric speech
reconstruction. We are not competing with their work — we are adding the tonal
dimension it does not address.

**Phase 4 — cross-lingual scaling.** Cantonese (6 tones), Taiwanese Hokkien,
Thai, Vietnamese. The CUDYS corpus from CUHK is Cantonese dysarthric speech and
would test tonal transfer directly.

## Honest limitations we carry forward

1. **All results are on simulated dysarthria.** The model trained on
   perturbations we generated, so part of the gain may be learning to invert
   our own simulation. Per Interspeech 2025 ("Synthetic Dysarthric Speech: A
   Supplement, Not a Substitute for Authentic") this is valid for architecture
   development and is not a clinical claim.
2. **No patient or clinical validation has occurred.**
3. **Voice restoration does not work yet.**
4. **The jitter perturbation axis is unvalidated.**

---

# 4. Target Audience & Impact Scope

## Primary audience

**Post-glossectomy oral-cancer patients in Taiwan.** Roughly **3,400 new male
oral-cancer cases annually**, concentrated in labouring and Indigenous
communities.

They are the primary target for a specific structural reason: **their surgery
is scheduled**. That is the only situation in which a voice can be banked
*before* it is lost, which makes a defined clinical workflow possible — record
Monday, operate Tuesday, restore afterward. A stroke gives no such warning.

## Secondary audiences

| population | scale in Taiwan | need |
|---|---|---|
| Stroke survivors with dysarthria | ~12,000 new cases/year | recognition (no banked voice available) |
| Parkinson's patients | prevalence +394% since 2000 | progressive — time to bank a voice |
| ALS, MSA, PSP | rare but severe | progressive |
| Cerebral palsy | lifelong | the largest group in existing corpora |

## Beneficiaries beyond the patient

- **Families and caregivers** — the immediate beneficiaries of being understood
- **Speech-language pathologists** — STER gives them an objective tonal outcome
  measure they currently lack for tracking therapy
- **Surgical teams** — a pre-operative voice-banking step that fits inside
  existing scheduling
- **The research community** — an open metric, an open simulator, and published
  negative results in a field where patient data is scarce

## Scaling potential

**Every tonal language.** Roughly a fifth of the world speaks one, and none of
them are served by the English-first dysarthria literature:

- **Mandarin** — 1.1 billion speakers (4 tones)
- **Cantonese** — 85 million (6 tones); CUDYS corpus exists at CUHK
- **Vietnamese** — 85 million (6 tones)
- **Thai** — 70 million (5 tones)
- **Taiwanese Hokkien** — 15 million, and directly relevant to Taiwan's elderly

The pipeline is **language-agnostic by construction** — the simulator is
acoustic, not linguistic. Only the tone metric is tonal-language-specific, and
it generalises to any language where pitch is lexically contrastive. The English
extension in progress demonstrates the same machinery applied to a non-tonal
language.

## Why Taiwan is the right place to start

Taiwan has one of the world's highest oral-cancer burdens, a super-aged
population, strong speech-research institutions, and a public health system
that could integrate a pre-operative voice-banking step. A solution proven here
transfers directly to every tonal-language country in the region.

## What success looks like

**Short term** — validate the tone finding on real patient speech, then publish
STER so other groups can measure what they currently cannot.

**Medium term** — a working voice-banking and restoration pathway piloted with
one Taiwanese hospital's head-and-neck oncology department.

**Long term** — nobody loses access to digital services because of how they
speak. Not because the technology got more tolerant, but because it learned to
listen properly.
