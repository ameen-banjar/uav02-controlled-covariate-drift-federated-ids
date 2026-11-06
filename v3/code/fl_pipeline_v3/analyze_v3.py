"""
UAV-02 v3 frozen analysis (DESIGN_V3.md section 5). Run ONCE after every job
in run_v3.jobs() is complete. Reads results_v3/*.csv only.

    python3.11 analyze_v3.py [--results-dir DIR] [--out-dir DIR] [--allow-partial]

All gates are directional replication criteria (fraction of seeds), not
significance tests. Equivalence uses two one-sided t-tests (TOST, alpha 0.05):
equivalent when the 90% t-interval of the seed means lies inside +-EQ_MARGIN.
"""
import argparse
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
from scipy import stats

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import run_v3 as R  # noqa: E402

csv.field_size_limit(10 ** 9)
FULL = {"sudden": list(range(15, 30)), "gradual": list(range(20, 26)),
        "recurring": list(range(15, 22)) + list(range(30, 37))}
INTERVALS = {"sudden": [(30, 45)], "gradual": [(35, 45)], "recurring": [(22, 29), (37, 45)]}
SCH = ["sudden", "gradual", "recurring"]
EQ_MARGIN = 0.01
PR_BOUND = 0.005
LINES = []


def out(s=""):
    LINES.append(s)
    print(s)


def summ(v):
    v = np.asarray(v, float)
    n = len(v)
    m, sd = float(v.mean()), float(v.std(ddof=1)) if n > 1 else 0.0
    h95 = stats.t.ppf(0.975, n - 1) * sd / np.sqrt(n) if n > 1 else 0.0
    h90 = stats.t.ppf(0.95, n - 1) * sd / np.sqrt(n) if n > 1 else 0.0
    return {"n": n, "mean": m, "sd": sd, "min": float(v.min()), "max": float(v.max()),
            "ci95": (m - h95, m + h95), "ci90": (m - h90, m + h90),
            "dz": m / sd if sd > 0 else float("nan"), "neg": int((v < 0).sum()), "pos": int((v > 0).sum())}


def fmt(s, extra=""):
    return (f"mean={s['mean']:+.4f} sd={s['sd']:.4f} range=[{s['min']:+.4f},{s['max']:+.4f}] "
            f"95%t=[{s['ci95'][0]:+.4f},{s['ci95'][1]:+.4f}] d_z={s['dz']:+.2f} neg {s['neg']}/{s['n']}{extra}")


def tost(s):
    lo, hi = s["ci90"]
    return lo > -EQ_MARGIN and hi < EQ_MARGIN


# ----------------------------------------------------------------------------- load
def load(rd):
    runs = {}
    for f in sorted(rd.glob("*__rounds.csv")):
        a, seed, algo, sched, _ = f.name.split("__")
        d = defaultdict(dict)
        for r in csv.DictReader(open(f)):
            d[int(r["round"])][(r["eval_set"], r["transform"])] = (
                float(r["strength"]), float(r["macro_f1"]), json.loads(r["per_class_recall_json"]),
                np.array(json.loads(r["confusion_matrix_json"]), float))
        runs[(a, int(seed), algo, sched)] = d
    probes = defaultdict(list)
    for f in sorted(rd.glob("*__probes.csv")):
        a, seed, algo, sched, _ = f.name.split("__")
        for r in csv.DictReader(open(f)):
            probes[(a, int(seed), algo, sched)].append(r)
    h1 = defaultdict(list)
    for f in sorted(rd.glob("*__h1.csv")):
        a, seed, algo, sched, _ = f.name.split("__")
        for r in csv.DictReader(open(f)):
            h1[(a, int(seed), algo)].append(r)
    return runs, probes, h1


def none_ref(arm):
    return "main_none" if arm.startswith(("main_", "exp_")) else arm


def reg_name(arm):
    return "Benign_Final" if arm == "cic" else "Regular"


