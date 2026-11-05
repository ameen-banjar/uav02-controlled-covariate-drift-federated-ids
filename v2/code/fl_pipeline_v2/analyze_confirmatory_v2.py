"""
UAV-02 v2 (CORRECTED) CONFIRMATORY analysis. Frozen together with v2/DESIGN_V2.md
before any v2 execution. Same estimands and code as the v1 analysis, with the
v2 changes listed in DESIGN_V2.md Section 4 (primary gate on macro-F1 only;
pre-specified predictions for Regular recall, H1 and H2; class-level
post-removal residuals added).

Three layers are kept strictly separate (they answer different questions and
were conflated in the calibration pilot's first recovery metric):
  L1 Immediate drift effect   : SAME model state, drifted vs clean validation
                                (within-run counterfactual). PRIMARY endpoint.
  L2 Training-history effect  : schedule-trained model vs matched `none`
                                control, both on CLEAN validation, during the
                                exposure period (strength > 0).            SECONDARY
  L3 Recovery                 : same formula as L2 but after strength has
                                returned to 0 (RecoveryGap).               SECONDARY
Plus H1 (susceptibility grows with training stage without drift exposure)
and H2 (class-specific MITM confusion): secondary PROSPECTIVE hypotheses
that were discovered in the calibration pilot -- never primary endpoints.

The >=4/5-seeds rule is a DIRECTIONAL REPLICATION GATE, not a significance
test. Effect sizes and per-seed distributions are always reported next to it.
Intervals are descriptive t-intervals over the 5 seeds; no p-values.
"""
import argparse
import csv
import json
import math
from pathlib import Path

import numpy as np
from scipy import stats

HERE = Path(__file__).resolve().parent
SEEDS = [76, 87, 98, 109, 120]
ALGOS = ["fedavg", "fedprox"]
SCHEDS = ["sudden", "gradual", "recurring"]
CLASSES = ["DoS", "Injection", "Ip Spoofing", "MITM", "Manipulation",
           "Password Cracking", "Regular", "Replay", "Unauth", "Video"]
MITM = CLASSES.index("MITM")
GATE_MIN_SEEDS = 4
H1_EARLY, H1_LATE = 15, 30
H2_DOS_MAX, H2_ANY_MIN, H2_MONITORED_MIN = 0.01, 0.10, 0.05
FULL_STRENGTH = 1.0 - 1e-9
METRICS = [("macro_f1", "macro-F1"), ("regular_recall", "Regular recall")]
PRIMARY_GATE_METRICS = ["macro_f1"]          # v2: gate on macro-F1 only (DESIGN_V2.md 4.1)
REGREC_PRED_ABS = 0.005                      # v2 prediction P-R: |mean Regular-recall L1| < 0.005

LINES = []


def out(s=""):
    LINES.append(s)
    print(s)


def summ(vals):
    v = np.asarray(vals, dtype=float)
    n = len(v)
    mean = float(v.mean())
    sd = float(v.std(ddof=1)) if n > 1 else float("nan")
    half = float(stats.t.ppf(0.975, n - 1) * sd / math.sqrt(n)) if n > 1 else float("nan")
    return dict(n=n, mean=mean, sd=sd, min=float(v.min()), max=float(v.max()),
                ci_lo=mean - half, ci_hi=mean + half,
                dz=(mean / sd) if sd and sd > 1e-12 else float("nan"))


def fmt(s):
    return (f"mean={s['mean']:+.4f} sd={s['sd']:.4f} range=[{s['min']:+.4f},{s['max']:+.4f}] "
            f"95%tInt=[{s['ci_lo']:+.4f},{s['ci_hi']:+.4f}] d_z={s['dz']:+.2f}")


