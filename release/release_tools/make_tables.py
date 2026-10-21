"""
Regenerate manuscript Tables 2-6 FROM THE SAVED OUTPUTS (NEW release tool,
2026-10-21). No model is trained or loaded and the dataset is not needed.

    python release_tools/make_tables.py --table 3        # one table
    python release_tools/make_tables.py --table all      # Tables 2-6 + key in-text values

Sources (all read-only):
  Table 2  frozen drift schedules (code/fl_pipeline/drift.py), cross-checked
           against the saved per-round `drift_strength` of all 40 runs
  Table 3  CONFIRMATORY L1 primary  - results_confirmatory/seed*_rounds.csv
  Table 4  CONFIRMATORY L3 residual - results_confirmatory/seed*_rounds.csv
  Table 5  CONFIRMATORY H2 pooled   - results_confirmatory/seed*_rounds.csv (confusion matrices)
  Table 6  POST-HOC held-out test (2026-10-19) - posthoc_added_after_results/
           post_hoc/heldout_test/per_checkpoint_test.csv, next to validation on
           the same saved rounds from results_confirmatory/seed*_rounds.csv
The estimand code is the frozen analysis's own (load_run, structure, summ from
code/fl_pipeline/analyze_confirmatory.py); Table 6 repeats the definitions of
post_hoc/posthoc_heldout_test.py and posthoc_heldout_test_9label.py.
Outputs: regenerated/table<N>.md (or --out-dir).
"""
import argparse
import csv
import json
import sys
from pathlib import Path

import numpy as np

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import _paths  # noqa: E402

_paths.add_frozen_code_to_path()
from analyze_confirmatory import load_run, structure, summ, SEEDS, ALGOS, SCHEDS, CLASSES, MITM  # noqa: E402
import drift as drift_mod  # noqa: E402

NAME = {"fedavg": "FedAvg", "fedprox": "FedProx"}
MINUS = "−"
# Post-hoc held-out round sets, as fixed in post_hoc/posthoc_heldout_test.py (FULL_ROUNDS, RESIDUAL_ROUNDS)
PH_FULL = {"sudden": [15, 20, 25, 29], "gradual": [20, 25], "recurring": [15, 20, 21, 30, 35, 36]}
PH_RESIDUAL = 45
PC = CLASSES.index("Password Cracking")


def f4(x, uni=False):
    s = f"{x:+.4f}"
    return s.replace("-", MINUS) if uni else s


def span(lo, hi):
    return f"{lo}–{hi}"


def runs_of(rounds):
    out = []
    for r in rounds:
        if out and r == out[-1][1] + 1:
            out[-1][1] = r
        else:
            out.append([r, r])
    return [tuple(x) for x in out]


def load_all():
    runs = {(s, a, sc): load_run(_paths.RESULTS, s, a, sc) for s in SEEDS for a in ALGOS for sc in ["none"] + SCHEDS}
    missing = [k for k, v in runs.items() if v is None]
    if missing:
        sys.exit(f"missing round CSVs: {missing[:3]}")
    struct = {sc: structure(runs[(SEEDS[0], "fedavg", sc)]) for sc in SCHEDS}
    return runs, struct


# ------------------------------------------------------------------ Table 2
def table2(runs, struct):
    rounds = range(1, drift_mod.NUM_ROUNDS + 1)
    for (s, a, sc), run in runs.items():          # executable schedule == saved strengths, every run
        assert [run[r]["drift_strength"] for r in rounds] == [float(drift_mod.SCHEDULES[sc](r)) for r in rounds], (s, a, sc)
    lines = ["**Table 2. Executed temporal schedules.** All intervals below are inclusive; full strength means the saved "
             "`drift_strength` equals one.", "",
             "| Schedule | Positive-strength rounds | Full-strength rounds | Post-removal intervals |",
             "|---|---|---|---|",
             "| None | None | None | Clean reference throughout |"]
    for sc in SCHEDS:
        exp, full, ivs = struct[sc]
        pos = " and ".join(span(*x) for x in runs_of(exp))
        fl = " and ".join(span(*x) for x in runs_of(full)) + f" ({len(full)} rounds)"
        post = " and ".join(span(*x) for x in ivs)
        lines.append(f"| {sc.capitalize()} | {pos} | {fl} | {post} |")
    return lines