# ----------------------------------------------------------------------------- estimands
def l1(run, sched, tr, es, metric, arm):
    vals = []
    for r in FULL[sched]:
        cl, dr = run[r][(es, "clean")], run[r][(es, tr)]
        if metric == "macro_f1":
            vals.append(dr[1] - cl[1])
        else:
            vals.append(dr[2][metric] - cl[2][metric])
    return float(np.mean(vals))


def l1_classes(run, sched, tr, es):
    keys = run[FULL[sched][0]][(es, "clean")][2].keys()
    return {k: l1(run, sched, tr, es, k, None) for k in keys}


def gap(run, ref, r, es, metric):
    a, b = run[r][(es, "clean")], ref[r][(es, "clean")]
    return (a[1] - b[1]) if metric == "macro_f1" else (a[2][metric] - b[2][metric])


def l2(run, ref, es, metric):
    exp = [r for r in run if run[r][(es, "clean")][0] > 0]
    return float(np.mean([gap(run, ref, r, es, metric) for r in exp]))


def h2_rates(run, sched, tr, es, classes):
    """per true class c: drifted minus clean rate of predicting MITM, per full-strength round."""
    mi = classes.index("MITM")
    outr = defaultdict(list)
    for r in FULL[sched]:
        cc, cd = run[r][(es, "clean")][3], run[r][(es, tr)][3]
        for i, c in enumerate(classes):
            if c == "MITM" or cc[i].sum() == 0:
                continue
            outr[c].append(cd[i, mi] / cd[i].sum() - cc[i, mi] / cc[i].sum())
    return outr


