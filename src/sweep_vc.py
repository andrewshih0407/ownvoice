"""
Sweep the LLE voice-conversion hyperparameters that actually matter.

The first conversion attempt DEGRADED intelligibility (CER 0.4048 -> 0.4881).
The vocoder ablation cleared the vocoder of blame: a mel -> waveform round trip
on clean speech costs -0.019 CER, i.e. it is transparent. So the failure is in
the LLE step, and the prime suspect is the HuBERT layer.

`content_features` originally used `last_hidden_state` — layer 24 of 24. In a
self-supervised speech model the deepest layers re-encode acoustic and speaker
detail, while intermediate layers hold the most speaker-invariant phonetic
content. Matching on the final layer means nearest-neighbour search compares
voice texture rather than phonetic identity, which is precisely the wrong thing
for content-based conversion.

Everything here is measured against the unconverted dysarthric baseline on the
same utterances, so a "win" means beating that number, not merely producing
audio.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

import numpy as np

import vc
from eval_vc import load_asr, normalize, transcribe
from metrics import score_corpus


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="../data/train")
    ap.add_argument("--severity", default="severe")
    ap.add_argument("-n", type=int, default=8, help="utterances per config")
    ap.add_argument("--layers", nargs="+", type=int, default=[6, 9, 12, 18, 24])
    ap.add_argument("--ks", nargs="+", type=int, default=[8])
    ap.add_argument("--ref-frames", type=int, default=20000)
    a = ap.parse_args()

    root = Path(a.root)
    rows = [json.loads(l) for l in (root / "manifest.jsonl").open(encoding="utf-8")]

    by_spk = defaultdict(list)
    for r in rows:
        if r["severity"] == a.severity:
            by_spk[r["speaker"]].append(r)
    spk = sorted(by_spk, key=lambda s: -len(by_spk[s]))[0]
    items = by_spk[spk][: a.n]
    all_clean = sorted({r["clean_path"] for r in by_spk[spk]})
    print(f"speaker {spk[:12]}  n={len(items)}  severity={a.severity}")

    asr = load_asr("openai/whisper-small")
    refs = [normalize(r["text"]) for r in items]

    # Baseline: unconverted dysarthric audio.
    dys_wavs = [vc.read_audio(root / r["dys_path"]) for r in items]
    base = score_corpus(
        [(t, normalize(h)) for t, h in zip(refs, transcribe(asr, dys_wavs))]
    )
    print(f"\nbaseline (unconverted): CER={base.cer:.4f}  STER={base.ster:.4f}\n")

    hdr = f"{'layer':>6} {'k':>4} {'CER':>8} {'ΔCER':>9} {'STER':>8} {'ΔSTER':>9}"
    print(hdr)
    print("-" * len(hdr))

    results = []
    for layer in a.layers:
        # Reference must be built with the SAME layer as the source features,
        # or the neighbour search compares incompatible spaces.
        refs_by_utt = {}
        for k in a.ks:
            hyps = []
            for r in items:
                key = r["clean_path"]
                if key not in refs_by_utt:
                    # Leave-one-out: exclude this utterance's own clean audio.
                    paths = [p for p in all_clean if p != key]
                    refs_by_utt[key] = vc.Reference.from_paths(
                        [root / p for p in paths],
                        max_frames=a.ref_frames,
                        layer=layer,
                    )
                wav = vc.convert(
                    root / r["dys_path"], refs_by_utt[key], k=k, layer=layer
                )
                hyps.append(wav)
            s = score_corpus(
                [(t, normalize(h)) for t, h in zip(refs, transcribe(asr, hyps))]
            )
            results.append((layer, k, s))
            print(
                f"{layer:>6} {k:>4} {s.cer:>8.4f} {s.cer-base.cer:>+9.4f} "
                f"{s.ster:>8.4f} {s.ster-base.ster:>+9.4f}"
            )

    best = min(results, key=lambda t: t[2].cer)
    print(
        f"\nbest: layer={best[0]} k={best[1]} CER={best[2].cer:.4f} "
        f"({best[2].cer-base.cer:+.4f} vs unconverted)"
    )
    # Margin must clear the sampling noise, not merely be positive. At n=8 the
    # apparent best (layer 6, -0.0238) REVERSED to +0.0403 at n=24 — a sign
    # flip. Treat anything under ~0.05 at n<50 as unproven.
    margin = base.cer - best[2].cer
    noisy = len(items) < 50
    if margin > 0.05 and not noisy:
        print(
            "Conversion IMPROVES intelligibility by a margin that clears the "
            "noise floor.\nSet DEFAULT_LAYER in vc.py and re-run eval_vc.py."
        )
    elif margin > 0.0:
        print(
            f"Improvement of {margin:.4f} CER at n={len(items)} is INSIDE the "
            "noise floor.\nDo not report this as a win. A sign flip between "
            "n=8 and n=24 has already\noccurred on this grid. Re-run at n>=50 "
            "before drawing any conclusion."
        )
    else:
        print(
            "No configuration beats the unconverted baseline. The LLE approach is\n"
            "not working on this data — likely because Chinese-HuBERT features of\n"
            "SEVERELY degraded speech are themselves out of distribution, so the\n"
            "neighbour search cannot find the right phonetic content regardless of\n"
            "layer. Next option: use the fine-tuned Whisper encoder as the content\n"
            "extractor, since it was explicitly adapted to dysarthric input."
        )

    out = root / "vc_sweep.json"
    out.write_text(
        json.dumps(
            {
                "speaker": spk,
                "severity": a.severity,
                "n": len(items),
                "baseline": base.as_dict(),
                "grid": [
                    {"layer": l, "k": k, **s.as_dict()} for l, k, s in results
                ],
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
