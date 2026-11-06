"""
POST-HOC DISPLAY (2026-11-06) for the UAV-02 v2 confirmatory campaign. Not part of
the frozen v2 code set; adds no endpoint and reads only saved v2 outputs.

  Figure 2  L1 paired seed points (delta macro-F1, delta Regular recall)
  Figure 3  L2/L3 clean trajectories (schedule minus matched `none`)
  Figure 4  H1: margin drop at every saved `none` checkpoint; r15 and r30 marked
  Figure 5  H2 pooled endpoint: delta(class -> MITM) over all full-strength rounds of
            all three schedules (rounds weighted equally), per seed, with the frozen
            0.05 and 0.10 thresholds
Figure 1 (schedules) is unchanged from v1 and is not redrawn.
Also writes h2_pooled_per_seed.csv (the per-seed values behind Figure 5 / Table 5).
"""
import csv
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

HERE = Path(__file__).resolve().parent
V2 = HERE.parent
sys.dont_write_bytecode = True
sys.path.insert(0, str(V2 / "code" / "fl_pipeline_v2"))
from analyze_confirmatory_v2 import load_run, structure, SEEDS, ALGOS, SCHEDS, CLASSES, MITM  # noqa: E402

RD = V2 / "results_confirmatory"
OD = HERE / "figures"
COL = {"fedavg": "#0072B2", "fedprox": "#D55E00"}
MRK = {"fedavg": "o", "fedprox": "D"}
NAME = {"fedavg": "FedAvg", "fedprox": "FedProx"}
INK, MUTED, GRID = "#1a1a1a", "#666666", "#e3e3e3"
plt.rcParams.update({"font.size": 9, "axes.edgecolor": MUTED, "axes.labelcolor": INK, "xtick.color": INK,
                     "ytick.color": INK, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6, "axes.axisbelow": True,
                     "figure.dpi": 150, "savefig.bbox": "tight"})


def save(fig, name):
    for ext in ("png", "pdf"):
        fig.savefig(OD / f"{name}.{ext}")
    plt.close(fig)


def runs_of(rs):
    out = []
    for r in rs:
        if out and r == out[-1][1] + 1:
            out[-1][1] = r
        else:
            out.append([r, r])
    return out


def fig2(runs, full):
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
            if key == "regular_recall":
                ax.set_ylim(-0.03, 0.03)
            ax.set_xticks([0, 1], [NAME[a] for a in ALGOS])
            ax.set_xlim(-0.5, 1.5)
            if j == 0:
                ax.set_ylabel(lab)
            if i == 0:
                ax.set_title(sc, fontsize=9, loc="left")
    save(fig, "fig2_primary_L1_v2")


def fig3(runs):
    fig, axes = plt.subplots(2, 3, figsize=(10, 5.2), sharex=True)
    rounds = sorted(runs[(SEEDS[0], "fedavg", "none")])
    for j, sc in enumerate(SCHEDS):
        exp = [r for r in rounds if runs[(SEEDS[0], "fedavg", sc)][r]["drift_strength"] > 0]
        for i, (key, lab) in enumerate((("macro_f1", "schedule − none: clean macro-F1"),
                                        ("regular_recall", "schedule − none: clean Regular recall"))):
            ax = axes[i, j]
            for lo, hi in runs_of(exp):
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
    save(fig, "fig3_L2_L3_trajectories_v2")


def fig4():
    fig, axes = plt.subplots(1, 2, figsize=(8, 3.3), sharey=True)
    for ax, a in zip(axes, ALGOS):
        d = {}
        for s in SEEDS:
            for r in csv.DictReader(open(RD / f"seed{s}_{a}_none_h1_margins.csv")):
                d[(s, int(r["round"]))] = float(r["margin_drop"])
        rr = sorted({k[1] for k in d})
        for s in SEEDS:
            ax.plot(rr, [d[(s, r)] for r in rr], color=COL[a], lw=0.8, alpha=0.45)
            ax.scatter([15, 30], [d[(s, 15)], d[(s, 30)]], s=26, color=COL[a], marker=MRK[a], zorder=3,
                       edgecolor="white", linewidth=0.8)
        ax.plot(rr, [np.mean([d[(s, r)] for s in SEEDS]) for r in rr], color=INK, lw=1.8, zorder=4)
        for x in (15, 30):
            ax.axvline(x, color=MUTED, lw=0.8, ls=":")
        ax.axhline(0, color=MUTED, lw=0.8)
        ax.set_xlabel("round of the clean-trained (`none`) checkpoint")
        ax.set_title(NAME[a], fontsize=9, loc="left")
    axes[0].set_ylabel("margin drop at strength 1\n(logit Regular − MITM)")
    save(fig, "fig4_H1_susceptibility_v2")


def h2_pooled(runs, full):
    rows = []
    for a in ALGOS:
        for s in SEEDS:
            rec = {"algorithm": a, "seed": s}
            for c in CLASSES:
                if c == "MITM":
                    continue
                ci = CLASSES.index(c)
                v = []
                for sc in SCHEDS:
                    for r in full[sc]:
                        R = runs[(s, a, sc)][r]
                        nd, nc = R["drifted_cm"][ci].sum(), R["clean_cm"][ci].sum()
                        if nc == 0:
                            continue
                        v.append(R["drifted_cm"][ci][MITM] / nd - R["clean_cm"][ci][MITM] / nc)
                if v:
                    rec[c] = float(np.mean(v))
            rows.append(rec)
    with open(HERE / "h2_pooled_per_seed.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    return rows


def fig5(rows):
    classes = ["Injection", "Unauth", "Video", "Replay", "Regular", "DoS"]
    fig, axes = plt.subplots(1, 2, figsize=(9, 3.4), sharey=True)
    for ax, a in zip(axes, ALGOS):
        rs = [r for r in rows if r["algorithm"] == a]
        for x, c in enumerate(classes):
            v = [r[c] for r in rs]
            ax.scatter([x] * len(v), v, s=26, color=COL[a], marker=MRK[a], zorder=3, edgecolor="white", linewidth=0.8)
            ax.hlines(np.mean(v), x - 0.25, x + 0.25, color=INK, lw=1.6, zorder=4)
        ax.axhline(0, color=MUTED, lw=0.8)
        ax.axhline(0.05, color=MUTED, lw=0.8, ls="--")
        ax.axhline(0.10, color=MUTED, lw=0.8, ls=":")
        ax.set_xticks(range(len(classes)), [f"{c}→MITM" for c in classes], rotation=30, ha="right")
        ax.set_title(NAME[a], fontsize=9, loc="left")
    axes[0].set_ylabel("Δ rate toward MITM\n(transformed − clean)")
    save(fig, "fig5_H2_class_specific_v2")


def main():
    OD.mkdir(parents=True, exist_ok=True)
    runs = {(s, a, sc): load_run(RD, s, a, sc) for s in SEEDS for a in ALGOS for sc in ["none"] + SCHEDS}
    assert all(v is not None for v in runs.values()), "all 40 v2 runs are required"
    full = {sc: structure(runs[(SEEDS[0], "fedavg", sc)])[1] for sc in SCHEDS}
    fig2(runs, full)
    fig3(runs)
    fig4()
    rows = h2_pooled(runs, full)
    fig5(rows)
    for a in ALGOS:
        rs = [r for r in rows if r["algorithm"] == a]
        print(a, {c: round(float(np.mean([r[c] for r in rs])), 4) for c in rs[0] if c not in ("algorithm", "seed")})
    print("written to", OD)


if __name__ == "__main__":
    main()
