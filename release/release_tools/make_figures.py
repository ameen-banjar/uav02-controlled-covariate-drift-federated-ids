"""
Regenerate manuscript Figures 1-5 FROM THE SAVED OUTPUTS (NEW release tool,
2026-10-21). No model is trained or loaded and the dataset is not needed.

    python release_tools/make_figures.py --figure 2      # one figure
    python release_tools/make_figures.py --figure all
    python release_tools/make_figures.py --figure all --compare   # pixel comparison with the archived PNGs

The drawing code is the archived POST-HOC display script
frozen_archive/post_hoc/make_figures_confirmatory.py (written after the
confirmatory run, committed in 7ac37fa), loaded unchanged with runpy; its
individual fig1..fig5 functions are called here so each figure has its own
command. It imports the frozen analysis/drift modules from frozen_archive/code.
Outputs: regenerated/figures/<name>.png and .pdf (or --out-dir).
"""
import argparse
import runpy
import sys
from pathlib import Path

import numpy as np

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import _paths  # noqa: E402

SCRIPT = _paths.FROZEN / "post_hoc" / "make_figures_confirmatory.py"
NAMES = {"1": "fig1_schedules", "2": "fig2_primary_L1", "3": "fig3_L2_L3_trajectories",
         "4": "fig4_H1_susceptibility", "5": "fig5_H2_class_specific"}


def compare(od, keys):
    import matplotlib.image as mpimg
    ok = True
    for k in keys:
        new, old = od / f"{NAMES[k]}.png", _paths.RESULTS / "figures" / f"{NAMES[k]}.png"
        a, b = mpimg.imread(new), mpimg.imread(old)
        if a.shape != b.shape:
            print(f"Figure {k}: size {a.shape} vs archived {b.shape} -> DIFFERENT")
            ok = False
            continue
        diff = np.abs(a.astype(float) - b.astype(float))
        same = float(diff.max()) == 0.0
        print(f"Figure {k}: {a.shape[1]}x{a.shape[0]} px, max abs pixel diff {diff.max():.4f}, "
              f"differing pixels {(diff.max(axis=-1) > 0).mean() * 100:.3f}% -> {'IDENTICAL PIXELS' if same else 'DIFFERENT'}")
        ok &= same
    return ok


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--figure", default="all", choices=list(NAMES) + ["all"])
    ap.add_argument("--out-dir", default=str(_paths.STAGING / "regenerated" / "figures"))
    ap.add_argument("--compare", action="store_true", help="compare PNG pixels with results_confirmatory/figures")
    a = ap.parse_args()
    od = Path(a.out_dir)
    od.mkdir(parents=True, exist_ok=True)

    _paths.add_frozen_code_to_path()
    g = runpy.run_path(str(SCRIPT), run_name="uav02_figures")       # defines fig1..fig5; main() is not run
    rd = _paths.RESULTS
    keys = list(NAMES) if a.figure == "all" else [a.figure]
    runs = full = None
    if any(k in ("2", "3", "5") for k in keys):
        runs = {(s, al, sc): g["load_run"](rd, s, al, sc)
                for s in g["SEEDS"] for al in g["ALGOS"] for sc in ["none"] + g["SCHEDS"]}
        full = {sc: g["structure"](runs[(g["SEEDS"][0], "fedavg", sc)])[1] for sc in g["SCHEDS"]}
    for k in keys:
        {"1": lambda: g["fig1"](od), "2": lambda: g["fig2"](runs, full, od), "3": lambda: g["fig3"](runs, od),
         "4": lambda: g["fig4"](rd, od), "5": lambda: g["fig5"](runs, full, od)}[k]()
        print(f"Figure {k}: {od / NAMES[k]}.png/.pdf")
    if a.compare:
        sys.exit(0 if compare(od, keys) else 1)


if __name__ == "__main__":
    main()
