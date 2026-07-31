"""
OwnVoice live demo — Streamlit Community Cloud entry point.

Why this exists separately from the React site: the site is deployed as a free
static Space and has no Python behind it, so its demo panel cannot reach a
model. Hugging Face now bills Docker and Gradio Spaces, and nothing else free
will host ~1 GB of weights plus torch. Streamlit Community Cloud will, from
this repo, at no cost — so the polished site presents the project and links
here for the part that actually runs the model.

MEMORY IS THE BINDING CONSTRAINT. Community Cloud gives roughly 2.7 GB. Two
whisper-small models in fp32 is about 2 GB before audio buffers, so the
baseline comparison is opt-in rather than automatic, and models are cached and
loaded one at a time. If the app dies on a comparison run, that is why.

Run locally with:  streamlit run streamlit_app.py
"""

from __future__ import annotations

import io
import sys
from pathlib import Path

import numpy as np
import soundfile as sf
import streamlit as st

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

TARGET_SR = 16_000
TUNED_MODEL = "anonymous6623/ownvoice-asr"
BASE_MODEL = "openai/whisper-small"
SAMPLE = ROOT / "site" / "public" / "samples" / "sample-clean.wav"
SAMPLE_TEXT = "與地主做良性的溝通"

st.set_page_config(page_title="OwnVoice — live demo", page_icon="🗣", layout="wide")


# --------------------------------------------------------------------------
# Loading. Cached so a rerun does not re-download ~1 GB.
# --------------------------------------------------------------------------
@st.cache_resource(show_spinner=False)
def load_asr(model_id: str):
    import torch
    from transformers import pipeline

    return pipeline(
        "automatic-speech-recognition",
        model=model_id,
        device=-1,  # Community Cloud is CPU-only
        torch_dtype=torch.float32,
        chunk_length_s=30,
    )


def normalize(text: str) -> str:
    """Must match src/metrics.py usage elsewhere, or scores are not comparable."""
    import zhconv

    text = zhconv.convert(text or "", "zh-tw")
    drop = " \t\n，。、？！：；「」『』（）,.?!:;\"'()《》…—-·"
    return "".join(c for c in text if c not in drop)


def read_audio(data: bytes) -> np.ndarray:
    y, sr = sf.read(io.BytesIO(data), dtype="float32", always_2d=False)
    if getattr(y, "ndim", 1) > 1:
        y = y.mean(axis=1)
    if sr != TARGET_SR:
        import librosa

        y = librosa.resample(y.astype(np.float64), orig_sr=sr, target_sr=TARGET_SR)
        y = y.astype(np.float32)
    peak = float(np.abs(y).max()) if y.size else 0.0
    if peak < 1e-5:
        raise ValueError("Audio appears to be silent.")
    return (y / peak * 0.95).astype(np.float32)


def transcribe(pipe, y: np.ndarray) -> str:
    out = pipe(
        {"raw": y, "sampling_rate": TARGET_SR},
        generate_kwargs={
            "language": "zh",
            "task": "transcribe",
            # Degraded speech sends Whisper into repetition loops that produced
            # CER above 1.0 during evaluation. These are what fixed it.
            "no_repeat_ngram_size": 4,
            "repetition_penalty": 1.15,
        },
    )
    return (out.get("text") if isinstance(out, dict) else str(out)) or ""


# --------------------------------------------------------------------------
st.title("OwnVoice — live demo")
st.caption(
    "Tone-aware speech recognition for Mandarin speakers with dysarthria · "
    "[project site](https://anonymous6623-ownvoice.static.hf.space) · "
    "[code](https://github.com/andrewshih0407/ownvoice)"
)

st.info(
    "**In Mandarin, tone is the word.** 統一 (tǒng yī, *unify*) and 同一 "
    "(tóng yī, *the same*) differ by one tone and mean different things. "
    "Dysarthria flattens the pitch contour that carries tone — so a mistoned "
    "syllable is not an accent, it is a different word.",
    icon="🗣",
)

with st.sidebar:
    st.header("How to use")
    st.markdown(
        "1. Load the sample, or upload clear Mandarin speech\n"
        "2. **Simulate** dysarthria — hear the problem\n"
        "3. **Transcribe** the degraded audio"
    )
    severity = st.select_slider(
        "Severity", options=["mild", "moderate", "severe"], value="severe"
    )
    compare = st.checkbox(
        "Also run stock Whisper (slower, more memory)", value=True
    )
    st.divider()
    st.caption(
        "CPU inference — expect 20-60s per transcription, and longer on the "
        "first run while ~1 GB of weights downloads."
    )
    st.caption(
        "**All results are on simulated dysarthria.** Valid for architecture "
        "comparison, not a clinical claim."
    )

