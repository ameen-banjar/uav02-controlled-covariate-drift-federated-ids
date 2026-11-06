# UAV-02 v2: corrected confirmatory campaign

**Why v2 exists.** In the ISOT extractor, the `Duration` column holds the IP time-to-live (TTL), not a duration. The v1 intervention multiplied it by 1.6, producing values above 255 (the largest possible TTL) in 79.9% of validation rows. A post-hoc ablation on the frozen v1 checkpoints (`../post_hoc/review_2026-11-06/`) showed that this edit produced the v1 Regular-recall response, the Regular/Video→MITM redirection and nearly all of the H1 contrast. v2 re-runs the campaign with `Duration` removed from the intervention. Nothing in v1 was changed.

## Order of events (all on the public repository)

| Step | Git state | Content |
|---|---|---|
| Ablation | commit `06cfc4f` | `post_hoc/review_2026-11-06/` |
| Freeze | tag `uav02-v2-confirmatory-freeze` (commit `8a22943`) | `DESIGN_V2.md` (changes, endpoints, predictions), `SHA256SUMS_v2`, `code/` |
| Results | tag `uav02-v2-results` (commit `361805e`) | `results_confirmatory/` (40 round CSVs, 10 H1 margin CSVs, checkpoints, provenance, `analysis/`), `logs/` |
| Display | tag `uav02-release-v2.0.0` | `post_hoc/` (Figures 2–5, `h2_pooled_per_seed.csv`), `release_tools/` |

The runner refused to start unless every file in `SHA256SUMS_v2` matched, the repository was clean and HEAD carried the freeze tag. All five seeds exited normally; no run triggered the physical-range guard; the frozen analysis was run once.

## Results against the frozen predictions (validation only)

| Endpoint | Prediction in `DESIGN_V2.md` | Outcome |
|---|---|---|
| Primary: L1 macro-F1 negative in ≥ 4/5 seeds, six combinations | passes in all six | **passes in all six** (5/5 seeds each; means −0.025 to −0.031) |
| P-R: abs. mean L1 Regular recall < 0.005 | holds in all six | **holds** (max 0.0002) |
| H1 | fails, at least for FedAvg | **fails** (FedAvg S +0.031, 2/5 negative; FedProx S −0.079, 5/5 negative) |
| H2b | fails | **fails** |
| H2a | no prediction | **fails** (FedAvg 1/5, FedProx 0/5) |

## Reproduce without training or the dataset

```bash
python3.11 v2/release_tools/rerun_v2_analysis.py
```

checks the v2 source hashes, re-runs the frozen v2 analysis into `v2/regenerated/analysis/` and compares `summary.txt`, `gates.json` and `primary_by_round.csv` byte for byte with the archived reports, then regenerates Figures 2–5 and the pooled H2 table. Re-running the training needs the ISOT dataset and the development-workspace layout described in `DESIGN_V2.md` §5.
