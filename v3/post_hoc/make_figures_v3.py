"""
POST-HOC DISPLAY (2026-11-08) for the UAV-02 v3 campaign. Not part of the frozen
code; adds no endpoint; reads only saved v3 outputs with the frozen loaders.

  fig2_v3_L1_td_vs_v2      per-seed L1 macro-F1: v2 arm (v2 eval), td arm (td eval),
                           and the same-checkpoint swaps; grey lines pair seeds
  fig3_v3_L2_L3            clean-control trajectories, td arm (seeds + mean) and v2 arm mean
  fig4_v3_dose             dose response on clean-trained none checkpoints (r15/30/45)
  fig5_v3_exposure         L1 and L3(r45) against exposed training-row share (k = 5, 8, 11, 15)
  fig6_v3_robustness       L1 and L3(r45) across all sudden-drift arms, with the +-0.01 band
"""
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.dont_write_bytecode = True
import analyze_v3 as A  # noqa: E402
import run_v3 as R  # noqa: E402

OD = HERE / "figures"
OD.mkdir(exist_ok=True)
COL = {"fedavg": "#0072B2", "fedprox": "#D55E00", "scaffold": "#009E73", "fednova": "#CC79A7", "fedadam": "#E69F00"}
MRK = {"fedavg": "o", "fedprox": "D", "scaffold": "s", "fednova": "^", "fedadam": "v"}
NAME = {"fedavg": "FedAvg", "fedprox": "FedProx", "scaffold": "SCAFFOLD", "fednova": "FedNova", "fedadam": "FedAdam"}
INK, MUTED, GRID = "#1a1a1a", "#666666", "#e3e3e3"
plt.rcParams.update({"font.size": 9, "axes.edgecolor": MUTED, "axes.labelcolor": INK, "xtick.color": INK,
                     "ytick.color": INK, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6, "axes.axisbelow": True,
                     "figure.dpi": 150, "savefig.bbox": "tight"})
SCH = A.SCH
SCHN = {"sudden": "Sudden", "gradual": "Gradual", "recurring": "Recurring"}


def save(fig, name):
    for ext in ("png", "pdf"):
        fig.savefig(OD / f"{name}.{ext}")
    plt.close(fig)


def L1(runs, arm, k, algo, s, tr, es="validation"):
    return A.l1(runs[(arm, k, algo, s)], s, tr, es, "macro_f1", arm)


def L3(runs, arm, k, algo, s, rnd=45, es="validation"):
    return A.gap(runs[(arm, k, algo, s)], runs[(A.none_ref(arm), k, algo, "none")], rnd, es, "macro_f1")


def fig2(runs):
    cols = [("main_v2", "v2", "v2 arm\neval v2"), ("main_td", "td", "td arm\neval td"),
            ("main_td", "v2", "td arm\neval v2"), ("main_v2", "td", "v2 arm\neval td")]
    fig, axes = plt.subplots(2, 3, figsize=(9.2, 5.4), sharey=True)
    for i, algo in enumerate(("fedavg", "fedprox")):
        for j, s in enumerate(SCH):
            ax = axes[i, j]
            vals = [[L1(runs, arm, k, algo, s, tr) for k in R.SEEDS10] for arm, tr, _ in cols]
            for k in range(10):
                ax.plot([0, 1], [vals[0][k], vals[1][k]], color="#b0b0b0", lw=0.7, zorder=1)
                ax.plot([2, 3], [vals[2][k], vals[3][k]], color="#d0d0d0", lw=0.6, zorder=1)
            for x, v in enumerate(vals):
                face = COL[algo] if x < 2 else "white"
                ax.scatter([x] * 10, v, s=24, facecolor=face, edgecolor=COL[algo], marker=MRK[algo],
                           linewidth=0.9, zorder=3)
                ax.hlines(np.mean(v), x - 0.22, x + 0.22, color=INK, lw=1.6, zorder=4)
            ax.axhline(0, color=MUTED, lw=0.8)
            ax.axvline(1.5, color=GRID, lw=1.0)
            ax.set_xticks(range(4), [c[2] for c in cols], fontsize=7)
            if i == 0:
                ax.set_title(SCHN[s])
            if j == 0:
                ax.set_ylabel(f"{NAME[algo]}\nL1 Δ macro-F1")
    save(fig, "fig2_v3_L1_td_vs_v2")


