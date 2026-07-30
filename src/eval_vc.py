"""
Evaluate LLE voice conversion: does it actually make dysarthric speech clearer?

Three questions, three metrics:

    intelligibility   CER from a STANDARD ASR on the converted audio, versus the
                      same ASR on the unconverted dysarthric audio.
    identity          WavLM x-vector cosine against the speaker's own clean
                      speech — the "own voice" claim, thresholded by the
                      calibration in speaker_sim.py.
    tone              STER, the project's differentiator.

Two rules that keep this honest:

LEAVE-ONE-OUT. The reference dictionary never contains the clean counterpart of
the utterance being converted. Our simulated data pairs every dysarthric clip
with its own clean version, so including it would let LLE copy the answer
frame-for-frame and report a meaningless near-zero CER.

EVALUATE WITH THE BASE ASR, not our fine-tuned one. The question is whether the
output is intelligible to an ordinary listener or an off-the-shelf system, not
whether it is intelligible to a model we specifically taught to understand
dysarthria. Using the tuned model here would flatter the result.

Reference modes:
    same    the speaker's own other clean utterances. ORACLE — impossible for a
            real patient, who has no clean recordings of anything. Reported as
            an upper bound on what the method can do.
    cross   a different healthy speaker. Deployable, and the configuration that
            makes stage 2 necessary, since identity is lost.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import soundfile as sf
import torch
import zhconv

import vc
from metrics import score_corpus
from speaker_sim import embed, similarity


def normalize(text: str) -> str:
    text = zhconv.convert(text or "", "zh-tw")
    drop = " \t\n，。、？！：；「」『』（）,.?!:;\"'()《》…—-·"
    return "".join(c for c in text if c not in drop)


def load_asr(model_id: str):
    from transformers import pipeline

    dev = "cuda" if torch.cuda.is_available() else "cpu"
    return pipeline(
        "automatic-speech-recognition",
        model=model_id,
        device=0 if dev == "cuda" else -1,
        torch_dtype=torch.float16 if dev == "cuda" else torch.float32,
    )


def transcribe(asr, wavs: list[np.ndarray], bs: int = 8) -> list[str]:
    out = asr(
        [{"raw": w, "sampling_rate": vc.TARGET_SR} for w in wavs],
        batch_size=bs,
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


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="../data/train")
    ap.add_argument("--asr", default="openai/whisper-small")
    ap.add_argument("--severity", default="severe")
    ap.add_argument("--mode", default="same", choices=["same", "cross"])
    ap.add_argument("--speakers", type=int, default=3)
    ap.add_argument("--per-speaker", type=int, default=8)
    ap.add_argument("--min-utts", type=int, default=12)
    ap.add_argument("-k", type=int, default=8)
    ap.add_argument("--ref-frames", type=int, default=20000)
    ap.add_argument("--save-samples", type=int, default=3)
    a = ap.parse_args()

    root = Path(a.root)
    rows = [json.loads(l) for l in (root / "manifest.jsonl").open(encoding="utf-8")]

    by_spk: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        if r["severity"] == a.severity:
            by_spk[r["speaker"]].append(r)

    eligible = [s for s, rs in by_spk.items() if len(rs) >= a.min_utts]
    eligible.sort(key=lambda s: -len(by_spk[s]))
    chosen = eligible[: a.speakers]
    if not chosen:
        raise SystemExit(
            f"no speaker has >= {a.min_utts} '{a.severity}' utterances. "
            "Build more data or lower --min-utts."
        )
    print(f"severity={a.severity}  mode={a.mode}  speakers={len(chosen)}")

    asr = load_asr(a.asr)
    print(f"evaluating with BASE asr: {a.asr}\n")

    pairs_dys, pairs_vc = [], []
    sim_dys, sim_vc = [], []
    saved = 0
    outdir = root / "_vc_samples"

    for spk in chosen:
        items = by_spk[spk][: a.per_speaker]
        all_clean = sorted({r["clean_path"] for r in by_spk[spk]})

        if a.mode == "cross":
            others = [s for s in eligible if s != spk]
            donor = others[0]
            ref_paths = sorted({r["clean_path"] for r in by_spk[donor]})
            ref = vc.Reference.from_paths(
                [root / p for p in ref_paths], max_frames=a.ref_frames
            )
            print(f"  {spk[:12]}: reference = donor {donor[:12]} "
                  f"({len(ref)} frames)")

        for r in items:
            if a.mode == "same":
                # LEAVE-ONE-OUT: drop this utterance's own clean counterpart.
                ref_paths = [p for p in all_clean if p != r["clean_path"]]
                if len(ref_paths) < 3:
                    continue
                ref = vc.Reference.from_paths(
                    [root / p for p in ref_paths], max_frames=a.ref_frames
                )

            dys = vc.read_audio(root / r["dys_path"])
            conv = vc.convert(dys, ref, k=a.k)

            hyp_dys, hyp_vc = transcribe(asr, [dys, conv])
            ref_txt = normalize(r["text"])
            pairs_dys.append((ref_txt, normalize(hyp_dys)))
            pairs_vc.append((ref_txt, normalize(hyp_vc)))

            clean_emb = embed(root / r["clean_path"])
            sim_dys.append(similarity(clean_emb, embed(dys)))
            sim_vc.append(similarity(clean_emb, embed(conv)))

            if saved < a.save_samples:
                outdir.mkdir(exist_ok=True)
                sf.write(outdir / f"{r['id']}_dys.wav", dys, vc.TARGET_SR)
                sf.write(outdir / f"{r['id']}_vc.wav", conv, vc.TARGET_SR)
                saved += 1

        print(f"  {spk[:12]}: {len(pairs_vc)} cumulative")

    s_dys = score_corpus(pairs_dys)
    s_vc = score_corpus(pairs_vc)

    hdr = f"\n{'':<16} {'CER':>8} {'STER':>8} {'intellig.':>10} {'spk sim':>9}"
    print(hdr)
    print("-" * (len(hdr) - 1))
    print(
        f"{'dysarthric':<16} {s_dys.cer:>8.4f} {s_dys.ster:>8.4f} "
        f"{s_dys.intelligibility:>9.1f}% {np.mean(sim_dys):>9.3f}"
    )
    print(
        f"{'converted':<16} {s_vc.cer:>8.4f} {s_vc.ster:>8.4f} "
        f"{s_vc.intelligibility:>9.1f}% {np.mean(sim_vc):>9.3f}"
    )
    print(
        f"{'delta':<16} {s_vc.cer-s_dys.cer:>+8.4f} "
        f"{s_vc.ster-s_dys.ster:>+8.4f} "
        f"{s_vc.intelligibility-s_dys.intelligibility:>+9.1f}% "
        f"{np.mean(sim_vc)-np.mean(sim_dys):>+9.3f}"
    )

    print(f"\nn={len(pairs_vc)} utterances, {len(chosen)} speakers")
    if a.mode == "same":
        print(
            "MODE=same is an ORACLE: it uses the speaker's own clean recordings,\n"
            "which no real patient has. Treat it as an upper bound, never as a\n"
            "deployable result. Run --mode cross for the realistic number."
        )

    # Identity verdict against the calibrated threshold (speaker_sim.py).
    THRESH = 0.766
    print()
    if np.mean(sim_vc) > THRESH:
        print(f"identity PRESERVED (sim {np.mean(sim_vc):.3f} > {THRESH})")
    else:
        print(
            f"identity LOST (sim {np.mean(sim_vc):.3f} <= {THRESH}) — this is "
            "what stage 2\n(Seed-VC identity restoration) exists to fix."
        )

    if s_vc.cer < s_dys.cer - 0.01:
        print("intelligibility IMPROVED by conversion.")
    elif s_vc.cer > s_dys.cer + 0.01:
        print(
            "intelligibility DEGRADED by conversion. The vocoder or the "
            "neighbour search is\nlosing more than the conversion recovers — do "
            "not report this as a win."
        )
    else:
        print("intelligibility essentially unchanged.")

    out = root / f"vc_eval_{a.mode}_{a.severity}.json"
    out.write_text(
        json.dumps(
            {
                "mode": a.mode,
                "severity": a.severity,
                "asr": a.asr,
                "k": a.k,
                "n": len(pairs_vc),
                "speakers": len(chosen),
                "dysarthric": s_dys.as_dict(),
                "converted": s_vc.as_dict(),
                "speaker_sim_dys": float(np.mean(sim_dys)),
                "speaker_sim_vc": float(np.mean(sim_vc)),
                "simulated": True,
                "oracle_reference": a.mode == "same",
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    print(f"\nwrote {out}")
    if saved:
        print(f"audio samples -> {outdir}")


if __name__ == "__main__":
    main()
