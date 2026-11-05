"""
UAV-02 v2 (CORRECTED) CONFIRMATORY runner. Protocol frozen in
repositories/paper-02-controlled-concept-drift/v2/DESIGN_V2.md BEFORE any
execution of this script. Identical to the v1 runner except: fresh seeds,
v2 freeze tag/hash file, v2 output folder, and the v2 drift module. Do not edit after the freeze commit except for a
documented execution bug that does not change the design.

Grid: {fedavg, fedprox} x {none, sudden, gradual, recurring} x FROZEN seeds,
45 rounds. Seeds are fixed (SEEDS below); a seed is never replaced or
dropped because of its result. held_out_test is never touched.

Usage:  python run_drift_confirmatory.py --seed 21
Refuses to run unless (a) the seed is in SEEDS, (b) every source file matches
the frozen SHA256SUMS in the paper-02 repo, and (c) that repo is clean and
HEAD carries the freeze tag. `--smoke DIR` is a wiring test only (fake seed,
3 rounds, forced drift, no frozen-state checks, never writes to results dir).
"""
import argparse
import csv
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import torch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from data import ISOTFederatedData, ALL_CATEGORIES  # noqa: E402
from model import AttackFamilyMLP, save_checkpoint  # noqa: E402
from algorithms import local_train, aggregate_weighted, evaluate  # noqa: E402
import drift as drift_mod  # noqa: E402

SEEDS = [76, 87, 98, 109, 120]        # v2 fresh seeds (v1 used 21..65); frozen; never substituted
ALGOS = ["fedavg", "fedprox"]
SCHEDULE_NAMES = ["none", "sudden", "gradual", "recurring"]
NUM_ROUNDS = drift_mod.NUM_ROUNDS
BATCH_SIZE = 4096
LR = 1e-3
FEDPROX_MU = 0.01
H1_ROUNDS = [5, 10, 15, 20, 25, 30, 35, 40, 45]   # {15, 30} = pre-specified H1 contrast; rest descriptive
FREEZE_TAG = "uav02-v2-confirmatory-freeze"
DEVICE = torch.device("mps") if torch.backends.mps.is_available() else torch.device("cpu")
REGULAR_IDX = ALL_CATEGORIES.index("Regular")
MITM_IDX = ALL_CATEGORIES.index("MITM")
PASSWORD_CRACKING_IDX = ALL_CATEGORIES.index("Password Cracking")
VALIDATION_LABEL_INDICES = [i for i in range(len(ALL_CATEGORIES)) if i != PASSWORD_CRACKING_IDX]

DEV_ROOT = HERE.parent
REPO_DIR = DEV_ROOT.parent / "repositories" / "paper-02-controlled-concept-drift"
RESULTS_DIR = HERE / "results_v2_confirmatory"

ROUND_COLUMNS = ["algorithm", "schedule", "seed", "round", "drift_strength",
                 "clean_macro_f1", "drifted_macro_f1", "delta_macro_f1",
                 "clean_regular_recall", "drifted_regular_recall", "delta_regular_recall",
                 "clean_per_class_recall_json", "drifted_per_class_recall_json",
                 "clean_confusion_matrix_json", "drifted_confusion_matrix_json"]
H1_COLUMNS = ["algorithm", "seed", "round", "margin_clean", "margin_strength1", "margin_drop"]


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def git(*args):
    return subprocess.run(["git", "-C", str(REPO_DIR), *args], capture_output=True, text=True, check=True).stdout.strip()


def verify_frozen_state():
    sums = REPO_DIR / "v2" / "SHA256SUMS_v2"
    if not sums.exists():
        sys.exit("REFUSING TO RUN: SHA256SUMS missing from the freeze repo.")
    mismatched = []
    for line in sums.read_text().splitlines():
        if not line.strip():
            continue
        digest, rel = line.split(None, 1)
        rel = rel.strip()
        if sha256(DEV_ROOT / rel) != digest:
            mismatched.append(rel)
    if mismatched:
        sys.exit(f"REFUSING TO RUN: files differ from the frozen commit: {mismatched}")
    if git("status", "--porcelain"):
        sys.exit("REFUSING TO RUN: freeze repo has uncommitted changes.")
    try:
        tags = git("tag", "--points-at", "HEAD").split()
    except subprocess.CalledProcessError:
        tags = []
    if FREEZE_TAG not in tags:
        sys.exit(f"REFUSING TO RUN: HEAD is not tagged {FREEZE_TAG}.")
    return {"git_head": git("rev-parse", "HEAD"), "tag": FREEZE_TAG,
            "file_sha256": {l.split(None, 1)[1].strip(): l.split(None, 1)[0]
                            for l in sums.read_text().splitlines() if l.strip()}}


