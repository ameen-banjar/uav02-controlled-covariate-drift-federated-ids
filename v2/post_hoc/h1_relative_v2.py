"""
POST-HOC (2026-11-06), not part of the frozen v2 protocol: H1 margin drop divided by the
absolute clean margin, per seed, at rounds 15 and 30 of the v2 `none` checkpoints.
Reads only v2/results_confirmatory/seed*_none_h1_margins.csv. Writes h1_relative_v2.txt.
"""
import csv
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
RD = HERE.parent / "results_confirmatory"
SEEDS = [76, 87, 98, 109, 120]
out = ["POST-HOC (2026-11-06) normalized H1 for v2: rel_drop = margin_drop / |margin_clean|; S_rel = rel_drop(r30) - rel_drop(r15)"]
for a in ("fedavg", "fedprox"):
    rows = {}
    for s in SEEDS:
        for r in csv.DictReader(open(RD / f"seed{s}_{a}_none_h1_margins.csv")):
            rows[(s, int(r["round"]))] = (float(r["margin_clean"]), float(r["margin_drop"]))
    for rnd in (15, 30, 45):
        mc = np.mean([rows[(s, rnd)][0] for s in SEEDS])
        rel = np.mean([rows[(s, rnd)][1] / abs(rows[(s, rnd)][0]) for s in SEEDS])
        out.append(f"[{a}] round {rnd}: mean clean margin {mc:.3f}, mean relative drop {rel:+.4f}")
    S = [rows[(s, 30)][1] / abs(rows[(s, 30)][0]) - rows[(s, 15)][1] / abs(rows[(s, 15)][0]) for s in SEEDS]
    out.append(f"[{a}] S_rel per seed: " + ", ".join(f"{s}:{v:+.4f}" for s, v in zip(SEEDS, S))
               + f" | mean {np.mean(S):+.4f} | negative {sum(v < 0 for v in S)}/5")
(HERE / "h1_relative_v2.txt").write_text("\n".join(out) + "\n")
print("\n".join(out))
