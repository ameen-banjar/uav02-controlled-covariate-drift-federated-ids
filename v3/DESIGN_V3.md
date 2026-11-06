# UAV-02 v3: expanded campaign (frozen before any v3 execution)

Frozen: 2026-11-06, tag `uav02-v3-freeze`. v1 and v2 (protocols, code, results) stay in this repository unchanged. v3 adds experiments; it does not replace or re-analyse v2.

## 1. Why v3

External reviews of the v2 manuscript (2026-11-06) accepted its claims within their stated limits but named limits that only new experiments can address: one intervention that passes per-feature domain checks but is not jointly consistent; five seeds; one partition; one exposure share; one architecture; two FL algorithms; full participation; validation sessions reused across development; one dataset; the raw H1 margin. v3 addresses each with a pre-specified arm.

## 2. Interventions (code: `fl_pipeline_v3/drift_v3.py`)

* **`v2`** — the v2 intervention, unchanged. It is not jointly consistent: in the ISOT extractor (isot-lab repo, commit `783e9bf`), `Srate = src packets / flow duration`, `flow_active_time = flow duration`, and on IP rows `Rate = payload bits / inter-packet interval` with `IAT` = that interval; v2 multiplies the time features by 1.6 and the rates by 0.4, so rate × time changes by a factor 0.64, and `std_duration` (std of flow timestamps) is not scaled.
* **`td` (time dilation, new, jointly consistent)** — every packet's timing is stretched by c = 1 + 0.6 s: `IAT`, `flow_active_time`, `std_duration` × c; `Srate`, `Drate` and IP-row `Rate` ÷ c; all size, count, flag, protocol, payload-entropy and TTL features unchanged. Each ISOT row is the mean over 10 consecutive packets (extractor `pcap_evaluation`, `n_rows = 10`), and a mean of values scaled by the same factor scales by that factor, so the identities rate × time = packets (or bits) hold exactly for every row; they are asserted on every call. Rows whose 10-packet window contains an 802.11 packet (mean `Protocol Type` > 17) keep `Rate` unchanged because their `Rate` mixes radiotap PHY rate and payload rate; their share is reported. Entropy is not edited: a slower link does not change payload content.
* **`td_time_only`, `td_rate_only`** — the two components of `td`, evaluation only.

Guards: a transform may not create a negative time or rate from a non-negative raw value (raw violations are counted, not edited); `td` identities asserted row by row.

## 3. Arms (code: `fl_pipeline_v3/run_v3.py`, `ARMS`; 360 jobs)

Seeds: `SEEDS10` = 131, 142, 153, 164, 175, 186, 197, 208, 219, 230; `SEEDS5` = the first five. No seed is replaced or dropped. Model, local training, rounds, schedules, class weights and preprocessing are those of v2 unless stated.

| Arm | Change from v2 | Train / evaluation transform | Schedules | Algorithms | Seeds | Jobs |
|---|---|---|---|---|---|---|
| `main_none` | — | none / v2 and td | none | FedAvg, FedProx | 10 | 20 |
| `main_v2` | — (replication of v2) | v2 / v2, td | sudden, gradual, recurring | FedAvg, FedProx | 10 | 60 |
| `main_td` | intervention | td / td, v2 | sudden, gradual, recurring | FedAvg, FedProx | 10 | 60 |
| `exp_k8`, `exp_k11`, `exp_k15` | 8, 11, 15 exposed clients (Regular-share order) | td | sudden | FedAvg, FedProx | 5 | 30 |
| `alpha_0.1`, `alpha_2`, `alpha_100` | re-partition of the 91 pool sessions, Dirichlet α | td | none, sudden | FedAvg, FedProx | 5 | 60 |
| `arch_wide` | MLP 256-128-64 | td | none, sudden | FedAvg, FedProx | 5 | 20 |
| `algo_scaffold`, `algo_fednova`, `algo_fedadam` | algorithm (settings screened in UAV-01 item 2 on the same data) | td | none, sudden | one each | 5 | 30 |
| `partial10` | 10 of 15 clients per round, seeded | td | none, sudden | FedAvg, FedProx | 5 | 20 |
| `fresh` | 12 pool sessions (4 Regular + 1 per attack class with ≥ 4 pool sessions) removed as a fresh evaluation set never used for evaluation before; remaining 79 re-partitioned (α 0.5) | td | none, sudden, gradual, recurring | FedAvg, FedProx | 5 | 40 |
| `cic` | CICIoT2023 (UAV-01 cleaned split; IAT < 0 rows removed; ≤ 60,000 train / 8,000 validation rows per class; 15 row-level Dirichlet(0.5) clients; 5 highest-Benign clients exposed) | td (IAT × c, Rate ÷ c) | none, sudden | FedAvg, FedProx | 5 | 20 |