def set_seed(seed):
    torch.manual_seed(seed)
    np.random.seed(seed)


@torch.no_grad()
def regular_mitm_margin(model, X_regular):
    """Mean logit[Regular] - logit[MITM] over Regular-true validation rows."""
    model.eval()
    logits = model(X_regular)
    return float((logits[:, REGULAR_IDX] - logits[:, MITM_IDX]).mean().cpu())


def transition_rounds(schedule_name):
    if schedule_name == "none":
        return set()
    if schedule_name == "sudden":
        return {drift_mod.DRIFT_START_SUDDEN - 1, drift_mod.DRIFT_START_SUDDEN,
                drift_mod.DRIFT_RECOVER_SUDDEN - 1, drift_mod.DRIFT_RECOVER_SUDDEN}
    if schedule_name == "gradual":
        return {drift_mod.DRIFT_RAMPUP_START_GRADUAL, drift_mod.DRIFT_RAMPUP_END_GRADUAL,
                drift_mod.DRIFT_RAMPDOWN_START_GRADUAL, drift_mod.DRIFT_RAMPDOWN_END_GRADUAL}
    return {b for lo, hi in drift_mod.DRIFT_RECURRING_WINDOWS for b in (lo - 1, lo, hi - 1, hi)}


def atomic_write_csv(path, header, rows):
    tmp = Path(str(path) + ".tmp")
    with open(tmp, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)
    tmp.replace(path)


