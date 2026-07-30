# Results log

> ## STER alignment defect — found, fixed, conclusion survives
>
> Found while verifying the live demo. STER paired syllables **by position**, so
> a single insertion hid every tone error after it:
>
> ```
> 我要買東西 -> 我要賣東西     STER 0.222   correct
> 我要買東西 -> 我就要買東西   STER 0.000   WRONG — real tone error, invisible
> ```
>
> It under-reported tone errors, and under-reported *more* on worse transcripts
> (more length mismatches), which confounded the baseline-vs-tuned comparison in
> an uncontrolled direction.
>
> **Fixed**: STER now aligns the syllable sequences with edit distance on the
> *segments* before comparing tones, so a tone difference cannot perturb the
> alignment and every segmentally-correct syllable is counted wherever it lands.
> Locked in by `src/test_metrics.py` — the regression case now scores 0.200
> instead of 0.000.
>
> **Re-ran `evaluate.py`. The numbers barely moved and the conclusion holds:**
>
> | | STER base | STER tuned | Δ |
> |---|---|---|---|
> | old (positional) | 0.0528 | 0.0491 | −0.0037 |
> | **fixed (aligned)** | **0.0529** | **0.0488** | **−0.0041** |
>
> The defect was real but its practical effect on this corpus was small, because
> Whisper's Mandarin output tends to match the reference in length, so positional
> pairing and alignment usually agreed. "Tone did not improve overall" is now
> measured with a correct metric rather than a confounded one.
>
> CER was never affected — jiwer aligns properly.

All numbers below are on **simulated** dysarthria. Nothing here is publishable
as an intelligibility claim — see the caveat at the bottom.

Hardware: RTX 5060 Laptop (8 GB), torch 2.11.0+cu128, transformers 5.14.1.

---

## 1. Simulation validation (`src/verify_sim.py`)

40 utterances, Common Voice zh-TW (CC0), 31 speakers, 3 severities, 120 pairs.

| metric | clean | mild | moderate | severe | verdict |
|---|---|---|---|---|---|
| tone-scale F0 std (st) | 2.545 | 1.845 | 1.271 | 1.173 | PASS — monotonic ↓ |
| spectral flux | 28.32 | 26.79 | 24.42 | 21.70 | PASS — monotonic ↓ |
| duration ratio | 1.00 | 1.11 | 1.33 | 1.67 | PASS — monotonic ↑ |
| jitter (residual, st) | 0.845 | 0.930 | 0.827 | 0.773 | **UNVALIDATED** |

### Metric bug found and fixed

First implementation measured raw F0 std and **failed**: 2.508 → 2.145 → 1.304 →
*1.671* (non-monotonic). Cause: prosodic flattening and jitter move raw F0
variance in *opposite* directions, so the metric summed two competing effects.

Fixed by decomposing the F0 track:

```
contour  = medfilt(F0)        -> tone      (falls with severity)
residual = F0 - medfilt(F0)   -> jitter    (should rise)
```

Mandarin tone lives in the slow contour (~100-300 ms), so median-filtering
isolates the tone-relevant component.

### Known limitation: jitter

No graded effect. Two unseparated causes: pyin's estimation floor (~0.8 st at
64 ms windows) may exceed the injected effect, or pyworld's synthesis may smooth
5 ms-scale F0 noise away entirely. Needs period-level analysis
(Praat/parselmouth), not frame-level pyin. **Deliberately deferred** — jitter is
a secondary voice-quality cue and the three axes carrying the scientific claim
all validate. **Do not claim jitter modelling in any writeup until fixed.**

---

## 2. ASR baseline (`src/baseline.py`)

`openai/whisper-small`, GPU, all 40 clips/condition, 31 speakers,
Traditional-Chinese normalized both sides via zhconv.

| condition | CER | STER | hallucination | intelligibility |
|---|---|---|---|---|
| clean | 0.107 | 0.016 | 0% | **89.3%** |
| mild | 0.168 | 0.034 | 0% | 83.2% |
| moderate | 0.248 | 0.034 | 2% | 75.2% |
| severe | 0.474 | 0.094 | 5% | **52.6%** |

**The gap stage 1 must close: 89.3% → 52.6%, i.e. ~37 points.**

Degradation is monotonic. An earlier run showed moderate (0.516) *worse* than
severe (0.478); that was an artifact of a 2-speaker sample at n=20 and
disappeared with proper speaker diversity.

### Two corrections made during this work

**Whisper hallucination.** First run gave severe CER = **2.843** — above 1.0
means insertions exceeded the reference: the decoder was looping, not
mis-hearing. `no_repeat_ngram_size=4` + `repetition_penalty=1.15` brought it to
0.474. Residual hallucination is now measured per condition rather than silently
inflating CER.

