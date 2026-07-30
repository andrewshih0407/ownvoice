"""
Loader for REAL dysarthric speech corpora (as opposed to `data.py`'s simulation).

Why this is a separate module: real corpora are fundamentally shaped differently
from the simulated ones. There is no paired clean counterpart — a dysarthric
speaker cannot produce the same utterance without dysarthria — so the manifest
carries only the dysarthric audio, and severity comes from the corpus's own
clinical labels rather than from a perturbation setting we chose.

Available today
---------------
easycall   changelinglab/easycall-dysarthria      CC-BY-NC-2.0, ungated
           21,386 utterances (11,901 train / 4,272 val / 5,213 test)
           Italian. Isolated command words. Per-speaker severity labels.

What EasyCall CAN establish:
    Whether the approach works on real dysarthria at all — i.e. whether
    fine-tuning genuinely helps on authentic pathological speech rather than on
    perturbations we designed and therefore already know how to invert. That is
    the single biggest open risk in the project and it is language-independent.

What EasyCall CANNOT establish:
    - Anything about tone. Italian is not tonal, so TER/STER are meaningless
      here and `metrics.py`'s tone functions must not be applied.
    - Continuous-speech performance. These are isolated command words, so there
      is almost no language-model context; CER here is not comparable to CER on
      Mandarin sentences.
    - The Taiwan clinical case, which needs Mandarin patient speech.

Requires a signed licence (weeks of lead time — file these now)
--------------------------------------------------------------
    MDSC / AISHELL-6B   Mandarin, 17 h, 21 dysarthric speakers  <- what we need
    CDSD                Mandarin, 133 h, 44 speakers
    TORGO               English, articulatory data, LDC
    UASpeech            English, 102 h

NOT USABLE: the unlicensed TORGO re-uploads on the Hub. They are restricted
patient medical data redistributed without authorization. Beyond the ethics, the
competition handbook makes improper data acquisition an explicit disqualification
criterion, so using them would put the entire submission at risk.
"""

from __future__ import annotations

import io
import json
from pathlib import Path

import librosa
import numpy as np
import soundfile as sf

TARGET_SR = 16_000

SOURCES = {
    "easycall": dict(
        repo="changelinglab/easycall-dysarthria",
        text_col="text",
        speaker_col="speaker",
        severity_col="dysarthria_severity",
        language="it",
        license="CC-BY-NC-2.0",
        tonal=False,
    ),
}


def _decode(raw: dict) -> tuple[np.ndarray, int] | None:
    """Decode a non-decoded HF audio value, bypassing datasets/torchcodec."""
    if raw is None:
        return None
    try:
        if raw.get("bytes"):
            y, sr = sf.read(io.BytesIO(raw["bytes"]), dtype="float64")
        elif raw.get("path"):
            y, sr = sf.read(raw["path"], dtype="float64")
        else:
            return None
    except Exception:
        return None
    if getattr(y, "ndim", 1) > 1:
        y = y.mean(axis=1)
    return np.asarray(y, dtype=np.float64), int(sr)


def build(
    source: str = "easycall",
    split: str = "train",
    limit: int = 2000,
    out_dir: str | Path = "data/real_easycall",
    min_dur: float = 0.2,
    max_dur: float = 12.0,
    shuffle_buffer: int = 4000,
    seed: int = 0,
) -> Path:
    """Materialize a real dysarthric corpus into WAVs + a manifest.

    Manifest schema matches `data.py` except:
        simulated   = False
        clean_path  = None       (no paired clean audio exists)
        severity    = the corpus's own clinical label
    """
    from datasets import Audio, load_dataset

    if source not in SOURCES:
        raise ValueError(f"source must be one of {list(SOURCES)}")
    spec = SOURCES[source]

    out_dir = Path(out_dir)
    (out_dir / "dys").mkdir(parents=True, exist_ok=True)

    print(
        f"source={source}  language={spec['language']}  "
        f"license={spec['license']}  tonal={spec['tonal']}"
    )
    if not spec["tonal"]:
        print(
            "NOTE: non-tonal language — TER/STER are meaningless here. "
            "Report CER only."
        )

    ds = load_dataset(spec["repo"], split=split, streaming=True)
    for col, feat in (ds.features or {}).items():
        if isinstance(feat, Audio):
            ds = ds.cast_column(col, Audio(decode=False))
    if shuffle_buffer > 0:
        ds = ds.shuffle(seed=seed, buffer_size=shuffle_buffer)

    fh = (out_dir / "manifest.jsonl").open("w", encoding="utf-8")
    rows: list[dict] = []
    kept = skipped = 0

    try:
        for i, ex in enumerate(ds):
            if kept >= limit:
                break
            text = (ex.get(spec["text_col"]) or "").strip()
            dec = _decode(ex.get("audio"))
            if not text or dec is None:
                skipped += 1
                continue
            y, sr = dec
            if sr != TARGET_SR:
                y = librosa.resample(y, orig_sr=sr, target_sr=TARGET_SR)
            dur = len(y) / TARGET_SR
            if not (min_dur <= dur <= max_dur):
                skipped += 1
                continue
            peak = np.abs(y).max()
            if peak < 1e-4:
                skipped += 1
                continue
            y = (y / peak * 0.95).astype(np.float32)

            uid = f"{source}_{i:06d}"
            p = out_dir / "dys" / f"{uid}.wav"
            sf.write(p, y, TARGET_SR)

            row = {
                "id": uid,
                "text": text,
                "clean_path": None,
                "dys_path": str(p.relative_to(out_dir)),
                "severity": str(ex.get(spec["severity_col"], "unknown")),
                "speaker": str(ex.get(spec["speaker_col"], "unk")),
                "duration": round(dur, 3),
                "simulated": False,
                "language": spec["language"],
            }
            rows.append(row)
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
            fh.flush()
            kept += 1
            if kept % 250 == 0:
                print(f"  {kept}/{limit}", flush=True)
    finally:
        fh.close()

    from collections import Counter

    print(f"\nwrote {kept} utterances ({skipped} skipped) -> {out_dir}")
    print(f"speakers: {len({r['speaker'] for r in rows})}")
    print("severity distribution:", dict(Counter(r["severity"] for r in rows)))
    return out_dir / "manifest.jsonl"


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description="Build a real dysarthric corpus.")
    ap.add_argument("--source", default="easycall", choices=list(SOURCES))
    ap.add_argument("--split", default="train")
    ap.add_argument("--limit", type=int, default=2000)
    ap.add_argument("--out", default="../data/real_easycall")
    ap.add_argument("--shuffle-buffer", type=int, default=4000)
    a = ap.parse_args()
    build(
        source=a.source,
        split=a.split,
        limit=a.limit,
        out_dir=a.out,
        shuffle_buffer=a.shuffle_buffer,
    )
