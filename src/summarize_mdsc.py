"""Summarise runs/mdsc_eval.jsonl: the pre-registered analysis in eval_mdsc.py.

Prints a markdown table (for docs/results.md) and writes a small JSON summary
the demo video reads.

Two p-values per group:
  clip p     paired Wilcoxon on per-clip CER (the pre-registered test). It treats
             every clip as independent, but clips come in groups of 20 from one
             speaker, so it overstates the evidence.
  patient p  paired Wilcoxon on per-speaker mean CER: one data point per person.
             This is the honest unit; report it next to the clip p.

--rescore recomputes CER and STER from the stored transcripts with the current
metrics.py (normalised exactly as the backend did), instead of using the scores
saved at eval time. Use it after a metric fix; CER must come out unchanged,
which the script checks.

usage: python src/summarize_mdsc.py runs/mdsc_eval.jsonl [out.json] [--rescore]
"""
import argparse
import json
from collections import defaultdict

import numpy as np
from scipy.stats import wilcoxon

ap = argparse.ArgumentParser()
ap.add_argument("jsonl")
ap.add_argument("out", nargs="?", default=None)
ap.add_argument("--rescore", action="store_true", help="recompute CER/STER with the current metrics.py")
a = ap.parse_args()

rows = [json.loads(l) for l in open(a.jsonl, encoding="utf-8")]

if a.rescore:
    from metrics import score
    from train_asr import normalize  # same normalisation the backend applied at eval time

    for r in rows:
        for model in ("ours", "stock"):
            s = score(normalize(r["ref"]), normalize(r[model] or ""))
            if abs(s.cer - r[f"{model}_cer"]) > 5e-5:  # stored scores are rounded to 4 decimals
                raise SystemExit(f"CER changed on {r['uid']} ({model}): normalisation differs from eval time")
            r[f"{model}_ster"] = s.ster
    print("rescored STER with the current metrics.py (CER unchanged on every clip)\n")


def _p(x, y, min_n):
    return float(wilcoxon(x, y).pvalue) if len(x) >= min_n and np.any(x != y) else None


def summary(rs):
    s = np.array([r["stock_cer"] for r in rs]); o = np.array([r["ours_cer"] for r in rs])
    st = np.array([r["stock_ster"] for r in rs]); ot = np.array([r["ours_ster"] for r in rs])
    d = {"n": len(rs), "speakers": len({r["speaker"] for r in rs}),
         "stock_cer": float(s.mean()), "ours_cer": float(o.mean()),
         "stock_ster": float(st.mean()), "ours_ster": float(ot.mean()),
         "rel_cer_cut": float((s.mean() - o.mean()) / s.mean()) if s.mean() else 0.0,
         "ours_better": int((o < s).sum()), "ours_worse": int((o > s).sum()), "ties": int((o == s).sum())}
    per_spk = defaultdict(list)
    for r in rs:
        per_spk[r["speaker"]].append((r["stock_cer"], r["ours_cer"]))
    spk_stock = np.array([np.mean([v[0] for v in vs]) for vs in per_spk.values()])
    spk_ours = np.array([np.mean([v[1] for v in vs]) for vs in per_spk.values()])
    d["speakers_improved"] = int((spk_ours < spk_stock).sum())
    d["speakers_worse"] = int((spk_ours > spk_stock).sum())
    d["wilcoxon_p"] = _p(s, o, 10)
    d["patient_wilcoxon_p"] = _p(spk_stock, spk_ours, 5)
    return d


groups = defaultdict(list)
for r in rows:
    groups["control" if r["group"] == "Control" else "dysarthric (all)"].append(r)
    if r["group"] != "Control":
        groups[r["band"]].append(r)

fmt = lambda p: f"{p:.3g}" if p is not None else "n/a"
res = {k: summary(v) for k, v in groups.items()}
print("| group | clips | speakers | stock CER | OwnVoice CER | relative cut | better / worse / tie | clip p | "
      "speakers better / worse | patient p | stock STER | OwnVoice STER |")
print("|---|---|---|---|---|---|---|---|---|---|---|---|")
for k in ["dysarthric (all)", "mild", "moderate", "severe", "control"]:
    if k in res:
        d = res[k]
        print(f"| {k} | {d['n']} | {d['speakers']} | {d['stock_cer']:.3f} | {d['ours_cer']:.3f} | {d['rel_cer_cut']*100:+.0f}% | "
              f"{d['ours_better']} / {d['ours_worse']} / {d['ties']} | {fmt(d['wilcoxon_p'])} | "
              f"{d['speakers_improved']} / {d['speakers_worse']} | {fmt(d['patient_wilcoxon_p'])} | "
              f"{d['stock_ster']:.3f} | {d['ours_ster']:.3f} |")
if a.out:
    json.dump({"ready": True, "rescored": a.rescore, **res}, open(a.out, "w"), indent=1)
