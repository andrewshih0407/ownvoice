"""
Choose the demo sample by running candidates through the LIVE API.

The demo's persuasive value depends on the contrast being visible: stock Whisper
should fail on the degraded clip where the fine-tuned model succeeds. Clip-level
variance is large (measured severe CER averages 0.47, so plenty of individual
clips go either way), and the shipped sample has to be one where the effect
actually shows.

This is not cherry-picking a claim — the site's headline numbers are corpus
averages measured elsewhere. This only selects which single clip to hand a
visitor who has no Mandarin audio of their own, and it selects it through
exactly the path the demo uses: POST /simulate then POST /transcribe.
"""

from __future__ import annotations

import io
import json
import pathlib
import sys

import requests

API = "http://127.0.0.1:7860"
ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from metrics import score  # noqa: E402
import zhconv  # noqa: E402


def norm(t: str) -> str:
    t = zhconv.convert(t or "", "zh-tw")
    drop = " \t\n，。、？！：；「」『』（）,.?!:;\"'()《》…—-·"
    return "".join(c for c in t if c not in drop)


def main(limit: int = 14, severity: str = "severe") -> None:
    root = ROOT / "data" / "train"
    rows = [json.loads(l) for l in (root / "manifest.jsonl").open(encoding="utf-8")]

    # HELD-OUT SPEAKERS ONLY. The first pass of this script picked from the head
    # of the manifest and the fine-tuned model scored CER 0.000 on 13 of 14
    # clips — far better than its measured 0.1683 average on severe, because
    # those were TRAINING clips and this model overfits hard (train loss 0.0018
    # with eval error rising). A demo built on a memorised clip would show
    # memorisation, not generalisation, and would deserve to be discounted.
    #
    # Reusing build_splits with the training seed and eval_frac reproduces the
    # exact holdout, so the shipped sample is one the model has never seen.
    from train_asr import build_splits

    _, eval_rows = build_splits(
        root, ("mild", "moderate", "severe"), 0.2, 0, include_clean=True
    )
    held_out = {r["speaker"] for r in eval_rows}
    print(f"held-out speakers: {len(held_out)}")

    seen: set[str] = set()
    cands = []
    for r in rows:
        if r["speaker"] not in held_out or r["clean_path"] in seen:
            continue
        seen.add(r["clean_path"])
        # Long enough to carry several tones, short enough to stay snappy.
        if 8 <= len(r["text"]) <= 18:
            cands.append(r)
        if len(cands) >= limit:
            break

    print(f"testing {len(cands)} clips at severity={severity} through the live API\n")
    print(f"{'clip':<22} {'base CER':>9} {'ours CER':>9} {'gain':>7}  ref")
    print("-" * 78)

    results = []
    for r in cands:
        clean = root / r["clean_path"]
        try:
            sim = requests.post(
                f"{API}/simulate",
                files={"file": (clean.name, clean.read_bytes(), "audio/wav")},
                data={"severity": severity},
                timeout=180,
            )
            sim.raise_for_status()
            tr = requests.post(
                f"{API}/transcribe",
                files={"file": ("sim.wav", sim.content, "audio/wav")},
                data={"reference": r["text"], "baseline": "true"},
                timeout=600,
            ).json()
        except Exception as exc:  # noqa: BLE001
            print(f"{clean.stem:<22} ERROR {exc}")
            continue

        b = score(norm(r["text"]), norm(tr.get("baseline_transcript", "")))
        t = score(norm(r["text"]), norm(tr.get("transcript", "")))
        gain = b.cer - t.cer
        results.append((gain, r, b, t, tr))
        print(
            f"{clean.stem:<22} {b.cer:>9.3f} {t.cer:>9.3f} {gain:>+7.3f}  {r['text'][:16]}"
        )

    if not results:
        raise SystemExit("no results")

    results.sort(key=lambda x: -x[0])
    gain, r, b, t, tr = results[0]

    print("\nbest contrast:")
    print(f"  file      {r['clean_path']}")
    print(f"  reference {r['text']}")
    print(f"  stock     {tr.get('baseline_transcript')}   CER {b.cer:.3f}")
    print(f"  ours      {tr.get('transcript')}   CER {t.cer:.3f}")
    print(f"  gain      {gain:+.3f} CER")
    if t.cer > 0.15:
        print("\n  NOTE: our own transcript is not clean on this clip either.")
    if gain < 0.15:
        print(
            "\n  NOTE: no clip showed a large contrast. Ship the sample anyway and"
            "\n  describe it honestly — do not imply a gap the demo cannot show."
        )

    (ROOT / "backend" / "sample_choice.json").write_text(
        json.dumps(
            {
                "clean_path": r["clean_path"],
                "text": r["text"],
                "severity": severity,
                "baseline_transcript": tr.get("baseline_transcript"),
                "tuned_transcript": tr.get("transcript"),
                "baseline_cer": round(b.cer, 4),
                "tuned_cer": round(t.cer, 4),
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    print(f"\nwrote backend/sample_choice.json")


if __name__ == "__main__":
    main()
