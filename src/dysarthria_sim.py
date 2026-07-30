"""
Perturbation-based dysarthria simulation for Mandarin speech.

Generates paired (dysarthric, clean) training data from clean speech corpora.
This exists because real Mandarin dysarthric corpora (MDSC, CDSD) are
license-gated with multi-week approval lag — simulation unblocks pipeline
development and architecture validation in the meantime.

IMPORTANT SCIENTIFIC CAVEAT
    Interspeech 2025, "Synthetic Dysarthric Speech: A Supplement, Not a
    Substitute for Authentic" — simulated data is valid for bootstrapping and
    architecture search. It is NOT valid for reporting intelligibility results.
    Any published/submitted metric must be measured on real dysarthric speech.

Perturbations implemented, each grounded in a documented acoustic correlate of
dysarthria:

    rate            Reduced speaking rate. Near-universal in dysarthria across
                    etiologies (PD, ALS, post-stroke).
    prosody         F0 range compression toward the speaker mean ("monopitch").
                    THIS IS THE CRITICAL ONE FOR MANDARIN: tone is carried by
                    F0 contour and is lexically meaningful, so flattening
                    prosody destroys word identity, not just naturalness.
    jitter          Cycle-to-cycle F0 perturbation. Correlates with laryngeal
                    control loss.
    smear           Spectral envelope smoothing = formant blurring. Models
                    imprecise articulation / reduced vowel space.
    breathy         Raised aperiodicity. Models incomplete glottal closure,
                    common post-laryngectomy and in PD.
    amplitude       Slow amplitude instability. Models respiratory support loss.

Severity presets follow the mild/moderate/severe convention used by TORGO and
UASpeech so simulated severity buckets map onto real corpora later.
"""

from __future__ import annotations

import numpy as np

try:
    import pyworld as pw

    _HAS_PYWORLD = True
except ImportError:  # pragma: no cover
    _HAS_PYWORLD = False

import librosa

# Severity presets. Values are deliberately conservative — over-perturbing
# produces speech that no model can recover, which teaches the model nothing.
SEVERITY = {
    "mild": dict(
        rate=0.90, prosody=0.30, jitter=0.010, smear=0.15, breathy=0.10, amp=0.05
    ),
    "moderate": dict(
        rate=0.75, prosody=0.55, jitter=0.025, smear=0.35, breathy=0.25, amp=0.12
    ),
    "severe": dict(
        rate=0.60, prosody=0.80, jitter=0.045, smear=0.55, breathy=0.40, amp=0.20
    ),
}


def _compress_f0(f0: np.ndarray, strength: float) -> np.ndarray:
    """Compress F0 toward its voiced mean. strength=0 no-op, 1.0 = monotone.

    Mandarin tone lives in this contour, so this is the perturbation that
    converts an intelligibility problem into a lexical-identity problem.
    """
    out = f0.copy()
    voiced = out > 0
    if not voiced.any():
        return out
    mean = out[voiced].mean()
    out[voiced] = mean + (out[voiced] - mean) * (1.0 - strength)
    return out


def _add_jitter(f0: np.ndarray, amount: float, rng: np.random.Generator) -> np.ndarray:
    """Multiplicative cycle-to-cycle F0 noise on voiced frames only."""
    out = f0.copy()
    voiced = out > 0
    noise = rng.normal(0.0, amount, size=out.shape)
    out[voiced] *= 1.0 + noise[voiced]
    return np.clip(out, 0.0, None)


def _smear_envelope(sp: np.ndarray, strength: float) -> np.ndarray:
    """Smooth the spectral envelope along frequency to blur formant peaks.

    Implemented as a moving average in the log domain, width scaled by
    strength. Log domain keeps this perceptually proportional.
    """
    if strength <= 0:
        return sp
    width = max(3, int(strength * 40) | 1)  # odd kernel, >=3
    kernel = np.ones(width, dtype=np.float64) / width
    log_sp = np.log(np.maximum(sp, 1e-12))
    smoothed = np.apply_along_axis(
        lambda row: np.convolve(row, kernel, mode="same"), axis=1, arr=log_sp
    )
    blended = (1.0 - strength) * log_sp + strength * smoothed
    return np.exp(blended)


def _amplitude_drift(
    y: np.ndarray, sr: int, strength: float, rng: np.random.Generator
) -> np.ndarray:
    """Slow (<3 Hz) multiplicative amplitude envelope instability."""
    if strength <= 0:
        return y
    n_ctrl = max(2, int(len(y) / sr * 3))
    ctrl = 1.0 + rng.normal(0.0, strength, size=n_ctrl)
    envelope = np.interp(
        np.linspace(0, n_ctrl - 1, len(y)), np.arange(n_ctrl), ctrl
    )
    return y * envelope


def _resample_frames(arr: np.ndarray, n_out: int, nearest: bool = False) -> np.ndarray:
    """Resample a frame sequence along axis 0 to `n_out` frames.

    Used for rate change. `nearest` is required for F0: linear interpolation
    across a voiced/unvoiced boundary would invent F0 values inside silence,
    producing phantom voicing.
    """
    n_in = arr.shape[0]
    if n_in == n_out:
        return arr
    idx = np.linspace(0, n_in - 1, n_out)
    if nearest:
        return arr[np.rint(idx).astype(int)]
    lo = np.floor(idx).astype(int)
    hi = np.minimum(lo + 1, n_in - 1)
    w = idx - lo
    if arr.ndim == 1:
        return arr[lo] * (1.0 - w) + arr[hi] * w
    return arr[lo] * (1.0 - w)[:, None] + arr[hi] * w[:, None]


