"""
Loaders for REAL dysarthric speech corpora, in one shared shape.

Every loader returns a Corpus: a language plus two maps, dysarthric and control,
from speaker id to that speaker's usable utterances (id, wav path, transcript).
The cross-validation code in real_cv.py works on this shape only, so adding a
corpus (Speech Accessibility Project, EasyCall, CDSD...) means adding one loader.

Corpora (all used under their licences, non-commercial research):
  TORGO       English, cerebral palsy / ALS, 8 dysarthric + 7 control speakers.
              University of Toronto, free for academic non-profit use, cite
              Rudzicz et al. 2012. Direct download; see data/torgo/fetch.sh.
  MDSC        Mandarin (AISHELL-6B), 21 dysarthric + 25 control, CC BY-NC 4.0.
              Behind a terms page a person must accept; nothing here downloads it.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

Utt = tuple[str, Path, str]  # (utterance id, wav path, transcript)


@dataclass(frozen=True)
class Corpus:
    name: str
    language: str  # Whisper language code: "zh" or "en"
    dysarthric: dict[str, list[Utt]] = field(default_factory=dict)
    control: dict[str, list[Utt]] = field(default_factory=dict)
    severity: dict[str, str] = field(default_factory=dict)  # speaker -> mild/moderate/severe, when known

    def n_utts(self, group: str) -> int:
        return sum(len(v) for v in getattr(self, group).values())


# ---------------------------------------------------------------- TORGO

# TORGO prompts mix read text with instructions to the speaker. Only read text has a transcript.
_INSTRUCTION = re.compile(r"^\s*\[.*\]\s*$")          # "[say Ah for 5 seconds]"
_INLINE_NOTE = re.compile(r"\s*\[[^\]]*\]")              # "read [as in I can read]" -> "read"
_PICTURE = re.compile(r"input/images|\.jpg$", re.I)      # picture description, free speech, no transcript


def clean_torgo_prompt(raw: str) -> str | None:
    """Transcript for a TORGO prompt, or None when the prompt has no readable transcript."""
    text = raw.strip()
    if not text or _INSTRUCTION.match(text) or _PICTURE.search(text) or text.lower() == "xxx":
        return None
    text = _INLINE_NOTE.sub("", text).strip()
    return text if re.search(r"[A-Za-z]", text) else None


def _torgo_wav(session: Path, utt_id: str) -> Path | None:
    """Head-mounted mic first (closer, cleaner), array mic as a fallback. One recording per prompt."""
    for mic in ("wav_headMic", "wav_arrayMic"):
        wav = session / mic / f"{utt_id}.wav"
        if wav.is_file():
            return wav
    return None


def _torgo_speaker(spk_dir: Path) -> list[Utt]:
    utts = []
    for session in sorted(spk_dir.glob("Session*")):
        for prompt in sorted((session / "prompts").glob("*.txt")):
            text = clean_torgo_prompt(prompt.read_text(encoding="utf-8", errors="ignore"))
            wav = _torgo_wav(session, prompt.stem) if text else None
            if wav:
                utts.append((f"{spk_dir.name}_{session.name}_{prompt.stem}", wav, text))
    return utts


def load_torgo(root: Path) -> Corpus:
    """Speakers F01..M05 are dysarthric; FC*/MC* are controls."""
    dys, ctl = {}, {}
    for spk_dir in sorted(p for p in root.iterdir() if p.is_dir() and re.fullmatch(r"[FM]C?\d\d", p.name)):
        utts = _torgo_speaker(spk_dir)
        if utts:
            (ctl if spk_dir.name[1] == "C" else dys)[spk_dir.name] = utts
    if not dys:
        raise SystemExit(f"No TORGO dysarthric speakers with transcripts under {root}.")
    return Corpus("torgo", "en", dys, ctl)


# ----------------------------------------------------------------- MDSC

def load_mdsc(root: Path, xlsx: Path | None = None) -> Corpus:
    """MDSC with the same usable-utterance filter as the published real-patient test (eval_mdsc.py)."""
    from eval_mdsc import band, clean, intelligibility, load_labels, usable

    groups = {}
    for folder in ("Uncontrol", "Control"):
        labels = load_labels(root / folder)
        wavs = {p.stem: p for p in (root / folder).rglob("*.wav")}
        by_spk: dict[str, list[Utt]] = {}
        for uid, text in labels.items():
            if uid in wavs and usable(uid, text):
                by_spk.setdefault(uid.split("_")[0], []).append((uid, wavs[uid], clean(text)))
        groups[folder] = {s: sorted(u) for s, u in sorted(by_spk.items())}
    if not groups["Uncontrol"]:
        raise SystemExit(f"No usable MDSC dysarthric utterances under {root / 'Uncontrol'}.")

    xlsx = xlsx or next((p for p in (root / "Intelligibility.xlsx", root.parent / "Intelligibility.xlsx") if p.is_file()), None)
    scores = intelligibility(xlsx) if xlsx else {}
    sev = {s: band(scores.get(s)) for s in groups["Uncontrol"] if s in scores}
    return Corpus("mdsc", "zh", groups["Uncontrol"], groups["Control"], sev)


LOADERS = {"torgo": load_torgo, "mdsc": load_mdsc}