Exposed clients in every arm: the k clients with the highest Regular (CICIoT: Benign) row share in that arm's manifest; k = 5 unless stated. The none reference for L2/L3 is `main_none` for `main_*` and `exp_*`, and the arm's own none run otherwise. Every job evaluates clean and transformed inputs every round; at saved rounds it also evaluates probe transforms (`td`, `v2` at s ∈ {0.25, 0.5, 0.75, 1}; components at s = 1). None runs record H1 margins, prediction-flip rates and Regular→other rates at rounds 5–45. The held-out test sessions are not used.

## 4. Pre-freeze pilot (disclosed)

Before this freeze, `td` was applied for evaluation only to the saved v2 checkpoints (`fl_pipeline_v3/prefreeze/td_on_v2_checkpoints.txt`): L1 macro-F1 −0.018 to −0.024 (negative in 5/5 seeds in all six combinations) versus −0.025 to −0.033 for `v2`; rate-only −0.013 to −0.016, time-only −0.006 to −0.011; H1 S under `td` +0.038 (FedAvg, 0/5 negative) and −0.028 (FedProx, 4/5). The predictions below use this pilot and the v2 results; v3 is therefore a confirmatory test of stated predictions on fresh seeds, not an independent discovery.

## 5. Endpoints, gates and predictions (code: `fl_pipeline_v3/analyze_v3.py`, run once)

Gates are directional replication criteria: ≥ 8/10 seeds (10-seed arms) or ≥ 4/5 seeds (5-seed arms). Equivalence: TOST at α = 0.05 with margin ±0.01 macro-F1 (90% t-interval of seed means inside ±0.01). No p-values are used for the directional gates.

1. **P1 (primary)** — `main_td`: L1 macro-F1 negative in ≥ 8/10 seeds in each of the six algorithm–schedule combinations. *Prediction: passes in all six; means between −0.012 and −0.030; smaller in magnitude than `main_v2` in each combination.*
2. **P2** — `main_v2`: the same gate. *Prediction: passes in all six (replication of v2 with ten new seeds).*
3. **P-R** — |mean L1 Regular recall| < 0.005 in `main_td` and `main_v2`. *Prediction: holds in all twelve.*
4. **EQ-L2, EQ-L3** — TOST on L2 (exposure mean) and on L3 at the last round of each post-removal interval, `main_td` and `main_v2`. *Prediction: equivalence shown for L2 and for every L3 point.*
5. **L3c** — class-level clean-recall residuals: descriptive, means and worst seeds.
6. **H1** — on `main_none`, for `td` and `v2`: raw S, relative S_rel (drop / |clean margin|) and flip contrast F; gates per algorithm; joint gate across algorithms. *Prediction: the joint raw-S gate fails for both transforms (FedAvg fails).* No prediction for FedProx alone.
7. **H2a, H2b** — v2 definitions, pooled over the three schedules, for `main_td` (td) and `main_v2` (v2). *Prediction: both fail.*
8. **Dose** — probe L1 on `main_none` checkpoints at rounds 15, 30, 45 for s ∈ {0.25, 0.5, 0.75, 1}. *Prediction: mean L1 decreases monotonically with s for `td`.* Components: *prediction: rate-only larger in magnitude than time-only; |non-additivity| < 0.005.*
9. **Exposure** — `sudden`, `td`, k ∈ {5, 8, 11, 15}: L1, L2, L3(r45) and per-seed OLS slopes on exposed row share; TOST on L3(r45) per k. No directional prediction.
10. **Robustness** — `alpha_*`, `arch_wide`, `algo_*`, `partial10`, `cic`: L1 macro-F1 gate (≥ 4/5) under `sudden`; L2/L3 and TOST descriptive. *Prediction: the L1 gate passes in every ISOT arm except possibly `algo_fedadam` (no prediction: its client learning rate learns slowly); no prediction for `cic`.*
11. **Fresh evaluation** — `fresh`: all endpoints on the validation and on the fresh sessions. *Prediction: L1 gate passes on the fresh sessions in all six combinations.*
12. **Audits** — joint-consistency audit of both interventions (identity factors), raw domain violations, 802.11-window share; CICIoT2023 feature audit (`cic_prepared/audit.json`).

A prediction that fails is reported as failed. No threshold, seed, arm, schedule or feature changes after this freeze.

## 6. Execution

`v3/launch_v3.sh`: every job of `run_v3.py --list-jobs`, at most three in parallel, `nice -n 15`. The runner refuses to start unless every file in `v3/SHA256SUMS_v3` matches, the repository is clean and HEAD carries `uav02-v3-freeze`. A job is complete when its rounds CSV exists; an interrupted campaign resumes. `analyze_v3.py` runs once after all 360 jobs. Copies of all v3 sources are in `v3/code/`.