def analyze(y: np.ndarray, sr: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Source-filter decomposition of clean audio: (f0, spectrogram, aperiodicity).

    Call this ONCE per utterance and feed the result to `perturb` for each
    severity. The previous design re-ran the full analysis per severity, which
    tripled the cost of the slowest step for no benefit.

    Uses dio + stonemask rather than harvest: harvest is more accurate but
    roughly an order of magnitude slower, and stonemask refinement closes most
    of the gap. At corpus scale that difference is hours.
    """
    if not _HAS_PYWORLD:
        raise RuntimeError("pyworld required for analyze()")
    f0, t = pw.dio(y, sr)
    f0 = pw.stonemask(y, f0, t, sr)
    sp = pw.cheaptrick(y, f0, t, sr)
    ap = pw.d4c(y, f0, t, sr)
    return f0, sp, ap


def perturb(
    f0: np.ndarray,
    sp: np.ndarray,
    ap: np.ndarray,
    sr: int,
    severity: str = "moderate",
    seed: int | None = None,
    **overrides,
) -> np.ndarray:
    """Apply dysarthria perturbations to a pre-computed decomposition.

    Rate change happens in the frame domain here, not by time-stretching the
    waveform and re-analyzing. That is both cheaper and cleaner: stretching then
    re-analyzing passes the signal through two rounds of estimation error.
    """
    if severity not in SEVERITY:
        raise ValueError(f"severity must be one of {list(SEVERITY)}, got {severity!r}")
    params = {**SEVERITY[severity], **overrides}
    rng = np.random.default_rng(seed)

    # 1. Rate reduction: slower speech => more frames.
    rate = params["rate"]
    if rate != 1.0:
        n_out = max(2, int(round(f0.shape[0] / rate)))
        f0 = _resample_frames(f0, n_out, nearest=True)
        sp = _resample_frames(sp, n_out)
        ap = _resample_frames(ap, n_out)

    # 2-4. Source and filter perturbations.
    f0 = _compress_f0(f0, params["prosody"])
    f0 = _add_jitter(f0, params["jitter"], rng)
    sp = _smear_envelope(sp, params["smear"])
    if params["breathy"] > 0:
        ap = np.clip(ap + params["breathy"] * (1.0 - ap), 0.0, 1.0)

    y = pw.synthesize(
        np.ascontiguousarray(f0),
        np.ascontiguousarray(sp),
        np.ascontiguousarray(ap),
        sr,
    )

    # 5. Respiratory instability.
    y = _amplitude_drift(y, sr, params["amp"], rng)

    peak = np.abs(y).max()
    if peak > 0:
        y = y / peak * 0.95
    return y.astype(np.float32)


def simulate(
    y: np.ndarray,
    sr: int,
    severity: str = "moderate",
    seed: int | None = None,
    **overrides,
) -> np.ndarray:
    """Apply dysarthria-like perturbations to a clean speech waveform.

    Args:
        y: mono float waveform.
        sr: sample rate.
        severity: one of "mild", "moderate", "severe".
        seed: RNG seed for reproducible pairs.
        **overrides: override individual preset parameters.

    Returns:
        Perturbed waveform, same dtype, length changed by the rate factor.
    """
    if severity not in SEVERITY:
        raise ValueError(f"severity must be one of {list(SEVERITY)}, got {severity!r}")

    y = np.ascontiguousarray(np.asarray(y, dtype=np.float64))

    if not _HAS_PYWORLD:
        # Degraded fallback: no F0 control, so no tone destruction. Architecture
        # still trainable but the Mandarin-specific claim cannot be studied.
        params = {**SEVERITY[severity], **overrides}
        rng = np.random.default_rng(seed)
        if params["rate"] != 1.0:
            y = librosa.effects.time_stretch(y, rate=params["rate"])
        if params["smear"] > 0:
            y = librosa.effects.preemphasis(y, coef=-params["smear"] * 0.5)
        y = _amplitude_drift(y, sr, params["amp"], rng)
        peak = np.abs(y).max()
        if peak > 0:
            y = y / peak * 0.95
        return y.astype(np.float32)

    f0, sp, ap = analyze(y, sr)
    return perturb(f0, sp, ap, sr, severity=severity, seed=seed, **overrides)


def pyworld_available() -> bool:
    """Whether full source-filter simulation (incl. tone destruction) is active."""
    return _HAS_PYWORLD


if __name__ == "__main__":
    import argparse
    import soundfile as sf

    ap = argparse.ArgumentParser(description="Simulate dysarthric speech.")
    ap.add_argument("input")
    ap.add_argument("output")
    ap.add_argument("--severity", default="moderate", choices=list(SEVERITY))
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()

    if not pyworld_available():
        print("WARNING: pyworld missing — F0/tone perturbation disabled.")

    y, sr = librosa.load(args.input, sr=None, mono=True)
    out = simulate(y, sr, severity=args.severity, seed=args.seed)
    sf.write(args.output, out, sr)
    print(f"{args.input} -> {args.output}  [{args.severity}]  {len(out)/sr:.2f}s")
