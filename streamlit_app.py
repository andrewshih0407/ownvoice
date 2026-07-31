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
BASE_MODEL = "openai/whisper-small"
TUNED_MODEL_ZH = "anonymous6623/ownvoice-asr"

# There is no TUNED_MODEL_EN. A dedicated English fine-tune was trained
# (runs/asr_en) and evaluated with matched, speaker-disjoint WER — the metric
# that actually reflects word-level accuracy, unlike the CER used during
# training which flatters English. Result: WER went from 5.66% (stock
# Whisper) to 6.04% (fine-tuned) overall, i.e. no improvement, and specifically
# worse on severe dysarthria (-11.3% relative). So English here runs stock
# Whisper only, and says so, rather than presenting an ineffective checkpoint
# as if it were the Mandarin result's counterpart.
LANGS = {
    "Mandarin": {
        "code": "zh",
        "sample": ROOT / "site" / "public" / "samples" / "sample-clean.wav",
        "sample_text": "與地主做良性的溝通",
        "tonal": True,
    },
    "English": {
        "code": "en",
        "sample": ROOT / "site" / "public" / "samples" / "sample-clean-en.wav",
        "sample_text": "ALL RIGHT SIT DOWN MY FRIENDS",
        "tonal": False,
    },
}

st.set_page_config(page_title="OwnVoice — live demo", page_icon="🗣", layout="wide")

