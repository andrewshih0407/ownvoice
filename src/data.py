"""
Build paired (dysarthric, clean) Mandarin datasets for OwnVoice training.

Source corpora — both openly licensed, deliberately chosen so the submission
carries no data-provenance risk (the competition handbook makes improper data
acquisition an explicit disqualification criterion):

    cv_zh_tw   JacobLinCool/common_voice_16_1_zh_TW_clean   CC0-1.0
               Taiwan-accented Mandarin. Preferred: the dysarthria corpora we
               are applying for (MDSC, CDSD) are PRC-recorded, and accent
               mismatch between conversion source and target degrades output.

    aishell3   AISHELL/AISHELL-3                            Apache-2.0
               85 h, 218 speakers, studio quality. Better for the voice-cloning
               target side because per-speaker data volume is high.

Output is a manifest JSONL plus WAV files on disk rather than a serialized HF
dataset — audio serialization is slow, opaque, and hard to inspect, and we want
to be able to listen to individual pairs while debugging the simulation.

Real dysarthric speech replaces the simulated side once licensing clears; the
manifest schema is identical either way, so no downstream code changes.
"""

from __future__ import annotations

import io
import json
from dataclasses import dataclass
from pathlib import Path

import librosa
import numpy as np
import soundfile as sf

from dysarthria_sim import SEVERITY, analyze, perturb, pyworld_available

TARGET_SR = 16_000  # Whisper's required input rate

SOURCES = {
    "cv_zh_tw": dict(
        repo="JacobLinCool/common_voice_16_1_zh_TW_clean",
        config=None,
        text_col="sentence",
        speaker_col="client_id",
        license="CC0-1.0",
        language="zh",
        tonal=True,
    ),
    "aishell3": dict(
        repo="AISHELL/AISHELL-3",
        config=None,
        text_col="transcription",
        speaker_col="speaker",
        license="Apache-2.0",
        language="zh",
        tonal=True,
    ),
    # English. Same pipeline, different corpus — the simulator is acoustic, not
    # linguistic, so it applies unchanged. Measured separately because the
    # Mandarin fine-tune did NOT transfer its dysarthria gain to English
    # (severe WER 0.290 stock vs 0.295 tuned), which is why English needs its
    # own model rather than a shared one. See src/test_english.py.
    #
    # NOTE ON LIBRISPEECH TEXT: references are fully spelled out ("mister",
    # "one hundred") while Whisper emits standard orthography ("mr", "100").
    # Scoring against them without a matching text normalizer inflates WER
    # several-fold. Train and evaluate within one convention, and do not
    # compare these numbers to published LibriSpeech results.
    "librispeech_en": dict(
        repo="openslr/librispeech_asr",
        config="clean",
        text_col="text",
        speaker_col="speaker_id",
        license="CC-BY-4.0",
        language="en",
        tonal=False,
    ),
}


@dataclass
class Manifest:
    """Paired-audio writer with an INCREMENTAL manifest.

    The manifest is appended per utterance and flushed, not written once at the
    end. Transcripts exist only in the manifest, so a build interrupted before
    the final write leaves orphaned WAVs that can never be used — which is
    exactly what happened once: ~1,900 files lost because the process was killed
    at 30%. Incremental writes make a partial build salvageable.
    """

    root: Path
    name: str = "manifest.jsonl"

    def __post_init__(self):
        self.root = Path(self.root)
        (self.root / "clean").mkdir(parents=True, exist_ok=True)
        (self.root / "dys").mkdir(parents=True, exist_ok=True)
        self.rows: list[dict] = []
        self._fh = (self.root / self.name).open("w", encoding="utf-8")

    def add(
        self,
        uid: str,
        text: str,
        clean: np.ndarray,
        dys: np.ndarray,
        severity: str,
        speaker: str,
        language: str = "zh",
    ) -> None:
        clean_p = self.root / "clean" / f"{uid}.wav"
        dys_p = self.root / "dys" / f"{uid}__{severity}.wav"
        if not clean_p.exists():
            sf.write(clean_p, clean, TARGET_SR)
        sf.write(dys_p, dys, TARGET_SR)
        row = {
            "id": f"{uid}__{severity}",
            "text": text,
            "clean_path": str(clean_p.relative_to(self.root)),
            "dys_path": str(dys_p.relative_to(self.root)),
            "severity": severity,
            "speaker": speaker,
            "duration": round(len(dys) / TARGET_SR, 3),
            "simulated": True,
            # Carried so downstream code can pick the right decoder language
            # and skip tone metrics on non-tonal corpora.
            "language": language,
        }
        self.rows.append(row)
        self._fh.write(json.dumps(row, ensure_ascii=False) + "\n")
        self._fh.flush()

    def write(self) -> Path:
        """Close the handle. Rows are already on disk."""
        if not self._fh.closed:
            self._fh.close()
        return self.root / self.name


def _decode_audio(raw: dict) -> tuple[np.ndarray, int] | None:
    """Decode a non-decoded HF audio value to (mono float64, sr).

    We deliberately bypass `datasets`' own decoder: recent versions require
    torchcodec (which needs a system FFmpeg), while soundfile already handles
    Common Voice's MP3 and AISHELL's WAV directly. One fewer moving part on
    Windows.
    """
    if raw is None:
        return None
    data = raw.get("bytes")
    path = raw.get("path")
    try:
        if data:
            y, sr = sf.read(io.BytesIO(data), dtype="float64", always_2d=False)
        elif path:
            y, sr = sf.read(path, dtype="float64", always_2d=False)
        else:
            return None
    except Exception:
        return None
    if getattr(y, "ndim", 1) > 1:
        y = y.mean(axis=1)
    return np.asarray(y, dtype=np.float64), int(sr)


