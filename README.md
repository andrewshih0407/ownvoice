# OwnVoice

**Tone-aware speech recognition for Mandarin speakers with dysarthria.**

🌐 **Website:** https://ownvoice.vercel.app · **Research demo:** https://ownvoice.vercel.app/research/
**Hosted demo (model runs here):** https://appapppy-m7fpkveuhxbkxapu2bbkdg.streamlit.app ·
**Model:** https://huggingface.co/anonymous6623/ownvoice-asr

---

## What this is

Dysarthria follows stroke, Parkinson's, ALS, cerebral palsy and head-and-neck
cancer surgery. Speech recognition collapses on it. In Mandarin there is a
second failure the English-language literature does not address: **tone is
lexically contrastive**, so a mistoned syllable is not an accent — it is a
different word. 統一 (tǒng yī, "unify") becomes 同一 (tóng yī, "the same").

This repo contains a dysarthria simulator, a tone-aware metric suite, a
fine-tuned Mandarin ASR model (whisper-small), an API, a website, and a Chrome
extension that captions calls and videos live. A phone app is designed but not
yet built.

Privacy: the extension sends audio only to the model server you point it at, so
with a server on your own machine audio stays on that machine. The hosted
Streamlit demo uploads the audio you give it to that server.

## Status (updated 2026-11-01)

