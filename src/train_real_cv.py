"""
Train ONE multilingual model on real dysarthric speech, and score it only on patients it never heard.

Speaker-disjoint k-fold cross-validation (real_cv.py): every fold holds out a set of
dysarthric speakers from every corpus, trains on the rest plus healthy controls plus
simulated pairs, and is scored on the held-out speakers. Each clip is scored by:
  stock   openai/whisper-small, untouched
  init    the starting checkpoint (default runs/asr_v1, our simulated-data model)
  cv      the fold model that never heard that speaker
Each training row carries its language token, so one model writes Chinese for Mandarin
speech and English for English speech.

Pre-registered before any result (2026-11-22):
  headline   mean per-clip CER, cv vs init and cv vs stock, per corpus, on
             --eval-per-speaker clips per dysarthric speaker (seed 0; for MDSC this is
             exactly the 2026-10-20 clip set); paired Wilcoxon on per-clip CER.
  secondary  STER (Mandarin), WER (English), per-speaker better/worse counts.
  Everything else is exploratory.

usage:
  python train_real_cv.py --torgo ../data/torgo                                  # TORGO now
  python train_real_cv.py --torgo ../data/torgo --mdsc ../data/mdsc/extracted    # once MDSC is here
  python train_real_cv.py ... --folds 0 --max-steps 2 --per-speaker 4 --eval-per-speaker 2   # smoke test
  python train_real_cv.py ... --summarize                                        # report only
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np
import soundfile as sf
import torch

from real_corpora import LOADERS, Corpus
from real_cv import drop_texts, eval_sample, key, make_folds, train_rows
from train_asr import Collator, normalize

SR = 16_000
LONG = {"zh": "chinese", "en": "english"}
# Must equal backend/app.py GEN_KWARGS (minus language), so scores match what the app serves.
DECODE = {"task": "transcribe", "no_repeat_ngram_size": 4, "repetition_penalty": 1.15}


def load_audio(path: str) -> np.ndarray:
    y, sr = sf.read(path, dtype="float32")
    if y.ndim > 1:
        y = y.mean(axis=1)
    if sr != SR:
        import librosa
        y = librosa.resample(y, orig_sr=sr, target_sr=SR)
    return y


class RowsDataset(torch.utils.data.Dataset):
    """Features and language-tagged labels computed on the fly (no multi-GB feature cache on disk)."""

    def __init__(self, rows: list[dict], processor):
        self.rows, self.p = rows, processor

    def __len__(self) -> int:
        return len(self.rows)

    def __getitem__(self, i: int) -> dict:
        r = self.rows[i]
        feats = self.p.feature_extractor(load_audio(r["audio_path"]), sampling_rate=SR).input_features[0]
        self.p.tokenizer.set_prefix_tokens(language=LONG[r["language"]], task="transcribe")
        labels = self.p.tokenizer(normalize(r["text"], r["language"])).input_ids
        return {"input_features": feats, "labels": labels}


def train_fold(rows: list[dict], init: str, out: Path, a) -> None:
    from transformers import Seq2SeqTrainer, Seq2SeqTrainingArguments, WhisperForConditionalGeneration, WhisperProcessor

    processor = WhisperProcessor.from_pretrained(init)
    model = WhisperForConditionalGeneration.from_pretrained(init)
    model.config.forced_decoder_ids = None
    model.config.suppress_tokens = []
    model.generation_config.forced_decoder_ids = None
    args = Seq2SeqTrainingArguments(
        output_dir=str(out / "ckpt"), per_device_train_batch_size=a.batch_size,
        gradient_accumulation_steps=a.grad_accum, learning_rate=a.lr, num_train_epochs=a.epochs,
        max_steps=a.max_steps, warmup_ratio=0.1, gradient_checkpointing=True, fp16=torch.cuda.is_available(),
        eval_strategy="no", save_strategy="no", logging_steps=10, report_to=[], seed=a.seed,
        remove_unused_columns=False, dataloader_num_workers=0)
    trainer = Seq2SeqTrainer(model=model, args=args, train_dataset=RowsDataset(rows, processor),
                             data_collator=Collator(processor), processing_class=processor)
    t0 = time.time()
    trainer.train()
    print(f"  trained {len(rows)} rows in {(time.time() - t0) / 60:.1f} min")
    trainer.save_model(str(out / "model"))
    processor.save_pretrained(str(out / "model"))


def score(ref: str, hyp: str, lang: str) -> dict:
    import jiwer
    r, h = normalize(ref, lang), normalize(hyp, lang)
    if lang == "zh":
        from metrics import score as zh_score
        s = zh_score(r, h)
        return {"cer": s.cer, "ster": s.ster}
    return {"cer": jiwer.cer(r, h) if r else 0.0, "wer": jiwer.wer(r, h) if r else 0.0}


def transcribe(model_id: str, clips: list[dict], out: Path) -> None:
    """Transcribe clips not yet in `out` (resumable), one JSON line per clip."""
    done = {json.loads(l)["clip"] for l in out.open(encoding="utf-8")} if out.exists() else set()
    todo = [c for c in clips if c["clip"] not in done]
    if not todo:
        return
    from transformers import pipeline
    asr = pipeline("automatic-speech-recognition", model=model_id, device=0 if torch.cuda.is_available() else -1,
                   chunk_length_s=30)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("a", encoding="utf-8") as fh:
        for n, c in enumerate(todo, 1):
            hyp = asr({"raw": load_audio(c["audio_path"]), "sampling_rate": SR},
                      generate_kwargs={"language": c["language"], **DECODE})["text"]
            fh.write(json.dumps({**c, "hyp": hyp, **score(c["ref"], hyp, c["language"])}, ensure_ascii=False) + "\n")
            fh.flush()
            if n % 20 == 0:
                print(f"    {out.stem}: {n}/{len(todo)}", flush=True)


def held_out_clips(corpora: list[Corpus], fold: list[str], per_speaker: int, seed: int) -> list[dict]:
    clips = []
    for c in corpora:
        for spk, utts in eval_sample(c, per_speaker, seed).items():
            if key(c, spk) in fold:
                clips += [{"clip": f"{c.name}:{u[0]}", "corpus": c.name, "speaker": key(c, spk),
                           "language": c.language, "audio_path": str(u[1]), "ref": u[2]} for u in utts]
    return clips


def _compare(rs: list[dict], a: str, b: str) -> dict:
    """b vs a on the same clips: mean CER, relative cut, paired Wilcoxon, per-clip and per-speaker counts."""
    from scipy.stats import wilcoxon
    x, y = np.array([r[a]["cer"] for r in rs]), np.array([r[b]["cer"] for r in rs])
    per_spk: dict[str, list[float]] = {}
    for r in rs:
        per_spk.setdefault(r[b]["speaker"], []).append(r[a]["cer"] - r[b]["cer"])
    return {"cut": float((x.mean() - y.mean()) / x.mean()) if x.mean() else 0.0,
            "p": float(wilcoxon(x, y).pvalue) if len(rs) >= 10 and np.any(x != y) else None,
            "better": int((y < x).sum()), "worse": int((y > x).sum()), "tie": int((y == x).sum()),
            "speakers_better": int(sum(np.mean(v) > 0 for v in per_spk.values())),
            "speakers_worse": int(sum(np.mean(v) < 0 for v in per_spk.values()))}


def summarize(out: Path) -> dict:
    preds: dict[str, dict] = {}
    for f in sorted((out / "preds").glob("*.jsonl")):
        tag = "cv" if f.stem.startswith("fold") else f.stem
        for line in f.open(encoding="utf-8"):
            r = json.loads(line)
            preds.setdefault(r["clip"], {})[tag] = r
    rows = [v for v in preds.values() if {"stock", "init", "cv"} <= v.keys()]
    report = {}
    print("| corpus | clips | speakers | stock CER | init CER | cv CER | cv vs init | p | cv vs stock | p | speakers better/worse vs init |")
    print("|---|---|---|---|---|---|---|---|---|---|---|")
    for corpus in sorted({r["cv"]["corpus"] for r in rows}):
        rs = [r for r in rows if r["cv"]["corpus"] == corpus]
        mean = {t: float(np.mean([r[t]["cer"] for r in rs])) for t in ("stock", "init", "cv")}
        vi, vs = _compare(rs, "init", "cv"), _compare(rs, "stock", "cv")
        extra = "ster" if rs[0]["cv"]["language"] == "zh" else "wer"
        report[corpus] = {"clips": len(rs), "speakers": len({r["cv"]["speaker"] for r in rs}), "cer": mean,
                          extra: {t: float(np.mean([r[t][extra] for r in rs])) for t in ("stock", "init", "cv")},
                          "cv_vs_init": vi, "cv_vs_stock": vs}
        fp = lambda p: f"{p:.2g}" if p is not None else "n/a"
        print(f"| {corpus} | {len(rs)} | {report[corpus]['speakers']} | {mean['stock']:.3f} | {mean['init']:.3f} | "
              f"{mean['cv']:.3f} | {vi['cut'] * 100:+.0f}% | {fp(vi['p'])} | {vs['cut'] * 100:+.0f}% | {fp(vs['p'])} | "
              f"{vi['speakers_better']} / {vi['speakers_worse']} |")
    (out / "summary.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
    return report


def run_fold(i: int, fold: list[str], corpora: list[Corpus], a) -> None:
    out = Path(a.out)
    fdir = out / f"fold{i}"
    sims = [(Path(a.sim_zh), "zh", a.sim_n), (Path(a.sim_en), "en", a.sim_n)]
    rows = train_rows(corpora, fold, a.per_speaker, a.controls_per_speaker, sims, seed=a.seed + i)
    clips = held_out_clips(corpora, fold, a.eval_per_speaker, a.seed)
    print(f"fold {i}: held out {fold}")
    if a.text_disjoint:
        test_texts = {normalize(c["ref"], c["language"]) for c in clips}
        before = len(rows)
        rows = drop_texts(rows, test_texts, normalize)
        assert not {normalize(r["text"], r["language"]) for r in rows} & test_texts
        print(f"  text-disjoint: dropped {before - len(rows)} rows that say a test transcript")
    fdir.mkdir(parents=True, exist_ok=True)
    with (fdir / "train_rows.jsonl").open("w", encoding="utf-8") as fh:
        fh.writelines(json.dumps(r, ensure_ascii=False) + "\n" for r in rows)
    print(f"  {len(rows)} training rows")
    if not (fdir / "model" / "config.json").exists() and not a.skip_train:
        train_fold(rows, a.init, fdir, a)
    clips = clips[: a.eval_limit] if a.eval_limit else clips
    print(f"  scoring {len(clips)} held-out clips")
    transcribe(a.base, clips, out / "preds" / "stock.jsonl")
    transcribe(a.init, clips, out / "preds" / "init.jsonl")
    transcribe(str(fdir / "model"), clips, out / "preds" / f"fold{i}.jsonl")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--torgo", default=None, help="TORGO root holding F01..M05, FC*, MC*")
    ap.add_argument("--mdsc", default=None, help="MDSC folder holding Uncontrol/ and Control/")
    ap.add_argument("--sim-zh", default="../data/train")
    ap.add_argument("--sim-en", default="../data/train_en")
    ap.add_argument("--sim-n", type=int, default=300, help="simulated rows per language per fold")
    ap.add_argument("--out", default="../runs/real_cv")
    ap.add_argument("--k", type=int, default=4)
    ap.add_argument("--folds", type=int, nargs="*", default=None)
    ap.add_argument("--init", default="../runs/asr_v1")
    ap.add_argument("--base", default="openai/whisper-small")
    ap.add_argument("--per-speaker", type=int, default=150)
    ap.add_argument("--controls-per-speaker", type=int, default=30)
    ap.add_argument("--eval-per-speaker", type=int, default=20)
    ap.add_argument("--eval-limit", type=int, default=0)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--epochs", type=float, default=1.0)
    ap.add_argument("--batch-size", type=int, default=4)
    ap.add_argument("--grad-accum", type=int, default=4)
    ap.add_argument("--lr", type=float, default=1e-5)
    ap.add_argument("--max-steps", type=int, default=-1)
    ap.add_argument("--skip-train", action="store_true")
    ap.add_argument("--no-text-disjoint", dest="text_disjoint", action="store_false",
                    help="allow training on test transcripts spoken by other speakers (inflates scores)")
    ap.add_argument("--summarize", action="store_true")
    a = ap.parse_args()

    out = Path(a.out)
    if a.summarize:
        summarize(out)
        return
    roots = {"torgo": a.torgo, "mdsc": a.mdsc}
    corpora = [LOADERS[n](Path(r)) for n, r in roots.items() if r]
    if not corpora:
        raise SystemExit("Give at least one real corpus: --torgo and/or --mdsc.")
    for c in corpora:
        print(f"{c.name} ({c.language}): {len(c.dysarthric)} dysarthric speakers / {c.n_utts('dysarthric')} clips, "
              f"{len(c.control)} controls / {c.n_utts('control')} clips")
    folds = make_folds(corpora, a.k, a.seed)
    out.mkdir(parents=True, exist_ok=True)
    (out / "folds.json").write_text(json.dumps(folds, indent=1), encoding="utf-8")
    for i in (a.folds if a.folds is not None else range(a.k)):
        run_fold(i, folds[i], corpora, a)
    summarize(out)


if __name__ == "__main__":
    main()