def _first_text(example: dict, preferred: str) -> str | None:
    """Transcript column names vary across community re-uploads."""
    for key in (preferred, "sentence", "transcription", "text", "transcript"):
        val = example.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()
    return None


def build(
    source: str = "cv_zh_tw",
    split: str = "train",
    limit: int = 200,
    severities: tuple[str, ...] = ("mild", "moderate", "severe"),
    out_dir: str | Path = "data/paired",
    seed: int = 0,
    min_dur: float = 0.8,
    max_dur: float = 12.0,
    shuffle_buffer: int = 5000,
) -> Path:
    """Stream a clean corpus, simulate dysarthria, write paired WAVs + manifest.

    Streaming avoids downloading the full corpus (AISHELL-3 is ~19 GB) when we
    only need a slice.
    """
    from datasets import Audio, load_dataset

    if source not in SOURCES:
        raise ValueError(f"source must be one of {list(SOURCES)}")
    spec = SOURCES[source]

    if not pyworld_available():
        raise RuntimeError(
            "pyworld unavailable — F0 perturbation is the core of the Mandarin "
            "tone hypothesis. Install pyworld before building data."
        )

    print(
        f"source={source}  language={spec.get('language','zh')}  "
        f"tonal={spec.get('tonal', True)}  license={spec['license']}  "
        f"streaming={spec['repo']}"
    )
    if not spec.get("tonal", True):
        print(
            "NOTE: non-tonal language — TER/STER are meaningless on this corpus. "
            "Report CER/WER only."
        )
    ds = load_dataset(spec["repo"], spec["config"], split=split, streaming=True)

    # Hand decoding to soundfile instead of datasets/torchcodec. EVERY Audio
    # column must be cast, not just the one we read: the batch formatter decodes
    # all of them eagerly, so a stray column (Common Voice ships an `original`
    # alongside `audio`) will still trigger the torchcodec import error.
    features = ds.features or {}
    audio_cols = [c for c, f in features.items() if isinstance(f, Audio)]
    for col in audio_cols:
        ds = ds.cast_column(col, Audio(decode=False))
    print(f"audio columns (decode disabled): {audio_cols}")

    # Shuffle the stream. Common Voice is ordered by contributor, so reading
    # sequentially yields almost no speaker variety — a 40-utterance sequential
    # read gave just 2 speakers, which is unusable for speaker-disjoint splits.
    if shuffle_buffer > 0:
        ds = ds.shuffle(seed=seed, buffer_size=shuffle_buffer)
        print(f"stream shuffled (buffer={shuffle_buffer})")

    man = Manifest(out_dir)
    kept = skipped = 0

    try:
        kept, skipped = _consume(
            ds, man, spec, source, limit, severities, seed, min_dur, max_dur
        )
    except KeyboardInterrupt:
        print("\ninterrupted — partial manifest is still valid")
    finally:
        path = man.write()

    n_speakers = len({r["speaker"] for r in man.rows})
    print(
        f"\nwrote {len(man.rows)} pairs from {kept} utterances "
        f"({skipped} skipped) -> {path}"
    )
    print(f"unique speakers: {n_speakers}")
    if n_speakers < 8:
        print(
            f"WARNING  only {n_speakers} speakers. Speaker-disjoint splits need "
            "many more;\n         raise --limit or --shuffle-buffer."
        )
    return path


def _consume(
    ds,
    man: Manifest,
    spec: dict,
    source: str,
    limit: int,
    severities: tuple[str, ...],
    seed: int,
    min_dur: float,
    max_dur: float,
) -> tuple[int, int]:
    kept = skipped = 0
    for i, ex in enumerate(ds):
        if kept >= limit:
            break

        text = _first_text(ex, spec["text_col"])
        decoded = _decode_audio(ex.get("audio"))
        if not text or decoded is None:
            skipped += 1
            continue

        y, sr = decoded
        if sr != TARGET_SR:
            y = librosa.resample(y, orig_sr=sr, target_sr=TARGET_SR)

        dur = len(y) / TARGET_SR
        if not (min_dur <= dur <= max_dur):
            skipped += 1
            continue

        peak = np.abs(y).max()
        if peak < 1e-4:  # silent/corrupt
            skipped += 1
            continue
        y = y / peak * 0.95

        uid = f"{source}_{i:06d}"
        speaker = str(ex.get(spec["speaker_col"], "unk"))

        # Decompose ONCE, then perturb per severity. Analysis is by far the
        # most expensive step, and it is identical across severities.
        f0, sp, ap = analyze(np.ascontiguousarray(y), TARGET_SR)
        for sev in severities:
            dys = perturb(f0, sp, ap, TARGET_SR, severity=sev, seed=seed + i)
            man.add(
                uid, text, y.astype(np.float32), dys, sev, speaker,
                language=spec.get("language", "zh"),
            )

        kept += 1
        if kept % 100 == 0:
            print(f"  {kept}/{limit} utterances ({len(man.rows)} pairs)", flush=True)

    return kept, skipped


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description="Build paired dysarthric/clean data.")
    ap.add_argument("--source", default="cv_zh_tw", choices=list(SOURCES))
    ap.add_argument("--split", default="train")
    ap.add_argument("--limit", type=int, default=200)
    ap.add_argument("--out", default="data/paired")
    ap.add_argument(
        "--severities", nargs="+", default=list(SEVERITY), choices=list(SEVERITY)
    )
    ap.add_argument("--shuffle-buffer", type=int, default=5000)
    a = ap.parse_args()
    build(
        source=a.source,
        split=a.split,
        limit=a.limit,
        severities=tuple(a.severities),
        out_dir=a.out,
        shuffle_buffer=a.shuffle_buffer,
    )
