# Software environment: contemporaneous provenance and reconstruction

This file separates what was **recorded when the confirmatory run happened** from what was **reconstructed later** to help readers set up an environment.

## A. Contemporaneous provenance (written during the run, 2026-09-25)

The frozen runner writes `provenance_seed<S>.json` at the start of each seed, after its frozen-state guard passes. The five files are in `frozen_archive/results_confirmatory/`:

| Seed | git HEAD | Tag | PyTorch | Device | Started (unix) |
|---:|---|---|---|---|---|
| 21 | 0a201c80ed6f | uav02-confirmatory-freeze-v1 | 2.10.0 | mps | 1790288488.0 |
| 32 | 0a201c80ed6f | uav02-confirmatory-freeze-v1 | 2.10.0 | mps | 1790288488.0 |
| 43 | 0a201c80ed6f | uav02-confirmatory-freeze-v1 | 2.10.0 | mps | 1790288488.0 |
| 54 | 0a201c80ed6f | uav02-confirmatory-freeze-v1 | 2.10.0 | mps | 1790319303.7 |
| 65 | 0a201c80ed6f | uav02-confirmatory-freeze-v1 | 2.10.0 | mps | 1790319305.5 |

Each file also records the SHA-256 of all 8 frozen source files. Those values match `frozen_archive/SHA256SUMS`. The per-seed logs are in `frozen_archive/results_confirmatory/logs/seed<S>.log`.

The provenance files record **only** the PyTorch version and the device. They record no Python, NumPy, pandas, scikit-learn, SciPy or matplotlib version, and no OS version.

## B. Post-hoc run manifest (compiled after the run, same day)

`frozen_archive/results_confirmatory/RUN_MANIFEST.json`/`.md` was compiled by `post_hoc/build_run_manifest.py` at 2026-09-25T12:01:43+03:00, after all 40 runs had finished. It records:

- Python 3.11.4, torch 2.10.0, numpy 1.26.4, pandas 2.3.3, scikit-learn 1.7.2, scipy 1.16.3, matplotlib 3.10.7 (read from the interpreter at compile time, not inside each training process)
- Apple M1, 8 logical CPUs, 16 GiB, macOS 26.3.1 arm64; backend MPS
- up to 3 concurrent seed processes (`xargs -P 3`)
- per-run start times **derived from file mtimes** (inferred, not measured). They are not a runtime benchmark.

## C. Post-hoc held-out-test evaluation (2026-10-19 / 2026-10-21)

`posthoc_added_after_results/post_hoc/heldout_test/run_info.json` records torch 2.10.0 and device **cpu**. That script forces CPU, and its evaluation involves no training.

## D. Reconstructed requirements (2026-10-21, this package)

`requirements-reconstructed.txt` pins the versions from A and B. It was **not** produced by `pip freeze` at run time. Install it with:

```bash
python3.11 -m venv .venv && . .venv/bin/activate && pip install -r environment/requirements-reconstructed.txt
```

The staging checks in `STAGING_REPORT.md` were run on 2026-10-21 on the original machine (Apple M1, macOS arm64, Python 3.11.4), with exactly these versions installed.

## E. Determinism and cross-backend statement

- **No bitwise reproducibility guarantee across backends, devices, or library versions is made.** Confirmatory training used the PyTorch MPS backend. The runner seeds `torch` and `numpy` per run but does not enable deterministic algorithms, and MPS kernels are not guaranteed bitwise deterministic. A re-run, even on the same hardware, may produce different round-level values. On CPU or CUDA, differences are expected.
- What *is* reproducible from this package: every manuscript table and figure. They are regenerated **from the saved outputs** (round CSVs, H1 margin CSVs, held-out per-checkpoint CSV), which are pure post-processing (NumPy/SciPy/matplotlib). Here the regenerated values matched exactly (see `STAGING_REPORT.md`).
- The post-hoc held-out evaluation runs inference on the saved checkpoints on CPU. Re-executing it on the original machine reproduced the archived `per_checkpoint_test.csv`, `run_info.json` and the per-seed H1 margins byte for byte on 2026-10-21 (see `STAGING_REPORT.md`). On other CPUs or BLAS builds, last-digit floating-point differences are possible.