def load_run(results_dir, seed, algo, sched):
    p = results_dir / f"seed{seed}_{algo}_{sched}_rounds.csv"
    if not p.exists():
        return None
    rows = {}
    for r in csv.DictReader(open(p)):
        rr = {k: float(r[k]) for k in ["drift_strength", "clean_macro_f1", "drifted_macro_f1", "delta_macro_f1",
                                       "clean_regular_recall", "drifted_regular_recall", "delta_regular_recall"]}
        rr["clean_recall"] = json.loads(r["clean_per_class_recall_json"])
        rr["drifted_recall"] = json.loads(r["drifted_per_class_recall_json"])
        rr["clean_cm"] = np.array(json.loads(r["clean_confusion_matrix_json"]), dtype=float)
        rr["drifted_cm"] = np.array(json.loads(r["drifted_confusion_matrix_json"]), dtype=float)
        rows[int(r["round"])] = rr
    return rows


def structure(runs_ref):
    """Exposure / full-strength rounds and recovery intervals, derived from the logged schedule strength."""
    rounds = sorted(runs_ref)
    exposure = [r for r in rounds if runs_ref[r]["drift_strength"] > 0]
    full = [r for r in rounds if runs_ref[r]["drift_strength"] >= FULL_STRENGTH]
    intervals, cur, seen = [], None, False
    for r in rounds:
        s = runs_ref[r]["drift_strength"]
        if s > 0:
            seen = True
            if cur:
                intervals.append(tuple(cur))
                cur = None
        elif seen:
            cur = [r, r] if cur is None else [cur[0], r]
    if cur:
        intervals.append(tuple(cur))
    return exposure, full, intervals


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--results-dir", default=str(HERE / "results_v2_confirmatory"))
    ap.add_argument("--out-dir", default=None)
    ap.add_argument("--allow-partial", action="store_true",
                    help="INTERIM/testing only: analyze whatever seeds are complete; gates are not evaluated")
    args = ap.parse_args()
    rd = Path(args.results_dir)
    od = Path(args.out_dir) if args.out_dir else rd / "analysis"
    od.mkdir(parents=True, exist_ok=True)

    runs, missing = {}, []
    for seed in SEEDS:
        for a in ALGOS:
            for sc in ["none"] + SCHEDS:
                r = load_run(rd, seed, a, sc)
                if r is None:
                    missing.append(f"seed{seed}_{a}_{sc}")
                else:
                    runs[(seed, a, sc)] = r
    if missing and not args.allow_partial:
        raise SystemExit(f"Incomplete: {len(missing)} runs missing (e.g. {missing[:3]}). "
                         f"The frozen analysis requires all {len(SEEDS)} seeds. Use --allow-partial for interim looks only.")
    seeds_ok = [s for s in SEEDS if all((s, a, sc) in runs for a in ALGOS for sc in ["none"] + SCHEDS)]
    partial = len(seeds_ok) < len(SEEDS)
    gates = {}
    if partial:
        out(f"*** INTERIM / PARTIAL ({len(seeds_ok)}/{len(SEEDS)} seeds complete: {seeds_ok}) -- NOT the frozen analysis; gates not evaluated ***")
    if not seeds_ok:
        raise SystemExit("no complete seed")

    def gate(count, n):
        return None if partial else (count >= GATE_MIN_SEEDS)

    present = [c for c in range(len(CLASSES))
               if runs[(seeds_ok[0], "fedavg", "none")][1]["clean_cm"][c].sum() > 0]
    out(f"Seeds analysed: {seeds_ok} | present validation classes: {[CLASSES[c] for c in present]}")
    struct = {}
    for sc in SCHEDS:
        ref = runs[(seeds_ok[0], "fedavg", sc)]
        struct[sc] = structure(ref)
        for s in seeds_ok:
            for a in ALGOS:
                assert [runs[(s, a, sc)][r]["drift_strength"] for r in sorted(ref)] == \
                       [ref[r]["drift_strength"] for r in sorted(ref)], "schedule strength differs across runs"
        exp, full, ivs = struct[sc]
        out(f"  {sc}: exposure rounds {exp[0]}-{exp[-1]}, full-strength rounds {full[0]}-{full[-1]} (n={len(full)}), recovery intervals {ivs}")

    # ---------------------------------------------------------------- L1 PRIMARY
    out("\n" + "=" * 100 + "\nL1  PRIMARY -- controlled drift response (drifted minus clean, same model state, mean over full-strength rounds)\n" + "=" * 100)
    out("Negative = drift hurts. v2 gate (directional replication, NOT significance): macro-F1 negative in >=4/5 seeds. "
        f"v2 prediction P-R: |mean Regular-recall response| < {REGREC_PRED_ABS}.")
    for a in ALGOS:
        for sc in SCHEDS:
            _, full, _ = struct[sc]
            per = {}
            for key, label in METRICS:
                per[key] = [float(np.mean([runs[(s, a, sc)][r][f"delta_{key}"] for r in full])) for s in seeds_ok]
            out(f"\n[{a}/{sc}]")
            counts = {}
            for key, label in METRICS:
                sm = summ(per[key])
                counts[key] = sum(v < 0 for v in per[key])
                out(f"  {label:15s} {fmt(sm)}  negative in {counts[key]}/{len(seeds_ok)} seeds")
                out(f"  {'':15s} per-seed: " + ", ".join(f"{s}:{v:+.4f}" for s, v in zip(seeds_ok, per[key])))
            ok = all(counts[k] >= GATE_MIN_SEEDS for k in PRIMARY_GATE_METRICS)
            gates[f"P_{a}_{sc}"] = None if partial else ok
            pr = abs(float(np.mean(per["regular_recall"]))) < REGREC_PRED_ABS
            gates[f"PR_{a}_{sc}"] = None if partial else pr
            out(f"  prediction P-R {a}/{sc}: |mean Regular-recall response| = {abs(float(np.mean(per['regular_recall']))):.4f} -> {'HOLDS' if pr else 'DOES NOT HOLD'}")
            out(f"  PRIMARY gate {a}/{sc}: {'PASS' if ok else 'FAIL'}" if not partial else "  gate: n/a (partial)")
            prof = {CLASSES[c]: float(np.mean([np.mean([runs[(s, a, sc)][r]["drifted_recall"][CLASSES[c]] -
                                                          runs[(s, a, sc)][r]["clean_recall"][CLASSES[c]]
                                                          for r in full]) for s in seeds_ok])) for c in present}
            out("  class-level recall response (mean over seeds): " + ", ".join(f"{k}:{v:+.3f}" for k, v in prof.items()))
    with open(od / "primary_by_round.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["algorithm", "schedule", "round", "strength", "mean_delta_macro_f1", "sd_delta_macro_f1",
                    "mean_delta_regular_recall", "sd_delta_regular_recall"])
        for a in ALGOS:
            for sc in SCHEDS:
                for r in sorted(runs[(seeds_ok[0], a, sc)]):
                    dm = [runs[(s, a, sc)][r]["delta_macro_f1"] for s in seeds_ok]
                    dr = [runs[(s, a, sc)][r]["delta_regular_recall"] for s in seeds_ok]
                    w.writerow([a, sc, r, runs[(seeds_ok[0], a, sc)][r]["drift_strength"], np.mean(dm),
                                np.std(dm, ddof=1) if len(dm) > 1 else "", np.mean(dr), np.std(dr, ddof=1) if len(dr) > 1 else ""])

    # ---------------------------------------------------------------- L2 SECONDARY
    out("\n" + "=" * 100 + "\nL2  SECONDARY -- training-history effect: schedule-trained CLEAN minus matched `none` CLEAN, mean over exposure rounds\n" + "=" * 100)
    for a in ALGOS:
        for sc in SCHEDS:
            exp, _, _ = struct[sc]
            out(f"\n[{a}/{sc}] exposure rounds {exp[0]}-{exp[-1]}")
            for key, label in METRICS:
                vals = [float(np.mean([runs[(s, a, sc)][r][f"clean_{key}"] - runs[(s, a, "none")][r][f"clean_{key}"]
                                       for r in exp])) for s in seeds_ok]
                out(f"  {label:15s} {fmt(summ(vals))}")
                out(f"  {'':15s} per-seed: " + ", ".join(f"{s}:{v:+.4f}" for s, v in zip(seeds_ok, vals)))

    # ---------------------------------------------------------------- L3 SECONDARY
    out("\n" + "=" * 100 + "\nL3  SECONDARY -- RecoveryGap_{m,r} = M^schedule_clean,r - M^none_clean,r, only inside strength==0 intervals after removal\n" + "=" * 100)
    out("Points per recovery interval [a,b]: immediate=a, +5=a+5 and +10=a+10 only if still inside the interval, residual=b (last clean round of the interval).")
    for a_ in ALGOS:
        for sc in SCHEDS:
            _, _, ivs = struct[sc]
            first_exp = struct[sc][0][0]
            for key, label in METRICS:
                pre = max([abs(runs[(s, a_, sc)][r][f"clean_{key}"] - runs[(s, a_, "none")][r][f"clean_{key}"])
                           for s in seeds_ok for r in runs[(s, a_, sc)] if r < first_exp] or [0.0])
                out(f"\n[{a_}/{sc}] {label}: pre-onset sanity max|gap| over rounds<{first_exp} = {pre:.6f} (expected ~0; trajectories identical before onset)")
                for (lo, hi) in ivs:
                    pts = [("immediate", lo)] + [(f"+{k}", lo + k) for k in (5, 10) if lo + k <= hi] + [("residual", hi)]
                    for name, r in pts:
                        vals = [runs[(s, a_, sc)][r][f"clean_{key}"] - runs[(s, a_, "none")][r][f"clean_{key}"] for s in seeds_ok]
                        out(f"  interval[{lo},{hi}] {name:9s}@r{r:<2d} {fmt(summ(vals))}")

    # ---------------------------------------------------------------- L3 class-level (v2 addition)
    out("\n" + "=" * 100 + "\nL3c SECONDARY (v2) -- class-level clean-recall residual at the last round of each post-removal interval (schedule minus matched none)\n" + "=" * 100)
    for a_ in ALGOS:
        for sc in SCHEDS:
            for (lo, hi) in struct[sc][2]:
                res = {CLASSES[c]: [runs[(s, a_, sc)][hi]["clean_recall"][CLASSES[c]] - runs[(s, a_, "none")][hi]["clean_recall"][CLASSES[c]]
                                    for s in seeds_ok] for c in present}
                out(f"[{a_}/{sc}] r{hi}: " + ", ".join(f"{k}:{np.mean(v):+.4f}(min {min(v):+.4f})" for k, v in res.items()))

    # ---------------------------------------------------------------- H1
    out("\n" + "=" * 100 + "\nH1 (secondary, prospective; discovered in pilot) -- same perturbation (strength=1) hurts more at later training stages, WITHOUT drift exposure\n" + "=" * 100)
    out(f"`none` checkpoints, Regular-true validation rows, margin=logit[Regular]-logit[MITM]; drop = margin(strength=1) - margin(clean). "
        f"Contrast S = drop(r{H1_LATE}) - drop(r{H1_EARLY}); S<0 means larger collapse later. Gate: S<0 in >=4/5 seeds in EACH algorithm.")
    h1_ok = True
    for a in ALGOS:
        drops = {}
        for s in seeds_ok:
            p = rd / f"seed{s}_{a}_none_h1_margins.csv"
            for r in csv.DictReader(open(p)):
                drops.setdefault(int(r["round"]), {})[s] = float(r["margin_drop"])
        d15 = [drops[H1_EARLY][s] for s in seeds_ok]
        d30 = [drops[H1_LATE][s] for s in seeds_ok]
        S = [b - c for b, c in zip(d30, d15)]
        cnt = sum(v < 0 for v in S)
        out(f"\n[{a}] drop@r{H1_EARLY}: {fmt(summ(d15))}\n[{a}] drop@r{H1_LATE}: {fmt(summ(d30))}\n[{a}] S: {fmt(summ(S))}  negative in {cnt}/{len(seeds_ok)} seeds")
        out(f"  per-seed S: " + ", ".join(f"{s}:{v:+.3f}" for s, v in zip(seeds_ok, S)))
        out("  descriptive dose-response (mean drop by round): " + ", ".join(f"r{r}:{np.mean(list(drops[r].values())):+.2f}" for r in sorted(drops)))
        h1_ok &= cnt >= GATE_MIN_SEEDS
    gates["H1"] = None if partial else h1_ok
    out(f"H1 directional replication: {'PASS' if h1_ok else 'FAIL'}" if not partial else "H1 gate: n/a (partial)")

    # ---------------------------------------------------------------- H2
    out("\n" + "=" * 100 + "\nH2 (secondary, prospective; discovered in pilot) -- class-specific drift response toward MITM\n" + "=" * 100)
    out(f"Delta(c->MITM) = drifted rate - clean rate for true class c, averaged over ALL full-strength rounds pooled across sudden/gradual/recurring (rounds weighted equally). "
        f"H2a: Delta(DoS)<{H2_DOS_MAX} AND max_c Delta>{H2_ANY_MIN}. H2b: Delta(Regular)>={H2_MONITORED_MIN} AND Delta(Video)>={H2_MONITORED_MIN}. Each: >=4/5 seeds, EACH algorithm.")
    h2a_ok = h2b_ok = True
    for a in ALGOS:
        per_seed = {}
        for s in seeds_ok:
            acc = {c: [] for c in present if c != MITM}
            for sc in SCHEDS:
                for r in struct[sc][1]:
                    run = runs[(s, a, sc)][r]
                    for c in acc:
                        rc, rd_ = run["clean_cm"][c], run["drifted_cm"][c]
                        acc[c].append(rd_[MITM] / rd_.sum() - rc[MITM] / rc.sum())
            per_seed[s] = {CLASSES[c]: float(np.mean(v)) for c, v in acc.items()}
        out(f"\n[{a}] mean Delta(class->MITM) over seeds: " +
            ", ".join(f"{k}:{np.mean([per_seed[s][k] for s in seeds_ok]):+.3f}" for k in per_seed[seeds_ok[0]]))
        for k in ("Regular", "Video", "DoS"):
            vals = [per_seed[s][k] for s in seeds_ok]
            out(f"  {k:8s}->MITM {fmt(summ(vals))}")
            out(f"  {'':8s}   per-seed: " + ", ".join(f"{s}:{v:+.3f}" for s, v in zip(seeds_ok, vals)))
        n_a = sum(per_seed[s]["DoS"] < H2_DOS_MAX and max(per_seed[s].values()) > H2_ANY_MIN for s in seeds_ok)
        n_b = sum(per_seed[s]["Regular"] >= H2_MONITORED_MIN and per_seed[s]["Video"] >= H2_MONITORED_MIN for s in seeds_ok)
        out(f"  H2a in {n_a}/{len(seeds_ok)} seeds | H2b in {n_b}/{len(seeds_ok)} seeds")
        h2a_ok &= n_a >= GATE_MIN_SEEDS
        h2b_ok &= n_b >= GATE_MIN_SEEDS
    gates["H2a"], gates["H2b"] = (None, None) if partial else (h2a_ok, h2b_ok)
    out(f"H2a: {'PASS' if h2a_ok else 'FAIL'} | H2b: {'PASS' if h2b_ok else 'FAIL'}" if not partial else "H2 gates: n/a (partial)")

    (od / "summary.txt").write_text("\n".join(LINES))
    (od / "gates.json").write_text(json.dumps({"partial": partial, "seeds": seeds_ok, "gates": gates}, indent=2))
    print(f"\nWrote {od}/summary.txt, gates.json, primary_by_round.csv")


if __name__ == "__main__":
    main()
