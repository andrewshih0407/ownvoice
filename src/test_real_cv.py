"""
Tests for the real-data cross-validation: prompt cleaning, the TORGO loader, folds, and leak checks.

The leak tests matter most: a fold that trains on a speaker it is scored on would
report numbers that look like generalisation and are really memorisation.
No audio is needed; wav files are empty placeholders.
Run: python test_real_cv.py   (or: pytest test_real_cv.py)
"""
from __future__ import annotations

import json
import random
import tempfile
from pathlib import Path

from real_corpora import Corpus, clean_torgo_prompt, load_torgo
from real_cv import drop_texts, eval_sample, key, make_folds, sim_rows, train_rows


def _corpus(name: str, lang: str, n_dys: int, n_ctl: int, utts_each: int = 30, severity=None) -> Corpus:
    mk = lambda spk: [(f"{spk}_{i:04d}", Path(f"/fake/{spk}/{i}.wav"), f"text {i}") for i in range(utts_each)]
    dys = {f"D{i:02d}": mk(f"D{i:02d}") for i in range(n_dys)}
    ctl = {f"C{i:02d}": mk(f"C{i:02d}") for i in range(n_ctl)}
    return Corpus(name, lang, dys, ctl, severity or {})


def test_clean_torgo_prompt():
    assert clean_torgo_prompt("storm\n") == "storm"
    assert clean_torgo_prompt("The quick brown fox jumps over the lazy dog.") == "The quick brown fox jumps over the lazy dog."
    assert clean_torgo_prompt("read [as in I can read]") == "read"
    for no_transcript in ("[say Ah for 5 seconds]", "[relax your mouth in its normal position]",
                          "input/images/kitchen.jpg", "xxx", "", "   "):
        assert clean_torgo_prompt(no_transcript) is None, no_transcript


def test_load_torgo_layout():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        files = {
            "F01/Session1/prompts/0001.txt": "storm", "F01/Session1/wav_headMic/0001.wav": "",
            "F01/Session1/prompts/0002.txt": "[say Ah for 5 seconds]", "F01/Session1/wav_headMic/0002.wav": "",
            "F01/Session1/prompts/0003.txt": "sip", "F01/Session1/wav_arrayMic/0003.wav": "",  # array mic only
            "F01/Session1/prompts/0004.txt": "chair",                                          # no audio at all
            "FC01/Session1/prompts/0001.txt": "yes", "FC01/Session1/wav_headMic/0001.wav": "",
        }
        for rel, body in files.items():
            (root / rel).parent.mkdir(parents=True, exist_ok=True)
            (root / rel).write_text(body, encoding="utf-8")
        c = load_torgo(root)
        assert c.language == "en"
        assert sorted(c.dysarthric) == ["F01"] and sorted(c.control) == ["FC01"]
        texts = {u[0]: (u[2], u[1].parent.name) for u in c.dysarthric["F01"]}
        assert texts == {"F01_Session1_0001": ("storm", "wav_headMic"), "F01_Session1_0003": ("sip", "wav_arrayMic")}


def test_folds_partition_every_speaker_once():
    a = _corpus("mdsc", "zh", 21, 0, severity={f"D{i:02d}": ("severe" if i < 6 else "moderate" if i < 10 else "mild") for i in range(21)})
    b = _corpus("torgo", "en", 8, 0)
    folds = make_folds([a, b], k=4, seed=0)
    flat = [s for f in folds for s in f]
    assert len(flat) == len(set(flat)) == 29
    assert max(map(len, folds)) - min(map(len, folds)) <= 1
    for f in folds:  # each corpus spread over every fold
        assert any(s.startswith("mdsc:") for s in f) and any(s.startswith("torgo:") for s in f)
    assert folds == make_folds([a, b], k=4, seed=0)  # deterministic


def test_train_rows_exclude_held_out():
    a, b = _corpus("mdsc", "zh", 6, 3), _corpus("torgo", "en", 4, 2)
    held = [key(a, "D00"), key(a, "D01"), key(b, "D00")]
    rows = train_rows([a, b], held, per_speaker=10, controls_per_speaker=5, sims=[], seed=0)
    speakers = {r["speaker"] for r in rows}
    assert not speakers & set(held)
    assert key(a, "D02") in speakers and key(b, "D03") in speakers and key(a, "C00") in speakers
    assert {r["language"] for r in rows} == {"zh", "en"}
    assert all(r["condition"] in ("real-dysarthric", "real-control") for r in rows)


def test_leak_check_raises():
    # A control speaker that shares a held-out speaker's key would leak; the check must stop it.
    c = _corpus("mdsc", "zh", 2, 0)
    leaky = Corpus("mdsc", "zh", c.dysarthric, {"D00": c.dysarthric["D00"]})
    try:
        train_rows([leaky], [key(leaky, "D00")], per_speaker=5, controls_per_speaker=5, sims=[], seed=0)
    except SystemExit as e:
        assert "held-out" in str(e)
    else:
        raise AssertionError("leak was not detected")


def test_drop_texts_removes_test_transcripts_from_every_speaker():
    norm = lambda t, lang: t.lower().strip(" .")
    rows = [{"text": "Storm.", "language": "en"}, {"text": "storm", "language": "en"},
            {"text": "chair", "language": "en"}, {"text": "STORM ", "language": "en"}]
    kept = drop_texts(rows, {"storm"}, norm)
    assert [r["text"] for r in kept] == ["chair"]


def test_eval_sample_matches_published_draw():
    c = _corpus("mdsc", "zh", 5, 0, utts_each=40)
    got = eval_sample(c, per_speaker=20, seed=0)
    rng = random.Random(0)  # eval_mdsc.py's loop, written out independently
    for spk in sorted(c.dysarthric):
        expect = set(rng.sample(sorted(u[0] for u in c.dysarthric[spk]), 20))
        assert {u[0] for u in got[spk]} == expect


def test_sim_rows_alternate_degraded_and_clean():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        with (root / "manifest.jsonl").open("w", encoding="utf-8") as fh:
            for i in range(10):
                fh.write(json.dumps({"id": f"u{i}", "text": "t", "clean_path": f"clean/{i}.wav",
                                     "dys_path": f"dys/{i}.wav", "severity": "mild", "speaker": f"s{i}"}) + "\n")
        rows = sim_rows(root, "zh", 4, random.Random(0))
        assert [r["condition"] for r in rows] == ["sim-mild", "sim-clean", "sim-mild", "sim-clean"]
        assert all(r["language"] == "zh" and r["speaker"].startswith("sim-zh:") for r in rows)


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print(f"ok  {t.__name__}")
    print(f"{len(tests)} passed")