# ------------------------------------------------------------------ Table 3 (L1 primary)
def table3(runs, struct):
    lines = ["**Table 3. Primary immediate response, seeds 21, 32, 43, 54, 65.** Mean and SD describe five seed summaries; "
             "intervals are descriptive, not significance tests.", "",
             "| Algorithm | Schedule | Metric | Mean | SD | Range | 95% t interval | d_z | Negative seeds |",
             "|---|---|---|---:|---:|---|---|---:|---:|"]
    for a in ALGOS:
        for sc in SCHEDS:
            full = struct[sc][1]
            for key, label in (("macro_f1", "macro-F1"), ("regular_recall", "Regular recall")):
                v = [float(np.mean([runs[(s, a, sc)][r][f"delta_{key}"] for r in full])) for s in SEEDS]
                m = summ(v)
                lines.append(f"| {NAME[a]} | {sc.capitalize()} | {label} | {m['mean']:+.4f} | {m['sd']:.4f} | "
                             f"[{m['min']:+.4f}, {m['max']:+.4f}] | [{m['ci_lo']:+.4f}, {m['ci_hi']:+.4f}] | "
                             f"{m['dz']:+.2f} | {sum(x < 0 for x in v)}/5 |")
    return lines


# ------------------------------------------------------------------ Table 4 (L3 residual)
def table4(runs, struct):
    lines = ["**Table 4. Residual clean macro-F1 gaps at the last round of each post-removal interval, seeds 21, 32, 43, 54, 65.** "
             "Complete intermediate and Regular-recall summaries are in the supplement.", "",
             "| Algorithm | Schedule / interval | Round | Mean | SD | Range | Descriptive 95% t interval |",
             "|---|---|---:|---:|---:|---|---|"]
    for a in ALGOS:
        for sc in SCHEDS:
            for lo, hi in struct[sc][2]:
                v = [runs[(s, a, sc)][hi]["clean_macro_f1"] - runs[(s, a, "none")][hi]["clean_macro_f1"] for s in SEEDS]
                m = summ(v)
                lines.append(f"| {NAME[a]} | {sc.capitalize()} / {span(lo, hi)} | {hi} | {f4(m['mean'], True)} | {m['sd']:.4f} | "
                             f"[{f4(m['min'], True)}, {f4(m['max'], True)}] | [{f4(m['ci_lo'], True)}, {f4(m['ci_hi'], True)}] |")
    return lines


# ------------------------------------------------------------------ Table 5 (H2 pooled)
def h2_per_seed(runs, struct, a):
    present = [c for c in range(len(CLASSES)) if runs[(SEEDS[0], "fedavg", "none")][1]["clean_cm"][c].sum() > 0]
    per = {}
    for s in SEEDS:
        acc = {c: [] for c in present if c != MITM}
        for sc in SCHEDS:
            for r in struct[sc][1]:
                run = runs[(s, a, sc)][r]
                for c in acc:
                    rc, rd = run["clean_cm"][c], run["drifted_cm"][c]
                    acc[c].append(rd[MITM] / rd.sum() - rc[MITM] / rc.sum())
        per[s] = {CLASSES[c]: float(np.mean(v)) for c, v in acc.items()}
    return per


def table5(runs, struct):
    lines = ["**Table 5. Pooled full-strength transition changes, seeds 21, 32, 43, 54, 65.**", "",
             "| Algorithm | True class → MITM | Mean | SD | Range | Descriptive 95% t interval | d_z |",
             "|---|---|---:|---:|---|---|---:|"]
    for a in ALGOS:
        per = h2_per_seed(runs, struct, a)
        for k in ("Regular", "Video"):
            m = summ([per[s][k] for s in SEEDS])
            lines.append(f"| {NAME[a]} | {k} | {m['mean']:+.4f} | {m['sd']:.4f} | [{m['min']:+.4f}, {m['max']:+.4f}] | "
                         f"[{m['ci_lo']:+.4f}, {m['ci_hi']:+.4f}] | {m['dz']:+.2f} |")
    return lines


# ------------------------------------------------------------------ Table 6 (POST-HOC held-out test)
def macro_f1(cm, labels):
    cm = np.asarray(cm, float)
    f = []
    for i in labels:
        tp, p, r = cm[i, i], cm[:, i].sum(), cm[i, :].sum()
        prec, rec = (tp / p if p else 0.0), (tp / r if r else 0.0)
        f.append(2 * prec * rec / (prec + rec) if prec + rec else 0.0)
    return float(np.mean(f))


