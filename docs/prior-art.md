# Prior art — what is already done, and what is left

Written after a literature check that materially changed the plan. Better to have
this on record than to have a judge discover it.

---

## The closest prior work is Taiwanese, and it is very close

**"Two-stage Voice Conversion for Dysarthric Speech Reconstruction with Speaker
Identity Preservation"** — Devin Chang, Ming-Chi Yen, Hsin-Te Hwang, Fo-Rui Li,
Ching-Feng Liu, Yu Tsao, Hsin-Min Wang.
[PDF](https://homepage.iis.sinica.edu.tw/papers/whm/new-7734-F.pdf)

- **Academia Sinica**, Taipei (Research Center for IT Innovation + Institute of
  Information Science)
- National Central University, Taoyuan
- **Chi Mei Hospital**, Tainan

Their stated contribution is restoring dysarthric speech **while preserving the
patient's own speaker identity** — which is OwnVoice's headline claim. It is not
novel.

### Their architecture (better than the one initially built here)

```
Stage 1  dysarthric -> normal        improves intelligibility
         VTN (seq2seq) or LLE, content features from
         Chinese-HuBERT / WavLM / Whisper, HiFi-GAN vocoder
         -> Chinese-HuBERT won

Stage 2  restore the patient's identity
         Seed-VC / FreeVC / SPARC / MKL-VC / Vevo / VQ-VAE baseline
         -> Seed-VC won, clearly, without costing intelligibility
```

This is **direct speech-to-speech** conversion. OwnVoice's stage 1 as built is an
ASR→TTS cascade, which puts a text bottleneck in the middle and discards prosody.
The wider SOTA agrees with them, not with the cascade:

- **CLARIS** (CHI 2026) — compact speech-to-speech restoration, SOTA
  intelligibility and naturalness, cross-lingual, real time (~30 ms per second of
  audio).
- **DiffDSR** (Interspeech 2025) — latent diffusion reconstruction preserving
  speaker identity.
- **Unsupervised Rhythm and Voice Conversion** ([arXiv 2501.10256](https://arxiv.org/abs/2501.10256))
  — rhythm conversion helps *most* for severe dysarthria.
- **Towards Inclusive ASR** ([arXiv 2505.14874](https://arxiv.org/abs/2505.14874))
  — VC for dysarthric ASR in low-resource languages (Spanish, Italian, Tamil).

### The methodological gift

They chose **LLE** explicitly because it "does not require a large training
dataset, which is advantageous in experiments with scarce dysarthric speech
data." Their entire dysarthric set was **one female patient reading 320
ten-character Mandarin sentences** (TMHINT).

Two implications:

1. The field is genuinely data-starved. Our reliance on simulation is far less
   unusual than it first appeared.
2. LLE + Chinese-HuBERT is the architecture matched to *our* constraint (public
   data only, no licensed Mandarin patient corpus). It beats trying to train a
   deep VC model on data we do not have.

---

## What remains unclaimed: tone

Full-text search of the Academia Sinica paper:

```
"tone"     0 hits
"tonal"    0 hits
"CER"      23 hits
"Mandarin" 11 hits
```

They work on Mandarin, report CER 23 times, and **never treat tone as a distinct
failure mode.** Neither does any other paper found in this survey.

That is the opening, and our own measurements already support it being a real
distinction:

- Simulated prosodic flattening collapses tone-scale F0 variance monotonically
  (2.545 → 1.173 st) while leaving segmental cues comparatively intact.
- In the matched evaluation, fine-tuning cut CER by 27.7% while overall STER
  moved −0.0037 — **character accuracy improved; tone accuracy did not.**
- A spontaneous baseline error shows the mechanism: 統一 (tǒng yī, "unify") →
  同一 (tóng yī, "the same") — a pure tone error that changes the word.

**Revised novelty claim:** not "restore dysarthric speech in the patient's own
voice" (published), but **"tone-aware dysarthric restoration for tonal
languages"** — the segmental tone error rate (STER) as an evaluation metric, and
explicit tone modelling in the restoration objective.

Worth verifying before submission: search specifically for tonal-language
dysarthria work in Cantonese and Thai. CUDYS (CUHK) studies "pitch and loudness
control" in Cantonese dysarthria and is the most likely place for the claim to
already exist.

---

## Consequences for the plan

1. **Reposition the pitch** around tone, not around own-voice restoration.
2. **Change stage 2** from a TTS cascade to Chinese-HuBERT content features +
   Seed-VC identity restoration — better validated and cheaper on our data
   budget.
3. **Approach Academia Sinica as a collaborator, not a competitor.** They already
   have a hospital partner (Chi Mei). The handbook explicitly scores "engaged
   collaboration units" and "future planned collaboration units."
4. **Cite all of this in the submission.** "Differences from existing solutions"
   is a scored field; showing command of the prior art and a precise, defensible
   delta is far stronger than an overreaching novelty claim a judge can puncture.