| component | state |
|---|---|
| Dysarthria simulator | working, acoustically validated |
| Tone metrics (CER / TER / **STER**) | working, regression-tested |
| Dysarthria-robust ASR (fine-tuned whisper-small) | **working**; tested on simulated *and* real patient speech |
| API (`/health`, `/simulate`, `/transcribe`, `/transcribe_chunk`) | working |
| Website ([ownvoice.vercel.app](https://ownvoice.vercel.app)) | working, deployed |
| Chrome extension (live captions in a side panel) | working with a model server on your own machine; mic path verified, tab capture untested |
| Phone app | **designed, not built** (see [`app/`](app/)) |
| Voice restoration | **not built**; the voice-conversion attempt failed and is documented |

Full numbers, including the negative results, are in [`docs/results.md`](docs/results.md).

## Data

- **Training:** Mozilla Common Voice zh-TW (CC0), `train` split. 1,000 sentences from
  91 speakers, each damaged at three severities by our simulator (3,000 dysarthric pairs),
  plus the 1,000 clean originals so the model does not forget normal speech. Splits are
  **speaker-disjoint**: one fifth of speakers are held out for evaluation.
- **Real-patient test:** MDSC / AISHELL-6B, Mandarin dysarthric speech (CC BY-NC 4.0).
  Used **only as a held-out test set**, never for training. Its audio is not in this repo
  and must not be redistributed. Speakers are referred to by ID only.

We trained on simulated speech because no Mandarin dysarthric corpus is large and open
enough to train on. MDSC is small, non-commercial and gated.

## Result 1: real patients (MDSC / AISHELL-6B)

420 recordings from 21 speakers with dysarthria (cerebral palsy, Wilson's disease),
20 random recordings per speaker, plus 5 healthy controls. The analysis was
pre-registered in [`src/eval_mdsc.py`](src/eval_mdsc.py) before any result existed.

| group | speakers | CER stock | CER OwnVoice | relative cut |
|---|---|---|---|---|
| mild | 11 | 0.444 | 0.318 | 28% |
| moderate | 4 | 1.015 | 0.700 | 31% |
| severe | 6 | 1.169 | 0.938 | 20% |
| **all dysarthric** | **21** | **0.760** | **0.568** | **25%** |
| healthy controls | 5 | 0.245 | 0.097 | 61% |

**25% fewer character errors on real dysarthric speech** (paired Wilcoxon p ≈ 1e-15).
OwnVoice was better for 20 of 21 speakers and slightly worse for one (DM0017, mild).

Caveats that go with this number every time:

- **Healthy controls improved too**, so part of the gain is not dysarthria-specific
  (plausibly adaptation to Taiwanese-Mandarin text and fewer stock hallucinations).
- **Absolute error is still high:** 57% overall, 94% for severe speakers. Severe speech
  is not yet usable as captions.
- The material is short smart-home commands, and the causes (CP, Wilson's) differ from
  the stroke, Parkinson's and oral-cancer population we target.

## Result 2: simulated dysarthria (held-out speakers)

Stock whisper-small falls from 89.3% to 52.6% intelligibility between clean and severe
simulated speech. Both models scored on the same held-out speakers:

| condition | CER stock | CER OwnVoice | relative cut |
|---|---|---|---|
| clean | 0.1076 | 0.1155 | −7% (slightly worse) |
| mild | 0.1605 | 0.1370 | 15% |
| moderate | 0.2074 | 0.1311 | 37% |
| severe | 0.2877 | 0.1683 | **41%** |
| **overall** | 0.1908 | 0.1380 | **28%** |

**Intelligibility 80.9% → 86.2%.** On simulated speech the gain grows with severity;
on real speech it did not (severe improved least), so the simulator does not fully
capture real severe dysarthria. That train/test gap is the main limitation.

**Tone (STER):** severe improved 43% (0.0947 → 0.0536), but overall barely moved
(0.0529 → 0.0488) because clean, mild and moderate got slightly worse. Generic
fine-tuning does not solve tone; that remains the open problem this project is about.

Per Interspeech 2025 ("Synthetic Dysarthric Speech: A Supplement, Not a Substitute
for Authentic"), simulated results are valid for architecture work, not as clinical
claims. Nothing here is a clinical claim.

---

## Quickstart

### Website only

```bash
cd site
npm ci
npm run dev          # http://localhost:5173
```

The interactive demo lives at **http://localhost:5173/#/research**, not on the
front page. The home route is the human-facing landing page; file upload, the
severity player, the record button, live transcription and stage mode are all
on the research route.

That demo will report the model server unreachable until you start the API
below, and it falls back to an embedded Streamlit iframe while the health check
fails. Everything else — the exploded view, the tone-flattening interaction,
all measured figures — is client-side and works standalone.

### API + website

```bash
pip install -r requirements.txt
```

On a CPU-only machine install torch first, or you will pull several GB of
unused CUDA libraries:

```bash
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cpu
```

Then, in two terminals:

```bash
python backend/app.py          # :7860
```

```bash
cd site && npm run dev         # :5173, CORS already allows this origin
```

By default the API loads the fine-tuned model from `runs/asr_v1`, which must be a
local folder (a Hugging Face model id is rejected with a 503). Download the
published model there first:

```bash
huggingface-cli download anonymous6623/ownvoice-asr --local-dir runs/asr_v1
```

### Chrome extension

With the API running, open `chrome://extensions`, turn on Developer mode, choose
**Load unpacked** and select `extension/`. Details in
[`extension/README.md`](extension/README.md). A zipped copy is on the website.

⚠ If `OWNVOICE_MODEL` equals the baseline model, the demo compares the model
against **itself** — identical transcripts, identical scores, no error. Check
`/health` for `"tuned_is_distinct_from_base": true`.

### Reproduce the results

```bash
cd src
```

Build a corpus (streams Common Voice zh-TW, CC0, and simulates dysarthria):

```bash
python data.py --limit 1000 --out ../data/train
```

Verify the simulation actually degrades speech the way it claims:

```bash
python verify_sim.py --root ../data/train
```

Measure the pre-training baseline:

```bash
python baseline.py --root ../data/train
```

Fine-tune. **One epoch is optimal** — it overfits after that:

```bash
python train_asr.py --root ../data/train --epochs 1
```

Matched before/after evaluation:

```bash
python evaluate.py --root ../data/train --tuned ../runs/asr_v1
```

Metric regression tests:

```bash
python test_metrics.py
```

Real-patient test (needs your own copy of MDSC / AISHELL-6B, from
https://www.aishelltech.com/AISHELL_6B; run from the repo root):

```bash
python src/eval_mdsc.py --root <extracted MDSC folder>
python src/summarize_mdsc.py runs/mdsc_eval.jsonl
```

---

## Repo layout

```
src/          simulation, metrics, training, evaluation
  dysarthria_sim.py   six perturbations over a pyworld decomposition
  verify_sim.py       acoustic validation, gates on three claims
  metrics.py          CER + TER + STER (alignment-based)
  test_metrics.py     STER regression tests
  data.py             paired corpus builder (openly licensed sources)
  data_real.py        loader for real dysarthric corpora
  baseline.py         pre-training reference, with hallucination detection
  train_asr.py        Whisper fine-tuning, speaker-disjoint splits
  evaluate.py         matched per-condition comparison
  data_mdsc.py        MDSC / AISHELL-6B loader
  eval_mdsc.py        pre-registered real-patient test
  summarize_mdsc.py   per-severity tables and significance tests
  vc.py, eval_vc.py, sweep_vc.py, ablate_vocoder.py
                      voice conversion — a documented NEGATIVE result
  speaker_sim.py      WavLM x-vector speaker identity calibration

backend/      FastAPI: /health, /simulate, /transcribe, /transcribe_chunk
product-site/ the website at ownvoice.vercel.app (static; serves the research demo at /research/)
site/         research demo source: React + Vite + TypeScript, three.js, GSAP, Lenis
extension/    Chrome extension: live captions from the mic or a tab
app/          phone app design (screens and build plan; not built yet)
scripts/      pack-extension.sh builds the extension download
docs/         results, prior art, dataset access
Dockerfile    single-origin container (site + API)
```

`data/` and `runs/` are gitignored. No datasets, patient audio or weights are in this repo.

## Key documents

- [`docs/results.md`](docs/results.md) — every measurement, including failures
- [`docs/prior-art.md`](docs/prior-art.md) — what is already published, and why
  the novelty claim is *tone*, not own-voice restoration
- [`docs/datasets.md`](docs/datasets.md) — which corpora are usable and which
  are restricted
- [`DEPLOY.md`](DEPLOY.md) — deployment

## Contributing

The first real-patient test is done (above). The highest-value open tasks now:

1. **Close the train/test gap.** Train on real, consented dysarthric speech, especially
   severe, instead of only simulated speech.
2. **Separate the dysarthria-specific gain** from general domain adaptation, for example
   with a control model fine-tuned on clean speech only.
3. **Test the target population** (stroke, Parkinson's, oral cancer) and conversational
   speech, not just commands.
4. **Personalization:** adapt the model to one speaker from a few minutes of their speech.

See [`docs/datasets.md`](docs/datasets.md) for which corpora are usable.

Do **not** add the unlicensed TORGO/UASpeech re-uploads circulating on dataset
hubs. They are restricted patient medical data redistributed without
authorisation.

## Licence

Code is [MIT](LICENSE). Datasets and derived model weights carry their own
terms — several are non-commercial, and anything trained on them inherits that.
See the note in [`LICENSE`](LICENSE).