**Premise test was invalid.** Originally compared ΔTER vs ΔCER. TER is computed
from *recognized text*, so it inherits every character error and cannot separate
tonal from segmental failure. The correct metric is **STER** — tone errors
counted only on syllables whose initial+final were recognized correctly.

### Tone finding (preliminary)

STER rises **0.016 → 0.094** clean→severe: tone errors on syllables the model got
segmentally *right*. It heard the syllable, not the tone.

A spontaneous example from the run, which is the project thesis in one line:

```
ref: 就是以武力統一中國   yi3 wu3 li4 TONG3 yi1   "to unify China by force"
hyp: 就是有利同一中國     you3 li4     TONG2 yi1   "advantageous, the same"
```

統一 (tong**3**) → 同一 (tong**2**) is a pure tone error that changes the word.
Effect is real but modest at n=40; report with n and do not extrapolate.

---

## 3. Speaker identity (`src/speaker_sim.py`)

`microsoft/wavlm-base-plus-sv` x-vector cosine. Underpins the "own voice" claim
and validates the paired-data design.

| comparison | n | mean | std | p05 | p95 |
|---|---|---|---|---|---|
| same-speaker | 9 | 0.888 | 0.060 | 0.783 | 0.948 |
| cross-speaker | 60 | 0.645 | 0.177 | 0.363 | 0.901 |
| clean vs mild | 40 | 0.951 | 0.035 | 0.868 | 0.985 |
| clean vs moderate | 40 | 0.935 | 0.035 | 0.859 | 0.979 |
| clean vs severe | 40 | 0.907 | 0.033 | 0.847 | 0.950 |

**PASS — simulation preserves speaker identity** (severe 0.907 vs threshold
0.766), so clean/dysarthric pairs are the same speaker and the paired design
holds.

### Caveats that matter

An earlier run on a 2-speaker set reported a margin of +0.599. That was
**degenerate**: with 2 speakers there is only one possible cross-pair, measured
repeatedly (std = 0.000). The honest margin with 31 speakers is **+0.243**.

The distributions **overlap**: cross-speaker p95 (0.901) exceeds same-speaker p05
(0.783). WavLM x-vector cosine is therefore a soft discriminator on this data,
and the 0.766 threshold should not be treated as a hard decision boundary.
same-speaker n=9 is also too small — shuffling means few speakers contributed
multiple utterances. Recalibrate on the larger training set.

---

## 4. Performance refactor

Initial data build ran ~3.3 h projected for 1500 utterances. Two causes, both
fixed:

- `pw.harvest` (accurate, ~10x slow) replaced with `pw.dio` + `pw.stonemask`.
- Source-filter analysis was re-run **per severity**; now run **once** per
  utterance and shared across severities (`analyze` / `perturb` split).
- Rate change moved from time-domain `librosa.time_stretch` + re-analysis to
  frame-domain resampling of the F0/spectral/aperiodicity sequences — cheaper
  and avoids two rounds of estimation error.

`verify_sim.py` re-run after the refactor: all three core claims still PASS, so
the speedup did not weaken the perturbation.

**Speaker diversity fix.** Common Voice streams in contributor order, so a
sequential 40-utterance read yielded only **2 speakers**. Adding
`.shuffle(buffer_size=N)` raised that to **31 speakers** from the same 40
utterances. Buffer 3000 is sufficient; 8000 mainly slows the cold start.

---

## 5. Training (`src/train_asr.py`)

Splits are **speaker-disjoint** — splitting by utterance would leak speaker
identity and let the model memorize voices instead of learning dysarthria.
Clean audio is included alongside dysarthric (3000 dys + 1000 clean) to avoid
catastrophic forgetting on normal speech, which a clinical system still needs.

Training set: 1000 utterances, 3000 pairs, **91 speakers**.

### Epoch 1 (stopped here on request)

whisper-small, batch 8 x grad-accum 2, fp16 + gradient checkpointing, 20% of
speakers held out, eval capped at 200 rows stratified by condition.
`runs/asr_v1/checkpoint-204`.

| metric | value |
|---|---|
| eval CER | 0.1644 |
| eval intelligibility | 83.56% |
| eval STER | 0.0491 |
| eval loss | 0.3284 |
| train loss | 11.00 → 0.063 |

GPU: 100% utilization, 7278/8151 MiB — whisper-small at batch 8 nearly saturates
8 GB. Epoch ≈ 20 min.

### Full run: 3 epochs, best model = epoch 1

