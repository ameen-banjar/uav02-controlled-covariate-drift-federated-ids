"""
POST-HOC (2026-10-21): per-seed held-out-test H1 margins.

posthoc_heldout_test.py computed these margins in memory on 2026-10-19 but only
wrote aggregate summaries. This script re-reads ONLY the 20 frozen `none`
checkpoints needed for H1 (2 algorithms x 5 seeds x rounds 15 and 30), on the
same 28 reserved test sessions, and writes every per-seed value. No training,
no selection, no frozen file changed; frozen code hashes are verified first.

Output: post_hoc/heldout_test/h1_margins_test_per_seed.csv and an appended
block in post_hoc/heldout_test/summary_h1_margins.txt.
"""
import csv
import hashlib
import sys
from pathlib import Path

import numpy as np
import torch

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
CODE = REPO / "code"
CKPT = REPO / "results_confirmatory" / "checkpoints"
OUT = HERE / "heldout_test"
DATASET = REPO.parent.parent / "development-workspace" / "isot_drone_dataset"
SEEDS = [21, 32, 43, 54, 65]


def sha256(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


for line in (REPO / "SHA256SUMS").read_text().splitlines():
    if line.strip():
        digest, rel = line.split(None, 1)
        if sha256(CODE / rel.strip()) != digest:
            sys.exit(f"REFUSING: frozen code differs from SHA256SUMS: {rel.strip()}")

sys.dont_write_bytecode = True
sys.path.insert(0, str(CODE / "fl_pipeline"))
sys.path.insert(0, str(CODE / "data_audit"))
import data as data_mod  # noqa: E402
import drift as drift_mod  # noqa: E402
from model import AttackFamilyMLP  # noqa: E402

data_mod.DATA_DIR = DATASET
CATS = data_mod.ALL_CATEGORIES
REG, MITM = CATS.index("Regular"), CATS.index("MITM")


def main():
    d = data_mod.ISOTFederatedData()
    d.fit_preprocessing()
    test_df = d._load_sessions(d.manifest["held_out_test_sessions"])
    Xt, yt = d.tensors_from_df(test_df)
    floor = drift_mod.compute_entropy_floor(test_df)
    Xt1, yt1 = d.tensors_from_df(drift_mod.apply_drift(test_df, 1.0, floor))
    mask = yt == REG

    def margin(model, X):
        model.eval()
        with torch.no_grad():
            lg = model(X[mask])
        return float((lg[:, REG] - lg[:, MITM]).mean())

    rows = []
    for algo in ("fedavg", "fedprox"):
        for s in SEEDS:
            rec = {"algorithm": algo, "seed": s}
            for r in (15, 30):
                m = AttackFamilyMLP(len(d.feature_cols))
                m.load_state_dict(torch.load(CKPT / f"{algo}_none_seed{s}_round{r}.pt", map_location="cpu"))
                rec[f"margin_clean_r{r}"] = margin(m, Xt)
                rec[f"margin_s1_r{r}"] = margin(m, Xt1)
                rec[f"drop_r{r}"] = rec[f"margin_s1_r{r}"] - rec[f"margin_clean_r{r}"]
            rec["S"] = rec["drop_r30"] - rec["drop_r15"]
            rows.append(rec)

    cols = ["algorithm", "seed", "margin_clean_r15", "margin_s1_r15", "drop_r15",
            "margin_clean_r30", "margin_s1_r30", "drop_r30", "S"]
    with open(OUT / "h1_margins_test_per_seed.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)

    lines = ["POST-HOC (2026-10-21) per-seed held-out-test H1 margins; 20 frozen none checkpoints; no training.",
             f"Test Regular rows: {int(mask.sum())}; entropy floor {floor:.4f}"]
    for algo in ("fedavg", "fedprox"):
        S = np.array([r["S"] for r in rows if r["algorithm"] == algo])
        lines.append(f"{algo}: S per seed " + ", ".join(f"{r['seed']}:{r['S']:+.4f}" for r in rows if r["algorithm"] == algo)
                     + f" | mean {S.mean():+.4f} sd {S.std(ddof=1):.4f} negative {int((S < 0).sum())}/5")
    (OUT / "summary_h1_margins.txt").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
