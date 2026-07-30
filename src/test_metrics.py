"""
Regression tests for the metrics, especially STER alignment.

STER previously compared syllables by position, so a single insertion made
every later tone error invisible. These cases lock in the fixed behaviour.
Run: python test_metrics.py
"""

from metrics import score

# (name, reference, hypothesis, expected STER or None to just report)
CASES = [
    ("perfect", "我要買東西", "我要買東西", 0.0),
    # 買 mai3 -> 賣 mai4 : same segment, wrong tone, 1 of 5 syllables
    ("tone-only, same length", "我要買東西", "我要賣東西", 0.2),
    # THE REGRESSION: same tone error, but preceded by an inserted syllable.
    # Positional zip scored this 0.000 and hid the error entirely.
    ("tone error AFTER insertion", "我要買東西", "我就要賣東西", 0.2),
    # Leading deletion shifts everything the other way.
    ("tone error AFTER deletion", "我要買東西", "要賣東西", 0.25),
    ("two insertions then tone error", "我要買東西", "我啊就要賣東西", 0.2),
    ("all tones wrong", "買賣", "賣買", 1.0),
    ("no overlap at all", "我要買東西", "完全不同", None),
    ("real baseline output", "與地主做良性的溝通", "與地主做人心的構同", None),
]


def main() -> int:
    print(f"{'case':34} {'CER':>7} {'TER':>7} {'STER':>7}  expected")
    print("-" * 70)
    failures = 0
    for name, ref, hyp, expected in CASES:
        s = score(ref, hyp)
        exp = "-" if expected is None else f"{expected:.3f}"
        bad = expected is not None and abs(s.ster - expected) > 1e-9
        failures += bad
        flag = "  <-- FAIL" if bad else ""
        print(
            f"{name:34} {s.cer:>7.3f} {s.ter:>7.3f} {s.ster:>7.3f}  {exp}{flag}"
        )

    print()
    if failures:
        print(f"{failures} FAILED")
    else:
        print("all STER expectations met")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
