"""
UAV-02 v3 POST-HOC analyses (written 2026-11-08, after the frozen
analyze_v3.py had been run once and its output inspected). Not part of the
frozen protocol. Reads results_v3/*.csv with the frozen loaders/estimands.

  A. Same-checkpoint swap: per seed, L1(td) - L1(v2) on the SAME checkpoints
     (main_td and main_v2 arms; both transforms are evaluated every round).
     Isolates the evaluation-input transform with the model state fixed.
  B. Arm vs arm: per seed, L1 of main_td under td minus L1 of main_v2 under v2.
     Training and evaluation transforms both differ; seeds matched.
     (Mean of B equals the difference of the frozen arm means.)
  C. Clean macro-F1 level and between-seed SD (none runs), for context of the
     +-0.01 equivalence margin.
  D. Class-recall L1 means for main_td and main_v2, and the L1 swap per class.
"""
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import analyze_v3 as A  # noqa: E402
import run_v3 as R  # noqa: E402

OUT = []


def out(s=""):
    OUT.append(s)
    print(s)


def main():
    runs, probes, h1 = A.load(Path(R.RESULTS))
    res = {}
    out("POST-HOC (not frozen). Seeds 131..230 (10 per combination).")
    out("\nA. same-checkpoint swap L1(td) - L1(v2), macro-F1, validation")
    for arm in ("main_td", "main_v2"):
        for algo in ("fedavg", "fedprox"):
            for s in A.SCH:
                v = [A.l1(runs[(arm, k, algo, s)], s, "td", "validation", "macro_f1", arm)
                     - A.l1(runs[(arm, k, algo, s)], s, "v2", "validation", "macro_f1", arm)
                     for k in R.SEEDS10]
                S = A.summ(v)
                res[f"A_{arm}_{algo}_{s}"] = S
                out(f"  {arm:8} {algo:7} {s:9} " + A.fmt(S).replace("neg", "td-less-negative(pos)") + f" pos {S['pos']}/10")
    out("\nB. arm vs arm: L1 main_td(td) - L1 main_v2(v2), macro-F1, validation")
    for algo in ("fedavg", "fedprox"):
        for s in A.SCH:
            v = [A.l1(runs[("main_td", k, algo, s)], s, "td", "validation", "macro_f1", "main_td")
                 - A.l1(runs[("main_v2", k, algo, s)], s, "v2", "validation", "macro_f1", "main_v2")
                 for k in R.SEEDS10]
            S = A.summ(v)
            res[f"B_{algo}_{s}"] = S
            out(f"  {algo:7} {s:9} " + A.fmt(S) + f" pos {S['pos']}/10")
    out("\nC. clean macro-F1 of none runs (validation)")
    for arm, seeds in (("main_none", R.SEEDS10), ("fresh", R.SEEDS5), ("alpha_0.1", R.SEEDS5),
                       ("alpha_2", R.SEEDS5), ("alpha_100", R.SEEDS5), ("cic", R.SEEDS5)):
        for algo in ("fedavg", "fedprox"):
            for rnd in (15, 30, 45):
                v = [runs[(arm, k, algo, "none")][rnd][("validation", "clean")][1] for k in seeds]
                S = A.summ(v)
                res[f"C_{arm}_{algo}_r{rnd}"] = S
                out(f"  {arm:10} {algo:7} r{rnd}: mean={S['mean']:.4f} sd={S['sd']:.4f} range=[{S['min']:.4f},{S['max']:.4f}]")
    for arm in ("fresh",):
        for algo in ("fedavg", "fedprox"):
            v = [runs[(arm, k, algo, "none")][45][("fresh", "clean")][1] for k in R.SEEDS5]
            S = A.summ(v)
            res[f"C_{arm}_{algo}_r45_freshset"] = S
            out(f"  {arm:10} {algo:7} r45 on fresh sessions: mean={S['mean']:.4f} sd={S['sd']:.4f}")
    out("\nD. class-recall L1 (mean over seeds), validation")
    for arm, tr in (("main_td", "td"), ("main_v2", "v2"), ("main_td", "v2"), ("main_v2", "td")):
        for algo in ("fedavg", "fedprox"):
            for s in A.SCH:
                cls = [A.l1_classes(runs[(arm, k, algo, s)], s, tr, "validation") for k in R.SEEDS10]
                m = {c: float(np.mean([d[c] for d in cls])) for c in cls[0]}
                res[f"D_{arm}_{tr}_{algo}_{s}"] = m
                out(f"  {arm:8} eval {tr:3} {algo:7} {s:9} " + ", ".join(
                    f"{c}:{m[c]:+.3f}" for c in ("Injection", "Video", "Unauth", "MITM", "Ip Spoofing", "Regular")))
    (HERE / "posthoc_v3.txt").write_text("\n".join(OUT) + "\n")
    (HERE / "posthoc_v3.json").write_text(json.dumps(res, indent=1, default=float))


if __name__ == "__main__":
    main()
