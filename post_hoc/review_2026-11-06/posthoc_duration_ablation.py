"""
POST-HOC (2026-11-06), added after an external review: feature ablation of the
evaluation-time intervention, with the Duration column held out or isolated.

Background. In the ISOT extractor, the IP-path value of the `Duration` column is
the packet TTL (Connectivity_features_time.duration() returns packet.ttl). The
frozen intervention multiplies it by 1 + 0.60 s. This script measures how much
of H1 and of the primary L1 contrasts depends on that single column.

Evaluation variants at full strength (s = 1), applied to the raw validation (and
held-out test) rows before standardization, with the same pooled Entropy floor:
  full      : the frozen transform (drift.apply_drift), reproduces the paper
  no_dur    : all six other features transformed, Duration left unchanged
  dur_only  : only Duration multiplied by 1.6; nothing else changed
  dur_clip  : the frozen transform, but transformed Duration clipped at 255 (max IP TTL)

Reads only saved checkpoints. No training, no checkpoint selection, no frozen
file changed (frozen code hashes are verified first). Outputs go to this folder.
"""
import csv
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import torch

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
CODE = REPO / "code"
CKPT = REPO / "results_confirmatory" / "checkpoints"
DATASET = REPO.parent.parent / "development-workspace" / "isot_drone_dataset"
SEEDS = [21, 32, 43, 54, 65]
ALGOS = ("fedavg", "fedprox")
FULL_ROUNDS = {"sudden": [15, 20, 25, 29], "gradual": [20, 25], "recurring": [15, 20, 21, 30, 35, 36]}
VARIANTS = ("full", "no_dur", "dur_only", "dur_clip")


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
from algorithms import evaluate  # noqa: E402
from model import AttackFamilyMLP  # noqa: E402

torch.set_num_threads(3)
data_mod.DATA_DIR = DATASET
CATS = data_mod.ALL_CATEGORIES
REG, MITM, VIDEO = CATS.index("Regular"), CATS.index("MITM"), CATS.index("Video")
VAL_LABELS = [i for i, c in enumerate(CATS) if c != "Password Cracking"]
k = drift_mod.MAX_MULTIPLICATIVE_SHIFT


def transform(df, variant, floor):
    if variant == "full":
        return drift_mod.apply_drift(df, 1.0, floor)
    d = df.copy()
    if variant == "dur_only":
        d["Duration"] = d["Duration"] * (1 + k)
        return d
    d = drift_mod.apply_drift(df, 1.0, floor)
    if variant == "no_dur":
        d["Duration"] = df["Duration"]
    elif variant == "dur_clip":
        d["Duration"] = np.minimum(d["Duration"], 255.0)
    return d