| epoch | eval CER | intelligibility | STER | train loss |
|---|---|---|---|---|
| 1 | **0.1644** | **83.56%** | 0.0491 | 0.063 |
| 2 | 0.1729 | 82.71% | 0.0499 | 0.0018 |
| 3 | 0.1760 | 82.40% | 0.0500 | 0.0049 |

**Monotonic overfitting from epoch 2 onward.** Train loss reached 0.0018 while
eval CER rose every epoch — 244M parameters memorized 3,200 training rows.
`load_best_model_at_end` with `metric_for_best_model="cer"` correctly restored
checkpoint-204, so the saved model is epoch 1.

Conclusion: **data scale is the binding constraint, not training time.** More
epochs are worthless here; more data is not. Total train runtime 1240 s.

---

## 6. Matched evaluation (`src/evaluate.py`) — the defensible number

Both models scored on the **same** held-out speakers, reusing `build_splits`
with identical seed and eval_frac so the holdout is reproduced exactly rather
than approximated. Broken out per condition, because a mixed average hides where
the model actually improved.

STER figures below are the **corrected, alignment-based** values (see the note
at the top of this file); CER is unchanged.

| condition | CER base | CER tuned | Δ | STER base | STER tuned | Δ |
|---|---|---|---|---|---|---|
| clean | 0.1076 | 0.1155 | **+0.0078** | 0.0269 | 0.0429 | **+0.0161** |
| mild | 0.1605 | 0.1370 | −0.0235 | 0.0401 | 0.0482 | +0.0081 |
| moderate | 0.2074 | 0.1311 | **−0.0763** | 0.0499 | 0.0502 | +0.0003 |
| severe | 0.2877 | 0.1683 | **−0.1194** | 0.0947 | 0.0536 | **−0.0410** |
| **overall** | 0.1908 | 0.1380 | **−0.0528** | 0.0529 | 0.0488 | −0.0041 |

**Intelligibility 80.9% → 86.2% (27.7% relative CER reduction).**

### The gain scales with severity — which is the clinically right shape

Severe improves most (−0.1194, 41% relative), then moderate (−0.0763, 37%),
then mild (−0.0235). The model helps most exactly where speech is least
intelligible.

### Two honest negatives

**Clean speech regressed** (CER +0.0078, STER +0.0167) *despite* clean audio
being included in training specifically to prevent this. Mitigation was partial,
not sufficient. A deployed system should route clean input to the base model, or
the clean:dysarthric ratio needs raising.

**Tone barely moved overall** (−0.0041), and the per-condition split explains
why the aggregate is misleading: severe STER improved substantially (0.0947 →
0.0536, 43% relative) while clean, mild and moderate STER all got slightly
*worse*. Tone recovery happened only where degradation was most extreme; net
effect across conditions is ~zero.

That is the core finding for the project: **generic ASR fine-tuning does not
solve tone.** Character accuracy improved 27.7% while tone accuracy stood still.
Tone needs explicit modelling — which is precisely the gap OwnVoice targets, and
which the closest prior work does not address (see `prior-art.md`).

### Caveat that limits all of the above

The model was trained on the same simulation it was evaluated on, so part of the
gain may be *learning to invert perturbations we designed* rather than learning
dysarthria. Testing against EasyCall (real dysarthric speech, `data_real.py`) is
the way to separate those. Until then, treat 86.2% as an architecture-comparison
figure, not an intelligibility claim.

---

## 7. Voice conversion (`src/vc.py`) — NEGATIVE RESULT

After the prior-art review (see `prior-art.md`) the plan was to replace the
ASR→TTS cascade with LLE voice conversion: Chinese-HuBERT content features,
nearest-neighbour reconstruction against clean reference speech, HiFi-GAN
vocoding. Both models MIT-licensed, no training required.

**It does not currently beat leaving the audio alone.**

First evaluation, severe dysarthria, oracle same-speaker reference, n=12:

| | CER | STER | intelligibility | spk sim |
|---|---|---|---|---|
| dysarthric | 0.4048 | 0.1507 | 59.5% | 0.887 |
| converted | 0.4881 | 0.1071 | 51.2% | 0.868 |
| delta | **+0.0833** | −0.0435 | −8.3% | −0.019 |

Identity was preserved (0.868 > 0.766 threshold) and tone improved, but
intelligibility got materially worse.

### Diagnosis 1 — the vocoder is not to blame

Round-trip ablation (`ablate_vocoder.py`), mel → waveform with no conversion:

| condition | CER |
|---|---|
| clean | 0.3077 |
| clean → round trip | **0.2885** |
| dysarthric | 0.5000 |
| dysarthric → round trip | 0.6538 |

