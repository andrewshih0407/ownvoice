"""
OwnVoice API — serves the dysarthria simulator and the fine-tuned recogniser.

Three endpoints, matching the contract the frontend already declares in
`site/src/lib/api.ts`:

    GET  /health      what is loaded, on what device
    POST /simulate    clean audio -> dysarthric audio   (no model needed)
    POST /transcribe  audio -> text, fine-tuned vs stock, optionally scored

Design notes
------------
Models load LAZILY. Whisper-small twice over is ~2 GB of RAM, and /health and
/simulate need none of it, so the server starts instantly and only pays that
cost when someone actually asks for a transcript. A cold first request is slow;
every one after is not.

Uploads are capped and processed entirely in memory. Nothing is written to
disk, nothing is logged, and the decoded array goes out of scope with the
request — the privacy claim on the site has to be true.

The generation settings here are NOT defaults. Degraded speech drives Whisper
into repetition loops that produced CER above 1.0 during evaluation;
no_repeat_ngram_size and repetition_penalty are what fixed it, and the same
values are used at training time.
"""

from __future__ import annotations

import io
import os
import sys
import time
from pathlib import Path
from typing import Optional

import numpy as np
import soundfile as sf
import torch
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

# The training modules live in src/ and import each other by bare name.
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

import zhconv  # noqa: E402
from dysarthria_sim import SEVERITY, analyze, perturb, pyworld_available  # noqa: E402
from metrics import score  # noqa: E402

TARGET_SR = 16_000
MAX_SECONDS = float(os.environ.get("OWNVOICE_MAX_SECONDS", 30))
MAX_UPLOAD_BYTES = int(os.environ.get("OWNVOICE_MAX_BYTES", 25 * 1024 * 1024))
TUNED_DIR = os.environ.get("OWNVOICE_MODEL", str(ROOT / "runs" / "asr_v1"))
BASE_MODEL = os.environ.get("OWNVOICE_BASE_MODEL", "openai/whisper-small")

# When a built frontend is present, this process serves the site AND the API
# from one origin — which is how the deployed Space runs, and why
# .env.production sets VITE_API_BASE="" so the client uses relative paths.
# In local dev the directory is absent and Vite serves the site on :5173
# instead, with CORS below covering the cross-origin case.
WEB_DIR = Path(os.environ.get("OWNVOICE_WEB", ROOT / "backend" / "web"))

GEN_KWARGS = {
    "language": "zh",
    "task": "transcribe",
    # Not defaults — see module docstring.
    "no_repeat_ngram_size": 4,
    "repetition_penalty": 1.15,
}

app = FastAPI(title="OwnVoice API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:4173",
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

_pipes: dict[str, object] = {}
_load_error: Optional[str] = None


def _device() -> str:
    return "cuda" if torch.cuda.is_available() else "cpu"


def _get_pipe(which: str):
    """Lazily build and cache an ASR pipeline. `which` is 'tuned' or 'base'."""
    global _load_error
    if which in _pipes:
        return _pipes[which]

    from transformers import pipeline

    model_id = TUNED_DIR if which == "tuned" else BASE_MODEL
    if which == "tuned" and not Path(model_id).exists():
        raise HTTPException(
            503,
            f"Fine-tuned model not found at {model_id}. Train it first, or set "
            "OWNVOICE_MODEL to a checkpoint directory.",
        )

    dev = _device()
    try:
        _pipes[which] = pipeline(
            "automatic-speech-recognition",
            model=model_id,
            device=0 if dev == "cuda" else -1,
            torch_dtype=torch.float16 if dev == "cuda" else torch.float32,
            chunk_length_s=30,
        )
    except Exception as exc:  # noqa: BLE001
        _load_error = f"{type(exc).__name__}: {exc}"
        raise HTTPException(503, f"Could not load {which} model: {_load_error}")
    return _pipes[which]


def normalize(text: str) -> str:
    """Traditional Chinese, punctuation stripped.

    Must stay byte-identical to the normalisation used in baseline.py,
    train_asr.py and evaluate.py — otherwise numbers served here would not be
    comparable to the numbers published on the site.
    """
    text = zhconv.convert(text or "", "zh-tw")
    drop = " \t\n，。、？！：；「」『』（）,.?!:;\"'()《》…—-·"
    return "".join(c for c in text if c not in drop)


async def _read_audio(upload: UploadFile) -> np.ndarray:
    """Decode an upload to mono float32 at 16 kHz, enforcing the caps."""
    raw = await upload.read()
    if not raw:
        raise HTTPException(400, "Empty upload.")
    if len(raw) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            413, f"File too large ({len(raw)/1e6:.1f} MB). Limit is "
                 f"{MAX_UPLOAD_BYTES/1e6:.0f} MB."
        )
    try:
        y, sr = sf.read(io.BytesIO(raw), dtype="float32", always_2d=False)
    except Exception:
        raise HTTPException(
            415,
            "Could not decode audio. WAV and FLAC are safest; MP3 support "
            "depends on the server's libsndfile build.",
        )
    if getattr(y, "ndim", 1) > 1:
        y = y.mean(axis=1)
    if y.size == 0:
        raise HTTPException(400, "Audio contains no samples.")

    if sr != TARGET_SR:
        import librosa

        y = librosa.resample(y.astype(np.float64), orig_sr=sr, target_sr=TARGET_SR)
        y = y.astype(np.float32)

    max_samples = int(MAX_SECONDS * TARGET_SR)
    if y.size > max_samples:
        y = y[:max_samples]

    peak = float(np.abs(y).max())
    if peak < 1e-5:
        raise HTTPException(400, "Audio appears to be silent.")
    return (y / peak * 0.95).astype(np.float32)