def main():
    d = data_mod.ISOTFederatedData()
    d.fit_preprocessing()
    splits = {"validation": d._load_sessions(d.manifest["validation_sessions"]),
              "test": d._load_sessions(d.manifest["held_out_test_sessions"])}
    exposed = __import__("pandas").concat([d.get_client_raw_df(c) for c in drift_mod.DRIFT_CLIENT_IDS])

    info = {}
    for name, df in list(splits.items()) + [("train_exposed_clients", exposed)]:
        dur = df["Duration"].to_numpy(float)
        info[name] = {"rows": int(len(dur)),
                      "share_raw_gt255": float((dur > 255).mean()),
                      "share_transformed_gt255": float((dur * (1 + k) > 255).mean()),
                      "raw_max": float(dur.max()), "raw_median": float(np.median(dur)),
                      "share_zero": float((dur == 0).mean())}

    tens = {}
    for name, df in splits.items():
        floor = drift_mod.compute_entropy_floor(df)
        X, y = d.tensors_from_df(df)
        tens[name] = {"clean": (X, y), "floor": floor}
        for v in VARIANTS:
            tens[name][v] = d.tensors_from_df(transform(df, v, floor))
        Xf, _ = d.tensors_from_df(drift_mod.apply_drift(df, 1.0, floor))
        assert torch.equal(Xf, tens[name]["full"][0]), "full variant must equal the frozen transform"

    def margin(model, X, y):
        with torch.no_grad():
            lg = model(X[y == REG])
        return float((lg[:, REG] - lg[:, MITM]).mean())

    def load(algo, sched, seed, rnd):
        m = AttackFamilyMLP(len(d.feature_cols))
        m.load_state_dict(torch.load(CKPT / f"{algo}_{sched}_seed{seed}_round{rnd}.pt", map_location="cpu"))
        m.eval()
        return m

    # ---- H1 on validation and test
    h1 = []
    for split in splits:
        Xc, yc = tens[split]["clean"]
        for algo in ALGOS:
            for s in SEEDS:
                rec = {"split": split, "algorithm": algo, "seed": s}
                for r in (15, 30):
                    m = load(algo, "none", s, r)
                    mc = margin(m, Xc, yc)
                    for v in VARIANTS:
                        Xv, yv = tens[split][v]
                        rec[f"drop_{v}_r{r}"] = margin(m, Xv, yv) - mc
                for v in VARIANTS:
                    rec[f"S_{v}"] = rec[f"drop_{v}_r30"] - rec[f"drop_{v}_r15"]
                h1.append(rec)

    # ---- L1 and H2 transition rates at saved full-strength rounds (validation)
    l1 = []
    Xc, yc = tens["validation"]["clean"]
    for algo in ALGOS:
        for sched, rounds in FULL_ROUNDS.items():
            for s in SEEDS:
                for r in rounds:
                    m = load(algo, sched, s, r)
                    mc = evaluate(m, Xc, yc, "cpu", CATS, eval_label_indices=VAL_LABELS, return_confusion_matrix=True)
                    cmc = np.array(mc["confusion_matrix"])
                    for v in VARIANTS:
                        Xv, yv = tens["validation"][v]
                        mv = evaluate(m, Xv, yv, "cpu", CATS, eval_label_indices=VAL_LABELS, return_confusion_matrix=True)
                        cmv = np.array(mv["confusion_matrix"])
                        rate = lambda cm, c: cm[c, MITM] / cm[c].sum()
                        l1.append({"algorithm": algo, "schedule": sched, "seed": s, "round": r, "variant": v,
                                   "d_macro_f1": mv["macro_f1"] - mc["macro_f1"],
                                   "d_regular_recall": mv["per_class_recall"]["Regular"] - mc["per_class_recall"]["Regular"],
                                   "d_regular_to_mitm": rate(cmv, REG) - rate(cmc, REG),
                                   "d_video_to_mitm": rate(cmv, VIDEO) - rate(cmc, VIDEO)})

    for fn, rows in (("h1_ablation_per_seed.csv", h1), ("l1_ablation_saved_rounds_validation.csv", l1)):
        with open(HERE / fn, "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)

    out = ["POST-HOC (2026-11-06) Duration ablation; saved checkpoints only; no training.",
           "Duration column statistics: " + json.dumps(info, indent=1)]
    for split in splits:
        for algo in ALGOS:
            rs = [r for r in h1 if r["split"] == split and r["algorithm"] == algo]
            out.append(f"H1 {split} {algo}: " + " | ".join(
                f"{v}: mean S {np.mean([r['S_' + v] for r in rs]):+.4f}, negative {sum(r['S_' + v] < 0 for r in rs)}/5"
                for v in VARIANTS))
    for algo in ALGOS:
        for sched in FULL_ROUNDS:
            for v in VARIANTS:
                seedmeans = {}
                for s in SEEDS:
                    rr = [r for r in l1 if r["algorithm"] == algo and r["schedule"] == sched and r["seed"] == s and r["variant"] == v]
                    seedmeans[s] = {kk: np.mean([r[kk] for r in rr]) for kk in ("d_macro_f1", "d_regular_recall", "d_regular_to_mitm", "d_video_to_mitm")}
                mf = [seedmeans[s]["d_macro_f1"] for s in SEEDS]
                rc = [seedmeans[s]["d_regular_recall"] for s in SEEDS]
                rm = [seedmeans[s]["d_regular_to_mitm"] for s in SEEDS]
                vm = [seedmeans[s]["d_video_to_mitm"] for s in SEEDS]
                out.append(f"L1 val saved-rounds {algo} {sched} {v}: dMF1 {np.mean(mf):+.4f} (neg {sum(x < 0 for x in mf)}/5) "
                           f"dRegRec {np.mean(rc):+.4f} (neg {sum(x < 0 for x in rc)}/5) "
                           f"Reg->MITM {np.mean(rm):+.4f} Video->MITM {np.mean(vm):+.4f}")
    (HERE / "summary_duration_ablation.txt").write_text("\n".join(out) + "\n")
    print("\n".join(out))


if __name__ == "__main__":
    main()
