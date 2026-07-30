"""
Baseline: how badly does dysarthria break off-the-shelf Mandarin ASR?

This is the "before" number. Every later claim about restoration is measured
against it, so it runs first and its output is the project's reference point.

It also produces the core evidence for the project's premise: if tone error rate
degrades faster than character error rate, then Mandarin dysarthria is not just
"harder ASR" — it is specifically a tonal failure, which is the argument that
distinguishes this work from the English-language dysarthria literature.

SCRIPT NORMALIZATION (do not remove)
    Common Voice zh-TW references are Traditional Chinese; Whisper frequently
    emits Simplified. Scoring them directly measures orthography, not
    recognition, and inflates CER by tens of points. Both sides are normalized
    to Traditional before scoring.
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

import soundfile as sf
import torch
import zhconv

from metrics import score_corpus

CONDITIONS = ["clean", "mild", "moderate", "severe"]


def normalize(text: str) -> str:
    """Traditional Chinese, whitespace and common punctuation stripped."""
    text = zhconv.convert(text or "", "zh-tw")
    drop = " \t\n，。、？！：；「」『』（）,.?!:;\"'()《》…—-·"
    return "".join(c for c in text if c not in drop)


def load_asr(model_id: str, device: str):
    from transformers import pipeline

    torch_dtype = torch.float16 if device == "cuda" else torch.float32
    return pipeline(
        "automatic-speech-recognition",
        model=model_id,
        device=0 if device == "cuda" else -1,
        torch_dtype=torch_dtype,
        chunk_length_s=30,
    )


def transcribe_all(asr, paths: list[Path], batch_size: int) -> list[str]:
    """Transcribe WAVs by passing decoded arrays, not filenames.

    The HF pipeline shells out to ffmpeg when given a path, which isn't
    installed here. Our WAVs are already mono 16 kHz, so soundfile reads them
    directly and we hand the pipeline arrays — one less system dependency.
    """
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
            # Degraded input drives Whisper into repetition loops, producing
            # CER > 1 from insertions alone. These curb the loop; residual
            # hallucination is measured and reported rather than hidden.
            "no_repeat_ngram_size": 4,
            "repetition_penalty": 1.15,
        },
    )
    if isinstance(out, dict):
        out = [out]
    return [o["text"] for o in out]


def hallucination_rate(pairs: list[tuple[str, str]], factor: float = 2.0) -> float:
    """Fraction of clips whose hypothesis exceeds `factor` x reference length.

    Reported separately because it is a different failure from mis-recognition:
    a looping decoder yields unbounded CER, which would otherwise swamp the
    intelligibility figure and make conditions incomparable.
    """
    if not pairs:
        return 0.0
    bad = sum(1 for r, h in pairs if len(r) and len(h) > factor * len(r))
    return bad / len(pairs)


def main(
    root: str = "../data/dev",
    model_id: str = "openai/whisper-small",
    limit: int | None = None,
    batch_size: int = 4,
) -> None:
    root = Path(root)
    manifest = root / "manifest.jsonl"
    if not manifest.exists():
        raise SystemExit(f"no manifest at {manifest} — run data.py first")

    rows = [json.loads(l) for l in manifest.open(encoding="utf-8")]

    # Group by condition. "clean" is deduped since each clean file is shared
    # across the severity variants generated from it.
    jobs: dict[str, list[tuple[Path, str]]] = defaultdict(list)
    seen_clean: set[str] = set()
    for r in rows:
        jobs[r["severity"]].append((root / r["dys_path"], r["text"]))
        if r["clean_path"] not in seen_clean:
            seen_clean.add(r["clean_path"])
            jobs["clean"].append((root / r["clean_path"], r["text"]))

    if limit:
        jobs = {k: v[:limit] for k, v in jobs.items()}

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"model={model_id}  device={device}")
    if device == "cpu":
        print("NOTE: running on CPU — slow. Re-run after the GPU driver is up.")
    asr = load_asr(model_id, device)

    results: dict[str, object] = {}
    halluc: dict[str, float] = {}
    for cond in CONDITIONS:
        items = jobs.get(cond)
        if not items:
            continue
        paths = [p for p, _ in items]
        refs = [t for _, t in items]
        print(f"\ntranscribing {cond} ({len(paths)} clips)...")
        hyps = transcribe_all(asr, paths, batch_size)
        pairs = [(normalize(r), normalize(h)) for r, h in zip(refs, hyps)]
        results[cond] = score_corpus(pairs)
        halluc[cond] = hallucination_rate(pairs)
        # Show one example so script/format problems are visible immediately.
        print(f"  ref: {pairs[0][0][:40]}")
        print(f"  hyp: {pairs[0][1][:40]}")

    hdr = (
        f"\n{'condition':<12} {'CER':>7} {'STER':>7} {'halluc':>8} "
        f"{'intellig.':>10} {'chars':>7}"
    )
    print(hdr)
    print("-" * (len(hdr) - 1))
    for cond in CONDITIONS:
        s = results.get(cond)
        if not s:
            continue
        flag = "  <-- unreliable" if s.cer > 1.0 else ""
        print(
            f"{cond:<12} {s.cer:>7.3f} {s.ster:>7.3f} "
            f"{halluc.get(cond, 0.0):>7.0%} {s.intelligibility:>9.1f}% "
            f"{s.n_ref_chars:>7}{flag}"
        )
    print(
        "\nCER > 1.0 means insertions exceed the reference length: the decoder is\n"
        "looping, not mis-hearing. Intelligibility is meaningless for those rows."
    )

    # Premise test. STER, not TER: TER is computed from recognized text, so it
    # inherits every character error and cannot separate tone from segmental
    # failure. STER counts tone errors only on syllables whose initial+final
    # were correct, which is the only tone-specific signal available here.
    reliable = [c for c in CONDITIONS if (results.get(c) and results[c].cer <= 1.0)]
    clean = results.get("clean")
    worst = results.get(reliable[-1]) if len(reliable) > 1 else None
    if clean and worst:
        name = reliable[-1]
        print(
            f"\ntone-specific test (clean -> {name}, the most degraded "
            f"non-looping condition):"
        )
        print(f"  STER {clean.ster:.3f} -> {worst.ster:.3f}")
        if worst.ster > clean.ster + 0.01:
            print(
                "  Tone errors appear on syllables that were segmentally CORRECT,\n"
                "  i.e. the model heard the syllable but not its tone. This is the\n"
                "  tone-specific failure the project targets. Effect is real but\n"
                "  modest at this severity and sample size — report it as\n"
                "  preliminary, with n, and do not extrapolate."
            )
        else:
            print(
                "  No tone-specific effect beyond segmental error on this data.\n"
                "  Do NOT assert the tonal-failure framing without stronger "
                "evidence."
            )

    out = root / "baseline.json"
    out.write_text(
        json.dumps(
            {
                "model": model_id,
                "device": device,
                "simulated": True,
                "n_utterances_per_condition": {
                    k: len(v) for k, v in jobs.items()
                },
                "hallucination_rate": halluc,
                "results": {k: v.as_dict() for k, v in results.items()},
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    print(f"\nwrote {out}")


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="../data/dev")
    ap.add_argument("--model", default="openai/whisper-small")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--batch-size", type=int, default=4)
    a = ap.parse_args()
    main(a.root, a.model, a.limit, a.batch_size)
