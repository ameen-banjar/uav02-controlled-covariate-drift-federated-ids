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
| Packet-level check, frozen | tag `uav02-v4-freeze` (commit `1719dc3`, 2026-11-10), pushed before any raw capture was opened | `../v4_packet_level_check/DESIGN_V4.md` and `code/`; `../tools/drift_validity_check/` |
| Packet-level check, results | tag `uav02-v4-results` (commit `56ba1e8`, 2026-11-11) | `../v4_packet_level_check/results/` (analysis run once; post-hoc `Rate` diagnostic in `results/post_hoc/`) |
| Release | tag `uav02-release-v3.1.0` (2026-11-12) | two post-hoc scripts in `post_hoc/`, `verify_v3_hashes.py`, the section "Release 3.1.0" below |

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

## Release 3.1.0 (2026-11-12)

No frozen file, result or number of v1, v2 or v3 changed. This release adds material; all of it was written after the v3 results were known.

1. **Packet-level check of time dilation** (`../v4_packet_level_check/`). The design and code were frozen and pushed (tag `uav02-v4-freeze`) before any raw capture file was opened, and the analysis was run once. Ten ISOT capture sessions were re-timed, the unmodified ISOT extractor (isot-lab commit `783e9bf`) was run again, and the table transform `td` was compared with the re-extracted features.
   - All four predictions hold in all 111,974 rows (22,921 IP rows from nine sessions; 89,053 IEEE 802.11 rows, all from one session). The sessions were chosen by file size, one per category, not at random.
   - The replication gate, which compares our extraction at the original timestamps with the distributed CSV files, **failed in four of ten sessions**, in the column `Rate` only (182 rows; 152 of them in the Unauth session). In every such row `Payload_Length` differs as well (`results/post_hoc/`). The records do not establish why the payload lengths differ. The predictions compare the extractor with itself and are not affected, but in these four sessions our extraction is not an exact replica of the distributed files.
   - The raw captures are third-party data and are not redistributed; `results/ARCHIVE_SHA256.txt` and `results/SAMPLE_PCAP_SHA256.txt` identify the files used.
2. **Drift validity checker** (`../tools/drift_validity_check/`). It reports name-content mismatches, values leaving their physical domain and changed rate x time relations for a tabular transform, from a feature file and a transform file, without a model. Its reports for the v1, v2 and td transforms on the 245,526 ISOT validation rows are in `reports/`.
3. **Post-hoc scripts** in `post_hoc/` (see `post_hoc/README.md`): `make_fig_swap_classes.py` (class recall by training arm and evaluation transform; Figure 3 of the manuscript) and `mitm_precision_f1_post_hoc.py` (MITM recall, precision and F1 from the saved confusion matrices).
4. **`verify_v3_hashes.py`.** `SHA256SUMS_v3` lists paths as they were in the development workspace. Run `python3 v3/verify_v3_hashes.py` from the repository root to check the files where they are stored here. Expected output: 24 files match, 3 data files not redistributed, 0 problems.

### Paths needed to re-run the frozen v3 code

`run_v3.py` and its hash guard expect the layout of the development workspace, which differs from the layout of this repository:

```
<root>/development-workspace/fl_pipeline_v3/                  <- copy of v3/code/fl_pipeline_v3/
<root>/development-workspace/data_audit/prepare_isot.py       <- copy of v3/code/prepare_isot.py
<root>/development-workspace/data_audit/federated_clients_manifest.json   <- copy of v3/code/federated_clients_manifest.json
<root>/repositories/paper-02-controlled-concept-drift/        <- this repository
```

The guard also requires this repository to be clean with HEAD at the tag `uav02-v3-freeze`, the ISOT data prepared as `prepare_isot.py` describes, and, for the `cic` arm, the prepared CICIoT2023 files regenerated by `cic_v3.py`. Reading the results needs none of this.

### Re-running the frozen analysis from this repository (no data, no training)

`analyze_v3.py` imports the data module, which looks for `prepare_isot.py` in a folder `data_audit/` next to `fl_pipeline_v3/`. From a clean copy of this repository:

```
cd v3/code
mkdir data_audit
cp prepare_isot.py federated_clients_manifest.json data_audit/
cd fl_pipeline_v3
python3 analyze_v3.py --results-dir ../../results --out-dir /tmp/v3_analysis
```

The three files written (`summary.txt`, `gates.json`, `table.csv`) are byte-identical to those in `results/analysis/`. Without the `data_audit/` step the script stops with `ModuleNotFoundError: No module named 'prepare_isot'`. The post-hoc scripts need the same step, with `results/` available as `fl_pipeline_v3/results_v3/` and the scripts placed in `fl_pipeline_v3/post_hoc/`. (Added 2026-11-12, after release 3.1.0; tested on a clean copy.)
