"""
Ablation: is the intelligibility loss coming from the LLE conversion, or from
the mel -> vocoder round trip underneath it?

`eval_vc.py` showed conversion made CER worse (0.4048 -> 0.4881). That has two
possible causes and they call for opposite fixes:

    the LLE step        -> tune k / regularization / reference size
    the vocoder path    -> the analysis-synthesis chain is lossy and no amount
                           of LLE tuning will help

The discriminating test is to pass audio through mel_spectrogram -> vocode with
NO conversion at all. Whatever CER that costs is the floor every converted
sample also pays.
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

import vc
from eval_vc import load_asr, normalize, transcribe
from metrics import score_corpus


def main(root: str = "../data/train", n: int = 10, severity: str = "severe") -> None:
    root = Path(root)
    rows = [json.loads(l) for l in (root / "manifest.jsonl").open(encoding="utf-8")]

    by_spk = defaultdict(list)
    for r in rows:
        if r["severity"] == severity:
            by_spk[r["speaker"]].append(r)
    spk = sorted(by_spk, key=lambda s: -len(by_spk[s]))[0]
    items = by_spk[spk][:n]

    asr = load_asr("openai/whisper-small")
    refs, conds = [], defaultdict(list)

    for r in items:
        refs.append(normalize(r["text"]))
        clean = vc.read_audio(root / r["clean_path"])
        dys = vc.read_audio(root / r["dys_path"])
        conds["clean"].append(clean)
        conds["clean_roundtrip"].append(vc.vocode(vc.mel_spectrogram(clean)))
        conds["dysarthric"].append(dys)
        conds["dys_roundtrip"].append(vc.vocode(vc.mel_spectrogram(dys)))

    print()
    print(f"{'condition':<18} {'CER':>8} {'intelligibility':>16}")
    print("-" * 44)
    results = {}
    for name, wavs in conds.items():
        hyps = transcribe(asr, wavs)
        s = score_corpus([(a, normalize(b)) for a, b in zip(refs, hyps)])
        results[name] = s
        print(f"{name:<18} {s.cer:>8.4f} {s.intelligibility:>15.1f}%")

    rt_cost = results["clean_roundtrip"].cer - results["clean"].cer
    print(f"\nvocoder round-trip cost on clean speech: {rt_cost:+.4f} CER")
    if rt_cost > 0.05:
        print(
            "The analysis-synthesis chain itself is lossy. Every converted sample\n"
            "pays this before conversion adds anything, so LLE tuning cannot fix\n"
            "it — the mel/vocoder pairing needs replacing (mismatched mel\n"
            "normalization, or swap in a vocoder matched to our feature config)."
        )
    else:
        print(
            "The vocoder is roughly transparent, so the loss is in the LLE step:\n"
            "tune k, the regularizer, and reference size."
        )
    print(f"\nn={n} utterances, speaker {spk[:12]}")


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="../data/train")
    ap.add_argument("-n", type=int, default=10)
    ap.add_argument("--severity", default="severe")
    a = ap.parse_args()
    main(a.root, a.n, a.severity)
