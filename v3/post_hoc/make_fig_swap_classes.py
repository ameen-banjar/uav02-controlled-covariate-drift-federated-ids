"""
POST-HOC figure (written 2026-11-11): class-recall response in the 2 x 2 of
training arm (main_v2, main_td) by evaluation transform (v2, td).

Per seed, L1 class recall = recall on transformed inputs minus recall on clean
inputs at the same checkpoint, averaged over the full-strength rounds (frozen
estimand A.l1_classes). Points sharing an evaluation transform are grouped, so
the figure shows whether the class response moves with the evaluation
transform or with the training arm.

Reads results_v3/*.csv with the frozen loaders. Writes figures/fig_swap_classes.*
and fig_swap_classes.json (the plotted seed means).
"""
import json
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
COL = {"fedavg": "#0072B2", "fedprox": "#D55E00"}
MRK = {"fedavg": "o", "fedprox": "D"}
NAME = {"fedavg": "FedAvg", "fedprox": "FedProx"}
INK, MUTED, GRID = "#1a1a1a", "#666666", "#e3e3e3"
plt.rcParams.update({"font.size": 9, "axes.edgecolor": MUTED, "axes.labelcolor": INK, "xtick.color": INK,
                     "ytick.color": INK, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6, "axes.axisbelow": True,
                     "figure.dpi": 150, "savefig.bbox": "tight"})
SCHN = {"sudden": "Sudden", "gradual": "Gradual", "recurring": "Recurring"}
CLASSES = ("MITM", "Video")
# x positions: evaluation v2 (trained v2, trained td) | evaluation td (trained v2, trained td)
CELLS = [("main_v2", "v2", 0.0), ("main_td", "v2", 1.0), ("main_v2", "td", 2.6), ("main_td", "td", 3.6)]
OFF = {"fedavg": -0.17, "fedprox": 0.17}


def main():
    runs, _, _ = A.load(Path(R.RESULTS))
    means = {}
    fig, axes = plt.subplots(len(CLASSES), 3, figsize=(9.2, 5.6), sharey="row")
    for i, cls in enumerate(CLASSES):
        for j, s in enumerate(A.SCH):
            ax = axes[i, j]
            for algo in ("fedavg", "fedprox"):
                for arm, tr, x in CELLS:
                    v = [100 * A.l1_classes(runs[(arm, k, algo, s)], s, tr, "validation")[cls] for k in R.SEEDS10]
                    means[f"{cls}_{s}_{algo}_{arm}_eval_{tr}"] = float(np.mean(v))
                    face = COL[algo] if arm == "main_v2" else "white"
                    ax.scatter([x + OFF[algo]] * 10, v, s=20, facecolor=face, edgecolor=COL[algo],
                               marker=MRK[algo], linewidth=0.9, zorder=3)
                    ax.hlines(np.mean(v), x + OFF[algo] - 0.15, x + OFF[algo] + 0.15, color=INK, lw=1.6, zorder=4)
            ax.axhline(0, color=MUTED, lw=0.8)
            ax.axvline(1.8, color=MUTED, lw=0.8, ls=(0, (3, 3)))
            ax.set_xlim(-0.6, 4.2)
            ax.set_xticks([0.0, 1.0, 2.6, 3.6], ["trained\nv2", "trained\ntd", "trained\nv2", "trained\ntd"], fontsize=7)
            if i == 0:
                ax.set_title(SCHN[s])
            if i == len(CLASSES) - 1:
                ax.text(0.5, -0.30, "evaluated with\nindependent scaling (v2)", ha="center", va="top",
                        fontsize=8, color=INK, transform=ax.get_xaxis_transform())
                ax.text(3.1, -0.30, "evaluated with\ntime dilation (td)", ha="center", va="top",
                        fontsize=8, color=INK, transform=ax.get_xaxis_transform())
            if j == 0:
                ax.set_ylabel(f"{cls} recall change\n(percentage points)")
    handles = [plt.Line2D([], [], marker=MRK[a], ls="", markerfacecolor=COL[a], markeredgecolor=COL[a],
                          markersize=5, label=NAME[a]) for a in ("fedavg", "fedprox")]
    handles += [plt.Line2D([], [], marker="s", ls="", markerfacecolor=MUTED, markeredgecolor=MUTED, markersize=5,
                           label="trained with v2 (filled)"),
                plt.Line2D([], [], marker="s", ls="", markerfacecolor="white", markeredgecolor=MUTED, markersize=5,
                           label="trained with td (open)")]
    fig.legend(handles=handles, loc="upper center", ncol=4, frameon=False, fontsize=8, bbox_to_anchor=(0.5, 1.0))
    fig.subplots_adjust(top=0.90, bottom=0.17, hspace=0.28, wspace=0.08)
    for ext in ("png", "pdf"):
        fig.savefig(OD / f"fig_swap_classes.{ext}")
    plt.close(fig)
    (HERE / "fig_swap_classes.json").write_text(json.dumps(means, indent=1))
    for k, v in means.items():
        if "fedprox" in k:
            print(f"{k:55} {v:+.2f}")


if __name__ == "__main__":
    main()
