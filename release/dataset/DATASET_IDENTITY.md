# ISOT Drone Dataset: identity of the bytes used by UAV-02

**No raw data is included in this package.** The ISOT Drone Dataset belongs to the ISOT Research Lab (University of Victoria) and is distributed under its own terms. Obtain it from the official source, then use the checksums below to confirm that your copy holds the same bytes UAV-02 used.

## Official acquisition route

1. ISOT Research Lab, University of Victoria, *Drone Datasets*: <https://onlineacademiccommunity.uvic.ca/isot/2024/12/05/drone-datasets/>. This page links the archive `ISOT Drone Dataset.zip` (18,545,613,820 bytes as recorded at extraction).
2. Dataset paper: Z. Chen, I. Traoré, M. Mamun, S. Saad, "Drone Anomaly Detection: Dataset and Unsupervised Machine Learning," *Foundations and Practice of Security (FPS 2024)*, LNCS 15532, pp. 186–201, Springer, 2025. DOI [10.1007/978-3-031-87499-4_12](https://doi.org/10.1007/978-3-031-87499-4_12).
3. Original source repository (context only): <https://github.com/isot-lab/Drone-Anomaly-Detection-Dataset-and-Unsupervised-Machine-Learning>.

The archive members are password-protected. The password is given in the official ISOT dataset description and is **not** repeated here. UAV-02 uses only the CSV feature files under `ISOT Drone Dataset/Dataset/new_feature_csv/`. The PCAP members are not used.

Extraction record (author's copy, 2026-08-15): only the `*.csv` members were fetched and decrypted. 137 CSV files, 1,409,995,394 bytes. Size and ZIP CRC32 of every local file match the archive's central directory (`isot_zip_members_crc32.csv`, checked 2026-10-21).

## Expected local layout

Point the tools at the `new_feature_csv` folder (flag `--data-dir`, or environment variable `UAV02_ISOT_DATA_DIR`). It must contain one sub-folder per category:

```
<data-dir>/DoS/  Injection/  Ip Spoofing/  MITM/  Manipulation/  Password Cracking/  Regular/  Replay/  Unauth/  Video/
```

Session names in the frozen partition manifest (`frozen_archive/code/data_audit/federated_clients_manifest.json`) are file names without `.csv`. For example, `DoS/Dos_1_4_30_20mins.pcap.csv` is session `Dos_1_4_30_20mins.pcap`.

## Files in this folder

| File | Content |
|---|---|
| `isot_sessions_sha256.csv` | One row per session CSV used (137): split, client id (training clients 0–14), category, session, relative path, size in bytes, row count (as read by `pandas.read_csv`, the frozen loader's reader), SHA-256 |
| `SHA256SUMS_isot_csv` | The same SHA-256 values in `shasum -a 256 -c` format, paths relative to `<data-dir>` |
| `expected_split_counts.json` | Sessions and rows per split |
| `isot_zip_members_crc32.csv` | Official ZIP member path, size and CRC32 for each file, from the author's extraction record |

## Expected counts (match the manuscript, §3.2 and §3.8)

| Split | Sessions | Rows |
|---|---:|---:|
| Training clients (15 constructed clients) | 91 | 2,150,122 |
| Validation | 18 | 245,526 |
| Held-out test (post-hoc use only) | 28 | 550,338 |
| **Total** | **137** | **2,945,986** |

All 137 CSVs in `new_feature_csv` are used. None is unassigned.

## Verify your copy

```bash
python release_tools/check_dataset.py --data-dir "/path/to/new_feature_csv" --rows
```

Or, without Python:

```bash
cd "/path/to/new_feature_csv" && shasum -a 256 -c "<package>/dataset/SHA256SUMS_isot_csv"
```

Verified on the author's machine on 2026-10-21: 137/137 SHA-256 match, and all split session and row counts match.

## Note on derived columns

The frozen loader drops six timestamp-contaminated columns (`ts`, `min_duration`, `max_duration`, `sum_duration`, `average_duration`, `flow_idle_time`), leaving 56 numeric features. The checksums above are for the **unmodified** CSV files. Nothing is pre-processed on disk.