# ----------------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--results-dir", default=str(R.RESULTS))
    ap.add_argument("--out-dir", default=None)
    ap.add_argument("--allow-partial", action="store_true")
    a = ap.parse_args()
    rd = Path(a.results_dir)
    od = Path(a.out_dir) if a.out_dir else rd / "analysis"
    od.mkdir(parents=True, exist_ok=True)
    runs, probes, h1 = load(rd)
    expected = {tuple(j.split("|")) for j in R.jobs()}
    have = {(k[0], str(k[1]), k[2], k[3]) for k in runs}
    missing = sorted(expected - have)
    out(f"jobs expected {len(expected)}, complete {len(have & expected)}, missing {len(missing)}")
    if missing and not a.allow_partial:
        sys.exit(f"incomplete campaign; first missing: {missing[:5]}")
    gates, table = {}, []

    def add(arm, algo, sched, es, tr, quantity, s):
        table.append({"arm": arm, "algorithm": algo, "schedule": sched, "eval_set": es, "transform": tr,
                      "quantity": quantity, **{k: (v if not isinstance(v, tuple) else f"{v[0]:+.6f};{v[1]:+.6f}")
                                              for k, v in s.items()}})

    def block(arm, tr, es="validation", scheds=SCH, gate_frac=0.8, label=None):
        A = R.ARMS[arm]
        label = label or arm
        out("\n" + "=" * 100 + f"\n{label}: L1 / L2 / L3 / L3c  (transform={tr}, eval_set={es})\n" + "=" * 100)
        for algo in A["algos"]:
            for sched in scheds:
                ks = [(arm, s, algo, sched) for s in A["seeds"] if (arm, s, algo, sched) in runs]
                if not ks:
                    continue
                ref = lambda k: runs.get((none_ref(arm), k[1], algo, "none"))
                mf = [l1(runs[k], sched, tr, es, "macro_f1", arm) for k in ks]
                rg = [l1(runs[k], sched, tr, es, reg_name(arm), arm) for k in ks]
                sm, sr = summ(mf), summ(rg)
                out(f"\n[{label} {algo}/{sched}] seeds {[k[1] for k in ks]}")
                out("  L1 macro-F1     " + fmt(sm) + "\n     per-seed " + ", ".join(f"{k[1]}:{v:+.4f}" for k, v in zip(ks, mf)))
                out(f"  L1 {reg_name(arm)} recall " + fmt(sr) + "\n     per-seed " + ", ".join(f"{k[1]}:{v:+.4f}" for k, v in zip(ks, rg)))
                add(arm, algo, sched, es, tr, "L1_macro_f1", sm)
                add(arm, algo, sched, es, tr, "L1_regular_recall", sr)
                g = sm["neg"] >= int(np.ceil(gate_frac * sm["n"]))
                gates[f"L1neg_{label}_{algo}_{sched}_{es}"] = bool(g)
                gates[f"PR_{label}_{algo}_{sched}_{es}"] = bool(abs(sr["mean"]) < PR_BOUND)
                cls = defaultdict(list)
                for k in ks:
                    for c, v in l1_classes(runs[k], sched, tr, es).items():
                        cls[c].append(v)
                out("  L1 class recall (mean): " + ", ".join(f"{c}:{np.mean(v):+.3f}" for c, v in sorted(cls.items())))
                if all(ref(k) for k in ks):
                    l2v = [l2(runs[k], ref(k), es, "macro_f1") for k in ks]
                    s2 = summ(l2v)
                    out("  L2 macro-F1     " + fmt(s2, f" | TOST(+-{EQ_MARGIN}) {'EQUIVALENT' if tost(s2) else 'not shown'}"))
                    add(arm, algo, sched, es, tr, "L2_macro_f1", s2)
                    gates[f"EQ_L2_{label}_{algo}_{sched}_{es}"] = tost(s2)
                    for lo, hi in INTERVALS[sched]:
                        for pt in sorted({lo, min(lo + 5, hi), hi}):
                            v = [gap(runs[k], ref(k), pt, es, "macro_f1") for k in ks]
                            s3 = summ(v)
                            tag = "residual" if pt == hi else ("immediate" if pt == lo else "+5")
                            out(f"  L3 [{lo},{hi}] {tag}@r{pt} " + fmt(s3, (f" | TOST {'EQUIVALENT' if tost(s3) else 'not shown'}" if pt == hi else "")))
                            if pt == hi:
                                add(arm, algo, sched, es, tr, f"L3_r{pt}_macro_f1", s3)
                                gates[f"EQ_L3_{label}_{algo}_{sched}_r{pt}_{es}"] = tost(s3)
                                cl3 = defaultdict(list)
                                for k in ks:
                                    a_, b_ = runs[k][pt][(es, "clean")][2], ref(k)[pt][(es, "clean")][2]
                                    for c in a_:
                                        cl3[c].append(a_[c] - b_[c])
                                out(f"  L3c r{pt}: " + ", ".join(f"{c}:{np.mean(v):+.4f}(min {np.min(v):+.4f})" for c, v in sorted(cl3.items())))

    # ---------------- primary and replication blocks
    block("main_td", "td", label="P1_main_td")
    block("main_v2", "v2", label="P2_main_v2")
    block("main_td", "v2", label="X_main_td_eval_v2")
    block("main_v2", "td", label="X_main_v2_eval_td")

    # ---------------- H1 on main_none (and descriptive for every none arm)
    out("\n" + "=" * 100 + "\nH1: clean-trained none checkpoints; S = drop(r30) - drop(r15); S_rel uses drop/|clean margin|; "
        "F = flip(r30) - flip(r15)\n" + "=" * 100)
    for arm in [k for k in R.ARMS if "none" in R.ARMS[k]["scheds"]]:
        A = R.ARMS[arm]
        frac = 0.8 if arm == "main_none" else 0.8
        for algo in A["algos"]:
            for tr in A["evals"]:
                S, Srel, F = [], [], []
                for s in A["seeds"]:
                    rows = {int(r["round"]): r for r in h1.get((arm, s, algo), []) if r["transform"] == tr}
                    if 15 not in rows or 30 not in rows:
                        continue
                    dr = {x: float(rows[x]["margin_transformed"]) - float(rows[x]["margin_clean"]) for x in (15, 30)}
                    rl = {x: dr[x] / abs(float(rows[x]["margin_clean"])) for x in (15, 30)}
                    S.append(dr[30] - dr[15])
                    Srel.append(rl[30] - rl[15])
                    F.append(float(rows[30]["flip_rate"]) - float(rows[15]["flip_rate"]))
                if not S:
                    continue
                ss, sr, sf = summ(S), summ(Srel), summ(F)
                need = int(np.ceil(frac * ss["n"]))
                out(f"[{arm} {algo} {tr}] S " + fmt(ss) + f"\n      S_rel " + fmt(sr) + f"\n      F(flip) " + fmt(sf).replace("neg", "neg(fewer flips later)"))
                add(arm, algo, "none", "validation", tr, "H1_S", ss)
                add(arm, algo, "none", "validation", tr, "H1_S_rel", sr)
                add(arm, algo, "none", "validation", tr, "H1_flip", sf)
                gates[f"H1_{arm}_{algo}_{tr}"] = ss["neg"] >= need
                gates[f"H1rel_{arm}_{algo}_{tr}"] = sr["neg"] >= need
                gates[f"H1flip_{arm}_{algo}_{tr}"] = sf["pos"] >= need
    for tr in ("td", "v2"):
        gates[f"H1_joint_main_none_{tr}"] = all(gates.get(f"H1_main_none_{al}_{tr}", False) for al in ("fedavg", "fedprox"))

    # ---------------- H2 on main_td (td) and main_v2 (v2), pooled over the three schedules
    from data import ALL_CATEGORIES
    out("\n" + "=" * 100 + "\nH2 (pooled full-strength rounds of the three schedules; equal round weight)\n" + "=" * 100)
    for arm, tr in (("main_td", "td"), ("main_v2", "v2")):
        A = R.ARMS[arm]
        for algo in A["algos"]:
            per = defaultdict(list)
            for s in A["seeds"]:
                pooled = defaultdict(list)
                for sched in SCH:
                    k = (arm, s, algo, sched)
                    if k in runs:
                        for c, v in h2_rates(runs[k], sched, tr, "validation", ALL_CATEGORIES).items():
                            pooled[c] += v
                for c, v in pooled.items():
                    per[c].append(float(np.mean(v)))
            if not per:
                continue
            n = len(per["DoS"])
            h2a = sum(1 for i in range(n) if per["DoS"][i] < 0.01 and max(per[c][i] for c in per) > 0.10)
            h2b = sum(1 for i in range(n) if per["Regular"][i] >= 0.05 and per["Video"][i] >= 0.05)
            out(f"[{arm} {algo}] " + ", ".join(f"{c}:{np.mean(v):+.4f}" for c, v in sorted(per.items())) + f" | H2a {h2a}/{n} H2b {h2b}/{n}")
            for c, v in per.items():
                add(arm, algo, "pooled", "validation", tr, f"H2_{c}_to_MITM", summ(v))
            gates[f"H2a_{arm}_{algo}"] = h2a >= int(np.ceil(0.8 * n))
            gates[f"H2b_{arm}_{algo}"] = h2b >= int(np.ceil(0.8 * n))

    # ---------------- dose response and component decomposition (probes on main_none checkpoints)
    out("\n" + "=" * 100 + "\nDOSE and COMPONENTS: probes on clean-trained main_none checkpoints, rounds 15/30/45, validation\n" + "=" * 100)
    for algo in ("fedavg", "fedprox"):
        for rnd in ("15", "30", "45"):
            dose = defaultdict(list)
            comp = defaultdict(list)
            for s in R.SEEDS10:
                pr = [p for p in probes.get(("main_none", s, algo, "none"), []) if p["round"] == rnd and p["eval_set"] == "validation"]
                if not pr:
                    continue
                cl = runs[("main_none", s, algo, "none")][int(rnd)][("validation", "clean")][1]
                for p in pr:
                    dv_ = float(p["macro_f1"]) - cl
                    if p["transform"] in ("td", "v2"):
                        dose[(p["transform"], float(p["strength"]))].append(dv_)
                    if float(p["strength"]) == 1.0:
                        comp[p["transform"]].append(dv_)
            if not dose:
                continue
            for tr in ("td", "v2"):
                ms = [np.mean(dose[(tr, x)]) for x in R.PROBE_STRENGTHS]
                mono = all(ms[i + 1] <= ms[i] for i in range(len(ms) - 1))
                out(f"[{algo} r{rnd} {tr}] dose " + ", ".join(f"s={x}:{m:+.4f}" for x, m in zip(R.PROBE_STRENGTHS, ms))
                    + f" | monotone decreasing: {mono}")
                gates[f"DOSEmono_{algo}_r{rnd}_{tr}"] = bool(mono)
            add_res = np.array(comp["td"]) - np.array(comp["td_time_only"]) - np.array(comp["td_rate_only"])
            out(f"[{algo} r{rnd}] components at s=1: td {np.mean(comp['td']):+.4f}, time-only {np.mean(comp['td_time_only']):+.4f}, "
                f"rate-only {np.mean(comp['td_rate_only']):+.4f}, non-additivity {np.mean(add_res):+.4f}")
            add("main_none", algo, f"r{rnd}", "validation", "td", "components_nonadditivity", summ(add_res))

    # ---------------- exposure share
    out("\n" + "=" * 100 + "\nEXPOSURE SHARE (sudden, td): k exposed clients in {5, 8, 11, 15}; per-seed OLS slope on exposed row share\n" + "=" * 100)
    import data as dmod
    man = json.loads(Path(dmod.MANIFEST_PATH).read_text())
    order = json.loads((R.MANIFESTS / "frozen_exposure_order.json").read_text())
    share = {k: sum(man["clients"][str(c)]["fedavg_weight_by_rows"] for c in order[:k]) for k in (5, 8, 11, 15)}
    arms_k = {5: "main_td", 8: "exp_k8", 11: "exp_k11", 15: "exp_k15"}
    for algo in ("fedavg", "fedprox"):
        for q in ("L1", "L2", "L3_r45"):
            per_k = {}
            for k, arm in arms_k.items():
                vals = []
                for s in R.SEEDS5:
                    run, ref = runs.get((arm, s, algo, "sudden")), runs.get(("main_none", s, algo, "none"))
                    if not run or not ref:
                        vals.append(np.nan)
                        continue
                    vals.append(l1(run, "sudden", "td", "validation", "macro_f1", arm) if q == "L1" else
                                l2(run, ref, "validation", "macro_f1") if q == "L2" else gap(run, ref, 45, "validation", "macro_f1"))
                per_k[k] = vals
            slopes = []
            for i in range(len(R.SEEDS5)):
                x = np.array([share[k] for k in per_k])
                y = np.array([per_k[k][i] for k in per_k])
                if np.isfinite(y).all():
                    slopes.append(float(np.polyfit(x, y, 1)[0]))
            out(f"[{algo} {q}] " + ", ".join(f"k={k}(share {share[k]:.3f}): {np.nanmean(v):+.4f}" for k, v in per_k.items())
                + (" | slope per unit share " + fmt(summ(slopes)) if len(slopes) > 1 else ""))
            if len(slopes) > 1:
                add("exposure", algo, "sudden", "validation", "td", f"slope_{q}", summ(slopes))
            for k, v in per_k.items():
                v = [x for x in v if np.isfinite(x)]
                if len(v) > 1 and q == "L3_r45":
                    s3 = summ(v)
                    gates[f"EQ_L3_exposure_k{k}_{algo}"] = tost(s3)

    # ---------------- robustness arms
    for arm in ("alpha_0.1", "alpha_2", "alpha_100", "arch_wide", "algo_scaffold", "algo_fednova",
                "algo_fedadam", "partial10", "cic"):
        block(arm, "td", scheds=["sudden"], label=f"R_{arm}")
    block("fresh", "td", es="validation", label="F_fresh_validation")
    block("fresh", "td", es="fresh", label="F_fresh_fresh")

    (od / "summary.txt").write_text("\n".join(LINES) + "\n")
    (od / "gates.json").write_text(json.dumps({"partial": bool(missing), "n_missing": len(missing), "gates": {k: bool(v) for k, v in gates.items()}}, indent=1))
    with open(od / "table.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=sorted({k for r in table for k in r}))
        w.writeheader()
        w.writerows(table)
    print(f"\nwrote {od}/summary.txt, gates.json, table.csv")


if __name__ == "__main__":
    main()
