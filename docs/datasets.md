# Dataset access status

Nothing has been downloaded yet. Every dysarthria corpus below is
**license-restricted** and requires a signed agreement submitted by a named
researcher. These are identifiable medical voice recordings of disabled
individuals — the licensing exists for good reason and must be honored.

**You have to sign and submit these yourself.** I can prepare the paperwork and
draft the research-purpose statements, but I can't sign legal agreements or
submit applications on your behalf.

## Critical path

Approval lag runs from days to several weeks. The build phase starts
mid-September. **File these now**, regardless of what happens with the proposal.

---

## Dysarthric speech (restricted)

### MDSC / AISHELL-6B — Mandarin Dysarthria Speech Corpus  ← GET THIS ONE

**Licence: CC BY NC 4.0.** Open, non-commercial. No signed legal agreement, no
institutional sponsor, no multi-week review. An earlier version of this file
said it "requires a direct request" — that was wrong.

- **Content:** 18,630 recordings / 17 h total.
  - dysarthric: 8,505 recordings, 9.4 h, **21 speakers** (12F/9M)
  - control: 10,125 recordings, 7.6 h, 25 speakers (13F/12M)
- **Speakers:** native Mandarin, ages 18–48, gender balanced. Etiologies
  include cerebral palsy and hepatolenticular degeneration (Wilson's disease).
- **Audio:** 16 kHz, quiet indoor, ~20 cm from a mobile microphone — the
  sample rate already matches our pipeline, so no resampling.
- **Text:** 10 wake-up words repeated 5× at varying speeds, plus 355
  non-wake-up items (fixed commands, free commands, household instructions and
  other phrases); 295 non-repeated sentences per speaker.
- **Paper:** [arXiv 2406.10304](https://arxiv.org/abs/2406.10304) (Interspeech 2024)
- **Baseline recipe:** https://github.com/greeeenmouth/LRDWWS
- **Related:** MDSC-Eval, a further 8,760 recordings / 9 h from 20 more
  dysarthric speakers, released for the SLT 2024 LRDWWS challenge
  (https://lrdwws.org/).

**Why this is the single most valuable thing to obtain.** It is *real Mandarin
dysarthric speech*. EasyCall can only tell us whether the approach survives on
authentic pathology; it is Italian and therefore cannot say anything about
tone. MDSC can test the tone claim itself — the project's whole argument — on
real patients rather than on perturbations we designed.

**Known limitation:** it is command- and wake-word oriented rather than
continuous conversational speech, so CER on it is not directly comparable to
CER on our Common Voice sentences. Tone is still fully present: Mandarin tone is
carried per syllable, and isolated words carry it just as sentences do.

**How to get it — needs a human, roughly ten minutes:**

1. From https://www.aishelltech.com/AISHELL_6B the "Dataset" button leads to
   https://opendata.aishelltech.com/aishell-6b
2. That page's data-application form wants a **Speechhome member ID** (free
   registration at https://www.speechhome.com/signup) plus a licence type.
3. The direct "Netdisk" download links are MyAirBridge (mab.to) transfers.
   Opening one presents a terms-and-conditions and personal-data-consent
   banner that must be accepted before the files are reachable.

Steps 2 and 3 both require accepting terms and creating an account, so they
have to be done by you rather than by an assistant.

### CDSD — Chinese Dysarthria Speech Database
- **Content:** 133 hrs, 44 speakers — the largest Chinese dysarthria corpus.
- **Access:** http://melab.psych.ac.cn/CDSD.html
  1. Download the license agreement: http://melab.psych.ac.cn/License_Agreement_CDSD.pdf
  2. Fill in and sign
  3. Submit via the external application link on the database page
- **Held by:** MELab, Institute of Psychology, Chinese Academy of Sciences
- **Paper:** [arXiv 2310.15930](https://arxiv.org/abs/2310.15930) (Interspeech 2024)
- **Note:** a PRC-institution dataset in a Taiwanese government competition —
  worth a moment's thought on optics and on any data-transfer restrictions.
  MDSC/AISHELL is also PRC-based. Flagging, not judging.

### TORGO
- **Content:** ~23 hrs English. 8 dysarthric speakers (cerebral palsy / ALS),
  7 controls. Includes **articulatory** measurements, not just acoustic.
- **Access:** LDC catalog [LDC2012S02](https://catalog.ldc.upenn.edu/LDC2012S02)
  (membership or fee), or the U Toronto page:
  https://www.cs.toronto.edu/~complingweb/data/TORGO/torgo.html
- **Use:** English, so not demo-facing — but the ALS/CP speaker profile matches
  the expansion population, and articulatory data is rare and valuable.

### UASpeech
- **Content:** 102.7 hrs, 29 speakers (16 dysarthric w/ CP, 13 typical).
  155 common + 300 uncommon words across three blocks.
- **Access:** signed license agreement with UIUC.
- **Use:** largest English dysarthria set; isolated words rather than
  continuous speech, so better for intelligibility scoring than conversion.

### DysArinVox
- Dysphonia & Dysarthria Mandarin corpus, Interspeech 2024. Not yet
  investigated — worth checking as a second Mandarin source.

---

## Healthy speech — voice cloning targets (open)

Needed to train the speaker-embedding and synthesis side. These are freely
available and can be pulled without any application.

| Corpus | Content | Notes |
|---|---|---|
| **AISHELL-3** | 85 hrs, 218 Mandarin speakers, 44.1kHz/16-bit | Multi-speaker TTS corpus; the natural base for voice cloning |
| **Common Voice zh-TW** | Crowdsourced Taiwan Mandarin | CC0; Taiwan-accented, unlike PRC corpora |
| **MAGICDATA** | Mandarin read speech | OpenSLR #68 |
| **TAT / TaigiSpeech** | Taiwanese Hokkien | For the Hokkien extension; low-resource |

Common Voice zh-TW matters more than its size suggests — the dysarthria corpora
are PRC-recorded, and Taiwan-accented Mandarin differs. Accent mismatch between
source and target will hurt output naturalness.

---

## Development strategy while licenses pend

Published perturbation methods can simulate dysarthric speech from healthy
speech (tempo reduction, jitter/shimmer injection, spectral smearing, prosodic
flattening). This unblocks pipeline development immediately using open corpora.

**Important caveat:** Interspeech 2025 published
*"Synthetic Dysarthric Speech: A Supplement, Not a Substitute for Authentic"* —
synthetic data bootstraps the pipeline but will not validate it. Any
intelligibility claim in the final submission must rest on real dysarthric
speech, and ideally on a real Taiwanese patient.

---

## On the "90%+" target

Needs defining before it means anything. Candidate metrics:

- **Word-level intelligibility** rated by naive human listeners, before vs.
  after conversion — this is the metric that matters clinically and the one
  judges will understand.
- **ASR word error rate** on converted vs. original speech — cheap, automatic,
  a reasonable proxy, but not the real outcome.
- **Speaker similarity** to the banked voice (cosine distance on speaker
  embeddings) — measures the "own voice" claim specifically.
- **Tone accuracy** — Mandarin-specific and non-negotiable; a mistoned output
  is a wrong word, not an accent.

90% intelligibility from severely dysarthric input would be at or beyond the
current research frontier. 90% on *mild-to-moderate* dysarthria is a defensible
target. Recommend committing to a target only after baselining on real MDSC
data — an unmet number in the proposal is worse than a conservative one met.