def _transcribe(which: str, y: np.ndarray) -> str:
    pipe = _get_pipe(which)
    out = pipe(
        {"raw": y, "sampling_rate": TARGET_SR}, generate_kwargs=GEN_KWARGS
    )
    return (out.get("text") if isinstance(out, dict) else str(out)) or ""


def _scores(reference: str, hypothesis: str) -> dict:
    s = score(normalize(reference), normalize(hypothesis))
    return {
        "cer": round(s.cer, 4),
        "ster": round(s.ster, 4),
        "intelligibility_pct": round(s.intelligibility, 2),
    }


def _tone_diff(reference: str, hypothesis: str) -> list[dict]:
    """Per-syllable tone comparison, so the UI can point at the exact failure."""
    from pypinyin import Style, lazy_pinyin

    def syls(t: str) -> list[str]:
        out = []
        for s in lazy_pinyin(normalize(t), style=Style.TONE3, errors="ignore"):
            if s:
                out.append(s if s[-1].isdigit() else s + "5")
        return out

    ref, hyp = syls(reference), syls(hypothesis)
    diff = []
    for r, h in zip(ref, hyp):
        r_seg, r_tone = r[:-1], r[-1]
        h_seg, h_tone = h[:-1], h[-1]
        diff.append(
            {
                "syllable": r_seg,
                "ref_tone": r_tone,
                "hyp_tone": h_tone,
                # Only meaningful where the segment matched; a segmental miss is
                # a different kind of error and must not be shown as a tone bug.
                "ok": (r_seg == h_seg) and (r_tone == h_tone),
                "segment_ok": r_seg == h_seg,
            }
        )
    return diff


def _tuned_is_distinct() -> bool:
    """Is the 'fine-tuned' model actually different from the baseline?

    Deploying without setting OWNVOICE_MODEL leaves both pointing at stock
    whisper. The demo would then compare a model against itself, print two
    identical transcripts and identical CERs, and still look like it worked —
    the worst kind of failure, because nothing errors. Surfaced here and shouted
    at boot so it cannot pass unnoticed.
    """
    return str(TUNED_DIR).rstrip("/\\") != str(BASE_MODEL).rstrip("/\\")


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "device": _device(),
        "gpu": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
        "loaded": sorted(_pipes.keys()),
        "tuned_model_present": Path(TUNED_DIR).exists()
        or not str(TUNED_DIR).startswith(("/", "C:", ".")),
        "tuned_model_path": TUNED_DIR,
        "base_model": BASE_MODEL,
        # False means the A/B comparison is meaningless — see _tuned_is_distinct.
        "tuned_is_distinct_from_base": _tuned_is_distinct(),
        "simulator_full": pyworld_available(),
        "severities": list(SEVERITY),
        "max_seconds": MAX_SECONDS,
        "last_load_error": _load_error,
        "note": "Models load lazily on first /transcribe call.",
    }