def run_seed(seed, out_dir, num_rounds, h1_rounds, algos, schedule_names, schedule_fns, provenance):
    out_dir.mkdir(parents=True, exist_ok=True)
    ckpt_dir = out_dir / "checkpoints"
    ckpt_dir.mkdir(exist_ok=True)
    (out_dir / f"provenance_seed{seed}.json").write_text(json.dumps(provenance, indent=2))
    print(f"Device={DEVICE} seed={seed} rounds={num_rounds} drift clients={drift_mod.DRIFT_CLIENT_IDS}", flush=True)

    data = ISOTFederatedData()
    data.fit_preprocessing()
    input_dim = len(data.feature_cols)
    val_df_raw = data._load_sessions(data.manifest["validation_sessions"])
    Xval, yval = data.tensors_from_df(val_df_raw)
    val_entropy_floor = drift_mod.compute_entropy_floor(val_df_raw)
    Xval_d1, yval_d1 = data.tensors_from_df(drift_mod.apply_drift(val_df_raw, 1.0, val_entropy_floor))
    Xval_reg = Xval[yval == REGULAR_IDX].to(DEVICE)
    Xval_d1_reg = Xval_d1[yval_d1 == REGULAR_IDX].to(DEVICE)

    client_ids = data.client_ids()
    raw_df = {cid: data.get_client_raw_df(cid) for cid in drift_mod.DRIFT_CLIENT_IDS}
    entropy_floor = {cid: drift_mod.compute_entropy_floor(raw_df[cid]) for cid in raw_df}
    static_tensors = {cid: data.get_client_data(cid) for cid in client_ids if cid not in drift_mod.DRIFT_CLIENT_IDS}
    weights_all = [data.client_weight_rows(cid) for cid in client_ids]
    s = sum(weights_all)
    weights_all = [w / s for w in weights_all]

    t0 = time.time()
    for algo in algos:
        for sched in schedule_names:
            rounds_path = out_dir / f"seed{seed}_{algo}_{sched}_rounds.csv"
            if rounds_path.exists():
                print(f"[skip] {rounds_path.name} already complete", flush=True)
                continue
            schedule_fn = schedule_fns[sched]
            save_rounds = set([1] + list(range(5, num_rounds + 1, 5)) + [num_rounds]) | transition_rounds(sched)
            set_seed(seed)
            global_model = AttackFamilyMLP(input_dim).to(DEVICE)
            mu = FEDPROX_MU if algo == "fedprox" else 0.0
            rows, h1_rows = [], []

            for rnd in range(1, num_rounds + 1):
                strength = schedule_fn(rnd)
                client_states = []
                for cid in client_ids:
                    if cid in drift_mod.DRIFT_CLIENT_IDS:
                        Xc, yc = data.tensors_from_df(drift_mod.apply_drift(raw_df[cid], strength, entropy_floor[cid]))
                    else:
                        Xc, yc = static_tensors[cid]
                    local_model = AttackFamilyMLP(input_dim).to(DEVICE)
                    local_model.load_state_dict(global_model.state_dict())
                    state, _, _ = local_train(local_model, Xc, yc, DEVICE, epochs=1, batch_size=BATCH_SIZE, lr=LR,
                                              mu=mu, global_state=global_model.state_dict(),
                                              class_weights=data.class_weights_full_balanced)
                    client_states.append(state)
                global_model.load_state_dict(aggregate_weighted(client_states, weights_all))

                m_clean = evaluate(global_model, Xval, yval, DEVICE, ALL_CATEGORIES,
                                   class_weights=data.class_weights_full_balanced,
                                   eval_label_indices=VALIDATION_LABEL_INDICES, return_confusion_matrix=True)
                if strength > 0:
                    Xv_d, yv_d = data.tensors_from_df(drift_mod.apply_drift(val_df_raw, strength, val_entropy_floor))
                else:
                    Xv_d, yv_d = Xval, yval
                m_drift = evaluate(global_model, Xv_d, yv_d, DEVICE, ALL_CATEGORIES,
                                   class_weights=data.class_weights_full_balanced,
                                   eval_label_indices=VALIDATION_LABEL_INDICES, return_confusion_matrix=True)
                rows.append([
                    algo, sched, seed, rnd, strength,
                    m_clean["macro_f1"], m_drift["macro_f1"], m_drift["macro_f1"] - m_clean["macro_f1"],
                    m_clean["per_class_recall"]["Regular"], m_drift["per_class_recall"]["Regular"],
                    m_drift["per_class_recall"]["Regular"] - m_clean["per_class_recall"]["Regular"],
                    json.dumps(m_clean["per_class_recall"]), json.dumps(m_drift["per_class_recall"]),
                    json.dumps(m_clean["confusion_matrix"]), json.dumps(m_drift["confusion_matrix"]),
                ])

                if sched == "none" and rnd in h1_rounds:
                    mc = regular_mitm_margin(global_model, Xval_reg)
                    m1 = regular_mitm_margin(global_model, Xval_d1_reg)
                    h1_rows.append([algo, seed, rnd, mc, m1, m1 - mc])
                if rnd in save_rounds:
                    save_checkpoint(global_model, ckpt_dir / f"{algo}_{sched}_seed{seed}_round{rnd}.pt")
                    print(f"[{algo}/{sched}] seed={seed} round {rnd}/{num_rounds} strength={strength:.2f} "
                          f"clean_mf1={m_clean['macro_f1']:.4f} delta_mf1={m_drift['macro_f1'] - m_clean['macro_f1']:+.4f} "
                          f"elapsed={time.time() - t0:.0f}s", flush=True)

            if h1_rows:
                atomic_write_csv(out_dir / f"seed{seed}_{algo}_none_h1_margins.csv", H1_COLUMNS, h1_rows)
            atomic_write_csv(rounds_path, ROUND_COLUMNS, rows)   # written last: its existence marks the run complete
    print(f"seed {seed} done in {time.time() - t0:.0f}s (held_out_test never touched)", flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int)
    ap.add_argument("--smoke", type=str, help="wiring test only: writes to this dir, fake seed, 3 rounds")
    args = ap.parse_args()

    if args.smoke:
        out_dir = Path(args.smoke)
        fns = dict(drift_mod.SCHEDULES)
        fns["sudden"] = lambda r: 1.0 if r >= 2 else 0.0
        run_seed(999, out_dir, 3, [1, 3], ["fedavg"], ["none", "sudden"], fns, {"smoke": True})
        return

    if args.seed not in SEEDS:
        sys.exit(f"seed must be one of the frozen SEEDS {SEEDS}")
    provenance = verify_frozen_state()
    provenance.update({"seed": args.seed, "torch": torch.__version__, "device": str(DEVICE),
                       "started_unix": time.time()})
    run_seed(args.seed, RESULTS_DIR, NUM_ROUNDS, H1_ROUNDS, ALGOS, SCHEDULE_NAMES, drift_mod.SCHEDULES, provenance)


if __name__ == "__main__":
    main()
