"""
Figure templates for UAV-02 (DISPLAY ONLY; not part of the frozen code set; no
new endpoint). Five figures, no more:
  1 frozen drift schedules            (no results needed)
  2 PRIMARY L1 paired seed points     (delta macro-F1, delta Regular recall)
  3 L2/L3 trajectories                (schedule minus matched `none`, clean validation)
  4 H1 susceptibility                 (margin collapse under strength=1, `none` r15 vs r30)
  5 H2 class-specific confusion       (Regular / Video / DoS -> MITM, window 1 vs 2)
Encoding: colour AND marker shape identify the algorithm (CVD-safe pair);
individual seeds are always drawn, means are secondary.
"""
import argparse
import csv
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from analyze_confirmatory import load_run, structure, SEEDS, ALGOS, SCHEDS, CLASSES, MITM  # noqa: E402
import drift as drift_mod  # noqa: E402

COL = {"fedavg": "#0072B2", "fedprox": "#D55E00"}
MRK = {"fedavg": "o", "fedprox": "D"}
NAME = {"fedavg": "FedAvg", "fedprox": "FedProx"}
INK, MUTED, GRID = "#1a1a1a", "#666666", "#e3e3e3"
plt.rcParams.update({"font.size": 9, "axes.edgecolor": MUTED, "axes.labelcolor": INK, "xtick.color": INK,
                     "ytick.color": INK, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6, "axes.axisbelow": True,
                     "figure.dpi": 150, "savefig.bbox": "tight"})


def save(fig, od, name):
    for ext in ("png", "pdf"):
        fig.savefig(od / f"{name}.{ext}")
    plt.close(fig)


def fig1(od):
    fig, axes = plt.subplots(1, 4, figsize=(11, 2.3), sharey=True)
    r = np.arange(1, drift_mod.NUM_ROUNDS + 1)
    for ax, sc in zip(axes, ["none", "sudden", "gradual", "recurring"]):
        ax.step(r, [drift_mod.SCHEDULES[sc](x) for x in r], where="post", color=INK, lw=1.6)
        ax.set_title(sc, fontsize=9, color=INK, loc="left")
        ax.set_xlabel("round")
        ax.set_ylim(-0.05, 1.1)
    axes[0].set_ylabel("drift strength")
    save(fig, od, "fig1_schedules")


def fig2(runs, full, od):
    fig, axes = plt.subplots(2, 3, figsize=(9, 5.2), sharex=True)
    for j, sc in enumerate(SCHEDS):
        for i, (key, lab) in enumerate((("macro_f1", "Δ macro-F1"), ("regular_recall", "Δ Regular recall"))):
            ax = axes[i, j]
            vals = {a: [np.mean([runs[(s, a, sc)][r][f"delta_{key}"] for r in full[sc]]) for s in SEEDS] for a in ALGOS}
            for k in range(len(SEEDS)):
                ax.plot([0, 1], [vals["fedavg"][k], vals["fedprox"][k]], color="#b0b0b0", lw=0.8, zorder=1)
            for x, a in enumerate(ALGOS):
                ax.scatter([x] * len(SEEDS), vals[a], s=28, color=COL[a], marker=MRK[a], zorder=3,
                           edgecolor="white", linewidth=0.8)
                ax.hlines(np.mean(vals[a]), x - 0.18, x + 0.18, color=INK, lw=1.6, zorder=4)
            ax.axhline(0, color=MUTED, lw=0.8)
            ax.set_xticks([0, 1], [NAME[a] for a in ALGOS])
            ax.set_xlim(-0.5, 1.5)
            if j == 0:
                ax.set_ylabel(lab)
            if i == 0:
                ax.set_title(sc, fontsize=9, loc="left")
    fig.text(0.01, -0.01, "Each point = one seed (mean over full-strength rounds); grey lines pair the same seed; bar = mean.",
             fontsize=8, color=MUTED)
    save(fig, od, "fig2_primary_L1")


def fig3(runs, od):
    fig, axes = plt.subplots(2, 3, figsize=(10, 5.2), sharex=True)
    rounds = sorted(runs[(SEEDS[0], "fedavg", "none")])
    for j, sc in enumerate(SCHEDS):
        exp = [r for r in rounds if runs[(SEEDS[0], "fedavg", sc)][r]["drift_strength"] > 0]
        for i, (key, lab) in enumerate((("macro_f1", "schedule − none: clean macro-F1"),
                                        ("regular_recall", "schedule − none: clean Regular recall"))):
            ax = axes[i, j]
            for lo, hi in _runs_of(exp):
                ax.axvspan(lo - 0.5, hi + 0.5, color="#f0e6d2", lw=0)
            for a in ALGOS:
                g = np.array([[runs[(s, a, sc)][r][f"clean_{key}"] - runs[(s, a, "none")][r][f"clean_{key}"]
                               for r in rounds] for s in SEEDS])
                for row in g:
                    ax.plot(rounds, row, color=COL[a], lw=0.6, alpha=0.30)
                ax.plot(rounds, g.mean(0), color=COL[a], lw=1.8, label=NAME[a])
            ax.axhline(0, color=MUTED, lw=0.8)
            if i == 1:
                ax.set_xlabel("round")
            if j == 0:
                ax.set_ylabel(lab, fontsize=8)
            if i == 0:
                ax.set_title(sc, fontsize=9, loc="left")
            if i == 0 and j == 0:
                ax.legend(frameon=False, fontsize=8)
    fig.text(0.01, -0.01, "Thin = individual seeds, thick = mean. Shaded = exposure (strength > 0): L2 inside, L3 (RecoveryGap) outside.",
             fontsize=8, color=MUTED)
    save(fig, od, "fig3_L2_L3_trajectories")


