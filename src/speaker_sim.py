"""
Speaker-identity similarity — the metric behind OwnVoice's central claim.

"Restores speech in the patient's OWN voice" is the differentiating claim, so it
needs a number, not an impression. This provides one: cosine similarity between
WavLM x-vectors (`microsoft/wavlm-base-plus-sv`, a speaker-verification model).

A raw cosine value means nothing on its own, so `calibrate` measures the two
reference distributions on our actual data:

    same-speaker      different utterances, one speaker   -> upper bound
    cross-speaker     different speakers                  -> chance floor

Stage-2 output only counts as "the patient's voice" if it scores near the
same-speaker distribution rather than the cross-speaker one.

It also answers a prerequisite question the paired-data design depends on:
does the dysarthria simulation preserve speaker identity? If perturbation
destroys the voice, then "clean" and "dysarthric" are different speakers and the
pairing is invalid.

Model choice: WavLMForXVector ships inside transformers, so this adds no new
dependency. ECAPA-TDNN (speechbrain) would be marginally stronger but pulls in a
separate framework.
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

import numpy as np
import soundfile as sf
import torch

MODEL_ID = "microsoft/wavlm-base-plus-sv"
TARGET_SR = 16_000

_model = None
_extractor = None


def _load():
    global _model, _extractor
    if _model is None:
        from transformers import AutoFeatureExtractor, WavLMForXVector

        _extractor = AutoFeatureExtractor.from_pretrained(MODEL_ID)
        _model = WavLMForXVector.from_pretrained(MODEL_ID)
        _model.eval()
        if torch.cuda.is_available():
            _model = _model.cuda()
    return _model, _extractor


def _read(path: Path) -> np.ndarray:
    y, sr = sf.read(path, dtype="float32", always_2d=False)
    if y.ndim > 1:
        y = y.mean(axis=1)
    if sr != TARGET_SR:
        import librosa

        y = librosa.resample(y, orig_sr=sr, target_sr=TARGET_SR)
    return y


@torch.no_grad()
def embed(source) -> np.ndarray:
    """L2-normalized x-vector for a WAV path or a float array."""
    model, extractor = _load()
    y = _read(Path(source)) if isinstance(source, (str, Path)) else np.asarray(source)
    inputs = extractor(y, sampling_rate=TARGET_SR, return_tensors="pt", padding=True)
    if torch.cuda.is_available():
        inputs = {k: v.cuda() for k, v in inputs.items()}
    vec = model(**inputs).embeddings[0].cpu().numpy()
    norm = np.linalg.norm(vec)
    return vec / norm if norm > 0 else vec


def similarity(a, b) -> float:
    """Cosine similarity in [-1, 1]. Accepts paths, arrays, or embeddings."""
    va = a if isinstance(a, np.ndarray) and a.ndim == 1 and a.size < 2048 else embed(a)
    vb = b if isinstance(b, np.ndarray) and b.ndim == 1 and b.size < 2048 else embed(b)
    return float(np.dot(va, vb))


def _summary(name: str, vals: list[float]) -> dict:
    arr = np.array(vals, dtype=float)
    if arr.size == 0:
        return {"name": name, "n": 0}
    return {
        "name": name,
        "n": int(arr.size),
        "mean": float(arr.mean()),
        "std": float(arr.std()),
        "p05": float(np.percentile(arr, 5)),
        "p95": float(np.percentile(arr, 95)),
    }


def calibrate(root: str = "../data/dev", max_pairs: int = 60, seed: int = 0) -> dict:
    """Measure same-speaker, cross-speaker, and clean-vs-simulated similarity."""
    root = Path(root)
    rows = [
        json.loads(l) for l in (root / "manifest.jsonl").open(encoding="utf-8")
    ]
    rng = np.random.default_rng(seed)

    # One clean file per utterance, grouped by speaker.
    by_speaker: dict[str, list[str]] = defaultdict(list)
    seen: set[str] = set()
    for r in rows:
        if r["clean_path"] in seen:
            continue
        seen.add(r["clean_path"])
        by_speaker[r["speaker"]].append(r["clean_path"])

    print(f"{len(seen)} clean utterances from {len(by_speaker)} speakers")

    cache: dict[str, np.ndarray] = {}

    def vec(rel: str) -> np.ndarray:
        if rel not in cache:
            cache[rel] = embed(root / rel)
        return cache[rel]

    # same-speaker: two different utterances from one speaker
    same = []
    multi = [s for s, ps in by_speaker.items() if len(ps) >= 2]
    for spk in multi:
        paths = by_speaker[spk]
        for i in range(len(paths) - 1):
            if len(same) >= max_pairs:
                break
            same.append(similarity(vec(paths[i]), vec(paths[i + 1])))

    # cross-speaker: utterances from two different speakers
    cross = []
    speakers = list(by_speaker)
    if len(speakers) >= 2:
        while len(cross) < max_pairs:
            a, b = rng.choice(len(speakers), size=2, replace=False)
            cross.append(
                similarity(
                    vec(by_speaker[speakers[a]][0]), vec(by_speaker[speakers[b]][0])
                )
            )

    # clean vs its own simulated counterpart, per severity
    by_sev: dict[str, list[float]] = defaultdict(list)
    for r in rows:
        if len(by_sev[r["severity"]]) >= max_pairs:
            continue
        by_sev[r["severity"]].append(
            similarity(vec(r["clean_path"]), embed(root / r["dys_path"]))
        )

    report = {
        "model": MODEL_ID,
        "same_speaker": _summary("same_speaker", same),
        "cross_speaker": _summary("cross_speaker", cross),
        "clean_vs_simulated": {
            k: _summary(k, v) for k, v in sorted(by_sev.items())
        },
    }

    hdr = f"\n{'comparison':<26} {'n':>4} {'mean':>8} {'std':>7} {'p05':>7} {'p95':>7}"
    print(hdr)
    print("-" * (len(hdr) - 1))
    for s in [report["same_speaker"], report["cross_speaker"]]:
        if s["n"]:
            print(
                f"{s['name']:<26} {s['n']:>4} {s['mean']:>8.3f} {s['std']:>7.3f} "
                f"{s['p05']:>7.3f} {s['p95']:>7.3f}"
            )
    for k, s in report["clean_vs_simulated"].items():
        if s["n"]:
            print(
                f"{'clean vs ' + k:<26} {s['n']:>4} {s['mean']:>8.3f} "
                f"{s['std']:>7.3f} {s['p05']:>7.3f} {s['p95']:>7.3f}"
            )

    same_m = report["same_speaker"].get("mean")
    cross_m = report["cross_speaker"].get("mean")
    print()
    if same_m is None or cross_m is None:
        print("inconclusive — need >=2 speakers with >=2 utterances each")
        return report

    margin = same_m - cross_m
    threshold = (same_m + cross_m) / 2
    print(f"same-speaker {same_m:.3f} vs cross-speaker {cross_m:.3f} "
          f"(margin {margin:+.3f})")
    if margin < 0.05:
        print(
            "WARNING  the two distributions barely separate on this data, so this\n"
            "         metric cannot yet certify voice identity. Do not report\n"
            "         speaker-similarity results until the margin is meaningful."
        )
    else:
        print(f"usable decision threshold ~= {threshold:.3f}")

    # Prerequisite check for the paired-data design.
    sev_means = {
        k: s["mean"] for k, s in report["clean_vs_simulated"].items() if s["n"]
    }
    if sev_means and margin >= 0.05:
        worst = min(sev_means, key=lambda k: sev_means[k])
        worst_v = sev_means[worst]
        print()
        if worst_v > threshold:
            print(
                f"PASS  simulation preserves speaker identity "
                f"(worst: {worst}={worst_v:.3f} > {threshold:.3f}).\n"
                "      Clean/dysarthric pairs are the same speaker, so the paired-"
                "data design holds."
            )
        else:
            print(
                f"FAIL  simulation DESTROYS speaker identity "
                f"(worst: {worst}={worst_v:.3f} <= {threshold:.3f}).\n"
                "      The perturbation is changing who the speaker sounds like, so\n"
                "      clean/dysarthric pairs are not the same voice and the paired\n"
                "      design is invalid. Reduce perturbation strength before "
                "training."
            )

    out = root / "speaker_calibration.json"
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\nwrote {out}")
    return report


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="../data/dev")
    ap.add_argument("--max-pairs", type=int, default=60)
    a = ap.parse_args()
    calibrate(a.root, a.max_pairs)
