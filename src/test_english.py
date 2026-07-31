"""
Does the Mandarin fine-tune still handle English?

The model was fine-tuned on Mandarin-only dysarthric data with the decoder
forced to language="zh". Whisper is multilingual, but fine-tuning on one
language routinely degrades the others — and we already know this model
overfits hard. So "dual-mode English + Mandarin" is a claim that has to be
measured before it is made, not assumed from the base model's capabilities.

This measures, on LibriSpeech (CC-BY-4.0):

    clean English      stock vs fine-tuned
    degraded English   stock vs fine-tuned   (same simulator; it is acoustic,
                                              not linguistic, so it applies to
                                              any language)

WER is the metric here, not CER — English has word delimiters, and WER is what
the English dysarthria literature reports. STER is meaningless: English is not
tonal.
"""

from __future__ import annotations

import sys

import jiwer
import numpy as np
import torch

TARGET_SR = 16_000
TUNED = "../runs/asr_v1"
BASE = "openai/whisper-small"


def load(model_id: str):
    from transformers import pipeline

    dev = "cuda" if torch.cuda.is_available() else "cpu"
    return pipeline(
        "automatic-speech-recognition",
        model=model_id,
        device=0 if dev == "cuda" else -1,
        torch_dtype=torch.float16 if dev == "cuda" else torch.float32,
    )


def norm(t: str) -> str:
    return " ".join(
        "".join(c for c in t.lower() if c.isalnum() or c.isspace()).split()
    )


def transcribe(pipe, y: np.ndarray) -> str:
    out = pipe(
        {"raw": y, "sampling_rate": TARGET_SR},
        generate_kwargs={
            "language": "en",
            "task": "transcribe",
            "no_repeat_ngram_size": 4,
            "repetition_penalty": 1.15,
        },
    )
    return (out.get("text") if isinstance(out, dict) else str(out)) or ""


def main(n: int = 8, severity: str = "severe") -> None:
    import io

    import soundfile as sf
    from datasets import Audio, load_dataset

    from dysarthria_sim import analyze, perturb

    print("loading LibriSpeech sample (CC-BY-4.0)...")
    ds = load_dataset(
        "hf-internal-testing/librispeech_asr_dummy", "clean", split="validation"
    )
    # Recent `datasets` decodes audio via torchcodec, which needs a system
    # FFmpeg. soundfile already handles these files, so bypass the decoder.
    for col, feat in (ds.features or {}).items():
        if isinstance(feat, Audio):
            ds = ds.cast_column(col, Audio(decode=False))

    clips = []
    for row in ds:
        raw = row["audio"]
        data = raw.get("bytes") if isinstance(raw, dict) else None
        if data:
            y, sr = sf.read(io.BytesIO(data), dtype="float64", always_2d=False)
        else:
            y, sr = sf.read(raw["path"], dtype="float64", always_2d=False)
        if getattr(y, "ndim", 1) > 1:
            y = y.mean(axis=1)
        sr = int(sr)
        if sr != TARGET_SR:
            import librosa

            y = librosa.resample(y, orig_sr=sr, target_sr=TARGET_SR)
        peak = np.abs(y).max()
        if peak < 1e-5:
            continue
        y = y / peak * 0.95
        # Cap at 12 s. The severe preset slows speech 1.67x, so anything longer
        # exceeds Whisper's 30 s window after simulation and trips long-form
        # generation, which needs timestamps and changes the decoding path.
        y = y[: 12 * TARGET_SR]
        clips.append((y.astype(np.float32), row["text"]))
        if len(clips) >= n:
            break

    print(f"{len(clips)} clips\n")

    print("simulating dysarthria on English...")
    degraded = []
    for y, _ in clips:
        f0, sp, ap = analyze(np.ascontiguousarray(y.astype(np.float64)), TARGET_SR)
        degraded.append(perturb(f0, sp, ap, TARGET_SR, severity=severity, seed=0))

    refs = [norm(t) for _, t in clips]
    rows = []
    for label, model_id in (("stock", BASE), ("fine-tuned", TUNED)):
        pipe = load(model_id)
        for cond, audio in (("clean", [c[0] for c in clips]), (severity, degraded)):
            hyps = [norm(transcribe(pipe, a)) for a in audio]
            wer = jiwer.wer(refs, hyps)
            cer = jiwer.cer("".join(refs), "".join(hyps))
            rows.append((label, cond, wer, cer, hyps[0][:52]))
        del pipe
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

    print()
    print("%-12s %-10s %8s %8s  %s" % ("MODEL", "AUDIO", "WER", "CER", "first hyp"))
    print("-" * 96)
    for label, cond, wer, cer, sample in rows:
        print("%-12s %-10s %8.3f %8.3f  %s" % (label, cond, wer, cer, sample))

    print()
    print("reference:", refs[0][:70])

    base_clean = next(r[2] for r in rows if r[0] == "stock" and r[1] == "clean")
    tuned_clean = next(r[2] for r in rows if r[0] == "fine-tuned" and r[1] == "clean")
    base_deg = next(r[2] for r in rows if r[0] == "stock" and r[1] == severity)
    tuned_deg = next(r[2] for r in rows if r[0] == "fine-tuned" and r[1] == severity)

    print()
    print("clean English    WER  %.3f -> %.3f  (%+.3f)" % (
        base_clean, tuned_clean, tuned_clean - base_clean))
    print("degraded English WER  %.3f -> %.3f  (%+.3f)" % (
        base_deg, tuned_deg, tuned_deg - base_deg))
    print()
    if tuned_clean > base_clean + 0.10:
        print("VERDICT: the fine-tune DEGRADED English badly. Do not advertise a")
        print("         dual-language model from this checkpoint — route English")
        print("         to stock Whisper, or train a separate English model.")
    elif tuned_deg < base_deg - 0.05:
        print("VERDICT: the fine-tune helps on degraded English too. Dysarthria")
        print("         robustness transferred across languages — that is a real")
        print("         and defensible global-impact claim.")
    else:
        print("VERDICT: English is roughly unchanged. The model is usable for")
        print("         English at stock quality, but the dysarthria gain did NOT")
        print("         transfer. Say 'supports English', not 'improves English'.")


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("-n", type=int, default=8)
    ap.add_argument("--severity", default="severe")
    a = ap.parse_args()
    main(a.n, a.severity)
