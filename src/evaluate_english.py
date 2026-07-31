"""
Matched before/after evaluation for the ENGLISH model — WER, not CER.

Why this exists separately from evaluate.py: the English training run's
internal eval metric (final_eval.json, 97.9% "intelligibility") is a CHARACTER
error rate applied to English text. That is the wrong unit for English and it
flatters the result — a single wrong word costs only a few character edits out
of a much longer string, so CER stays low even when word-level accuracy is
mediocre. English ASR is conventionally scored with WORD error rate, and that
is what decides whether this model is fit to ship.

This reuses build_splits with the EXACT seed and eval_frac used at training
time (seed=0, eval_frac=0.2 — confirmed against runs/train_en.log: "55 total,
11 held out"), so the held-out speakers here are the speakers asr_en never
trained on, not an approximation.

Text normalization uses jiwer's standard English transform (lowercase, strip
punctuation, collapse whitespace). This does NOT fully resolve orthographic
convention mismatches — LibriSpeech references spell out numbers and titles
("mister", "one hundred") while Whisper emits standard orthography ("mr",
"100") — so some residual inflation of WER is expected and reported, not
hidden.
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

import jiwer
import soundfile as sf
import torch

sys.path.insert(0, str(Path(__file__).resolve().parent))
from train_asr import build_splits  # reuses the exact split logic from training

TARGET_SR = 16_000
CONDITIONS = ["clean", "mild", "moderate", "severe"]

_TRANSFORM = jiwer.Compose(
    [
        jiwer.ToLowerCase(),
        jiwer.RemovePunctuation(),
        jiwer.RemoveMultipleSpaces(),
        jiwer.Strip(),
        jiwer.ReduceToListOfListOfWords(),
    ]
)


def load_asr(model_id: str, device: str):
    from transformers import pipeline

    return pipeline(
        "automatic-speech-recognition",
        model=model_id,
        device=0 if device == "cuda" else -1,
        torch_dtype=torch.float16 if device == "cuda" else torch.float32,
        chunk_length_s=30,
    )


def transcribe(asr, paths: list[Path], bs: int) -> list[str]:
    inputs = []
    for p in paths:
        y, sr = sf.read(p, dtype="float32", always_2d=False)
        if y.ndim > 1:
            y = y.mean(axis=1)
        inputs.append({"raw": y, "sampling_rate": int(sr)})
    out = asr(
        inputs,
        batch_size=bs,
        generate_kwargs={
            "language": "en",
            "task": "transcribe",
            "no_repeat_ngram_size": 4,
            "repetition_penalty": 1.15,
        },
    )
    if isinstance(out, dict):
        out = [out]
    return [o["text"] for o in out]


def wer_cer(refs: list[str], hyps: list[str]) -> tuple[float, float]:
    wer = jiwer.wer(
        refs, hyps, reference_transform=_TRANSFORM, hypothesis_transform=_TRANSFORM
    )
    cer = jiwer.cer(refs, hyps)  # unnormalized, for cross-reference only
    return wer, cer


def evaluate_model(model_id: str, buckets: dict, root: Path, device: str, bs: int):
    asr = load_asr(model_id, device)
    scores = {}
    for cond in CONDITIONS:
        rows = buckets.get(cond)
        if not rows:
            continue
        paths = [root / r["audio_path"] for r in rows]
        hyps = transcribe(asr, paths, bs)
        refs = [r["text"] for r in rows]
        wer, cer = wer_cer(refs, hyps)
        scores[cond] = {"wer": wer, "cer": cer, "n": len(rows)}
        print(f"    {cond:<10} WER={wer:.4f}  CER={cer:.4f}  n={len(rows)}")
    del asr
    if device == "cuda":
        torch.cuda.empty_cache()
    return scores


def main() -> None:
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="../data/train_en")
    ap.add_argument("--base", default="openai/whisper-small")
    ap.add_argument("--tuned", default="../runs/asr_en")
    ap.add_argument("--eval-frac", type=float, default=0.2)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument(
        "--severities", nargs="+", default=["mild", "moderate", "severe"]
    )
    ap.add_argument("--max-per-condition", type=int, default=60)
    ap.add_argument("--batch-size", type=int, default=8)
    a = ap.parse_args()

    root = Path(a.root)
    _, eval_rows = build_splits(
        root, tuple(a.severities), a.eval_frac, a.seed, include_clean=True
    )

    buckets: dict[str, list[dict]] = defaultdict(list)
    for r in eval_rows:
        if len(buckets[r["condition"]]) < a.max_per_condition:
            buckets[r["condition"]].append(r)

    n_speakers = len({r["speaker"] for r in eval_rows})
    print(
        f"\nheld-out speakers: {n_speakers}   "
        + "  ".join(f"{c}={len(buckets[c])}" for c in CONDITIONS if buckets.get(c))
    )
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"device={device}\n")

    print(f"[1/2] baseline: {a.base}")
    base = evaluate_model(a.base, buckets, root, device, a.batch_size)
    print(f"\n[2/2] fine-tuned (English): {a.tuned}")
    tuned = evaluate_model(a.tuned, buckets, root, device, a.batch_size)

    hdr = f"\n{'condition':<10} | {'WER base':>9} {'WER tuned':>10} {'rel Δ':>8}"
    print(hdr)
    print("-" * (len(hdr) - 1))
    for cond in CONDITIONS:
        b, t = base.get(cond), tuned.get(cond)
        if not b or not t:
            continue
        rel = (b["wer"] - t["wer"]) / b["wer"] * 100 if b["wer"] else 0.0
        print(f"{cond:<10} | {b['wer']:>9.4f} {t['wer']:>10.4f} {rel:>+7.1f}%")

    # Weighted overall by utterance count (all conditions have equal n here).
    def overall(d: dict, key: str) -> float:
        tot_n = sum(v["n"] for v in d.values())
        return sum(v[key] * v["n"] for v in d.values()) / tot_n if tot_n else 0.0

    b_wer, t_wer = overall(base, "wer"), overall(tuned, "wer")
    print("-" * (len(hdr) - 1))
    rel = (b_wer - t_wer) / b_wer * 100 if b_wer else 0.0
    print(f"{'OVERALL':<10} | {b_wer:>9.4f} {t_wer:>10.4f} {rel:>+7.1f}%")

    print(f"\nWord accuracy: {(1-b_wer)*100:.1f}% -> {(1-t_wer)*100:.1f}%")
    print(
        "\nNOTE: WER here is inflated by orthographic convention mismatches "
        "(LibriSpeech spells\nout 'mister'/'one hundred'; Whisper emits "
        "'mr'/'100') that affect BOTH models equally,\nso the comparison "
        "between them is valid even though neither absolute number is."
    )

    verdict_path = root / "matched_eval_en.json"
    verdict_path.write_text(
        json.dumps(
            {
                "base": a.base,
                "tuned": a.tuned,
                "held_out_speakers": n_speakers,
                "metric": "WER (jiwer standard English normalization)",
                "per_condition": {"base": base, "tuned": tuned},
                "overall": {"base_wer": b_wer, "tuned_wer": t_wer},
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    print(f"\nwrote {verdict_path}")

    if t_wer < b_wer - 0.02:
        print("\nVERDICT: genuine improvement — safe to ship an English mode.")
    elif t_wer > b_wer + 0.02:
        print(
            "\nVERDICT: fine-tuning made English WORSE. Do NOT ship an English "
            "mode on this\ncheckpoint — route English to stock Whisper instead."
        )
    else:
        print(
            "\nVERDICT: no meaningful difference from stock Whisper. Shipping "
            "this would not\nbe dishonest, but it would not be a differentiator "
            "either — say so plainly if shipped."
        )


if __name__ == "__main__":
    main()
