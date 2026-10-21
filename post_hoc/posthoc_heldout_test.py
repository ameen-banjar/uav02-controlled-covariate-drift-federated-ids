"""
POST-HOC held-out-test evaluation of the FROZEN UAV-02 confirmatory checkpoints.

Added on 2026-10-19, AFTER the confirmatory results were seen. Not part of the
frozen protocol; no gate, no p-value, no new endpoint. The frozen design kept
held_out_test untouched during confirmation; this script is the first and only
read of those 28 sessions for UAV-02.

What it does NOT do: no training, no fine-tuning, no checkpoint or round
selection (every saved checkpoint of every run is evaluated and the estimands
use fixed round sets defined below before computing), no change to any frozen
file. Frozen modules are imported read-only from ../code after their SHA-256
digests are checked against ../SHA256SUMS; the only runtime change is pointing
the data loader at the dataset copy in development-workspace (data.DATA_DIR),
because the repository copy does not ship the dataset.

Estimands (held-out-test analogues of the frozen ones, computed on the subset
of rounds that have saved checkpoints; the validation analogue on the SAME
rounds is reported next to each for an apples-to-apples comparison):
  PH-L1  transformed-minus-clean metric at the same checkpoint, averaged over
         saved full-strength rounds (sudden 15,20,25,29; gradual 20,25;
         recurring 15,20,21,30,35,36).
  PH-L3  clean schedule model minus clean matched `none` model at the last
         round of each post-removal interval that has a matched none checkpoint (45 only;
         the recurring r29 residual cannot be formed because none-r29 was not saved).
  PH-H1  none-schedule models: test Regular-minus-MITM logit-margin drop under
         full-strength transformation, S = drop(r30) - drop(r15).
  PH-H2  transformed-minus-clean rate of true-class -> MITM predictions, pooled
         (equal round weight) over the saved full-strength rounds of the three
         schedules; H2a/H2b conditions counted per seed, descriptively.
Test-set transform: same drift.apply_drift; its Entropy floor is the 5th
percentile of the pooled TEST covariates, mirroring how the frozen runner built
the validation transform. Macro-F1 averages a fixed label list = the classes
present in the test labels (stated in the output).

Usage (from the development-workspace python env):
  python post_hoc/posthoc_heldout_test.py
Outputs: post_hoc/heldout_test/ (per-checkpoint CSV, summary.txt, run_info.json)
"""
import csv
import hashlib
import json
import math
import sys
import time
from pathlib import Path

import numpy as np
import torch
from scipy import stats

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
CODE = REPO / "code"
RES = REPO / "results_confirmatory"
CKPT = RES / "checkpoints"
OUT = HERE / "heldout_test"
DATASET = REPO.parent.parent / "development-workspace" / "isot_drone_dataset"
SEEDS = [21, 32, 43, 54, 65]
ALGOS = ["fedavg", "fedprox"]
FULL_ROUNDS = {"sudden": [15, 20, 25, 29], "gradual": [20, 25], "recurring": [15, 20, 21, 30, 35, 36]}
RESIDUAL_ROUNDS = {"sudden": [45], "gradual": [45], "recurring": [45]}   # recurring r29 needs a none-r29 checkpoint, which the runner did not save


