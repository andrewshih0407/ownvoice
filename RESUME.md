# Resume here

Paused mid-training on request. Everything below is on disk.

## State

| thing | status |
|---|---|
| Code (`src/`, 7 modules) | committed to git |
| Docs (`README`, `datasets.md`, `results.md`) | committed |
| Training data `data/train/` | 1000 utts, 3000 pairs, **91 speakers**, manifest written |
| Dev data `data/dev2/` | 40 utts, 31 speakers, baseline + speaker calibration |
| Checkpoint `runs/asr_v1/checkpoint-204` | **epoch 1 of 3, saved** (922 MB model + 1.8 GB optimizer) |
| Training run | **stopped at epoch 1/3** |

Data and checkpoints are gitignored (large, and real dysarthria corpora are
license-restricted patient data that must never be redistributed).

## Epoch 1 result

whisper-small, 1 epoch, mixed eval (clean+mild+moderate+severe, 200 rows
stratified, held-out speakers):

```
eval_cer            0.1644
eval_intelligibility  83.56%
eval_ster           0.0491
eval_loss           0.3284
train loss          11.00 -> 0.063   (converging cleanly)
```

## The comparison that still needs doing — read this first

The epoch-1 number is **not** directly comparable to the baseline. Baseline was
measured on `data/dev2`; training eval used held-out speakers from `data/train`.
Different test sets.

Rough, non-rigorous comparison (baseline per-condition, equally weighted):

```
baseline mixed CER  ~ (0.107 + 0.168 + 0.248 + 0.474) / 4 = 0.249
epoch-1  mixed CER  = 0.164                  -> ~34% relative CER reduction

baseline mixed STER ~ (0.016 + 0.034 + 0.034 + 0.094) / 4 = 0.0445
epoch-1  mixed STER = 0.0491                 -> NO improvement, possibly worse
```

**That STER result is the interesting one.** Character recognition improved
substantially while tone accuracy did not. If it holds up on a matched test set,
it is direct evidence for the project's central claim: tone is a *separate,
harder* failure mode that general ASR fine-tuning does not fix. That is the gap
OwnVoice exists to close.

It could also be an artifact of comparing two different test sets. **Do not cite
it either way until the next step is run.**

## Next steps, in order

1. **Matched before/after evaluation.** Run `baseline.py` against the held-out
   speakers of `data/train`, then evaluate `checkpoint-204` on that identical
   set. Until both numbers come from one test set, no improvement claim is
   defensible.

2. **Finish training.** 2 of 3 epochs remain. Resume from the checkpoint:

   ```
   cd src
   python -u train_asr.py --root ../data/train --model openai/whisper-small \
     --out ../runs/asr_v1 --epochs 3 --batch-size 8 --grad-accum 2 \
     --eval-frac 0.2 --max-eval 200
   ```

   Add `--resume-from-checkpoint ../runs/asr_v1/checkpoint-204` (needs wiring
   into `train_asr.py` — currently unimplemented) or just rerun from scratch;
   epoch 1 took roughly 20 min on the RTX 5060.

   **Do not pipe the run through `Select-String`** — it buffers until the stream
   closes, so interim loss and eval lines are invisible. Redirect to a file and
   `tail` it instead.

3. **Per-condition eval.** The mixed average hides where the model actually
   improved. Severe (baseline 0.474) is what matters clinically; a good mixed
   number could be carried entirely by clean and mild.

4. **Scale data.** 1000 utterances is small. Build 5-10k
   (`data.py --limit 10000`), roughly 1.7 utt/s so ~1-2 h.

5. **Stage 2 — voice cloning**, the actual "own voice" differentiator, not yet
   started. Needs a Mandarin zero-shot TTS (CosyVoice 2, F5-TTS, or IndexTTS).
   The evaluation metric already exists in `speaker_sim.py`.

6. **File the dataset licence applications.** Still the true critical path — see
   `docs/datasets.md`. Everything so far is on *simulated* dysarthria, which per
   Interspeech 2025 is valid for development and unusable for validation.

## Standing caveats

- Every number is on **simulated** dysarthria. No intelligibility claim is
  publishable until measured on real patient speech.
- **Jitter perturbation is unvalidated** — no graded effect detected. Do not
  claim jitter modelling. See `results.md` §1.
- Speaker-similarity distributions **overlap** (cross p95 0.901 vs same p05
  0.783), so 0.766 is a soft threshold, not a decision boundary. same-speaker
  n=9 is too small; recalibrate on `data/train`.

## Competition context

- Submission deadline **July 31, 2026, 17:00 GMT+8** — a written online form, no
  prototype required.
- Team must be **3-10 members with at least one non-Taiwanese national**. Still
  unresolved and it is an eligibility gate.
- Finals (late Oct) weight Implementation & Verification at 30%, scored as
  *progress since submission* — so submitting early-stage is fine, arguably
  better.
