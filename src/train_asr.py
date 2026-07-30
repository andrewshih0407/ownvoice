"""
Fine-tune Whisper for dysarthria-robust Mandarin ASR (stage 1 of OwnVoice).

Architecture context — OwnVoice is a two-stage cascade:

    stage 1 (here)  dysarthric speech -> text
                    A general-purpose ASR collapses on dysarthric input
                    (measured: 93.2% -> ~50% intelligibility, see baseline.py).
                    This stage recovers that loss.

    stage 2 (next)  text -> speech in the patient's BANKED voice
                    Zero-shot voice cloning from pre-operative recordings.

The cascade is chosen deliberately over direct speech-to-speech conversion: it
is trainable on modest data, each stage is independently measurable, and stage 1
failures are legible (you can read the transcript). The cost is lost prosody and
added latency, both of which stage 2 must address.

Run `baseline.py` first — training without a before-number is unfalsifiable.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import soundfile as sf
import torch
import zhconv

from metrics import score_corpus

TARGET_SR = 16_000


def normalize(text: str) -> str:
    """Traditional Chinese, punctuation stripped. Must match baseline.py."""
    text = zhconv.convert(text or "", "zh-tw")
    drop = " \t\n，。、？！：；「」『』（）,.?!:;\"'()《》…—-·"
    return "".join(c for c in text if c not in drop)


@dataclass
class Collator:
    """Pad log-mel features and labels; mask pad tokens out of the loss."""

    processor: Any

    def __call__(self, features: list[dict]) -> dict[str, torch.Tensor]:
        batch = self.processor.feature_extractor.pad(
            [{"input_features": f["input_features"]} for f in features],
            return_tensors="pt",
        )
        labels_batch = self.processor.tokenizer.pad(
            [{"input_ids": f["labels"]} for f in features], return_tensors="pt"
        )
        labels = labels_batch["input_ids"].masked_fill(
            labels_batch.attention_mask.ne(1), -100
        )
        # Whisper prepends BOS during generation; strip it from the targets so
        # it isn't learned twice.
        if (labels[:, 0] == self.processor.tokenizer.bos_token_id).all().item():
            labels = labels[:, 1:]
        batch["labels"] = labels
        return batch


def build_splits(
    root: Path,
    severities: tuple[str, ...],
    eval_frac: float,
    seed: int,
    include_clean: bool = True,
) -> tuple[list[dict], list[dict]]:
    """Split by SPEAKER, never by utterance.

    Splitting by utterance leaks speaker identity across train/eval and inflates
    results — the model memorizes voices rather than learning dysarthria.

    `include_clean` adds the unperturbed audio as additional training examples.
    Training on dysarthric speech alone invites catastrophic forgetting: the
    model would specialize on degraded input and regress on normal speech. A
    clinical system has to handle both, since the same patient's speech varies
    day to day and the ASR also transcribes clinicians and family.
    """
    raw = [
        json.loads(l) for l in (root / "manifest.jsonl").open(encoding="utf-8")
    ]

    rows = []
    for r in raw:
        if r["severity"] in severities:
            rows.append({**r, "audio_path": r["dys_path"], "condition": r["severity"]})

    if include_clean:
        seen: set[str] = set()
        for r in raw:
            if r["clean_path"] in seen:
                continue
            seen.add(r["clean_path"])
            rows.append(
                {**r, "audio_path": r["clean_path"], "condition": "clean"}
            )

    from collections import Counter

    print("training conditions:", dict(Counter(r["condition"] for r in rows)))
    speakers = sorted({r["speaker"] for r in rows})
    rng = np.random.default_rng(seed)
    rng.shuffle(speakers)
    n_eval = max(1, int(len(speakers) * eval_frac))
    eval_speakers = set(speakers[:n_eval])

    train = [r for r in rows if r["speaker"] not in eval_speakers]
    evl = [r for r in rows if r["speaker"] in eval_speakers]
    print(
        f"speakers: {len(speakers)} total, {len(eval_speakers)} held out\n"
        f"rows: {len(train)} train / {len(evl)} eval"
    )
    if not train or not evl:
        raise SystemExit(
            "empty split — need at least 2 distinct speakers. Build more data."
        )
    return train, evl


def to_dataset(rows: list[dict], root: Path, processor):
    from datasets import Dataset

    def gen():
        for r in rows:
            y, sr = sf.read(root / r["audio_path"], dtype="float32")
            if y.ndim > 1:
                y = y.mean(axis=1)
            feats = processor.feature_extractor(
                y, sampling_rate=sr, return_tensors="np"
            ).input_features[0]
            labels = processor.tokenizer(normalize(r["text"])).input_ids
            yield {"input_features": feats, "labels": labels}

    return Dataset.from_generator(gen)


def main(
    root: str = "../data/dev",
    model_id: str = "openai/whisper-small",
    out_dir: str = "../runs/asr",
    severities: tuple[str, ...] = ("mild", "moderate", "severe"),
    epochs: float = 3.0,
    batch_size: int = 4,
    grad_accum: int = 4,
    lr: float = 1e-5,
    eval_frac: float = 0.25,
    seed: int = 0,
    max_steps: int = -1,
    include_clean: bool = True,
    max_eval: int = 200,
    resume: str | None = None,
) -> None:
    from transformers import (
        Seq2SeqTrainer,
        Seq2SeqTrainingArguments,
        WhisperForConditionalGeneration,
        WhisperProcessor,
    )

    root = Path(root)
    cuda = torch.cuda.is_available()
    print(f"model={model_id}  cuda={cuda}")
    if not cuda:
        print(
            "WARNING: no CUDA. Fine-tuning Whisper on CPU is impractical for a "
            "real run.\nUse --max-steps 2 to smoke-test the code path only."
        )

    processor = WhisperProcessor.from_pretrained(
        model_id, language="chinese", task="transcribe"
    )
    model = WhisperForConditionalGeneration.from_pretrained(model_id)
    model.config.forced_decoder_ids = None
    model.config.suppress_tokens = []
    model.generation_config.language = "zh"
    model.generation_config.task = "transcribe"
    model.generation_config.forced_decoder_ids = None
    # Same loop suppression that fixed CER > 1.0 in the baseline.
    model.generation_config.no_repeat_ngram_size = 4
    model.generation_config.repetition_penalty = 1.15

    train_rows, eval_rows = build_splits(
        root, severities, eval_frac, seed, include_clean=include_clean
    )

    # Cap the in-training eval set. Eval uses generation (predict_with_generate),
    # which is far slower than a forward pass, so an unbounded eval set can cost
    # more than the training itself. Stratified by condition so the capped set
    # still covers every severity.
    if max_eval and len(eval_rows) > max_eval:
        per_cond = max(1, max_eval // len({r["condition"] for r in eval_rows}))
        bucketed: dict[str, list[dict]] = {}
        for r in eval_rows:
            bucketed.setdefault(r["condition"], []).append(r)
        eval_rows = [r for rs in bucketed.values() for r in rs[:per_cond]]
        print(f"eval capped to {len(eval_rows)} rows ({per_cond}/condition)")
    train_ds = to_dataset(train_rows, root, processor)
    eval_ds = to_dataset(eval_rows, root, processor)

    def compute_metrics(pred):
        label_ids = pred.label_ids
        label_ids[label_ids == -100] = processor.tokenizer.pad_token_id
        refs = processor.tokenizer.batch_decode(label_ids, skip_special_tokens=True)
        hyps = processor.tokenizer.batch_decode(
            pred.predictions, skip_special_tokens=True
        )
        s = score_corpus(
            [(normalize(r), normalize(h)) for r, h in zip(refs, hyps)]
        )
        return {
            "cer": round(s.cer, 4),
            "ster": round(s.ster, 4),
            "intelligibility": round(s.intelligibility, 2),
        }

    args = Seq2SeqTrainingArguments(
        output_dir=out_dir,
        per_device_train_batch_size=batch_size,
        gradient_accumulation_steps=grad_accum,
        per_device_eval_batch_size=batch_size,
        learning_rate=lr,
        num_train_epochs=epochs,
        max_steps=max_steps,
        warmup_ratio=0.1,
        gradient_checkpointing=True,
        fp16=cuda,
        eval_strategy="epoch" if max_steps < 0 else "no",
        save_strategy="epoch" if max_steps < 0 else "no",
        predict_with_generate=True,
        generation_max_length=128,
        logging_steps=10,
        report_to=[],
        seed=seed,
        load_best_model_at_end=max_steps < 0,
        metric_for_best_model="cer",
        greater_is_better=False,
    )

    trainer = Seq2SeqTrainer(
        model=model,
        args=args,
        train_dataset=train_ds,
        eval_dataset=eval_ds,
        data_collator=Collator(processor),
        compute_metrics=compute_metrics,
        processing_class=processor,
    )

    if resume:
        print(f"resuming from {resume}")
        trainer.train(resume_from_checkpoint=resume)
    else:
        trainer.train()

    if max_steps < 0:
        final = trainer.evaluate()
        print("\nfinal eval:", json.dumps(final, indent=2, default=str))
        Path(out_dir).mkdir(parents=True, exist_ok=True)
        (Path(out_dir) / "final_eval.json").write_text(
            json.dumps(final, indent=2, default=str), encoding="utf-8"
        )
        trainer.save_model(out_dir)
        processor.save_pretrained(out_dir)
        print(f"saved -> {out_dir}")
        print(
            "\nCompare against data/dev/baseline.json. Note both are SIMULATED "
            "dysarthria;\nno intelligibility claim is publishable until measured "
            "on real patient speech."
        )


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="../data/dev")
    ap.add_argument("--model", default="openai/whisper-small")
    ap.add_argument("--out", default="../runs/asr")
    ap.add_argument("--severities", nargs="+", default=["mild", "moderate", "severe"])
    ap.add_argument("--epochs", type=float, default=3.0)
    ap.add_argument("--batch-size", type=int, default=4)
    ap.add_argument("--grad-accum", type=int, default=4)
    ap.add_argument("--lr", type=float, default=1e-5)
    ap.add_argument("--eval-frac", type=float, default=0.25)
    ap.add_argument("--max-steps", type=int, default=-1)
    ap.add_argument(
        "--no-clean",
        action="store_true",
        help="train on dysarthric audio only (risks forgetting normal speech)",
    )
    ap.add_argument("--max-eval", type=int, default=200)
    ap.add_argument(
        "--resume-from-checkpoint",
        default=None,
        help="path to a checkpoint-N dir to continue training from",
    )
    a = ap.parse_args()
    main(
        root=a.root,
        model_id=a.model,
        out_dir=a.out,
        severities=tuple(a.severities),
        epochs=a.epochs,
        batch_size=a.batch_size,
        grad_accum=a.grad_accum,
        lr=a.lr,
        eval_frac=a.eval_frac,
        max_steps=a.max_steps,
        include_clean=not a.no_clean,
        max_eval=a.max_eval,
        resume=a.resume_from_checkpoint,
    )