col_in, col_out = st.columns(2, gap="large")

with col_in:
    st.subheader("1 · Input")
    upload = st.file_uploader("Mandarin audio (WAV/FLAC/MP3)", type=["wav", "flac", "mp3"])

    use_sample = st.button("Use our sample clip", use_container_width=True)
    if use_sample and SAMPLE.exists():
        st.session_state["audio"] = SAMPLE.read_bytes()
        st.session_state["reference"] = SAMPLE_TEXT
    if upload is not None:
        st.session_state["audio"] = upload.read()

    audio = st.session_state.get("audio")
    if audio:
        st.audio(audio)

    reference = st.text_input(
        "Reference text (optional — enables scoring)",
        value=st.session_state.get("reference", ""),
        placeholder=SAMPLE_TEXT,
    )

    if st.button("Simulate dysarthria", type="primary", use_container_width=True,
                 disabled=not audio):
        try:
            from dysarthria_sim import analyze, perturb, pyworld_available

            if not pyworld_available():
                st.error("pyworld unavailable — F0 perturbation cannot run.")
            else:
                with st.spinner(f"Degrading to {severity}…"):
                    y = read_audio(audio)
                    f0, sp, ap = analyze(
                        np.ascontiguousarray(y.astype(np.float64)), TARGET_SR
                    )
                    out = perturb(f0, sp, ap, TARGET_SR, severity=severity, seed=0)
                    buf = io.BytesIO()
                    sf.write(buf, out, TARGET_SR, format="WAV", subtype="PCM_16")
                    st.session_state["sim"] = buf.getvalue()
                    st.session_state["sim_sev"] = severity
                    st.session_state.pop("result", None)
        except Exception as exc:  # noqa: BLE001
            st.error(f"Simulation failed: {exc}")

    if st.session_state.get("sim"):
        st.markdown(f"**Simulated · {st.session_state['sim_sev']}**")
        st.audio(st.session_state["sim"])

with col_out:
    st.subheader("2 · Recognition")

    sim = st.session_state.get("sim")
    target_label = "simulated" if sim else "original"
    st.caption(f"Will transcribe the **{target_label}** audio.")

    if st.button("Transcribe", type="primary", use_container_width=True,
                 disabled=not (sim or audio)):
        data = sim or audio
        try:
            y = read_audio(data)
            results = {}

            if compare:
                with st.spinner("Stock Whisper… (first run downloads weights)"):
                    results["Stock Whisper"] = transcribe(load_asr(BASE_MODEL), y)
            with st.spinner("OwnVoice fine-tuned…"):
                results["OwnVoice (fine-tuned)"] = transcribe(
                    load_asr(TUNED_MODEL), y
                )

            st.session_state["result"] = results
        except Exception as exc:  # noqa: BLE001
            st.error(
                f"Transcription failed: {exc}\n\n"
                "If this looks like a memory error, untick the stock-Whisper "
                "comparison in the sidebar — two models exceed the free tier."
            )

    results = st.session_state.get("result")
    if results:
        scored = bool(reference.strip())
        if scored:
            from metrics import score

        for name, text in results.items():
            ours = name.startswith("OwnVoice")
            st.markdown(f"**{name}**")
            if scored:
                s = score(normalize(reference), normalize(text))
                c1, c2, c3 = st.columns(3)
                c1.metric("CER", f"{s.cer:.3f}")
                c2.metric("STER", f"{s.ster:.3f}")
                c3.metric("Intelligible", f"{s.intelligibility:.1f}%")
            st.success(text) if ours else st.warning(text)

        if scored and len(results) == 2:
            from metrics import score

            base = score(normalize(reference), normalize(results["Stock Whisper"]))
            tuned = score(
                normalize(reference), normalize(results["OwnVoice (fine-tuned)"])
            )
            delta = base.cer - tuned.cer
            if delta > 0.005:
                st.info(f"Fine-tuning reduced CER by **{delta:.3f}** on this clip.")
            elif delta < -0.005:
                st.warning(
                    f"Stock Whisper did **better** on this clip by {-delta:.3f} CER. "
                    "Per-clip results vary; the corpus average is a 27.7% relative "
                    "reduction."
                )
            else:
                st.info("Both models scored the same on this clip.")

st.divider()
st.caption(
    "Measured on a matched test set with speaker-disjoint splits: "
    "intelligibility 80.9% → 86.2% (−27.7% relative CER), and −41% on severe "
    "dysarthria. Tone error rate did **not** improve (−0.004) — generic ASR "
    "fine-tuning does not fix tone, which is the gap this project targets. "
    "All figures are on simulated dysarthria."
)