def _runs_of(rs):
    out, cur = [], None
    for r in rs:
        cur = [r, r] if cur is None or r != cur[1] + 1 else [cur[0], r]
        if cur[1] == r and (not out or out[-1][0] != cur[0]):
            out.append(cur)
        else:
            out[-1] = cur
    return [tuple(x) for x in out]


def fig4(rd, od):
    fig, axes = plt.subplots(1, 2, figsize=(7, 3.3), sharey=True)
    for ax, a in zip(axes, ALGOS):
        d = {}
        for s in SEEDS:
            for r in csv.DictReader(open(rd / f"seed{s}_{a}_none_h1_margins.csv")):
                d[(s, int(r["round"]))] = float(r["margin_drop"])
        for s in SEEDS:
            ax.plot([0, 1], [d[(s, 15)], d[(s, 30)]], color=COL[a], lw=0.9, alpha=0.6)
            ax.scatter([0, 1], [d[(s, 15)], d[(s, 30)]], s=26, color=COL[a], marker=MRK[a], zorder=3,
                       edgecolor="white", linewidth=0.8)
        ax.plot([0, 1], [np.mean([d[(s, 15)] for s in SEEDS]), np.mean([d[(s, 30)] for s in SEEDS])],
                color=INK, lw=1.8, zorder=4)
        ax.set_xticks([0, 1], ["round 15", "round 30"])
        ax.set_xlim(-0.4, 1.4)
        ax.set_title(NAME[a], fontsize=9, loc="left")
    axes[0].set_ylabel("margin collapse under strength=1\n(logit Regular − MITM, `none` models)")
    save(fig, od, "fig4_H1_susceptibility")


def fig5(runs, full, od):
    classes = ["Regular", "Video", "DoS"]
    wins = {"window 1 (r15–21)": range(15, 22), "window 2 (r30–36)": range(30, 37)}
    N = {c: int(runs[(SEEDS[0], "fedavg", "none")][1]["clean_cm"][CLASSES.index(c)].sum()) for c in classes}
    fig, axes = plt.subplots(1, 2, figsize=(9, 3.5), sharey=True)
    for ax, a in zip(axes, ALGOS):
        for ci, c in enumerate(classes):
            ci_ = CLASSES.index(c)
            for wi, (wn, rr) in enumerate(wins.items()):
                v = []
                for s in SEEDS:
                    dd = np.mean([runs[(s, a, "recurring")][r]["drifted_cm"][ci_][MITM] / runs[(s, a, "recurring")][r]["drifted_cm"][ci_].sum()
                                  - runs[(s, a, "recurring")][r]["clean_cm"][ci_][MITM] / runs[(s, a, "recurring")][r]["clean_cm"][ci_].sum()
                                  for r in rr])
                    v.append(dd)
                x = ci * 3 + wi
                ax.scatter([x] * len(v), v, s=26, color=COL[a], marker=MRK[a], zorder=3, edgecolor="white",
                           linewidth=0.8, alpha=0.95 if wi else 0.55)
                ax.hlines(np.mean(v), x - 0.25, x + 0.25, color=INK, lw=1.6, zorder=4)
        ax.set_xticks([0.5, 3.5, 6.5], [f"{c}→MITM\nN={N[c]:,}" for c in classes])
        ax.set_title(NAME[a], fontsize=9, loc="left")
        ax.axhline(0, color=MUTED, lw=0.8)
    axes[0].set_ylabel("Δ rate (drifted − clean)")
    fig.text(0.01, -0.09, "Recurring schedule. Left point of each pair = window 1 (faded), right = window 2. Points = seeds, bar = mean. N = validation rows of the true class.",
             fontsize=8, color=MUTED)
    save(fig, od, "fig5_H2_class_specific")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--results-dir", default=str(HERE.parent / "results_drift_confirmatory"))
    ap.add_argument("--out-dir", default=None)
    args = ap.parse_args()
    rd = Path(args.results_dir)
    od = Path(args.out_dir) if args.out_dir else rd / "figures"
    od.mkdir(parents=True, exist_ok=True)
    fig1(od)
    runs = {(s, a, sc): load_run(rd, s, a, sc) for s in SEEDS for a in ALGOS for sc in ["none"] + SCHEDS}
    if any(v is None for v in runs.values()):
        raise SystemExit("figures 2-5 need all 5 seeds complete; figure 1 was written")
    full = {sc: structure(runs[(SEEDS[0], "fedavg", sc)])[1] for sc in SCHEDS}
    fig2(runs, full, od)
    fig3(runs, od)
    fig4(rd, od)
    fig5(runs, full, od)
    print(f"figures written to {od}")


if __name__ == "__main__":
    main()
