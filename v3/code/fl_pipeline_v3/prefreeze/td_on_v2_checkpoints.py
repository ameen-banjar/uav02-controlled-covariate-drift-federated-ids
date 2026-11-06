"""PRE-FREEZE pilot (2026-11-06), disclosed in DESIGN_V3.md: evaluation-only, the
time-dilation transform applied to the saved v2 checkpoints (seeds 76-120).
Used only to state the v3 predictions; not v3 evidence."""
import sys, json
from pathlib import Path
import numpy as np, torch
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import drift_v3 as dv
from data import ISOTFederatedData, ALL_CATEGORIES
from model import AttackFamilyMLP
from algorithms import evaluate
CK = HERE.parents[2] / "repositories/paper-02-controlled-concept-drift/v2/results_confirmatory/checkpoints"
SEEDS = [76, 87, 98, 109, 120]
FULL = {"sudden": [15, 20, 25, 29], "gradual": [20, 25], "recurring": [15, 20, 21, 30, 35, 36]}
d = ISOTFederatedData(); d.fit_preprocessing()
val = d._load_sessions(d.manifest["validation_sessions"]); fl = dv.compute_entropy_floor(val)
Xc, yc = d.tensors_from_df(val)
T = {t: d.tensors_from_df(dv.apply(val, 1.0, t, fl)) for t in ("td", "v2", "td_time_only", "td_rate_only")}
labs = [i for i, c in enumerate(ALL_CATEGORIES) if c != "Password Cracking"]
R, M = ALL_CATEGORIES.index("Regular"), ALL_CATEGORIES.index("MITM")
def load(a, s, seed, r):
    m = AttackFamilyMLP(len(d.feature_cols)); m.load_state_dict(torch.load(CK / f"{a}_{s}_seed{seed}_round{r}.pt", map_location="cpu")); m.eval(); return m
out = []
for a in ("fedavg", "fedprox"):
    for s, rr in FULL.items():
        res = {t: [] for t in T}
        for seed in SEEDS:
            v = {t: [] for t in T}
            for r in rr:
                m = load(a, s, seed, r); mc = evaluate(m, Xc, yc, "cpu", ALL_CATEGORIES, eval_label_indices=labs)["macro_f1"]
                for t, (X, y) in T.items():
                    v[t].append(evaluate(m, X, y, "cpu", ALL_CATEGORIES, eval_label_indices=labs)["macro_f1"] - mc)
            for t in T: res[t].append(np.mean(v[t]))
        out.append(f"L1 {a} {s}: " + " | ".join(f"{t} {np.mean(x):+.4f} (neg {sum(np.array(x)<0)}/5)" for t, x in res.items()))
    S = {t: [] for t in ("td", "v2")}
    for seed in SEEDS:
        for t in S:
            dr = []
            for r in (15, 30):
                m = load(a, "none", seed, r); sel = yc == R
                with torch.no_grad():
                    lc, lt = m(Xc[sel]), m(T[t][0][sel])
                dr.append(float((lt[:, R] - lt[:, M]).mean() - (lc[:, R] - lc[:, M]).mean()))
            S[t].append(dr[1] - dr[0])
    out.append(f"H1 {a}: " + " | ".join(f"{t} S {np.mean(x):+.4f} (neg {sum(np.array(x)<0)}/5)" for t, x in S.items()))
(HERE / "td_on_v2_checkpoints.txt").write_text("\n".join(out) + "\n"); print("\n".join(out))