def table6(runs, struct):
    T = {}
    for r in csv.DictReader(open(_paths.HELDOUT / "per_checkpoint_test.csv")):
        T[(r["algorithm"], r["schedule"], int(r["seed"]), int(r["round"]))] = r
    if len(T) != 480:
        sys.exit(f"expected 480 held-out checkpoint rows, found {len(T)}")
    L9 = [i for i in range(len(CLASSES)) if i != PC]
    lines = ["**Table 6. Post-hoc held-out-test versus validation on the same saved rounds (seed means, n = 5).**", "",
             "| Algorithm | Schedule | Δ macro-F1 test (10 classes) | Δ macro-F1 test (9 classes) | Δ macro-F1 validation | "
             "Δ Regular recall test | Δ Regular recall validation | Residual macro-F1 r45 test |",
             "|---|---|---:|---:|---:|---:|---:|---:|"]
    for a in ALGOS:
        for sc, rr in PH_FULL.items():
            def seedmean(fn):
                return float(np.mean([np.mean([fn(s, r) for r in rr]) for s in SEEDS]))
            te10 = seedmean(lambda s, r: float(T[(a, sc, s, r)]["delta_macro_f1"]))
            te9 = seedmean(lambda s, r: macro_f1(json.loads(T[(a, sc, s, r)]["drifted_confusion_matrix_json"]), L9)
                           - macro_f1(json.loads(T[(a, sc, s, r)]["clean_confusion_matrix_json"]), L9))
            va = seedmean(lambda s, r: runs[(s, a, sc)][r]["delta_macro_f1"])
            tr = seedmean(lambda s, r: float(T[(a, sc, s, r)]["delta_regular_recall"]))
            vr = seedmean(lambda s, r: runs[(s, a, sc)][r]["delta_regular_recall"])
            res = float(np.mean([float(T[(a, sc, s, PH_RESIDUAL)]["clean_macro_f1"])
                                 - float(T[(a, "none", s, PH_RESIDUAL)]["clean_macro_f1"]) for s in SEEDS]))
            lines.append(f"| {NAME[a]} | {sc.capitalize()} | " + " | ".join(f4(x, True) for x in (te10, te9, va, tr, vr, res)) + " |")
    return lines


# ------------------------------------------------------------------ key in-text values (Sections 4.3, 4.4)
def intext(runs, struct):
    lines = ["**Key in-text values (Sections 4.3-4.4), confirmatory validation.**", ""]
    for a in ALGOS:
        l2 = []
        for sc in SCHEDS:
            exp = struct[sc][0]
            v = [float(np.mean([runs[(s, a, sc)][r]["clean_macro_f1"] - runs[(s, a, "none")][r]["clean_macro_f1"] for r in exp]))
                 for s in SEEDS]
            l2.append(f"{sc} {np.mean(v):+.4f}")
        lines.append(f"- L2 mean exposure-period macro-F1 gap, {NAME[a]}: " + ", ".join(l2))
    for a in ALGOS:
        d = {}
        for s in SEEDS:
            for r in csv.DictReader(open(_paths.RESULTS / f"seed{s}_{a}_none_h1_margins.csv")):
                d[(s, int(r["round"]))] = float(r["margin_drop"])
        S = [d[(s, 30)] - d[(s, 15)] for s in SEEDS]
        m = summ(S)
        lines.append(f"- H1 {NAME[a]}: S mean {m['mean']:+.4f}, SD {m['sd']:.4f}, range [{m['min']:+.4f}, {m['max']:+.4f}], "
                     f"interval [{m['ci_lo']:+.4f}, {m['ci_hi']:+.4f}], d_z {m['dz']:+.2f}, negative {sum(x < 0 for x in S)}/5; "
                     f"mean drop r15 {np.mean([d[(s, 15)] for s in SEEDS]):+.4f}, r30 {np.mean([d[(s, 30)] for s in SEEDS]):+.4f}")
    return lines


TABLES = {"2": table2, "3": table3, "4": table4, "5": table5, "6": table6, "intext": intext}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--table", default="all", choices=list(TABLES) + ["all"])
    ap.add_argument("--out-dir", default=str(_paths.STAGING / "regenerated"))
    a = ap.parse_args()
    od = Path(a.out_dir)
    od.mkdir(parents=True, exist_ok=True)
    runs, struct = load_all()
    for key in (TABLES if a.table == "all" else [a.table]):
        lines = TABLES[key](runs, struct)
        name = f"table{key}.md" if key != "intext" else "intext_values.md"
        (od / name).write_text("\n".join(lines) + "\n")
        print("\n".join(lines) + "\n")
    print(f"written to {od}")


if __name__ == "__main__":
    main()
