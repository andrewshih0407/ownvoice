"""
Matched before/after evaluation — two models, one identical test set.

This exists because the epoch-1 number was NOT comparable to the baseline:
`baseline.py` measured `data/dev2` while training evaluated held-out speakers of
`data/train`. Different test sets cannot support an improvement claim, however
tempting the direction of the numbers.

Here both models are scored on exactly the same held-out speakers, reusing
`build_splits` with the same seed and eval_frac as training so the speaker
holdout is reproduced bit-for-bit rather than approximated.

Results are broken out PER CONDITION. A mixed average hides where a model
actually improved: severe dysarthria is what matters clinically, and a good
average can be carried entirely by the clean and mild rows.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

import soundfile as sf
import torch
import zhconv

from metrics import score_corpus
from train_asr import build_splits

CONDITIONS = ["clean", "mild", "moderate", "severe"]


def normalize(text: str) -> str:
    """Must stay identical to baseline.py and train_asr.py."""
    text = zhconv.convert(text or "", "zh-tw")
    drop = " \t\n，。、？！：；「」『』（）,.?!:;\"'()《》…—-·"
    return "".join(c for c in text if c not in drop)


def load_asr(model_id: str, device: str):
    from transformers import pipeline

    return pipeline(
        "automatic-speech-recognition",
        model=model_id,
        device=0 if device == "cuda" else -1,
        torch_dtype=torch.float16 if device == "cuda" else torch.float32,
        chunk_length_s=30,
    )


def transcribe(asr, paths: list[Path], batch_size: int) -> list[str]:
    inputs = []
    for p in paths:
        y, sr = sf.read(p, dtype="float32", always_2d=False)
        if y.ndim > 1:
            y = y.mean(axis=1)
        inputs.append({"raw": y, "sampling_rate": int(sr)})
    out = asr(
        inputs,
        batch_size=batch_size,
        generate_kwargs={
            "language": "zh",
            "task": "transcribe",
            "no_repeat_ngram_size": 4,
            "repetition_penalty": 1.15,
        },
    )
    if isinstance(out, dict):
        out = [out]
    return [o["text"] for o in out]


def evaluate_model(
    model_id: str, buckets: dict[str, list[dict]], root: Path, device: str, bs: int
) -> dict:
    asr = load_asr(model_id, device)
    scores = {}
    for cond in CONDITIONS:
        rows = buckets.get(cond)
        if not rows:
            continue
        paths = [root / r["audio_path"] for r in rows]
        hyps = transcribe(asr, paths, bs)
        pairs = [
            (normalize(r["text"]), normalize(h)) for r, h in zip(rows, hyps)
        ]
        scores[cond] = score_corpus(pairs)
        print(f"    {cond:<10} CER={scores[cond].cer:.4f}")
    del asr
    if device == "cuda":
        torch.cuda.empty_cache()
    return scores


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="../data/train")
    ap.add_argument("--base", default="openai/whisper-small")
    ap.add_argument("--tuned", required=True, help="path to fine-tuned checkpoint")
    # These MUST match the training run or the holdout is not reproduced.
    ap.add_argument("--eval-frac", type=float, default=0.2)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--severities", nargs="+",
                    default=["mild", "moderate", "severe"])
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
    print(f"\n[2/2] fine-tuned: {a.tuned}")
    tuned = evaluate_model(a.tuned, buckets, root, device, a.batch_size)

    hdr = (
        f"\n{'condition':<10} | {'CER base':>9} {'CER tuned':>10} {'Δ':>8} | "
        f"{'STER base':>10} {'STER tuned':>11} {'Δ':>8}"
    )
    print(hdr)
    print("-" * (len(hdr) - 1))
    for cond in CONDITIONS:
        b, t = base.get(cond), tuned.get(cond)
        if not b or not t:
            continue
        print(
            f"{cond:<10} | {b.cer:>9.4f} {t.cer:>10.4f} {t.cer-b.cer:>+8.4f} | "
            f"{b.ster:>10.4f} {t.ster:>11.4f} {t.ster-b.ster:>+8.4f}"
        )

    # Weighted overall, by reference characters — not a mean of rates.
    def overall(d: dict, attr: str) -> float:
        num = sum(getattr(s, attr) * s.n_ref_chars for s in d.values())
        den = sum(s.n_ref_chars for s in d.values())
        return num / den if den else 0.0

    b_cer, t_cer = overall(base, "cer"), overall(tuned, "cer")
    b_ster, t_ster = overall(base, "ster"), overall(tuned, "ster")
    print("-" * (len(hdr) - 1))
    print(
        f"{'OVERALL':<10} | {b_cer:>9.4f} {t_cer:>10.4f} {t_cer-b_cer:>+8.4f} | "
        f"{b_ster:>10.4f} {t_ster:>11.4f} {t_ster-b_ster:>+8.4f}"
    )

    print(
        f"\nintelligibility: {(1-b_cer)*100:.1f}% -> {(1-t_cer)*100:.1f}%"
        f"   ({(b_cer-t_cer)/b_cer*100:+.1f}% relative CER change)"
        if b_cer
        else ""
    )

    # The tone question this project exists to answer.
    print()
    if t_ster < b_ster - 0.005:
        print(
            "Tone errors DECREASED alongside character errors: fine-tuning on "
            "simulated\ndysarthria improved tone recovery too."
        )
    elif t_ster > b_ster + 0.005:
        print(
            "Tone errors INCREASED while character errors fell. Fine-tuning "
            "bought segmental\naccuracy at the cost of tone — direct support for "
            "treating tone as a distinct\nfailure mode needing explicit "
            "modelling, which is OwnVoice's core argument."
        )
    else:
        print(
            "Tone errors essentially UNCHANGED while character errors moved. "
            "Generic ASR\nfine-tuning does not address tone; it needs explicit "
            "modelling. This is the gap\nOwnVoice targets."
        )

    out = root / "matched_eval.json"
    out.write_text(
        json.dumps(
            {
                "base": a.base,
                "tuned": a.tuned,
                "held_out_speakers": n_speakers,
                "eval_frac": a.eval_frac,
                "seed": a.seed,
                "simulated": True,
                "per_condition": {
                    "base": {k: v.as_dict() for k, v in base.items()},
                    "tuned": {k: v.as_dict() for k, v in tuned.items()},
                },
                "overall": {
                    "base_cer": b_cer,
                    "tuned_cer": t_cer,
                    "base_ster": b_ster,
                    "tuned_ster": t_ster,
                },
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    print(f"\nwrote {out}")
    print(
        "\nREMINDER: simulated dysarthria. Valid for architecture comparison, "
        "not for\nany published intelligibility claim."
    )


if __name__ == "__main__":
    main()
