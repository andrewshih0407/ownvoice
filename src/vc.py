"""
Stage 1 (VC architecture): dysarthric -> intelligible speech, no training.

Replaces the earlier ASR->TTS cascade. Rationale in docs/prior-art.md: the
closest prior work (Academia Sinica / Chi Mei Hospital) and the wider SOTA
(CLARIS, DiffDSR) all use direct speech-to-speech conversion. A text bottleneck
discards prosody and timing, which matters for a communication prosthesis.

Method — locally linear embedding (LLE) voice conversion:

    1. Chinese-HuBERT encodes the source frame-by-frame into content features
       that are largely speaker-independent.
    2. For each source frame, find its k nearest neighbours among the reference
       speaker's frames in that same content space.
    3. Solve for barycentric weights reconstructing the source feature from
       those neighbours, then apply the SAME weights to the neighbours'
       mel-spectrogram frames.
    4. Vocode the resulting mel with HiFi-GAN.

Why LLE rather than a trained model: it is non-parametric, so it needs no
training data at all. The Sinica paper chose it explicitly because it "does not
require a large training dataset, which is advantageous in experiments with
scarce dysarthric speech data" — their entire corpus was one patient reading 320
sentences. Our ASR run confirmed the same constraint from the other direction:
whisper-small overfit 3,200 rows after a single epoch.

Models (both MIT):
    TencentGameMate/chinese-hubert-large   content features
    microsoft/speecht5_hifigan             80-bin mel @ 16 kHz -> waveform

Reference modes:
    same-speaker   the speaker's own clean audio. Only possible because our
                   dysarthria is simulated, so a clean counterpart exists. This
                   is an ORACLE upper bound, not a deployable configuration —
                   a real patient has no clean recording of the same utterance.
    cross-speaker  a different, healthy speaker. Realistic, and what a real
                   deployment must use. Identity is lost here, which is exactly
                   what stage 2 (Seed-VC) has to restore.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import soundfile as sf
import torch

TARGET_SR = 16_000
HUBERT_ID = "TencentGameMate/chinese-hubert-large"
VOCODER_ID = "microsoft/speecht5_hifigan"

_hubert = _hubert_fe = _vocoder = _mel_fe = None


def _device() -> str:
    return "cuda" if torch.cuda.is_available() else "cpu"


def _load():
    """Lazy-load the three models once."""
    global _hubert, _hubert_fe, _vocoder, _mel_fe
    if _hubert is None:
        from transformers import (
            AutoFeatureExtractor,
            HubertModel,
            SpeechT5FeatureExtractor,
            SpeechT5HifiGan,
        )

        dev = _device()
        _hubert_fe = AutoFeatureExtractor.from_pretrained(HUBERT_ID)
        _hubert = HubertModel.from_pretrained(HUBERT_ID).to(dev).eval()
        _vocoder = SpeechT5HifiGan.from_pretrained(VOCODER_ID).to(dev).eval()
        _mel_fe = SpeechT5FeatureExtractor.from_pretrained("microsoft/speecht5_tts")
    return _hubert, _hubert_fe, _vocoder, _mel_fe


def read_audio(path: str | Path) -> np.ndarray:
    y, sr = sf.read(path, dtype="float32", always_2d=False)
    if y.ndim > 1:
        y = y.mean(axis=1)
    if sr != TARGET_SR:
        import librosa

        y = librosa.resample(y, orig_sr=sr, target_sr=TARGET_SR)
    return y.astype(np.float32)


#: Which transformer layer to read content from. NOT the last one.
#: HuBERT-large has 24 layers; the final layer encodes acoustic and speaker
#: detail, while intermediate layers carry the most speaker-invariant phonetic
#: content. Using last_hidden_state made kNN match on voice texture instead of
#: phonetic content, which is why the first conversion attempt degraded
#: intelligibility. Tune with `sweep_vc.py`.
DEFAULT_LAYER = 12


@torch.no_grad()
def content_features(y: np.ndarray, layer: int | None = None) -> np.ndarray:
    """Chinese-HuBERT hidden states at `layer`, (frames, 1024). ~50 Hz.

    Args:
        layer: transformer layer index. 0 is the CNN feature projection output;
            1..24 are transformer blocks. None uses DEFAULT_LAYER.
    """
    model, fe, _, _ = _load()
    layer = DEFAULT_LAYER if layer is None else layer
    inputs = fe(y, sampling_rate=TARGET_SR, return_tensors="pt")
    inputs = {k: v.to(_device()) for k, v in inputs.items()}
    out = model(**inputs, output_hidden_states=True)
    hs = out.hidden_states
    if not (0 <= layer < len(hs)):
        raise ValueError(f"layer must be in [0, {len(hs)-1}], got {layer}")
    return hs[layer][0].cpu().numpy()


def mel_spectrogram(y: np.ndarray) -> np.ndarray:
    """80-bin log-mel matching the HiFi-GAN's expected input. (frames, 80)."""
    _, _, _, mel_fe = _load()
    out = mel_fe(audio_target=y, sampling_rate=TARGET_SR, return_tensors="np")
    return np.asarray(out["input_values"][0], dtype=np.float32)


