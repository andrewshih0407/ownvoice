# Resume here

## Prototype status

| component | status |
|---|---|
| Data pipeline + simulation | **working**, acoustically validated |
| Tone-aware metrics (CER / TER / STER) | **working** |
| Speaker-identity calibration | **working** |
| Stage 1 — dysarthria-robust Mandarin ASR | **WORKING** — the prototype |
| Stage 1 alt — LLE voice conversion | **fails**, diagnosed, documented |
| Stage 2 — own-voice restoration | **not built** |

Git: 3 commits, 21 files. Data and checkpoints gitignored.

## The working result

`runs/asr_v1` — whisper-small fine-tuned on simulated dysarthric Mandarin.
Matched evaluation, both models on identical held-out speakers:

| condition | CER base → tuned | Δ |
|---|---|---|
| clean | 0.1076 → 0.1155 | +0.0078 (regression) |
| mild | 0.1605 → 0.1370 | −0.0235 |
| moderate | 0.2074 → 0.1311 | −0.0763 |
| severe | 0.2877 → 0.1683 | **−0.1194** |
| overall | 0.1908 → 0.1380 | **−0.0528** |

**Intelligibility 80.9% → 86.2% (−27.7% relative CER).** Gains scale with
severity, which is the clinically correct shape.

## What does NOT work — read before pitching

**There is no audio output yet.** Stage 2 (restoring the patient's own voice) is
unbuilt, and the LLE voice-conversion route that was supposed to replace the
cascade *degrades* intelligibility (+0.0833 CER). Full diagnosis in
`results.md` §7.

Consequence for any demo: the system currently converts dysarthric speech to
**text**, not to restored speech. The "hear them speak again" moment is not
available. Do not build a pitch around it.

**Tone did not improve** overall (STER −0.0037) even as CER fell 27.7%. That is
the project's most useful finding — generic ASR fine-tuning does not fix tone —
but it means the tone claim is currently *motivating evidence*, not a solved
problem.

**Everything is simulated.** The model was trained on perturbations we designed,
so some of the 27.7% may be learning to invert our own simulation. `data_real.py`
loads EasyCall (real dysarthric speech, CC-BY-NC-2.0, 21k utterances, Italian)
which would settle this. Not yet run.

## Next steps

1. **Validate on EasyCall.** Single highest-value experiment: does the gain
   survive on real dysarthric speech? `python data_real.py --limit 2000`
2. **More data.** Training overfits after 1 epoch (train loss 0.0018, eval CER
   rising). Data scale is the binding constraint. `data.py --limit 10000`.
3. **Fix clean-speech regression.** Route clean input to the base model, or
   raise the clean:dysarthric ratio in training.
4. **Stage 2**, best options first: fine-tuned Whisper encoder as VC content
   extractor; larger multi-speaker references; VTN-style trained conversion on
   our parallel pairs; or test mild/moderate instead of severe.

## Key commands

```
cd src
python data.py --limit 10000 --out ../data/train_big     # build data
python train_asr.py --root ../data/train --epochs 1      # 1 epoch is optimal
python evaluate.py --root ../data/train --tuned ../runs/asr_v1   # matched eval
python verify_sim.py --root ../data/dev2                 # simulation validity
```

Do not pipe training through PowerShell `Select-String` — it buffers until the
stream closes. Redirect to a file and tail it.

## Standing caveats

- Simulated dysarthria only; no publishable intelligibility claim.
- **Jitter perturbation unvalidated** — no graded effect. Do not claim it.
- Speaker-similarity distributions overlap (cross p95 0.901 vs same p05 0.783);
  0.766 is a soft threshold.
- Sampling noise is severe at small n — a layer sweep flipped sign between n=8
  and n=24. Require n≥50 before believing any margin under 0.05 CER.

## Prior art — repositioning required

`docs/prior-art.md`. Academia Sinica + Chi Mei Hospital already published
own-voice-preserving dysarthric restoration, and their architecture
(Chinese-HuBERT + Seed-VC) is better validated than ours. **"Restore dysarthric
speech in the patient's own voice" is not novel.**

What remains unclaimed: **tone**. Their paper mentions "tone" zero times while
reporting CER 23 times. Reposition around tone-aware restoration for tonal
languages, and treat Academia Sinica as a collaboration target — the handbook
scores "engaged collaboration units".

## Competition

- Deadline **July 31, 2026, 17:00 GMT+8** — online form, written, no prototype
  required.
- Team **3–10 members, ≥1 non-Taiwanese national** — unresolved eligibility gate.
- Finals score *progress since submission* at 30%, so an early-stage submission
  with a credible plan is a good position.