On clean speech the vocoder costs **−0.019 CER** — transparent, marginally
beneficial (it smooths noise). Since LLE output is assembled from *clean*
reference mels, it inherits the transparent path, not the degraded one. The
failure is in the LLE step.

(Note the separate finding that HiFi-GAN badly degrades *dysarthric* audio,
+0.154 CER — it was trained on healthy speech and dysarthric acoustics are out
of distribution. Not our failure mode here, but relevant to any design that
vocodes pathological speech directly.)

### Diagnosis 2 — layer choice was a real bug, but not the fix

`content_features` originally used `last_hidden_state`, i.e. layer 24 of 24. In
self-supervised speech models the deepest layers re-encode acoustic and speaker
detail while intermediate layers carry speaker-invariant phonetic content, so
nearest-neighbour search was matching voice texture instead of content.

Layer sweep, severe, oracle reference:

| layer | n=8 ΔCER | n=24 ΔCER |
|---|---|---|
| 6 | −0.0238 | **+0.0403** (sign flip) |
| 9 | +0.0952 | — |
| 12 | −0.0238 | **−0.0268** (replicated) |
| 18 | +0.1667 | — |
| 24 | +0.1190 | — |

Layer 6 reversed sign between sample sizes — the n=8 sweep was measuring noise.
Layer 12 replicated a modest −0.0268 CER, and `DEFAULT_LAYER` is set to 12.

### Honest status

Best VC configuration gives roughly **−0.027 CER (~6% relative)** — and even
that comes with STER *worsening* by +0.037, and is measured in **oracle mode**
using the speaker's own clean recordings, which no real patient has.

Compare the ASR route: **−0.0528 CER overall, −0.1194 on severe**, on a matched
test set, with no oracle. **The cascade is the working prototype; the VC route is
not.**

### Why it likely fails here when it worked for the Sinica group

- Their stage-1 winner was VTN, a *trained* seq2seq; LLE was the low-data
  comparison, not the headline.
- Their reference was four normal speakers with substantial data. Ours is one
  speaker, ~13.7k frames.
- Their dysarthria is real and moderate; our "severe" preset may be more extreme
  than real severe, pushing Chinese-HuBERT features far out of distribution so
  neighbour search cannot find the right phonetic content at any layer.

### Next options, in order of expected value

1. Use the **fine-tuned Whisper encoder** as the content extractor — it was
   explicitly adapted to dysarthric input, unlike Chinese-HuBERT.
2. Much larger, multi-speaker reference dictionaries.
3. Train VTN-style seq2seq conversion on our parallel pairs (we have exact
   clean/dysarthric alignment, which the Sinica group did not).
4. Test on mild/moderate rather than severe, where features stay in
   distribution.

---

### Superseded: the earlier invalid comparison

Baseline was measured on `data/dev2`; training eval used held-out speakers from
`data/train`. **Different test sets**, so this is indicative only:

```
baseline mixed CER  ~ 0.249  ->  epoch-1 0.164   (~34% relative reduction)
baseline mixed STER ~ 0.0445 ->  epoch-1 0.0491  (no improvement, maybe worse)
```

The STER result is the interesting one: character recognition improved
substantially while **tone accuracy did not**. If that survives a matched-test-set
evaluation, it is direct evidence for the central claim — tone is a separate,
harder failure that generic ASR fine-tuning does not fix. It could equally be an
artifact of the mismatched test sets. **Do not cite it in either direction until
before/after are measured on one identical set.**

Also note the mixed average hides per-condition behaviour. Severe (baseline CER
0.474) is what matters clinically, and a good mixed number could be carried
entirely by the clean and mild rows.

### Fragility fixed

An earlier background build was killed at ~30% and lost ~1,900 WAVs, because
transcripts existed only in the manifest and the manifest was written once at the
end. `Manifest` now appends and flushes per utterance, so a partial build stays
usable.

Monitoring note: piping a training run through PowerShell `Select-String` buffers
until the stream closes — interim loss and eval lines never appear. Redirect to a
file and tail it.

---

## Standing caveat

Every number here is on **perturbation-simulated** dysarthria, not real patient
speech. Per Interspeech 2025 (*"Synthetic Dysarthric Speech: A Supplement, Not a
Substitute for Authentic"*), simulation is valid for architecture development and
unusable for validation.

Real-data path: MDSC (AISHELL-6B) is least encumbered; CDSD, TORGO and UASpeech
need signed licenses. See `datasets.md`. **File those applications** — approval
lag is weeks and the competition build phase starts mid-September.
