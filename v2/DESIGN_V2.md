# UAV-02 v2: corrected confirmatory protocol (frozen before any v2 execution)

Frozen: 2026-11-06, tag `uav02-v2-confirmatory-freeze`. The v1 protocol (`DESIGN_FROZEN.md`, tag `uav02-confirmatory-freeze-v1`) and all v1 results stay in this repository unchanged.

## 1. Why a v2 campaign

An external review and our own check of the ISOT extractor (commit `783e9bf`, `Connectivity_features_time.duration()` returns `packet.ttl`) showed that the `Duration` column is the IP time-to-live, not a session or flow duration. v1 multiplied it by 1.6 at full strength, which produces values above 255, the largest possible IP TTL, in 79.9% of validation rows, 49.7% of held-out-test rows and 94.9% of the transformed clients' training rows.

A post-hoc ablation on the frozen v1 checkpoints (`post_hoc/review_2026-11-06/`, run before this freeze) found:
- H1 contrast S: full transform −3.34 (FedAvg) / −3.14 (FedProx); without Duration +0.02 / −0.08; Duration alone −3.40 / −3.13.
- Validation L1 at saved full-strength rounds: the Regular-recall response and the Regular/Video→MITM redirection almost vanish without Duration (e.g. FedProx recurring Regular recall −0.074 → 0.000; Video→MITM +0.56 → +0.02), while the macro-F1 response stays negative in 5/5 seeds in every algorithm–schedule combination (−0.024 to −0.032).

v1 therefore mixed a physically valid timing/throughput intervention with an invalid out-of-range edit. v2 re-runs the campaign with the invalid edit removed. Because the v2 predictions below were formed after seeing v1 and the ablation, v2 is a confirmatory replication of those predictions under a corrected intervention, not an independent discovery.

## 2. What is unchanged from v1

Dataset, the 15-client session partition (manifest SHA-256 unchanged), the 18 validation sessions, the 56 input features and preprocessing, the MLP, local training (1 epoch, Adam 1e-3, batch 4,096, full balanced class weights), FedAvg and FedProx (μ = 0.01), 45 rounds, all 15 clients every round, the five transformed clients (11, 1, 14, 10, 9), the four schedules and their rounds, the magnitudes (±60% multiplicative, Entropy −0.50 with the 5th-percentile floor), the checkpoint and H1 rounds, the L1/L2/L3 estimands, and the H1/H2 definitions and thresholds. `data.py`, `model.py` and `algorithms.py` are byte-identical to the v1 frozen files.

## 3. What changes

1. **Intervention:** `Duration` is removed from the transformed features. Transformed: Rate, Srate, Drate (× (1 − 0.60 s)); IAT, flow_active_time (× (1 + 0.60 s)); Entropy (− 0.50 s, floored). Every transformed column is checked against its physical domain on every call (rates and times ≥ 0; payload entropy in [0, 8] bits); a violation stops the run.
2. **Seeds:** fresh seeds 76, 87, 98, 109, 120. No seed is replaced or dropped.
3. **Held-out test:** not used. The 28 test sessions were already evaluated post hoc for v1 and in UAV-01; v2 is validation-only. All v2 conclusions are validation-set results.

## 4. Pre-specified v2 endpoints and predictions

All gates are directional replication gates (≥ 4/5 seeds), not significance tests; effect sizes, per-seed values and descriptive t-intervals are always reported.

1. **Primary (P):** L1 macro-F1 response (transformed minus clean, same checkpoint, mean over full-strength rounds) is negative in ≥ 4/5 seeds for each of the six algorithm–schedule combinations. *Prediction: passes in all six.*
2. **Prediction P-R (Regular recall):** |mean L1 Regular-recall response| < 0.005 in each combination. *Prediction: holds in all six.* (v1 gated Regular recall as a primary metric; v2 does not, because the ablation identified that effect as a Duration artifact.)
3. **L2, L3 (secondary, descriptive):** as in v1, plus class-level clean-recall residuals at the last round of every post-removal interval (L3c), reported for all present classes with means and worst seeds.
4. **H1 (secondary):** same contrast S = drop(r30) − drop(r15) on `none` checkpoints with the v2 transform; same gate. *Prediction: the v1 H1 effect does not replicate; S is near zero (FedAvg) or small (FedProx), and the gate fails for at least FedAvg.*
5. **H2 (secondary):** same H2a/H2b definitions and thresholds. *Prediction: H2b fails (the ablation showed Regular→MITM and Video→MITM changes near zero without Duration). No prediction is made for H2a, because the ablation did not measure the other classes' transitions.*

A prediction that fails is reported as failed. No threshold, seed, schedule or feature is changed after this freeze.

## 5. Execution

`development-workspace/fl_pipeline_v2/run_drift_confirmatory_v2.py --seed <s>`, at most three seeds in parallel, low priority (`nice`). The runner refuses to start unless every file listed in `v2/SHA256SUMS_v2` matches, this repository is clean, and HEAD carries tag `uav02-v2-confirmatory-freeze`. Each completed run writes its round CSV last, so an interrupted seed resumes at the first incomplete run. The frozen analysis is `analyze_confirmatory_v2.py`, run once after all five seeds are complete. A copy of every v2 source file is stored in `v2/code/`.
