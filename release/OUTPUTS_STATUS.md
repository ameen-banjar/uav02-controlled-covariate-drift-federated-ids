# Status of every output: confirmatory vs post-hoc

The protocol was frozen at commit `0a201c8` (tag `uav02-confirmatory-freeze-v1`, 2026-09-25 01:21 +03:00), before any confirmatory run. Anything the frozen runner or the frozen analysis did not produce is **post-hoc**. Post-hoc items were produced after the confirmatory results existed and add no confirmatory endpoint, gate or p-value.

## 1. CONFIRMATORY (frozen code, executed 2026-09-25)

| Item | Location | Produced by |
|---|---|---|
| Frozen design, code, hashes | `frozen_archive/DESIGN_FROZEN.md`, `frozen_archive/code/`, `frozen_archive/SHA256SUMS` | freeze commit `0a201c8` |
| Round-level metrics + confusion matrices, 40 runs × 45 rounds | `frozen_archive/results_confirmatory/seed<S>_<algo>_<schedule>_rounds.csv` (40) | `code/fl_pipeline/run_drift_confirmatory.py` |
| H1 logit margins, `none` runs | `frozen_archive/results_confirmatory/seed<S>_<algo>_none_h1_margins.csv` (10) | same runner |
| Checkpoints (480) | `frozen_archive/results_confirmatory/checkpoints/` | same runner |
| Per-seed provenance, logs | `frozen_archive/results_confirmatory/provenance_seed<S>.json`, `logs/seed<S>.log` | same runner |
| Frozen analysis: L1/L2/L3/H1/H2 report and gates | `frozen_archive/results_confirmatory/analysis/summary.txt`, `gates.json`, `primary_by_round.csv` | `code/fl_pipeline/analyze_confirmatory.py`, run once on all 5 seeds |

Archived in commit `7ac37fa` (tag `uav02-confirmatory-results-v1`, 2026-09-25 12:54 +03:00). Commit `7ac37fa` only **adds** files to `0a201c8` (563 additions, 0 modifications), so the 12 freeze-tag files inside `frozen_archive/` are byte-identical to the tag.

Manuscript items: **Tables 2–5**, §4.1–4.5 values.

## 2. POST-HOC, 2026-09-25 (after results were seen; committed in `7ac37fa`)

| Item | Location | Script (in `frozen_archive/post_hoc/`) | Label |
|---|---|---|---|
| Primary criteria per metric; H2 confusion as count/N | `results_confirmatory/analysis/supplement.txt`, `h2_counts_supplement.csv` | `report_supplement.py` | display only |
| Figures 1–5 | `results_confirmatory/figures/fig1…fig5 .png/.pdf` | `make_figures_confirmatory.py` | display only |
| Run manifest (start times inferred from mtimes) | `results_confirmatory/RUN_MANIFEST.json/.md` | `build_run_manifest.py` | reconstructed |
| Normalized (relative) H1 | `results_confirmatory/analysis/posthoc_h1_relative.txt` | `posthoc_h1_relative.py` | **exploratory** |

Manuscript items: **Figures 1–5**, §4.4 relative-H1 values.

## 3. POST-HOC, 2026-10-19 and 2026-10-21: held-out test (in no git commit)

These files are untracked in the author's freeze repository. They are copied byte-identically to `posthoc_added_after_results/post_hoc/`.

| Item | Date | Script | Notes |
|---|---|---|---|
| `heldout_test/per_checkpoint_test.csv`, `summary.txt`, `run_info.json` | 2026-10-19 | `posthoc_heldout_test.py` | first and only read of the 28 reserved test sessions; all 480 checkpoints; CPU inference; no training or selection |
| `heldout_test/summary_9label.txt` | 2026-10-19 | `posthoc_heldout_test_9label.py` | 9-class macro-F1 from the saved confusion matrices; no model loaded |
| `heldout_test/h1_margins_test_per_seed.csv`, `summary_h1_margins.txt` | 2026-10-21 | `posthoc_heldout_test_h1_margins.py` | per-seed test H1 margins from the 20 `none` checkpoints at rounds 15/30 |

Manuscript items: **Table 6**, §3.8, §4.6.

## 4. RELEASE TOOLING, 2026-10-21 (this package; changes no result)

`release_tools/`, `dataset/`, `environment/`, `expected/`, `regenerated/`, and the top-level documents. These tools only read the items above, check them, and regenerate tables and figures from them. `regenerated/` holds the output of the staging verification run, for comparison.
