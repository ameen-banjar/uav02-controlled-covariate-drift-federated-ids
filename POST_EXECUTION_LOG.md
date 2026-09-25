# UAV-02 post-execution log

Chronology (2026-09-25, local time). This file is separate from `DESIGN_FROZEN.md`, which is unchanged.

1. **Freeze:** commit `0a201c8`, tag `uav02-confirmatory-freeze-v1` (design, code, SHA256SUMS), before any confirmatory run.
2. **Execution:** seeds 21, 32, 43 started 01:21 (3 parallel processes); seeds 54, 65 started 09:55 as slots freed; all 40 runs completed by ~12:00. The runner verified the frozen hashes/tag at every seed start (`provenance_seed*.json`). No frozen file was modified; hashes re-verified after the run (0 mismatches). No result was opened before all seeds finished.
3. **Frozen analysis:** `analyze_confirmatory.py` run once on the complete 5-seed set (`results_confirmatory/analysis/summary.txt`, `gates.json`).
4. **Post-hoc, added after the results were seen (not part of the frozen protocol; no gates, no p-values):**
   - `post_hoc/report_supplement.py`: primary criteria shown separately per metric; H2 confusion as count/N. Written and tested on synthetic data before the results existed; first run on real data after the frozen analysis.
   - `post_hoc/make_figures_confirmatory.py`: five display figures (same status).
   - `post_hoc/build_run_manifest.py`: run manifest reconstructed from provenance files and file mtimes; start times are derived/inferred, not measured.
   - `post_hoc/posthoc_h1_relative.py`: exploratory normalized H1 (relative margin collapse). Motivated by the alternative explanation that logit scale grows with training; the reading rule was stated before computing. Result: mean clean margin grew ~21% (r15 -> r30) while the relative collapse grew from about -0.29 to -0.78 in both algorithms, negative S_rel in 5/5 seeds for each; all denominators large (min |clean margin| > 3.7).
5. **Calibration vs confirmation:** the pilot (seed 11) overestimated the Regular-recall response (e.g. FedAvg recurring -0.181 vs -0.043 confirmatory); macro-F1 responses were similar. H2b (Regular->MITM and Video->MITM >= 0.05 pooled) failed the frozen threshold (Regular->MITM 0/5 seeds FedAvg, 2/5 FedProx). Reported as is.
6. **Terminology (to be written in the manuscript, not here):** the intervention alters input features with labels fixed, i.e. controlled temporal covariate/distribution drift P(X), not shown to change P(Y|X).
