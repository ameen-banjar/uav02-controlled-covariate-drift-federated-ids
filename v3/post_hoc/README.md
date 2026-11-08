# v3 post-hoc analyses (not part of the frozen protocol)

Written 2026-11-08, after `analyze_v3.py` had been run once (timestamp in `../results/analysis/analysis_run_timestamp.txt`). They read only `results_v3/*.csv` with the frozen loaders and estimands of `analyze_v3.py`, and add no endpoint.

- `posthoc_v3.py` → `posthoc_v3.txt`, `posthoc_v3.json`. Contents:
  - A: same-checkpoint swap td − v2;
  - B: arm vs arm td − v2, paired by seed;
  - C: clean macro-F1 levels of the none runs;
  - D: class-recall L1 for both arms under both transforms.
- `make_figures_v3.py` → `figures/`: Figures 2–6 of the manuscript.

To run them, place these files in `code/fl_pipeline_v3/post_hoc/` next to the frozen code, with `results_v3/` present.
