# UAV-02 reproducibility package

**Controlled Temporal Covariate Drift in Federated UAV Intrusion Detection: Separating Immediate Response, Training History, and Post-Removal Residuals.** Ameen Banjar, University of Jeddah (abanjar@uj.edu.sa, ORCID 0000-0002-0871-5153).

This repository lets a reader:

1. inspect the protocol and code exactly as frozen before the confirmatory run;
2. regenerate every table (2–6) and figure (1–5) of the manuscript **from the saved outputs**, with one command each, without training and without the dataset;
3. confirm that a local copy of the third-party ISOT Drone Dataset holds the same bytes the study used;
4. re-run the frozen confirmatory training, if desired, under the runner's own frozen-state guard.

## History and status of every file

| Git state | Date | What it contains | Status |
|---|---|---|---|
| tag `uav02-confirmatory-freeze-v1` (commit `0a201c8`) | 2026-09-25 01:21 +03:00 | Frozen design (`DESIGN_FROZEN.md`, in Arabic), the eight frozen source files under `code/`, `SHA256SUMS`, the partition manifest | **frozen before any confirmatory execution; never edited** |
| tag `uav02-confirmatory-results-v1` (commit `7ac37fa`) | 2026-09-25 12:54 +03:00 | Confirmatory outputs: 40 round CSVs with confusion matrices, 10 H1 margin CSVs, 480 checkpoints, provenance, logs, frozen analysis, plus the post-hoc displays of the same day | adds files only; no frozen file changed |
| tag `uav02-release-v1.0.0` (this release) | 2026-10-21 | `post_hoc/posthoc_heldout_test*.py` and `post_hoc/heldout_test/` (held-out-test evaluation, first read 2026-10-19), `release/` (these tools), `LICENSE`, `CITATION.cff` | **post-hoc** analyses and new wrapper code; no frozen file changed |

`release/OUTPUTS_STATUS.md` labels every output as confirmatory or post-hoc. The root `README.md` is the frozen one from 2026-09-25 and still describes the run as pending; it is left unchanged on purpose.

## Requirements

Python 3.11 with the versions in `release/environment/requirements-reconstructed.txt`. Tables and figures need only NumPy, SciPy and matplotlib.

```bash
python3.11 -m venv .venv && . .venv/bin/activate && pip install -r release/environment/requirements-reconstructed.txt
```

Run the commands below from the `release/` folder (`cd release`).

## 0. Check the frozen code

```bash
cd ../code && shasum -a 256 -c ../SHA256SUMS && cd ../release
```

## 1. Regenerate the tables and compare them with the manuscript

```bash
python release_tools/make_tables.py --table all
```

```bash
python release_tools/verify_against_manuscript.py
```

| Table | Source | Status |
|---|---|---|
| 2 Executed schedules | frozen `drift.py`, cross-checked against the saved `drift_strength` of all 40 runs | confirmatory |
| 3 Primary L1 | `results_confirmatory/seed*_rounds.csv` | confirmatory |
| 4 L3 residuals | same | confirmatory |
| 5 H2 pooled transitions | same (confusion matrices) | confirmatory |
| 6 Held-out test vs validation | `post_hoc/heldout_test/per_checkpoint_test.csv` + validation round CSVs | **post-hoc** |

## 2. Regenerate the figures

```bash
python release_tools/make_figures.py --figure all --compare
```

The drawing code is the archived post-hoc display script `post_hoc/make_figures_confirmatory.py`, loaded unchanged.

## 3. Re-run the frozen analysis on the saved outputs

```bash
python release_tools/rerun_frozen_analysis.py
```

## 4. Check your copy of the dataset

The ISOT Drone Dataset is third-party and is **not** redistributed here. Obtain it from the official route in `release/dataset/DATASET_IDENTITY.md` (ISOT Research Lab, University of Victoria; Chen et al., 2025, DOI 10.1007/978-3-031-87499-4_12). Then point the tools at its `new_feature_csv` folder:

```bash
export UAV02_ISOT_DATA_DIR="/path/to/ISOT Drone Dataset/Dataset/new_feature_csv"
```

```bash
python release_tools/check_dataset.py --rows
```

Expected: 137/137 SHA-256 matches; 91 / 18 / 28 sessions; 2,150,122 / 245,526 / 550,338 rows.

## 5. (Optional) Re-execute the post-hoc held-out-test scripts

Inference only on the archived checkpoints, on CPU. Table 6 does not depend on re-running them.

```bash
python release_tools/rerun_heldout_posthoc.py --script h1_margins
```

```bash
python release_tools/rerun_heldout_posthoc.py --script heldout
```

The `heldout` run takes about 30 minutes on an Apple M1. Each run reports whether its outputs are byte-identical to the archived ones.

## 6. (Optional) Re-run confirmatory training

The frozen runner refuses to train unless its sources match `SHA256SUMS`, the checkout is clean, and HEAD carries the tag `uav02-confirmatory-freeze-v1`. Make a separate clean checkout of that tag:

```bash
git clone https://github.com/ameen-banjar/uav02-controlled-covariate-drift-federated-ids ../uav02-freeze
```

```bash
git -C ../uav02-freeze checkout uav02-confirmatory-freeze-v1
```

```bash
python release_tools/run_confirmatory.py --freeze-checkout ../uav02-freeze --check-only
```

```bash
python release_tools/run_confirmatory.py --freeze-checkout ../uav02-freeze --out ../uav02-rerun --seed 21
```

A re-run is **not** expected to be bitwise identical: the original used PyTorch 2.10.0 on Apple MPS without deterministic kernels (see `release/environment/PROVENANCE.md`). Re-run outputs are new evidence, not the confirmatory results.

## Scope statements

- Validation-set results are confirmatory. Held-out-test results are post-hoc (first read 2026-10-19, after the confirmatory results were seen).
- The frozen design text lists gradual full strength as "20–24" in one sentence, while the executed schedule and the frozen analysis use 20–25. Table 2 follows the executed schedule and the saved strengths.
- AI assistance (Claude Code, Codex) and the author's responsibility are described in the manuscript's Methods §3.9.

## License

Code, configuration, partition manifests and derived results: MIT (see `LICENSE`). The ISOT Drone Dataset is not included and remains the property of its owners under their own terms.
