"""
UAV-02 v3 expanded campaign runner. Protocol: repositories/paper-02-controlled-
concept-drift/v3/DESIGN_V3.md, frozen before any v3 execution (tag
uav02-v3-freeze). One process runs one JOB = (arm, seed, algorithm, schedule).

    python3.11 run_v3.py --list-jobs            # prints every frozen job spec
    python3.11 run_v3.py --job "main_td|131|fedavg|sudden"
    python3.11 run_v3.py --smoke DIR --job SPEC # wiring test: 3 rounds, no guard

Refuses to run (except --smoke) unless every file in v3/SHA256SUMS_v3 matches,
the repo is clean, and HEAD carries the freeze tag. A job is complete when its
rounds CSV exists (written last); completed jobs are skipped, so an interrupted
campaign resumes. held_out_test is never touched. No seed is replaced.
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
import drift_v3 as dv  # noqa: E402
from algorithms import local_train, aggregate_weighted, evaluate  # noqa: E402
from advanced_algorithms import (zeros_like_state, local_train_scaffold, aggregate_scaffold,  # noqa: E402
                                 local_train_fednova, aggregate_fednova, local_train_generic, aggregate_fedadam)
from model import AttackFamilyMLP, save_checkpoint  # noqa: E402

FREEZE_TAG = "uav02-v3-freeze"
DEV_ROOT = HERE.parent
REPO_DIR = DEV_ROOT.parent / "repositories" / "paper-02-controlled-concept-drift"
RESULTS = HERE / "results_v3"
DEVICE = torch.device("mps") if torch.backends.mps.is_available() else torch.device("cpu")

SEEDS10 = [131, 142, 153, 164, 175, 186, 197, 208, 219, 230]
SEEDS5 = SEEDS10[:5]
NUM_ROUNDS = dv.NUM_ROUNDS
BATCH, LR, MU = 4096, 1e-3, 0.01
H1_ROUNDS = [5, 10, 15, 20, 25, 30, 35, 40, 45]
PROBE_STRENGTHS = [0.25, 0.5, 0.75, 1.0]
ALGO_CFG = {  # SCAFFOLD/FedNova/FedAdam settings: UAV-01 item-2 screened configuration on the same data
    "scaffold": {"lr": 0.1}, "fednova": {"lr": 0.3},
    "fedadam": {"client_lr": 0.001, "server_lr": 0.03, "beta1": 0.9, "beta2": 0.99, "tau": 1e-3}}

FROZEN_MANIFEST = DEV_ROOT / "data_audit" / "federated_clients_manifest.json"
MANIFESTS = HERE / "manifests"


def arm(dataset="isot", manifest=None, train="td", evals=("td",), k=5, hidden=(128, 64),
        participation=None, seeds=SEEDS5, algos=("fedavg", "fedprox"), scheds=("none", "sudden"),
        eval_sets=("validation",)):
    return dict(dataset=dataset, manifest=str(manifest or FROZEN_MANIFEST), train=train, evals=list(evals), k=k,
                hidden=list(hidden), participation=participation, seeds=seeds, algos=list(algos),
                scheds=list(scheds), eval_sets=list(eval_sets))


ARMS = {
    # primary block: frozen manifest, 10 fresh seeds, both interventions; the none runs are shared
    "main_none": arm(train=None, evals=("v2", "td"), seeds=SEEDS10, scheds=("none",)),
    "main_v2": arm(train="v2", evals=("v2", "td"), seeds=SEEDS10, scheds=("sudden", "gradual", "recurring")),
    "main_td": arm(train="td", evals=("td", "v2"), seeds=SEEDS10, scheds=("sudden", "gradual", "recurring")),
    # exposure share (alternative explanation for small residuals); none baseline = main_none
    "exp_k8": arm(k=8, scheds=("sudden",)), "exp_k11": arm(k=11, scheds=("sudden",)),
    "exp_k15": arm(k=15, scheds=("sudden",)),
    # heterogeneity of the client partition
    "alpha_0.1": arm(manifest=MANIFESTS / "alpha_0.1.json"), "alpha_2": arm(manifest=MANIFESTS / "alpha_2.json"),
    "alpha_100": arm(manifest=MANIFESTS / "alpha_100.json"),
    # architecture
    "arch_wide": arm(hidden=(256, 128, 64)),
    # further FL algorithms
    "algo_scaffold": arm(algos=("scaffold",)), "algo_fednova": arm(algos=("fednova",)),
    "algo_fedadam": arm(algos=("fedadam",)),
    # partial participation: 10 of 15 clients per round
    "partial10": arm(participation=10),
    # fresh evaluation sessions never used for evaluation before
    "fresh": arm(manifest=MANIFESTS / "fresh.json", scheds=("none", "sudden", "gradual", "recurring"),
                 eval_sets=("validation", "fresh")),
    # second dataset
    "cic": arm(dataset="cic"),
}


def jobs():
    out = []
    for name, a in ARMS.items():
        for seed in a["seeds"]:
            for algo in a["algos"]:
                for sched in a["scheds"]:
                    out.append(f"{name}|{seed}|{algo}|{sched}")
    return out


# ----------------------------------------------------------------------------- guard
def sha256(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def git(*args):
    return subprocess.run(["git", "-C", str(REPO_DIR), *args], capture_output=True, text=True, check=True).stdout.strip()


def verify_frozen_state():
    sums = REPO_DIR / "v3" / "SHA256SUMS_v3"
    if not sums.exists():
        sys.exit("REFUSING: v3/SHA256SUMS_v3 missing")
    bad = [rel for d, rel in (l.split(None, 1) for l in sums.read_text().splitlines() if l.strip())
           if sha256(DEV_ROOT / rel.strip()) != d]
    if bad:
        sys.exit(f"REFUSING: files differ from the freeze: {bad}")
    if git("status", "--porcelain"):
        sys.exit("REFUSING: repo has uncommitted changes")
    if FREEZE_TAG not in git("tag", "--points-at", "HEAD").split():
        sys.exit(f"REFUSING: HEAD is not tagged {FREEZE_TAG}")
    return {"git_head": git("rev-parse", "HEAD"), "tag": FREEZE_TAG}


# ----------------------------------------------------------------------------- data
class Data:
    def __init__(self, a):
        self.dataset = a["dataset"]
        if self.dataset == "cic":
            from cic_v3 import CICData
            self.d = CICData()
            self.d.fit_preprocessing()
            self.classes = self.d.categories
            self.eval_raw = {"validation": self.d.validation_raw()}
            order = self.d.clients_meta["exposure_order"]
            self.reg_name = "Benign_Final"
        else:
            from data import ISOTFederatedData, ALL_CATEGORIES
            self.d = ISOTFederatedData(manifest_path=a["manifest"])
            self.d.fit_preprocessing()
            self.classes = ALL_CATEGORIES
            m = self.d.manifest
            self.eval_raw = {"validation": self.d._load_sessions(m["validation_sessions"])}
            if "fresh" in a["eval_sets"]:
                self.eval_raw["fresh"] = self.d._load_sessions(m["fresh_eval_sessions"])
            order = m.get("exposure_order") or json.loads((MANIFESTS / "frozen_exposure_order.json").read_text())
            self.reg_name = "Regular"
        self.exposed = [int(c) for c in order[: a["k"]]]
        self.reg_idx = self.classes.index(self.reg_name)
        self.mitm_idx = self.classes.index("MITM") if "MITM" in self.classes else None
        self.eval_labels, self.eval_floor, self._cache = {}, {}, {}
        for es, df in self.eval_raw.items():
            y = self.d.label_encoder.transform(df["cls" if self.dataset == "cic" else "_category"])
            self.eval_labels[es] = sorted(set(int(v) for v in y))
            self.eval_floor[es] = dv.compute_entropy_floor(df) if self.dataset == "isot" else 0.0

    def eval_tensors(self, es, transform, s):
        key = (es, transform, round(float(s), 6))
        if key not in self._cache:
            df = self.eval_raw[es]
            if transform != "clean" and s > 0:
                df = dv.apply(df, s, transform, self.eval_floor[es], self.dataset)
            X, y = self.d.tensors_from_df(df)
            self._cache[key] = (X, y)
        return self._cache[key]


# ----------------------------------------------------------------------------- run
def round_rows_header():
    return ["arm", "seed", "algorithm", "schedule", "round", "strength", "eval_set", "transform",
            "macro_f1", "per_class_recall_json", "confusion_matrix_json"]


def write_csv(path, header, rows):
    tmp = Path(str(path) + ".tmp")
    with open(tmp, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)
    tmp.replace(path)


def save_rounds(sched):
    base = set([1] + list(range(5, NUM_ROUNDS + 1, 5)))
    extra = {"sudden": {14, 15, 29, 30}, "gradual": {10, 20, 25, 35},
             "recurring": {14, 15, 21, 22, 29, 30, 36, 37}}.get(sched, set())
    return base | extra


@torch.no_grad()
def margin_and_flips(model, X_clean, X_tr, reg_idx, other_idx):
    model.eval()
    lc, lt = model(X_clean.to(DEVICE)), model(X_tr.to(DEVICE))
    if other_idx is None:   # CIC: margin to the strongest competing class
        def mg(l):
            o = l.clone()
            o[:, reg_idx] = -1e9
            return l[:, reg_idx] - o.max(1).values
    else:
        def mg(l):
            return l[:, reg_idx] - l[:, other_idx]
    pc, pt = lc.argmax(1), lt.argmax(1)
    return (float(mg(lc).mean()), float(mg(lt).mean()), float((pc != pt).float().mean()),
            float(((pc == reg_idx) & (pt != reg_idx)).float().mean()))


def run_job(spec, out_dir, num_rounds, provenance, smoke=False):
    name, seed, algo, sched = spec.split("|")
    seed = int(seed)
    a = ARMS[name]
    out_dir.mkdir(parents=True, exist_ok=True)
    tag = f"{name}__{seed}__{algo}__{sched}"
    rounds_path = out_dir / f"{tag}__rounds.csv"
    if rounds_path.exists():
        print(f"[skip] {tag}", flush=True)
        return
    (out_dir / "provenance").mkdir(exist_ok=True)
    (out_dir / "provenance" / f"{tag}.json").write_text(json.dumps(provenance, indent=1))
    ck = out_dir / "checkpoints"
    ck.mkdir(exist_ok=True)

    D = Data(a)
    d = D.d
    sched_fn = (lambda r: 1.0 if r >= 2 else 0.0) if (smoke and sched != "none") else dv.SCHEDULES[sched]
    train_tr = a["train"]
    cids = d.client_ids()
    raw = {c: d.get_client_raw_df(c) for c in D.exposed} if sched != "none" else {}
    floor = {c: (dv.compute_entropy_floor(raw[c]) if D.dataset == "isot" else 0.0) for c in raw}
    static = {}
    for c in cids:
        if c not in raw:
            static[c] = d.tensors_from_df(d.get_client_raw_df(c)) if D.dataset == "cic" else d.get_client_data(c)
    w_all = np.array([d.client_weight_rows(c) for c in cids], dtype=float)
    w_all = w_all / w_all.sum()
    audit = {c: dv.audit_counts(raw[c], D.dataset) for c in raw}
    (out_dir / "provenance" / f"{tag}__exposed_audit.json").write_text(json.dumps(
        {"exposed": D.exposed, "exposed_row_share": float(sum(w_all[cids.index(c)] for c in D.exposed)),
         "audit": audit}, indent=1))

    torch.manual_seed(seed)
    np.random.seed(seed)
    in_dim, n_cls = len(d.feature_cols), len(D.classes)
    gm = AttackFamilyMLP(in_dim, n_classes=n_cls, hidden=tuple(a["hidden"])).to(DEVICE)
    cw = d.class_weights_full_balanced
    c_glob = zeros_like_state(gm) if algo == "scaffold" else None
    c_loc = {c: zeros_like_state(gm) for c in cids} if algo == "scaffold" else None
    m_st = {k: torch.zeros_like(v, dtype=torch.float32, device="cpu") for k, v in gm.state_dict().items()} if algo == "fedadam" else None
    v_st = {k: torch.zeros_like(v, dtype=torch.float32, device="cpu") for k, v in gm.state_dict().items()} if algo == "fedadam" else None

    rows, probes, h1 = [], [], []
    t0 = time.time()
    keep = save_rounds(sched)
    for rnd in range(1, num_rounds + 1):
        s = sched_fn(rnd)
        part = cids
        if a["participation"]:
            rng = np.random.RandomState(seed * 1000 + rnd)
            part = sorted(rng.choice(cids, size=a["participation"], replace=False).tolist())
        w = np.array([w_all[cids.index(c)] for c in part])
        w = (w / w.sum()).tolist()
        g_state = {k: v.detach().cpu().clone() for k, v in gm.state_dict().items()}
        states, extra = [], []
        for c in part:
            if c in raw:
                X, y = d.tensors_from_df(dv.apply(raw[c], s, train_tr, floor[c], D.dataset)) if s > 0 else d.tensors_from_df(raw[c])
            else:
                X, y = static[c]
            lm = AttackFamilyMLP(in_dim, n_classes=n_cls, hidden=tuple(a["hidden"])).to(DEVICE)
            lm.load_state_dict(gm.state_dict())
            if algo in ("fedavg", "fedprox"):
                st, _, _ = local_train(lm, X, y, DEVICE, epochs=1, batch_size=BATCH, lr=LR,
                                       mu=MU if algo == "fedprox" else 0.0, global_state=gm.state_dict(), class_weights=cw)
            elif algo == "scaffold":
                st, dc, new_ci, _, _, _ = local_train_scaffold(lm, X, y, DEVICE, c_glob, c_loc[c], g_state, epochs=1,
                                                               batch_size=BATCH, lr=ALGO_CFG["scaffold"]["lr"], class_weights=cw)
                c_loc[c] = new_ci
                extra.append(dc)
            elif algo == "fednova":
                st, n_steps, _, _ = local_train_fednova(lm, X, y, DEVICE, epochs=1, batch_size=BATCH,
                                                        lr=ALGO_CFG["fednova"]["lr"], optimizer="sgd", class_weights=cw)
                extra.append(n_steps)
            else:
                st, _, _, _ = local_train_generic(lm, X, y, DEVICE, epochs=1, batch_size=BATCH,
                                                  lr=ALGO_CFG["fedadam"]["client_lr"], optimizer="sgd", class_weights=cw)
            states.append({k: v.detach().cpu() for k, v in st.items()})
        if algo in ("fedavg", "fedprox"):
            new = aggregate_weighted(states, w)
        elif algo == "scaffold":
            new, c_glob = aggregate_scaffold(states, extra, w, c_glob)
        elif algo == "fednova":
            new = aggregate_fednova(states, g_state, w, extra)
        else:
            cfg = ALGO_CFG["fedadam"]
            new, m_st, v_st = aggregate_fedadam(states, g_state, w, m_st, v_st, server_lr=cfg["server_lr"],
                                                beta1=cfg["beta1"], beta2=cfg["beta2"], tau=cfg["tau"])
        gm.load_state_dict(new)

        def ev(es, tr, st_):
            X, y = D.eval_tensors(es, tr, st_)
            m = evaluate(gm, X, y, DEVICE, D.classes, eval_label_indices=D.eval_labels[es], return_confusion_matrix=True)
            return m["macro_f1"], json.dumps(m["per_class_recall"]), json.dumps(m["confusion_matrix"])

        for es in a["eval_sets"]:
            rows.append([name, seed, algo, sched, rnd, s, es, "clean", *ev(es, "clean", 0)])
            if s > 0:
                for tr in a["evals"]:
                    rows.append([name, seed, algo, sched, rnd, s, es, tr, *ev(es, tr, s)])
        if rnd in keep:
            save_checkpoint(gm, ck / f"{tag}__r{rnd}.pt")
            probe_tr = (["td", "td_time_only", "td_rate_only"] + (["v2"] if "v2" in a["evals"] else []))
            for es in a["eval_sets"]:
                for tr in probe_tr:
                    for ps in (PROBE_STRENGTHS if tr in ("td", "v2") else [1.0]):
                        probes.append([name, seed, algo, sched, rnd, ps, es, tr, *ev(es, tr, ps)])
        if sched == "none" and rnd in H1_ROUNDS:
            Xc, yc = D.eval_tensors("validation", "clean", 0)
            for tr in a["evals"]:
                Xt, yt = D.eval_tensors("validation", tr, 1.0)
                sel = yc == D.reg_idx
                h1.append([name, seed, algo, rnd, tr, *margin_and_flips(gm, Xc[sel], Xt[sel], D.reg_idx, D.mitm_idx)])
        if rnd in keep or rnd == num_rounds:
            last = [r for r in rows if r[4] == rnd and r[6] == "validation"]
            print(f"[{tag}] r{rnd} s={s:.2f} " + " ".join(f"{r[7]}={r[8]:.4f}" for r in last)
                  + f" t={time.time() - t0:.0f}s", flush=True)

    write_csv(out_dir / f"{tag}__probes.csv", round_rows_header(), probes)
    if h1:
        write_csv(out_dir / f"{tag}__h1.csv", ["arm", "seed", "algorithm", "round", "transform", "margin_clean",
                                              "margin_transformed", "flip_rate", "regular_to_other_rate"], h1)
    write_csv(rounds_path, round_rows_header(), rows)   # written last: marks the job complete
    print(f"[done] {tag} {time.time() - t0:.0f}s", flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--job")
    ap.add_argument("--list-jobs", action="store_true")
    ap.add_argument("--smoke")
    args = ap.parse_args()
    if args.list_jobs:
        print("\n".join(jobs()))
        return
    if args.smoke:
        run_job(args.job, Path(args.smoke), 3, {"smoke": True}, smoke=True)
        return
    if args.job not in jobs():
        sys.exit("job is not in the frozen job list")
    prov = verify_frozen_state()
    prov.update({"job": args.job, "torch": torch.__version__, "device": str(DEVICE), "started_unix": time.time()})
    run_job(args.job, RESULTS, NUM_ROUNDS, prov)


if __name__ == "__main__":
    main()