# ----------------------------------------------------------------------------
# Styling only — no functional change below this block. Matches the palette,
# type and pill/tile shapes defined in site/src/styles/global.css so this page
# reads as the same product as the React site rather than default Streamlit
# gray. config.toml sets the base colors; everything Streamlit's theme system
# cannot reach (fonts, radii, tile-style panels) is layered on here.
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Archivo:wght@700;800;900&family=Figtree:wght@400;500;600;700&display=swap');

    :root {
        --cream: #f4efe6;
        --cream-2: #efe7d9;
        --ink: #14110f;
        --ink-soft: #4a443d;
        --cobalt: #3e6be0;
        --marigold: #f4b024;
        --tangerine: #ee6c34;
        --grass: #3fa85b;
        --violet: #8a5cf6;
        --sky: #62c6e8;
    }

    html, body, [class*="css"] {
        font-family: 'Figtree', system-ui, sans-serif;
    }

    /* Match the site's dark hero band behind the page chrome. */
    [data-testid="stAppViewContainer"] {
        background: var(--cream);
    }
    [data-testid="stHeader"] {
        background: transparent;
    }
    [data-testid="stSidebar"] {
        background: #0b0a10;
        color: var(--cream);
    }
    [data-testid="stSidebar"] * {
        color: var(--cream) !important;
    }

    h1, h2, h3 {
        font-family: 'Archivo', system-ui, sans-serif !important;
        font-weight: 900 !important;
        letter-spacing: -0.02em;
        color: var(--ink);
    }
    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3 {
        color: var(--cream);
    }

    /* Pill buttons, matching .btn in the site. */
    .stButton > button, .stDownloadButton > button {
        border-radius: 999px !important;
        font-family: 'Figtree', sans-serif;
        font-weight: 600;
        border: none !important;
        background: var(--ink) !important;
        color: var(--cream) !important;
        transition: background .2s ease;
    }
    .stButton > button:hover, .stDownloadButton > button:hover {
        background: var(--cobalt) !important;
        color: #fff !important;
    }
    .stButton > button[kind="primary"] {
        background: var(--cobalt) !important;
    }
    .stButton > button[kind="primary"]:hover {
        background: var(--tangerine) !important;
    }

    /* Metric tiles: acrylic block instead of Streamlit's bare numbers. */
    [data-testid="stMetric"] {
        background: var(--cobalt);
        border-radius: 18px;
        padding: 14px 18px;
        color: #fff;
    }
    [data-testid="stMetric"] label,
    [data-testid="stMetricValue"] {
        color: #fff !important;
    }

    /* Info/success/warning callouts, softened to the tile palette. */
    [data-testid="stAlertContainer"], .stAlert {
        border-radius: 18px !important;
    }

    /* File uploader and text inputs, rounded to match .demo-file / .demo-select. */
    [data-testid="stFileUploaderDropzone"] {
        border-radius: 14px !important;
        border: 2px dashed var(--ink-soft) !important;
    }
    .stTextInput input, .stTextArea textarea {
        border-radius: 12px !important;
        font-family: 'Figtree', sans-serif !important;
    }

    /* Slider handle in cobalt rather than Streamlit's default red. */
    [data-testid="stSlider"] [role="slider"] {
        background-color: var(--cobalt) !important;
    }
    [data-baseweb="slider"] div[style*="background-color"] {
        background-color: var(--cobalt) !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


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


def normalize_zh(text: str) -> str:
    """Must match src/metrics.py usage elsewhere, or scores are not comparable."""
    import zhconv

    text = zhconv.convert(text or "", "zh-tw")
    drop = " \t\n，。、？！：；「」『』（）,.?!:;\"'()《》…—-·"
    return "".join(c for c in text if c not in drop)


def normalize_en(text: str) -> str:
    """Matches the jiwer.Compose transform used in src/evaluate_english.py."""
    import re

    text = (text or "").lower().strip()
    text = re.sub(r"[^\w\s]", "", text)
    return re.sub(r"\s+", " ", text).strip()


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


def transcribe(pipe, y: np.ndarray, language_code: str) -> str:
    out = pipe(
        {"raw": y, "sampling_rate": TARGET_SR},
        generate_kwargs={
            "language": language_code,
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
    "Tone-aware speech recognition for Mandarin and English speakers with "
    "dysarthria · "
    "[project site](https://anonymous6623-ownvoice.static.hf.space) · "
    "[code](https://github.com/andrewshih0407/ownvoice)"
)

lang_name = st.radio("Language", list(LANGS.keys()), horizontal=True)
lang = LANGS[lang_name]

if lang["tonal"]:
    st.info(
        "**In Mandarin, tone is the word.** 統一 (tǒng yī, *unify*) and 同一 "
        "(tóng yī, *the same*) differ by one tone and mean different things. "
        "Dysarthria flattens the pitch contour that carries tone — so a "
        "mistoned syllable is not an accent, it is a different word. The "
        "model below is fine-tuned and measurably reduces character error "
        "rate over stock Whisper.",
        icon="🗣",
    )
else:
    st.warning(
        "**English here runs stock Whisper, not a dysarthria-tuned model.** "
        "We trained one (LibriSpeech + the same six-perturbation simulator "
        "used for Mandarin) and evaluated it with matched, speaker-disjoint "
        "word error rate — the metric that actually reflects English "
        "accuracy, since character error rate flatters it. Result: WER "
        "5.66% → 6.04%, i.e. no improvement, and specifically worse on "
        "severe dysarthria (-11.3% relative). We are not shipping that "
        "checkpoint as if it matched the Mandarin result. This is genuinely "
        "unsolved, not hidden.",
        icon="⚠️",
    )

with st.sidebar:
    st.header("How to use")
    st.markdown(
        f"1. Load the sample, or upload clear {lang_name} speech\n"
        "2. **Simulate** dysarthria — hear the problem\n"
        "3. **Transcribe** the degraded audio"
    )
    severity = st.select_slider(
        "Severity", options=["mild", "moderate", "severe"], value="severe"
    )
    compare = st.checkbox(
        "Also run stock Whisper (slower, more memory)",
        value=True,
        disabled=not lang["tonal"],
        help=None if lang["tonal"] else "English only has stock Whisper — nothing to compare against.",
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
    upload = st.file_uploader(
        f"{lang_name} audio (WAV/FLAC/MP3)", type=["wav", "flac", "mp3"], key=f"upload_{lang_name}"
    )

    ref_key = f"reference_{lang_name}"

    use_sample = st.button("Use our sample clip", use_container_width=True)
    if use_sample and lang["sample"].exists():
        st.session_state["audio"] = lang["sample"].read_bytes()
        st.session_state["audio_lang"] = lang_name
        st.session_state[ref_key] = lang["sample_text"]
    if upload is not None:
        st.session_state["audio"] = upload.read()
        st.session_state["audio_lang"] = lang_name

    audio = st.session_state.get("audio")
    if audio and st.session_state.get("audio_lang") == lang_name:
        st.audio(audio)
    else:
        audio = None

    # No `value=` here on purpose: once a widget has an explicit `key`,
    # Streamlit only honors `value` on that key's very first mount, and
    # silently ignores it after — session_state[key] is the supported way to
    # set it programmatically (e.g. from the sample-clip button) afterwards.
    reference = st.text_input(
        "Reference text (optional — enables scoring)",
        placeholder=lang["sample_text"],
        key=ref_key,
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

            if lang["tonal"]:
                if compare:
                    with st.spinner("Stock Whisper… (first run downloads weights)"):
                        results["Stock Whisper"] = transcribe(
                            load_asr(BASE_MODEL), y, lang["code"]
                        )
                with st.spinner("OwnVoice fine-tuned…"):
                    results["OwnVoice (fine-tuned)"] = transcribe(
                        load_asr(TUNED_MODEL_ZH), y, lang["code"]
                    )
            else:
                with st.spinner("Whisper (English)… (first run downloads weights)"):
                    results["Whisper (English, general-purpose)"] = transcribe(
                        load_asr(BASE_MODEL), y, lang["code"]
                    )

            st.session_state["result"] = results
            st.session_state["result_lang"] = lang_name
        except Exception as exc:  # noqa: BLE001
            st.error(
                f"Transcription failed: {exc}\n\n"
                "If this looks like a memory error, untick the stock-Whisper "
                "comparison in the sidebar — two models exceed the free tier."
            )

    results = st.session_state.get("result")
    if results and st.session_state.get("result_lang") == lang_name:
        scored = bool(reference.strip())

        if lang["tonal"]:
            if scored:
                from metrics import score

            for name, text in results.items():
                ours = name.startswith("OwnVoice")
                st.markdown(f"**{name}**")
                if scored:
                    s = score(normalize_zh(reference), normalize_zh(text))
                    c1, c2, c3 = st.columns(3)
                    c1.metric("CER", f"{s.cer:.3f}")
                    c2.metric("STER", f"{s.ster:.3f}")
                    c3.metric("Intelligible", f"{s.intelligibility:.1f}%")
                if ours:
                    st.success(text)
                else:
                    st.warning(text)

            if scored and len(results) == 2:
                from metrics import score

                base = score(normalize_zh(reference), normalize_zh(results["Stock Whisper"]))
                tuned = score(
                    normalize_zh(reference), normalize_zh(results["OwnVoice (fine-tuned)"])
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
        else:
            import jiwer

            for name, text in results.items():
                st.markdown(f"**{name}**")
                if scored:
                    wer = jiwer.wer(normalize_en(reference), normalize_en(text))
                    c1, c2 = st.columns(2)
                    c1.metric("WER", f"{wer:.3f}")
                    c2.metric("Word accuracy", f"{(1 - wer) * 100:.1f}%")
                st.warning(text)
            st.caption(
                "No fine-tuned comparison here — see the notice above. This "
                "is the same general-purpose Whisper model whether or not "
                "the audio was degraded."
            )

st.divider()
if lang["tonal"]:
    st.caption(
        "Measured on a matched test set with speaker-disjoint splits: "
        "intelligibility 80.9% → 86.2% (−27.7% relative CER), and −41% on severe "
        "dysarthria. Tone error rate did **not** improve (−0.004) — generic ASR "
        "fine-tuning does not fix tone, which is the gap this project targets. "
        "All figures are on simulated dysarthria."
    )
else:
    st.caption(
        "English fine-tuning result, matched speaker-disjoint WER: clean "
        "4.92% → 6.06%, mild 6.06% → 5.95%, moderate 5.61% → 5.38%, severe "
        "6.06% → 6.75% (fine-tuned vs. stock). Overall −6.6% relative, i.e. "
        "worse. Included here because reporting a negative result honestly "
        "is part of this project, not because English is solved."
    )
