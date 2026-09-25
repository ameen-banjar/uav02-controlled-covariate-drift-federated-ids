"""
POST-HOC EXPLORATORY sensitivity analysis for H1 (added AFTER the confirmatory
results were seen; not part of the frozen protocol; no gate, no p-value).

Question: is the growth of the absolute margin collapse between round 15 and
round 30 (frozen H1 statistic) just a by-product of logit scale growing with
training?  Relative collapse:
    S_rel_r = (M_drift_r - M_clean_r) / |M_clean_r|
using the SAME `none`-model margins already logged by the runner
(margin_clean, margin_strength1). Denominators are reported, never patched
with an epsilon; a small |M_clean| simply marks the ratio as unstable.
Reading rule (stated by the author before computing): S_rel(r30) more negative
than S_rel(r15) in >=4/5 seeds -> H1 survives normalization; disappears ->
"absolute susceptibility increases, largely tracking logit-scale growth";
reversed -> reported as such.
"""
import csv
import math
from pathlib import Path

import numpy as np
from scipy import stats

HERE = Path(__file__).resolve().parent
RD = HERE.parent / "results_drift_confirmatory"
SEEDS = [21, 32, 43, 54, 65]
LINES = []


def out(s=""):
    LINES.append(s)
    print(s)


def summ(v):
    v = np.asarray(v, float)
    n, m, sd = len(v), v.mean(), v.std(ddof=1)
    h = stats.t.ppf(0.975, n - 1) * sd / math.sqrt(n)
    return (f"mean={m:+.3f} sd={sd:.3f} range=[{v.min():+.3f},{v.max():+.3f}] "
            f"95%tInt=[{m - h:+.3f},{m + h:+.3f}] d_z={m / sd:+.2f}")


out("POST-HOC / EXPLORATORY (after confirmatory results were seen). Not a frozen endpoint; no gate, no p-value.\n")
for algo in ("fedavg", "fedprox"):
    d = {}
    for s in SEEDS:
        for r in csv.DictReader(open(RD / f"seed{s}_{algo}_none_h1_margins.csv")):
            d[(s, int(r["round"]))] = (float(r["margin_clean"]), float(r["margin_strength1"]))
    rounds = sorted({r for _, r in d})
    out(f"[{algo}]")
    out("  round: mean clean margin | min |clean margin| over seeds | mean absolute drop | mean relative drop (drop/|clean|)")
    for r in rounds:
        mc = [d[(s, r)][0] for s in SEEDS]
        ab = [d[(s, r)][1] - d[(s, r)][0] for s in SEEDS]
        rel = [(d[(s, r)][1] - d[(s, r)][0]) / abs(d[(s, r)][0]) for s in SEEDS]
        out(f"   r{r:<3d} {np.mean(mc):+7.3f} | {min(abs(x) for x in mc):6.3f} | {np.mean(ab):+7.3f} | {np.mean(rel):+7.3f}")
    rel15 = [(d[(s, 15)][1] - d[(s, 15)][0]) / abs(d[(s, 15)][0]) for s in SEEDS]
    rel30 = [(d[(s, 30)][1] - d[(s, 30)][0]) / abs(d[(s, 30)][0]) for s in SEEDS]
    S = [b - a for a, b in zip(rel15, rel30)]
    out(f"  clean margin r15: {' '.join(f'{d[(s, 15)][0]:+.2f}' for s in SEEDS)}   r30: {' '.join(f'{d[(s, 30)][0]:+.2f}' for s in SEEDS)}")
    out(f"  relative drop r15: {summ(rel15)}")
    out(f"  relative drop r30: {summ(rel30)}")
    out(f"  S_rel = rel(r30) - rel(r15): {summ(S)}  negative in {sum(x < 0 for x in S)}/5 seeds")
    out("  per-seed S_rel: " + ", ".join(f"{s}:{x:+.3f}" for s, x in zip(SEEDS, S)))
    out("")
(RD / "analysis" / "posthoc_h1_relative.txt").write_text("\n".join(LINES))
