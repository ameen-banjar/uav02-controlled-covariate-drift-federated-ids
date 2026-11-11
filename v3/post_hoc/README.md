# v3 post-hoc analyses (not part of the frozen protocol)

Written 2026-11-08, after `analyze_v3.py` had been run once (timestamp in `../results/analysis/analysis_run_timestamp.txt`). They read only `results_v3/*.csv` with the frozen loaders and estimands of `analyze_v3.py`, and add no endpoint.

- `posthoc_v3.py` → `posthoc_v3.txt`, `posthoc_v3.json`. Contents:
  - A: same-checkpoint swap td − v2;
  - B: arm vs arm td − v2, paired by seed;
  - C: clean macro-F1 levels of the none runs;
  - D: class-recall L1 for both arms under both transforms.
- `make_figures_v3.py` → `figures/`: Figures 2–6 of the manuscript.

To run them, place these files in `code/fl_pipeline_v3/post_hoc/` next to the frozen code, with `results_v3/` present.

## Correction (2026-11-08, after release v3.0.0)

In section A of `posthoc_v3.txt` as released in v3.0.0, the count of seeds with a negative paired value (td lowered macro-F1 more than v2) was printed under the label `td-less-negative(pos)`. The script now prints it as `neg k/10`, followed by `pos k/10`. The only lines that changed are those labels and a two-line key; all numbers and `posthoc_v3.json` are unchanged. To see the original output, check out the tag `uav02-release-v3.0.0`.

## Added in release 3.1.0 (2026-11-12)

Both scripts were written after all v3 results were known, read only `results_v3/*.csv` with the frozen loaders of `analyze_v3.py`, and add no frozen endpoint. Run them the same way as the scripts above.

- `make_fig_swap_classes.py` (written 2026-11-11) -> `figures/fig_swap_classes.{png,pdf}` and `fig_swap_classes.json` (the plotted seed means). Change in MITM and Video recall for each training arm (`main_v2`, `main_td`) under each evaluation transform (v2, td), using the frozen estimand `l1_classes`. This is Figure 3 of the manuscript.
- `mitm_precision_f1_post_hoc.py` (written 2026-11-12) -> `mitm_precision_f1_post_hoc.txt`. Change in MITM recall, precision and F1 (transformed minus clean, full-strength rounds, mean over ten seeds) computed from the saved confusion matrices. The recomputed recall equals the stored per-class recall exactly (last line of the output).