def fig3(runs):
    fig, axes = plt.subplots(2, 3, figsize=(9.2, 5.0), sharex=True, sharey=True)
    rounds = list(range(1, 46))
    for i, algo in enumerate(("fedavg", "fedprox")):
        for j, s in enumerate(SCH):
            ax = axes[i, j]
            ref = R.SEEDS10
            exp = [r for r in rounds if runs[("main_td", ref[0], algo, s)][r][("validation", "clean")][0] > 0]
            for lo, hi in _runs(exp):
                ax.axvspan(lo - 0.5, hi + 0.5, color="#f0e6d2", lw=0)
            g = np.array([[A.gap(runs[("main_td", k, algo, s)], runs[("main_none", k, algo, "none")], r,
                                 "validation", "macro_f1") for r in rounds] for k in ref])
            gv = np.array([[A.gap(runs[("main_v2", k, algo, s)], runs[("main_none", k, algo, "none")], r,
                                  "validation", "macro_f1") for r in rounds] for k in ref])
            for row in g:
                ax.plot(rounds, row, color=COL[algo], lw=0.5, alpha=0.25)
            ax.plot(rounds, g.mean(0), color=COL[algo], lw=1.8, label="td arm (mean)")
            ax.plot(rounds, gv.mean(0), color=INK, lw=1.1, ls="--", label="v2 arm (mean)")
            ax.axhline(0, color=MUTED, lw=0.8)
            ax.axhspan(-0.01, 0.01, color="#dddddd", alpha=0.35, lw=0)
            if i == 0:
                ax.set_title(SCHN[s])
            if j == 0:
                ax.set_ylabel(f"{NAME[algo]}\nclean Δ macro-F1 vs none")
            if i == 1:
                ax.set_xlabel("Round")
    axes[0, 0].legend(frameon=False, fontsize=7, loc="lower left")
    save(fig, "fig3_v3_L2_L3")


def _runs(rs):
    out = []
    for r in rs:
        if out and r == out[-1][1] + 1:
            out[-1][1] = r
        else:
            out.append([r, r])
    return out


def fig4(runs, probes):
    fig, axes = plt.subplots(1, 2, figsize=(8.4, 3.2), sharey=True)
    for ax, algo in zip(axes, ("fedavg", "fedprox")):
        for tr, ls in (("td", "-"), ("v2", "--")):
            for rnd, alpha in ((15, 0.45), (30, 0.7), (45, 1.0)):
                ys = []
                for st in (0.25, 0.5, 0.75, 1.0):
                    v = []
                    for k in R.SEEDS10:
                        rows = probes[("main_none", k, algo, "none")]
                        cl = runs[("main_none", k, algo, "none")][rnd][("validation", "clean")][1]
                        dr = [r for r in rows if int(r["round"]) == rnd and r["transform"] == tr
                              and r["eval_set"] == "validation" and abs(float(r["strength"]) - st) < 1e-9]
                        if dr:
                            v.append(float(dr[0]["macro_f1"]) - cl)
                    ys.append(np.mean(v))
                ax.plot([0.25, 0.5, 0.75, 1.0], ys, ls=ls, marker="o", ms=3, color=COL[algo], alpha=alpha,
                        label=f"{tr}, round {rnd}")
        ax.axhline(0, color=MUTED, lw=0.8)
        ax.set_title(NAME[algo])
        ax.set_xlabel("Strength s (evaluation only)")
    axes[0].set_ylabel("Δ macro-F1 (clean-trained none checkpoints)")
    axes[1].legend(frameon=False, fontsize=7, ncol=2)
    save(fig, "fig4_v3_dose")