@app.post("/simulate")
async def simulate_endpoint(
    file: UploadFile = File(...),
    severity: str = Form("moderate"),
) -> Response:
    """Apply the dysarthria simulation and return WAV audio."""
    if severity not in SEVERITY:
        raise HTTPException(400, f"severity must be one of {list(SEVERITY)}")
    if not pyworld_available():
        raise HTTPException(
            503,
            "pyworld is unavailable, so F0 perturbation — the core of the "
            "tone hypothesis — cannot run. Install pyworld.",
        )

    y = await _read_audio(file)
    t0 = time.perf_counter()
    f0, sp, ap = analyze(np.ascontiguousarray(y.astype(np.float64)), TARGET_SR)
    out = perturb(f0, sp, ap, TARGET_SR, severity=severity, seed=0)

    buf = io.BytesIO()
    sf.write(buf, out, TARGET_SR, format="WAV", subtype="PCM_16")
    return Response(
        content=buf.getvalue(),
        media_type="audio/wav",
        headers={
            "X-Severity": severity,
            "X-Elapsed-Ms": str(round((time.perf_counter() - t0) * 1000)),
            "Content-Disposition": f'inline; filename="simulated_{severity}.wav"',
        },
    )


@app.post("/transcribe")
async def transcribe_endpoint(
    file: UploadFile = File(...),
    reference: Optional[str] = Form(None),
    baseline: bool = Form(True),
) -> dict:
    """Transcribe with the fine-tuned model, and optionally stock Whisper."""
    y = await _read_audio(file)

    t0 = time.perf_counter()
    tuned_text = _transcribe("tuned", y)
    result: dict = {
        "transcript": tuned_text.strip(),
        "duration_s": round(len(y) / TARGET_SR, 2),
        "device": _device(),
    }

    if baseline:
        result["baseline_transcript"] = _transcribe("base", y).strip()

    if reference and reference.strip():
        result["scores"] = _scores(reference, tuned_text)
        if baseline:
            result["baseline_scores"] = _scores(
                reference, result["baseline_transcript"]
            )
        result["tone_diff"] = _tone_diff(reference, tuned_text)

    result["elapsed_ms"] = round((time.perf_counter() - t0) * 1000)
    return result


# ---------------------------------------------------------------------------
# Static frontend. Mounted LAST so it cannot shadow the API routes above.
# ---------------------------------------------------------------------------
if WEB_DIR.is_dir() and (WEB_DIR / "index.html").exists():
    from fastapi.responses import FileResponse
    from fastapi.staticfiles import StaticFiles

    app.mount(
        "/assets", StaticFiles(directory=WEB_DIR / "assets"), name="assets"
    )
    if (WEB_DIR / "samples").is_dir():
        app.mount(
            "/samples", StaticFiles(directory=WEB_DIR / "samples"), name="samples"
        )

    @app.get("/{full_path:path}")
    def spa(full_path: str):
        """Serve real files if they exist, otherwise index.html.

        The site is a single-page app with client-side routes (/how, /method,
        /code). A visitor deep-linking or refreshing on one of those must get
        index.html rather than a 404, and the router then takes over.
        """
        candidate = (WEB_DIR / full_path).resolve()
        # Containment check: never serve anything outside WEB_DIR, whatever the
        # path contains.
        if (
            full_path
            and WEB_DIR.resolve() in candidate.parents
            and candidate.is_file()
        ):
            return FileResponse(candidate)
        return FileResponse(WEB_DIR / "index.html")

    print(f"[ownvoice] serving frontend from {WEB_DIR}")
else:
    print(f"[ownvoice] no frontend at {WEB_DIR} — API only")

if not _tuned_is_distinct():
    print(
        "\n"
        "[ownvoice] ============================ WARNING ============================\n"
        f"[ownvoice] OWNVOICE_MODEL and OWNVOICE_BASE_MODEL are both {BASE_MODEL!r}.\n"
        "[ownvoice] The demo will compare the model against ITSELF: two identical\n"
        "[ownvoice] transcripts, identical CERs, and no error anywhere. Set\n"
        "[ownvoice] OWNVOICE_MODEL to the fine-tuned checkpoint before showing this\n"
        "[ownvoice] to anyone.\n"
        "[ownvoice] =================================================================\n"
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        # 0.0.0.0 in a container; loopback locally unless overridden.
        host=os.environ.get("OWNVOICE_HOST", "127.0.0.1"),
        port=int(os.environ.get("OWNVOICE_PORT", 7860)),
        log_level="info",
    )