def sha256(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def verify_frozen_code():
    bad = []
    for line in (REPO / "SHA256SUMS").read_text().splitlines():
        if line.strip():
            digest, rel = line.split(None, 1)
            if sha256(CODE / rel.strip()) != digest:
                bad.append(rel.strip())
    if bad:
        sys.exit(f"REFUSING: frozen code differs from SHA256SUMS: {bad}")


verify_frozen_code()
sys.path.insert(0, str(CODE / "fl_pipeline"))
sys.path.insert(0, str(CODE / "data_audit"))
import data as data_mod  # noqa: E402
import drift as drift_mod  # noqa: E402
from model import AttackFamilyMLP  # noqa: E402
from algorithms import evaluate  # noqa: E402

data_mod.DATA_DIR = DATASET          # runtime pointer only; no file is edited
CATS = data_mod.ALL_CATEGORIES
REG, MITM = CATS.index("Regular"), CATS.index("MITM")
DEVICE = torch.device("cpu")         # deterministic, no accelerator dependence
LINES = []


def out(s=""):
    LINES.append(s)
    print(s, flush=True)


def summ(v, fmt="+.4f"):
    v = np.asarray(v, float)
    n, m, sd = len(v), v.mean(), v.std(ddof=1)
    h = stats.t.ppf(0.975, n - 1) * sd / math.sqrt(n) if sd > 0 else 0.0
    dz = m / sd if sd > 0 else float("nan")
    return (f"mean={m:{fmt}} sd={sd:.4f} range=[{v.min():{fmt}},{v.max():{fmt}}] "
            f"95%t=[{m - h:{fmt}},{m + h:{fmt}}] d_z={dz:+.2f} neg={int((v < 0).sum())}/{n}")


def main():
    t0 = time.time()
    OUT.mkdir(exist_ok=True)
    d = data_mod.ISOTFederatedData()
    d.fit_preprocessing()                                   # training pool only, as frozen
    test_df = d._load_sessions(d.manifest["held_out_test_sessions"])
    Xt, yt = d.tensors_from_df(test_df)
    floor = drift_mod.compute_entropy_floor(test_df)
    test_labels = sorted(set(yt.numpy().tolist()))
    support = {CATS[i]: int((yt == i).sum()) for i in range(len(CATS))}
    cw = d.class_weights_full_balanced
    Xt1, yt1 = d.tensors_from_df(drift_mod.apply_drift(test_df, 1.0, floor))
    reg_mask = (yt == REG)

    def ev(model, X, y):
        return evaluate(model, X, y, DEVICE, CATS, class_weights=cw, eval_label_indices=test_labels,
                        return_confusion_matrix=True)

    def margin(model, X):
        model.eval()
        with torch.no_grad():
            lg = model(X[reg_mask])
        return float((lg[:, REG] - lg[:, MITM]).mean())

    rows, cache = [], {}
    files = sorted(CKPT.glob("*.pt"))
    for i, f in enumerate(files):
        algo, sched, seed_s, rnd_s = f.stem.split("_")
        seed, rnd = int(seed_s[4:]), int(rnd_s[5:])
        model = AttackFamilyMLP(len(d.feature_cols))
        model.load_state_dict(torch.load(f, map_location="cpu"))
        strength = drift_mod.SCHEDULES[sched](rnd)
        mc = ev(model, Xt, yt)
        if strength > 0:
            Xd, yd = d.tensors_from_df(drift_mod.apply_drift(test_df, strength, floor))
            md = ev(model, Xd, yd)
        else:
            md = mc
        rec = {"algorithm": algo, "schedule": sched, "seed": seed, "round": rnd, "strength": strength,
               "clean_macro_f1": mc["macro_f1"], "drifted_macro_f1": md["macro_f1"],
               "clean_regular_recall": mc["per_class_recall"]["Regular"],
               "drifted_regular_recall": md["per_class_recall"]["Regular"],
               "clean_cm": mc["confusion_matrix"], "drifted_cm": md["confusion_matrix"]}
        if sched == "none" and rnd in (15, 30):
            rec["margin_clean"], rec["margin_s1"] = margin(model, Xt), margin(model, Xt1)
        cache[(algo, sched, seed, rnd)] = rec
        rows.append(rec)
        if (i + 1) % 40 == 0:
            print(f"  evaluated {i + 1}/{len(files)} checkpoints ({time.time() - t0:.0f}s)", flush=True)

    with open(OUT / "per_checkpoint_test.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["algorithm", "schedule", "seed", "round", "strength", "clean_macro_f1", "drifted_macro_f1",
                    "delta_macro_f1", "clean_regular_recall", "drifted_regular_recall", "delta_regular_recall",
                    "clean_confusion_matrix_json", "drifted_confusion_matrix_json"])
        for r in rows:
            w.writerow([r["algorithm"], r["schedule"], r["seed"], r["round"], r["strength"],
                        r["clean_macro_f1"], r["drifted_macro_f1"], r["drifted_macro_f1"] - r["clean_macro_f1"],
                        r["clean_regular_recall"], r["drifted_regular_recall"],
                        r["drifted_regular_recall"] - r["clean_regular_recall"],
                        json.dumps(r["clean_cm"]), json.dumps(r["drifted_cm"])])

    # validation values for the same rounds, from the frozen round logs
    val = {}
    for f in sorted(RES.glob("seed*_rounds.csv")):
        for r in csv.DictReader(open(f)):
            val[(r["algorithm"], r["schedule"], int(r["seed"]), int(r["round"]))] = r

    out("POST-HOC (2026-10-19, after confirmatory results were seen). Held-out test = 28 reserved sessions, "
        "read for the first time here. No training, no selection, no frozen file changed. No gate, no p-value.")
    out(f"Test rows: {len(yt)}; Entropy floor (pooled test 5th pct): {floor:.4f}")
    out("Test support: " + ", ".join(f"{k}={v}" for k, v in support.items()))
    out("Macro-F1 label set (classes present in test): " + ", ".join(CATS[i] for i in test_labels))
    out(f"Checkpoints evaluated: {len(rows)} (all saved checkpoints of the 40 runs)\n")

    out("PH-L1  transformed-minus-clean, mean over saved full-strength rounds  [test | validation on the same rounds]")
    for algo in ALGOS:
        for sched, rr in FULL_ROUNDS.items():
            for metric, key in (("macro-F1", "macro_f1"), ("Regular recall", "regular_recall")):
                te = [np.mean([cache[(algo, sched, s, r)]["drifted_" + key] - cache[(algo, sched, s, r)]["clean_" + key]
                               for r in rr]) for s in SEEDS]
                vk = "delta_macro_f1" if key == "macro_f1" else "delta_regular_recall"
                va = [np.mean([float(val[(algo, sched, s, r)][vk]) for r in rr]) for s in SEEDS]
                out(f"  {algo:7s} {sched:9s} {metric:15s} TEST {summ(te)}")
                out(f"  {'':7s} {'':9s} {'':15s} VAL  {summ(va)}")
    out("")

    out("PH-L3  clean schedule model minus clean none model (macro-F1) at end of each post-removal interval")
    for algo in ALGOS:
        for sched, rr in RESIDUAL_ROUNDS.items():
            for r in rr:
                te = [cache[(algo, sched, s, r)]["clean_macro_f1"] - cache[(algo, "none", s, r)]["clean_macro_f1"]
                      for s in SEEDS]
                va = [float(val[(algo, sched, s, r)]["clean_macro_f1"]) - float(val[(algo, "none", s, r)]["clean_macro_f1"])
                      for s in SEEDS]
                out(f"  {algo:7s} {sched:9s} r{r:<3d} TEST {summ(te)}")
                out(f"  {'':7s} {'':9s} {'':4s} VAL  {summ(va)}")
    out("")

    out("PH-H1  none models: test margin drop (Regular-minus-MITM) under full-strength transform; S = drop30 - drop15")
    for algo in ALGOS:
        drops = {r: [cache[(algo, "none", s, r)]["margin_s1"] - cache[(algo, "none", s, r)]["margin_clean"]
                     for s in SEEDS] for r in (15, 30)}
        S = [b - a for a, b in zip(drops[15], drops[30])]
        out(f"  {algo:7s} drop15 {summ(drops[15])}")
        out(f"  {'':7s} drop30 {summ(drops[30])}")
        out(f"  {'':7s} S      {summ(S)}")
    out("")

    out("PH-H2  transformed-minus-clean rate of true class -> MITM, pooled over saved full-strength rounds (test)")
    for algo in ALGOS:
        per_seed = []
        for s in SEEDS:
            deltas = {}
            for c in range(len(CATS)):
                if c == MITM or support[CATS[c]] == 0:
                    continue
                vals = []
                for sched, rr in FULL_ROUNDS.items():
                    for r in rr:
                        rec = cache[(algo, sched, s, r)]
                        n = sum(rec["clean_cm"][c])
                        vals.append(rec["drifted_cm"][c][MITM] / n - rec["clean_cm"][c][MITM] / n)
                deltas[CATS[c]] = float(np.mean(vals))
            per_seed.append(deltas)
        for cname in ("DoS", "Regular", "Video"):
            if cname in per_seed[0]:
                out(f"  {algo:7s} {cname:8s}->MITM {summ([p[cname] for p in per_seed])}")
        h2a = sum(p.get("DoS", 0) < 0.01 and max(p.values()) > 0.10 for p in per_seed)
        h2b = sum(p.get("Regular", 0) >= 0.05 and p.get("Video", 0) >= 0.05 for p in per_seed)
        out(f"  {algo:7s} H2a conditions met in {h2a}/5 seeds; H2b conditions met in {h2b}/5 seeds (descriptive)")
    out(f"\nElapsed {time.time() - t0:.0f}s")

    (OUT / "summary.txt").write_text("\n".join(LINES) + "\n")
    (OUT / "run_info.json").write_text(json.dumps({
        "date": "2026-10-19", "label": "POST-HOC, after confirmatory results were seen",
        "script_sha256": sha256(Path(__file__)), "torch": torch.__version__, "device": str(DEVICE),
        "n_checkpoints": len(rows), "test_rows": int(len(yt)), "test_support": support,
        "entropy_floor_test": floor, "frozen_code_verified": True}, indent=2))


if __name__ == "__main__":
    main()