def fig5(runs):
    arms = {5: "main_td", 8: "exp_k8", 11: "exp_k11", 15: "exp_k15"}
    share = {5: 0.174, 8: 0.281, 11: 0.399, 15: 1.0}
    fig, axes = plt.subplots(1, 2, figsize=(8.4, 3.2))
    for algo, dx in (("fedavg", -0.012), ("fedprox", 0.012)):
        for ax, f in ((axes[0], lambda arm, k: L1(runs, arm, k, algo, "sudden", "td")),
                      (axes[1], lambda arm, k: L3(runs, arm, k, algo, "sudden"))):
            means = []
            for kk, arm in arms.items():
                v = [f(arm, k) for k in R.SEEDS5]
                ax.scatter([share[kk] + dx] * 5, v, s=18, color=COL[algo], marker=MRK[algo], alpha=0.6,
                           edgecolor="white", linewidth=0.6)
                means.append(np.mean(v))
            ax.plot([share[k] + dx for k in arms], means, color=COL[algo], lw=1.6, label=NAME[algo])
    axes[0].set_ylabel("L1 Δ macro-F1 (td, sudden)")
    axes[1].set_ylabel("L3 clean Δ macro-F1 at round 45")
    axes[1].axhspan(-0.01, 0.01, color="#dddddd", alpha=0.4, lw=0)
    for ax in axes:
        ax.axhline(0, color=MUTED, lw=0.8)
        ax.set_xlabel("Exposed share of training rows (k = 5, 8, 11, 15)")
    axes[0].legend(frameon=False, fontsize=7)
    save(fig, "fig5_v3_exposure")


def fig6(runs):
    rows = [("main_td", "fedavg", "validation", "Main (α=0.5, 128-64)"), ("main_td", "fedprox", "validation", ""),
            ("alpha_0.1", "fedavg", "validation", "α = 0.1"), ("alpha_0.1", "fedprox", "validation", ""),
            ("alpha_2", "fedavg", "validation", "α = 2"), ("alpha_2", "fedprox", "validation", ""),
            ("alpha_100", "fedavg", "validation", "α = 100"), ("alpha_100", "fedprox", "validation", ""),
            ("arch_wide", "fedavg", "validation", "MLP 256-128-64"), ("arch_wide", "fedprox", "validation", ""),
            ("partial10", "fedavg", "validation", "10 of 15 clients/round"), ("partial10", "fedprox", "validation", ""),
            ("algo_scaffold", "scaffold", "validation", "SCAFFOLD"), ("algo_fednova", "fednova", "validation", "FedNova"),
            ("algo_fedadam", "fedadam", "validation", "FedAdam"),
            ("fresh", "fedavg", "validation", "Fresh arm, validation"), ("fresh", "fedprox", "validation", ""),
            ("fresh", "fedavg", "fresh", "Fresh arm, fresh sessions"), ("fresh", "fedprox", "fresh", ""),
            ("cic", "fedavg", "validation", "CICIoT2023"), ("cic", "fedprox", "validation", "")]
    fig, axes = plt.subplots(1, 2, figsize=(9.2, 6.2), sharey=True)
    ylab = []
    for y, (arm, algo, es, lab) in enumerate(rows):
        seeds = R.SEEDS5
        for ax, f in ((axes[0], lambda k: L1(runs, arm, k, algo, "sudden", "td", es)),
                      (axes[1], lambda k: L3(runs, arm, k, algo, "sudden", 45, es))):
            v = np.array([f(k) for k in seeds])
            S = A.summ(v)
            ax.scatter(v, [y] * len(v), s=10, color=COL[algo], alpha=0.35, marker=MRK[algo], lw=0)
            ax.errorbar(S["mean"], y, xerr=[[S["mean"] - S["ci95"][0]], [S["ci95"][1] - S["mean"]]],
                        fmt=MRK[algo], color=COL[algo], ms=5, capsize=2, lw=1.1)
        ylab.append(lab if lab else "")
    for ax in axes:
        ax.axvline(0, color=MUTED, lw=0.8)
        ax.set_yticks(range(len(rows)), ylab, fontsize=7)
    axes[0].invert_yaxis()
    axes[1].axvspan(-0.01, 0.01, color="#dddddd", alpha=0.4, lw=0)
    axes[0].set_xlabel("L1 Δ macro-F1 (td, sudden; seeds 131-175)")
    axes[1].set_xlabel("L3 clean Δ macro-F1 at round 45")
    handles = [plt.Line2D([], [], color=COL[a], marker=MRK[a], ls="", label=NAME[a]) for a in COL]
    axes[1].legend(handles=handles, frameon=False, fontsize=7, loc="lower right")
    save(fig, "fig6_v3_robustness")


def main():
    runs, probes, _ = A.load(Path(R.RESULTS))
    fig2(runs)
    fig3(runs)
    fig4(runs, probes)
    fig5(runs)
    fig6(runs)
    print("figures written to", OD)


if __name__ == "__main__":
    main()
