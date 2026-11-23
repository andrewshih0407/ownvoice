"""
Speaker-disjoint cross-validation over REAL dysarthric speech, across corpora and languages.

One multilingual model is trained per fold. Each fold holds out a set of dysarthric
speakers (from every corpus at once) and is scored only on them, so every score is on
a patient the model never heard. Everything here is deterministic and model-free so it
can be tested without audio.

The property that must never break: no audio from a held-out speaker reaches training.
`train_rows` checks it and raises if it fails.
"""
from __future__ import annotations

import json
import random
from pathlib import Path

from real_corpora import Corpus, Utt

SpeakerKey = str  # "corpus:speaker", unique across corpora
BAND_ORDER = ("severe", "moderate", "mild", "unknown")


def key(corpus: Corpus, speaker: str) -> SpeakerKey:
    return f"{corpus.name}:{speaker}"


def make_folds(corpora: list[Corpus], k: int, seed: int) -> list[list[SpeakerKey]]:
    """Deal every dysarthric speaker into k folds, round-robin, grouped by corpus then severity.

    Grouping before dealing spreads each corpus and each severity band evenly over the
    folds; shuffling within a group (seeded) keeps the assignment from following speaker ids.
    """
    rng = random.Random(seed)
    folds: list[list[SpeakerKey]] = [[] for _ in range(k)]
    i = 0
    for c in corpora:
        for band in BAND_ORDER:
            members = sorted(s for s in c.dysarthric if c.severity.get(s, "unknown") == band)
            rng.shuffle(members)
            for s in members:
                folds[i % k].append(key(c, s))
                i += 1
    return [sorted(f) for f in folds]


def eval_sample(corpus: Corpus, per_speaker: int, seed: int) -> dict[str, list[Utt]]:
    """The scored clips for every dysarthric speaker of one corpus.

    Same draw as eval_mdsc.py: one Random(seed), speakers in sorted order, rng.sample over
    each speaker's sorted ids. For MDSC this returns exactly the clips behind the published
    2026-10-20 real-patient numbers, so the new results are directly comparable.
    """
    rng = random.Random(seed)
    out = {}
    for spk in sorted(corpus.dysarthric):
        utts = corpus.dysarthric[spk]
        picked = set(rng.sample(sorted(u[0] for u in utts), min(per_speaker, len(utts))))
        out[spk] = [u for u in utts if u[0] in picked]
    return out


def _row(utt: Utt, corpus: Corpus, speaker: str, condition: str) -> dict:
    uid, wav, text = utt
    return {"id": f"{corpus.name}:{uid}", "audio_path": str(Path(wav).resolve()), "text": text,
            "speaker": key(corpus, speaker), "language": corpus.language, "condition": condition}


def sim_rows(sim_root: Path, language: str, n: int, rng: random.Random) -> list[dict]:
    """n rows from a simulated corpus, alternating degraded and clean, so earlier gains are kept."""
    if n <= 0 or not (sim_root / "manifest.jsonl").is_file():
        return []
    raw = [json.loads(l) for l in (sim_root / "manifest.jsonl").open(encoding="utf-8")]
    rows = []
    for i, r in enumerate(rng.sample(raw, min(n, len(raw)))):
        degraded = i % 2 == 0
        rel = r["dys_path"] if degraded else r["clean_path"]
        rows.append({"id": f"sim-{language}:{r['id']}:{i % 2}", "audio_path": str((sim_root / rel).resolve()),
                     "text": r["text"], "speaker": f"sim-{language}:{r['speaker'][:16]}", "language": language,
                     "condition": f"sim-{r['severity']}" if degraded else "sim-clean"})
    return rows


def train_rows(corpora: list[Corpus], held_out: list[SpeakerKey], per_speaker: int, controls_per_speaker: int,
               sims: list[tuple[Path, str, int]], seed: int) -> list[dict]:
    """Training rows for one fold: held-in patients, healthy controls, simulated pairs.

    Raises if a held-out speaker's audio is present: that would leak the test set.
    """
    rng = random.Random(seed)
    held = set(held_out)
    rows = []
    for c in corpora:
        for spk, utts in c.dysarthric.items():
            if key(c, spk) not in held:
                rows += [_row(u, c, spk, "real-dysarthric") for u in rng.sample(utts, min(per_speaker, len(utts)))]
        for spk, utts in c.control.items():
            rows += [_row(u, c, spk, "real-control") for u in rng.sample(utts, min(controls_per_speaker, len(utts)))]
    for sim_root, language, n in sims:
        rows += sim_rows(sim_root, language, n, rng)
    leaked = {r["speaker"] for r in rows} & held
    if leaked:
        raise SystemExit(f"held-out speakers in training data: {sorted(leaked)}")
    rng.shuffle(rows)
    return rows


def drop_texts(rows: list[dict], texts: set[str], norm) -> list[dict]:
    """Remove training rows whose normalised transcript is in `texts` (the fold's test transcripts).

    Corpora like TORGO and MDSC have every speaker read the same prompt list, so a
    speaker-disjoint split alone still trains on the exact words it is tested on, from
    other speakers. On TORGO that was 157 of 160 test clips (2026-11-22). Dropping them
    makes the test new-speaker AND new-text. `norm(text, language)` must be the scoring
    normaliser so "same text" means the same thing in training and scoring.
    """
    return [r for r in rows if norm(r["text"], r["language"]) not in texts]
