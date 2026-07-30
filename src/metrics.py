"""
Evaluation metrics for Mandarin dysarthric speech restoration.

Metric choice matters here and differs from the English dysarthria literature:

  CER (character error rate) is the primary metric, not WER. Written Chinese has
  no word delimiters, so WER depends entirely on an arbitrary segmenter and is
  not comparable across papers.

  TER (tone error rate) is the metric that captures the Mandarin-specific
  problem and does not appear in the English dysarthria literature at all.
  Mandarin tone is lexically contrastive: if a restoration outputs the right
  syllable with the wrong tone, it has produced A DIFFERENT WORD, not an accent.
  A system can post a respectable CER while being clinically unusable because
  its tones are wrong, so TER must be reported alongside CER.

  STER (segmental TER) reports tone errors only on syllables whose
  initial+final were recognized correctly — isolating tone modelling from
  segmental recognition. Without this split you cannot tell whether the model
  is mishearing the syllable or mishearing the tone.

KNOWN DEFECT IN STER — READ BEFORE CITING IT
--------------------------------------------
STER pairs syllables BY POSITION (``zip``), not by alignment. A single
insertion or deletion shifts the hypothesis relative to the reference, and
every syllable after that point compares against the wrong reference syllable,
fails the ``r_seg == h_seg`` guard, and is silently dropped from the
denominator.

Measured:

    reference 我要買東西  hypothesis 我要賣東西    -> STER 0.222  (correct)
    reference 我要買東西  hypothesis 我就要買東西  -> STER 0.000  (WRONG:
                                                     the tone error is real
                                                     but invisible)

So STER **under-reports** tone errors, and it under-reports *more* on worse
transcripts, because those contain more insertions and deletions. That biases
any baseline-vs-tuned comparison in an uncontrolled direction: the weaker model
has more length mismatches, so more of its tone errors go uncounted.

Consequence: the STER figures in docs/results.md (baseline 0.0528, tuned
0.0491, and the "tone did not improve" conclusion drawn from them) are
CONFOUNDED and must not be cited as evidence until this is fixed.

The fix is to align the two syllable sequences with edit distance first — the
machinery already exists in ``_levenshtein_ops`` — and compare tones only on
substitution/match pairs from that alignment, rather than on positional pairs.
CER is unaffected: it uses jiwer, which aligns properly.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict

import jiwer
from pypinyin import Style, lazy_pinyin

# Neutral tone in pypinyin's TONE3 style is rendered without a digit; map to 5
# per standard convention so alignment lengths stay consistent.
_NEUTRAL = "5"


def _syllables(text: str) -> list[str]:
    """Chinese text -> pinyin syllables with explicit tone digits (e.g. ma1)."""
    out = []
    for syl in lazy_pinyin(text, style=Style.TONE3, errors="ignore"):
        if not syl:
            continue
        out.append(syl if syl[-1].isdigit() else syl + _NEUTRAL)
    return out


def _split_tone(syl: str) -> tuple[str, str]:
    """'zhong1' -> ('zhong', '1')"""
    return syl[:-1], syl[-1]


def _levenshtein_ops(ref: list, hyp: list) -> tuple[int, int, int, int]:
    """Return (substitutions, deletions, insertions, ref_len) via edit distance."""
    n, m = len(ref), len(hyp)
    # dp[i][j] = (cost, sub, del, ins)
    dp = [[(0, 0, 0, 0)] * (m + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        dp[i][0] = (i, 0, i, 0)
    for j in range(1, m + 1):
        dp[0][j] = (j, 0, 0, j)

    for i in range(1, n + 1):
        for j in range(1, m + 1):
            if ref[i - 1] == hyp[j - 1]:
                dp[i][j] = dp[i - 1][j - 1]
                continue
            c_sub, c_del, c_ins = dp[i - 1][j - 1], dp[i - 1][j], dp[i][j - 1]
            best = min(c_sub[0], c_del[0], c_ins[0]) + 1
            if c_sub[0] <= c_del[0] and c_sub[0] <= c_ins[0]:
                dp[i][j] = (best, c_sub[1] + 1, c_sub[2], c_sub[3])
            elif c_del[0] <= c_ins[0]:
                dp[i][j] = (best, c_del[1], c_del[2] + 1, c_del[3])
            else:
                dp[i][j] = (best, c_ins[1], c_ins[2], c_ins[3] + 1)

    _, sub, dele, ins = dp[n][m]
    return sub, dele, ins, n


def _rate(sub: int, dele: int, ins: int, ref_len: int) -> float:
    return (sub + dele + ins) / ref_len if ref_len else 0.0


@dataclass
class Scores:
    cer: float
    ter: float
    ster: float
    syllable_er: float
    n_ref_chars: int
    n_ref_syllables: int

    @property
    def intelligibility(self) -> float:
        """Headline percentage, defined as 1 - CER. Report TER next to it."""
        return max(0.0, 1.0 - self.cer) * 100.0

    def as_dict(self) -> dict:
        d = asdict(self)
        d["intelligibility_pct"] = round(self.intelligibility, 2)
        return d


def score(reference: str, hypothesis: str) -> Scores:
    """Score one Mandarin reference/hypothesis pair.

    Args:
        reference: ground-truth Chinese text.
        hypothesis: ASR or restored-speech transcription.
    """
    ref_chars = [c for c in reference if not c.isspace()]
    hyp_chars = [c for c in hypothesis if not c.isspace()]
    cer = (
        jiwer.cer("".join(ref_chars), "".join(hyp_chars))
        if ref_chars
        else 0.0
    )

    ref_syl, hyp_syl = _syllables(reference), _syllables(hypothesis)
    syl_er = _rate(*_levenshtein_ops(ref_syl, hyp_syl))

    ref_tones = [_split_tone(s)[1] for s in ref_syl]
    hyp_tones = [_split_tone(s)[1] for s in hyp_syl]
    ter = _rate(*_levenshtein_ops(ref_tones, hyp_tones))

    # STER: tone errors restricted to positionally-matched, segmentally-correct
    # syllables. Only meaningful when the two sequences are comparable.
    matched = wrong_tone = 0
    for r, h in zip(ref_syl, hyp_syl):
        r_seg, r_tone = _split_tone(r)
        h_seg, h_tone = _split_tone(h)
        if r_seg == h_seg:
            matched += 1
            if r_tone != h_tone:
                wrong_tone += 1
    ster = wrong_tone / matched if matched else 0.0

    return Scores(
        cer=cer,
        ter=ter,
        ster=ster,
        syllable_er=syl_er,
        n_ref_chars=len(ref_chars),
        n_ref_syllables=len(ref_syl),
    )


def score_corpus(pairs: list[tuple[str, str]]) -> Scores:
    """Aggregate over (reference, hypothesis) pairs, weighted by reference length.

    Aggregating this way rather than averaging per-utterance rates avoids
    letting short utterances dominate the headline number.
    """
    tot_cer_num = tot_chars = 0.0
    t_sub = t_del = t_ins = t_len = 0
    s_sub = s_del = s_ins = s_len = 0
    matched = wrong_tone = 0

    for ref, hyp in pairs:
        ref_chars = [c for c in ref if not c.isspace()]
        hyp_chars = [c for c in hyp if not c.isspace()]
        if ref_chars:
            tot_cer_num += jiwer.cer("".join(ref_chars), "".join(hyp_chars)) * len(
                ref_chars
            )
            tot_chars += len(ref_chars)

        ref_syl, hyp_syl = _syllables(ref), _syllables(hyp)
        a, b, c, n = _levenshtein_ops(ref_syl, hyp_syl)
        s_sub, s_del, s_ins, s_len = s_sub + a, s_del + b, s_ins + c, s_len + n

        a, b, c, n = _levenshtein_ops(
            [_split_tone(s)[1] for s in ref_syl],
            [_split_tone(s)[1] for s in hyp_syl],
        )
        t_sub, t_del, t_ins, t_len = t_sub + a, t_del + b, t_ins + c, t_len + n

        for r, h in zip(ref_syl, hyp_syl):
            r_seg, r_tone = _split_tone(r)
            h_seg, h_tone = _split_tone(h)
            if r_seg == h_seg:
                matched += 1
                if r_tone != h_tone:
                    wrong_tone += 1

    return Scores(
        cer=tot_cer_num / tot_chars if tot_chars else 0.0,
        ter=_rate(t_sub, t_del, t_ins, t_len),
        ster=wrong_tone / matched if matched else 0.0,
        syllable_er=_rate(s_sub, s_del, s_ins, s_len),
        n_ref_chars=int(tot_chars),
        n_ref_syllables=s_len,
    )


if __name__ == "__main__":
    # Demonstrates why TER is non-negotiable: a tone-only error is a wrong WORD.
    # 買 (mai3, "buy") vs 賣 (mai4, "sell") — opposite meanings, CER catches it
    # as one char, but the semantic damage is total.
    cases = [
        ("我要買東西", "我要買東西", "perfect"),
        ("我要買東西", "我要賣東西", "tone-only error: buy -> SELL"),
        ("我要買東西", "我要買東西了", "insertion"),
    ]
    for ref, hyp, label in cases:
        s = score(ref, hyp)
        print(f"{label:32} CER={s.cer:.3f} TER={s.ter:.3f} STER={s.ster:.3f}")
