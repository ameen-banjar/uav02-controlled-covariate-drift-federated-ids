"""
Reporting supplement for the UAV-02 confirmatory study (DISPLAY ONLY, not part
of the frozen code set; adds no endpoint, threshold or gate).

Fills three reporting requirements that the frozen analysis prints only as
rates or as a combined verdict:
  A. Primary criteria shown SEPARATELY: macro-F1 criterion and Regular-recall
     criterion each get their own pass / did-not-pass line (the frozen combined
     gate, which requires both, is quoted unchanged from analyze_confirmatory).
  B. Every confusion rate as count/N (mean per-round count out of N validation
     rows of that true class), never a bare percentage; classes with no
     validation support print NA, not 0.
  C. Continuous per-seed values next to every binary criterion.
"""
import argparse
import csv
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from analyze_confirmatory import (load_run, structure, SEEDS, ALGOS, SCHEDS, CLASSES, MITM,  # noqa: E402
                                  GATE_MIN_SEEDS)

WINDOWS = {"recurring window 1 (r15-21)": ("recurring", range(15, 22)),
           "recurring window 2 (r30-36)": ("recurring", range(30, 37))}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--results-dir", default=str(HERE.parent / "results_drift_confirmatory"))
    ap.add_argument("--out-dir", default=None)
    args = ap.parse_args()
    rd = Path(args.results_dir)
    od = Path(args.out_dir) if args.out_dir else rd / "analysis"
    od.mkdir(parents=True, exist_ok=True)
    runs = {(s, a, sc): load_run(rd, s, a, sc) for s in SEEDS for a in ALGOS for sc in ["none"] + SCHEDS}
    if any(v is None for v in runs.values()):
        raise SystemExit("incomplete results; run only after all 5 seeds finished")
    lines = []

    def out(x=""):
        lines.append(x)
        print(x)

    full = {sc: structure(runs[(SEEDS[0], "fedavg", sc)])[1] for sc in SCHEDS}

    out("A. PRIMARY criteria, reported separately (negative = drift hurts; direction gate >=4/5 seeds)")
    for a in ALGOS:
        for sc in SCHEDS:
            for key, label in (("macro_f1", "Macro-F1"), ("regular_recall", "Regular-recall")):
                v = [float(np.mean([runs[(s, a, sc)][r][f"delta_{key}"] for r in full[sc]])) for s in SEEDS]
                k = sum(x < 0 for x in v)
                out(f"  {a}/{sc:9s} {label:14s} criterion {'PASSED' if k >= GATE_MIN_SEEDS else 'did NOT pass'} "
                    f"({k}/5 negative) values: " + " ".join(f"{x:+.4f}" for x in v))

    out("\nB. H2 confusion toward MITM as count/N  (count = mean per-round number of validation rows of the true class "
        "predicted MITM; N = validation rows of that class; same rows re-evaluated each round)")
    rows = []
    present_N = {c: runs[(SEEDS[0], "fedavg", "none")][1]["clean_cm"][c].sum() for c in range(len(CLASSES))}
    for a in ALGOS:
        for wname, (sc, rr) in list(WINDOWS.items()) + [("all full-strength rounds pooled (3 schedules)", (None, None))]:
            out(f"\n  [{a}] {wname}")
            for c, cname in enumerate(CLASSES):
                if c == MITM:
                    continue
                N = int(present_N[c])
                if N == 0:
                    out(f"    {cname:18s} NA (no validation support)")
                    continue
                per_seed = []
                for s in SEEDS:
                    pairs = ([(sc, r) for r in rr] if sc else [(x, r) for x in SCHEDS for r in full[x]])
                    kd = float(np.mean([runs[(s, a, x)][r]["drifted_cm"][c][MITM] for x, r in pairs]))
                    kc = float(np.mean([runs[(s, a, x)][r]["clean_cm"][c][MITM] for x, r in pairs]))
                    per_seed.append((kd, kc))
                    rows.append([a, wname, s, cname, N, kd, kc, kd / N, kc / N, (kd - kc) / N])
                if cname in ("Regular", "Video", "DoS", "Injection", "Unauth"):
                    out(f"    {cname:18s} N={N:<7d} drifted count/N per seed: " +
                        " ".join(f"{kd:.0f}/{N}" for kd, _ in per_seed))
                    out(f"    {'':18s} {'':9s} delta rate per seed:         " +
                        " ".join(f"{(kd - kc) / N:+.4f}" for kd, kc in per_seed))
    with open(od / "h2_counts_supplement.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["algorithm", "window", "seed", "class", "N", "drifted_mean_count", "clean_mean_count",
                    "drifted_rate", "clean_rate", "delta_rate"])
        w.writerows(rows)
    (od / "supplement.txt").write_text("\n".join(lines))
    print(f"\nWrote {od}/supplement.txt and h2_counts_supplement.csv")


if __name__ == "__main__":
    main()