@torch.no_grad()
def vocode(mel: np.ndarray) -> np.ndarray:
    """80-bin log-mel -> waveform."""
    _, _, voc, _ = _load()
    t = torch.from_numpy(np.asarray(mel, dtype=np.float32)).to(_device())
    return voc(t).cpu().numpy().astype(np.float32)


def _resample_frames(arr: np.ndarray, n_out: int) -> np.ndarray:
    """Linear resample along the frame axis.

    HuBERT runs at ~50 Hz and the vocoder's mel at 62.5 Hz, so the two frame
    sequences must be put on a common clock before they can be paired.
    """
    n_in = arr.shape[0]
    if n_in == n_out or n_in < 2:
        return arr
    idx = np.linspace(0, n_in - 1, n_out)
    lo = np.floor(idx).astype(int)
    hi = np.minimum(lo + 1, n_in - 1)
    w = (idx - lo)[:, None]
    return arr[lo] * (1 - w) + arr[hi] * w


class Reference:
    """A frame-aligned (content feature, mel) dictionary from clean speech."""

    def __init__(self, feats: np.ndarray, mels: np.ndarray):
        self.feats = feats.astype(np.float32)
        self.mels = mels.astype(np.float32)
        # Unit-normalize so nearest-neighbour search is cosine, which is far
        # more stable than raw L2 on HuBERT activations.
        norms = np.linalg.norm(self.feats, axis=1, keepdims=True)
        self.unit = self.feats / np.maximum(norms, 1e-8)

    def __len__(self) -> int:
        return self.feats.shape[0]

    @classmethod
    def from_paths(
        cls,
        paths: list[str | Path],
        max_frames: int = 60_000,
        layer: int | None = None,
    ):
        feats, mels = [], []
        total = 0
        for p in paths:
            y = read_audio(p)
            f = content_features(y, layer=layer)
            m = mel_spectrogram(y)
            # Put both on the mel clock.
            f = _resample_frames(f, m.shape[0])
            n = min(f.shape[0], m.shape[0])
            feats.append(f[:n])
            mels.append(m[:n])
            total += n
            if total >= max_frames:
                break
        if not feats:
            raise ValueError("no reference audio")
        return cls(np.concatenate(feats), np.concatenate(mels))


def convert(
    source: str | Path | np.ndarray,
    reference: Reference,
    k: int = 8,
    reg: float = 1e-3,
    layer: int | None = None,
) -> np.ndarray:
    """Convert source speech toward the reference voice via LLE. Returns waveform.

    Args:
        source: dysarthric audio (path or waveform).
        reference: clean-speech dictionary.
        k: neighbours per frame. Small k copies the reference too literally;
           large k over-smooths and blurs articulation.
        reg: Tikhonov regularizer on the local Gram matrix. Neighbouring HuBERT
           frames are highly collinear, so the Gram matrix is near-singular and
           the solve is unstable without it.
    """
    y = read_audio(source) if not isinstance(source, np.ndarray) else source
    src_mel = mel_spectrogram(y)
    src_feat = _resample_frames(content_features(y, layer=layer), src_mel.shape[0])

    norms = np.linalg.norm(src_feat, axis=1, keepdims=True)
    src_unit = src_feat / np.maximum(norms, 1e-8)

    # Cosine similarity against every reference frame, in blocks to bound memory.
    n_src = src_unit.shape[0]
    out_mel = np.zeros((n_src, reference.mels.shape[1]), dtype=np.float32)
    block = 512
    for start in range(0, n_src, block):
        chunk = src_unit[start : start + block]
        sim = chunk @ reference.unit.T
        idx = np.argpartition(-sim, kth=min(k, sim.shape[1] - 1), axis=1)[:, :k]

        for i in range(chunk.shape[0]):
            nb = reference.feats[idx[i]]                  # (k, D)
            diff = nb - src_feat[start + i][None, :]      # (k, D)
            gram = diff @ diff.T                          # (k, k)
            gram += np.eye(k, dtype=np.float32) * reg * np.trace(gram) / k
            try:
                w = np.linalg.solve(gram, np.ones(k, dtype=np.float32))
            except np.linalg.LinAlgError:
                w = np.ones(k, dtype=np.float32)
            s = w.sum()
            w = w / s if abs(s) > 1e-8 else np.full(k, 1.0 / k, dtype=np.float32)
            out_mel[start + i] = w @ reference.mels[idx[i]]

    return vocode(out_mel)


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description="LLE voice conversion.")
    ap.add_argument("source")
    ap.add_argument("output")
    ap.add_argument("--reference", nargs="+", required=True)
    ap.add_argument("-k", type=int, default=8)
    a = ap.parse_args()

    ref = Reference.from_paths(a.reference)
    print(f"reference frames: {len(ref)}")
    wav = convert(a.source, ref, k=a.k)
    sf.write(a.output, wav, TARGET_SR)
    print(f"{a.source} -> {a.output}  ({len(wav)/TARGET_SR:.2f}s)")
