# UAV-02 v3: expanded campaign (360 runs)

**Why v3 exists.** In the ISOT extractor, v2 scales rates and times independently: every rate–time product changes by a factor of 0.64 at full strength, and `std_duration` is not scaled. v3 adds a time-dilation intervention (`td`) that keeps those scaling relations, given fixed packets and fixed 10-packet aggregation windows. It compares `td` with v2 under ten matched seeds. It also varies the exposure share, the partition (α), the architecture, the optimizer (SCAFFOLD, FedNova, FedAdam), the participation (10 of 15 clients), the evaluation sessions (12 newly held-out sessions) and the dataset (CICIoT2023). Nothing in v1 or v2 was changed.

## Order of events (all on the public repository)

| Step | Git state | Content |
|---|---|---|
| Freeze | tag `uav02-v3-freeze` (commit `d5124d1`, 2026-11-06 12:03:41 +03:00) | `DESIGN_V3.md` (arms, endpoints, predictions, pre-freeze pilot), `SHA256SUMS_v3` (27 files), `code/` |
| Execution | — | 360 jobs, three in parallel, 2026-11-06 12:04 to 2026-11-07 22:13 +03:00; all exited with code 0 (`logs/_done.txt` ends with `ALL_DONE`) |
| Addendum | written during execution, before any v3 metric was opened | `addendum/POST_FREEZE_ADDENDUM_2026-11-06.md` (r2) and its dated snapshot with SHA-256 |
| Results | tag `uav02-v3-results` (commit `8b2fc39`) | `results/` (round, probe and H1 CSVs, provenance, `analysis/` from one run of the frozen `analyze_v3.py`), `logs/`, `addendum/` |
| Post hoc | commit `a70c862` | `post_hoc/` (paired td−v2 comparisons, clean performance levels, Figures 2–6), `evidence/` |
| Release | tag `uav02-release-v3.0.0` | this README, `CITATION.cff` |
| Correction release | tag `uav02-release-v3.0.1` (sign-label fix in commit `8e570cb`) | corrected post-hoc label; this README's corrections section |

The runner refused to start unless every file in `SHA256SUMS_v3` matched, the repository was clean, and HEAD carried the freeze tag. All 27 hashes were verified again after the campaign.

## Evidence that the freeze was public before the first run

- GitHub's public Events API records a `PushEvent` to `main` with head `d5124d1` at **2026-11-06T09:03:50Z**. The snapshot is in `evidence/github_events_snapshot_2026-11-08.json`. GitHub keeps these events for 90 days, and the author saved the snapshot, so it is a record rather than an independent attestation.
- The first job logs (`logs/main_none_131_*.log`, `logs/main_none_142_*.log`) were created at 2026-11-06 12:04:03 +03:00, which is 09:04:03Z.

## What is not in the repository

- **Model checkpoints.** The 314 MB of checkpoints are listed with their SHA-256 digests in `results/CHECKPOINTS_SHA256.txt` and are available from the author.
- **Datasets.** The ISOT and CICIoT2023 data are not redistributed. `code/fl_pipeline_v3/cic_prepared/` holds the metadata of the prepared CICIoT2023 subset (`meta.json`, `audit.json`, `clients.json`). The prepared parquet and npy files are not included: `cic_v3.py` regenerates them from the companion study's cleaned split, and `SHA256SUMS_v3` lists their digests so a regenerated copy can be checked.

## Results against the frozen predictions (validation)

| # | Item | Outcome |
|---|---|---|
| 1 | L1 gate, `main_td` | holds: 10/10 seeds negative in all six combinations; means −0.0154 to −0.0239, smaller than v2 in all six |
| 2 | L1 gate, `main_v2` | holds: 10/10 in five combinations, 9/10 in FedAvg gradual |
| 3 | Regular recall below 0.005 | holds (largest 0.0008) |
| 4 | Equivalence (TOST ±0.01) | L2 holds (12/12). L3 **fails in part** (12/16): gradual round 45 in both arms |
| 6 | H1 joint gate fails | holds (fails) |
| 7 | H2a and H2b fail | holds |
| 8 | Dose response monotone; rate component larger than time component; non-additivity below 0.005 | monotone holds; rate > time **fails** (3/6); non-additivity holds |
| 10 | Robustness L1 gates | **fail** in one arm, α = 2 with FedProx (+0.0124); all other arms pass |
| 11 | Fresh-session L1 gate | holds (−0.0034 to −0.0043) |

Items 5, 9 and 12 are descriptive or audits. Full output: `results/analysis/summary.txt` and `gates.json` (309 gates).

## Corrections after v3.0.0 (release v3.0.1, 2026-11-08)

No result, frozen file, seed or number changed.

1. **Post-hoc sign label (commit `8e570cb`).** In section A of `post_hoc/posthoc_v3.txt`, v3.0.0 printed the count of negative seeds (td lowered macro-F1 more than v2) under the label `td-less-negative(pos)`. It is now printed as `neg k/10`, followed by `pos k/10`. `posthoc_v3.json` is byte-identical.
2. **802.11 field descriptions.** We checked the ISOT extractor at isot-lab commit `783e9bf` again. The dated addendum (A2–A3) describes two fields imprecisely; it is kept unchanged as a dated record.
   - On 802.11 packets, `Rate` is not the raw radiotap PHY rate. `Communication_features.py` returns the payload rate derived from it, PHY rate × payload size / packet size. This value has no timing term, so leaving it unchanged under time dilation remains consistent.
   - On 802.11 packets, `Feature_extraction.py` initializes `wifi_dur` to 0 and never updates it, so the extractor writes 0 to `Duration`; the column is not a frame-duration field. This explains the zeros reported in A3, and the 255 argument for IP rows is unaffected.
