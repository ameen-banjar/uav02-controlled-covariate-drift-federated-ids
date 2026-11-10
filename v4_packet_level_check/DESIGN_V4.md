# V4 design: packet-level check of the time-dilation transform

Status: FROZEN by the commit that carries the tag `uav02-v4-freeze`. The
design and the code in `code/` were written and tested on a synthetic capture
(`selftest`, 1,203 generated packets) before any raw capture file was opened.
Written 2026-11-10, after all v1 to v3 results were known. It is a
post-freeze addition to the study. No model is trained or evaluated here, so
no v1 to v3 number can change.

## 1. Claim under test

Section 3.4 of the manuscript states that the tabular time-dilation transform
(`td`, `v3/code/fl_pipeline_v3/drift_v3.py`) returns the row "the extractor
would output for the uniformly re-timed trace, given its per-packet
definitions". Until now this rests on reading the extractor code and on an
identity assertion inside the transform. V4 tests it directly: re-time the
packets, run the extractor again, and compare with the transformed table.

## 2. What V4 can and cannot show

It can show whether the table transform reproduces the extractor's output for
a trace whose packet timestamps were stretched by a constant factor.

It cannot show that a real slower network would produce that trace. Queueing,
loss, retransmission, time-outs and application reactions are not modelled.
The manuscript wording on this point stays as it is.

## 3. Materials

- Raw captures: the ISOT Drone Anomaly Detection Dataset archive linked from
  the ISOT Research Lab page (manuscript reference [7]). Record the archive
  SHA-256 and the SHA-256 of every capture file used.
- Extractor: `isot-lab/Drone-Anomaly-Detection-Dataset-and-Unsupervised-Machine-Learning`,
  commit `783e9bf8d7235ed01ecbe6f1d801381c967278ff`, directory
  `feature_extraction/`. Feature code is used unmodified. The driver
  `Generating_dataset.py` is replaced by our own driver that keeps its steps
  (split with `tcpdump -C 20`, one `Feature_extraction()` per sub-file,
  10-packet mean rows) but runs at most 3 low-priority processes and keeps the
  per-sub-file CSV files apart. Any other change needed to run the code is
  recorded as a diff in `deviations/`.
- Distributed CSV files: the copies already used for v1 to v3
  (`MANIFEST.json` hashes).

## 4. Sample (fixed before any capture is opened)

Rule: for each of the ten categories, the session whose distributed CSV file
is smallest in bytes (ties by file name). The rule uses only files the study
already holds.

| Category | Session |
|---|---|
| DoS | slowloris_5_1_15mins |
| Injection | Instruction_injection_8_5_14_4mins |
| Ip Spoofing | IP_spoofing_4_5_17_1mins |
| MITM | mitm_station_mode_5_5_24 |
| Manipulation | manipulate_1_5_22_10mins |
| Password Cracking | pwd_crack_deau_and_eqpol_1_5_6_30mins_raw |
| Regular | regular_16_2_5_20 |
| Replay | replay_4_5_22_10mins |
| Unauth | unauthen_8_5_16_3mins |
| Video | video_6_5_14_5mins |

If a listed capture is missing from the archive or cannot be read, take the
next smallest session of that category and record the substitution.

## 5. Procedure, per session

Code: `code/run_session.py`, `code/retime_pcap.py`, `code/extract_one.py`.

1. Split the original capture with `tcpdump -r <file> -w <prefix> -C 20`.
2. **Original-epoch extraction.** Run the extractor on every sub-file.
   Output: `F0`.
3. **Replication gate.** Compare `F0` with the distributed CSV of that
   session: same row count, and after sorting both by `ts`, the columns
   `IAT, flow_active_time, std_duration, Srate, Drate, Rate, Protocol Type`
   agree within relative tolerance 1e-6 in every row. A failed gate is
   reported. The session stays in the comparison, because the steps below
   compare the extractor with itself, and the gate result is shown beside it.
4. **Re-based and re-timed copies.** For every sub-file, write copies in
   which each packet timestamp t becomes 1 s + c (t − t0), where t0 is the
   first timestamp of the sub-file, for c = 1 (re-based baseline), c = 1.6
   (primary) and c = 1.3 (secondary, only for sessions that split into a
   single sub-file, to bound the running time). Packet bytes and order are
   unchanged. The arithmetic is done on integer nanoseconds and the copies
   carry nanosecond timestamps, so both factors are exact for microsecond
   input. The split is not repeated, so slice and flow membership are
   identical by construction.
   The origin is moved because the extractor keeps capture times as
   floating-point seconds. At the original epoch (about 1.7e9 s) their
   resolution is about 2.4e-7 s, which would add rounding noise unrelated to
   the claim. Every model feature depends on time differences only, so the
   origin does not enter the claim. The effect of the origin is reported
   separately (V4-D4).
5. Run the extractor on the copies. Outputs: `F0b` (c = 1) and `F_pcap(c)`.
6. Apply the table transform to the re-based baseline:
   `F_table(c) = drift_v3.apply(F0b, s, "td")`, with s = 1 for c = 1.6 and
   s = 0.5 for c = 1.3. Rows are matched by position within each sub-file. A
   sub-file whose row count differs between `F_pcap` and `F0b` counts as
   disagreeing in every row.

Environment for the extractor: Python 3.11, pandas 1.5.3, numpy 1.26.4,
scipy below 1.14, dpkt 1.9.8, scapy 2.8.0. pandas 1.5 is required because
the extractor averages a frame that contains a text column, which later
pandas versions refuse. The analysis script runs in the study's own
environment and imports the frozen `v3/code/fl_pipeline_v3/drift_v3.py`.

## 6. Outcomes

`F_pcap` is compared with `F_table`, both derived from the re-based copies.
For each column and row, the relative difference is
|F_pcap − F_table| / max(|F_table|, 1e-12). A row agrees on a column if the
relative difference is at most 1e-6 or the absolute difference is at most
1e-9. Missing values must be missing in both.

Model feature columns are the columns the detector reads, that is, all
extractor columns except `ts, min_duration, max_duration, sum_duration,
average_duration, flow_idle_time`.

Predictions, stated before the data are seen:

- **V4-P1.** On IP rows, each of `IAT, flow_active_time, std_duration,
  Srate, Drate, Rate` agrees in at least 99.9% of rows, at c = 1.6.
- **V4-P2.** On 802.11 rows, `IAT, flow_active_time, std_duration, Srate,
  Drate` agree in at least 99.9% of rows and `Rate` is unchanged from `F0`
  in at least 99.9% of rows.
- **V4-P3.** Every other model feature column is unchanged from `F0` in at
  least 99.9% of rows.
- **V4-P4.** No slice mixes IP and 802.11 packets in the sampled sessions.

Each prediction is reported as holds or fails, per session and pooled, with
the share of agreeing rows and the largest difference. For every failure the
disagreeing rows are traced to the extractor line that produced them. A
failed prediction is reported in the manuscript as a limit of the table
transform; the transform is not edited afterwards to make it pass.

Descriptive, no prediction:

- **V4-D1.** The same table for c = 1.3, on the sessions that have a single
  sub-file.
- **V4-D2.** Distance of the independent-scaling transform (`v2`, s = 1) from
  `F_pcap(1.6)` on the same six columns. `v2` has no packet-level
  counterpart; this row only shows how far it is from the re-timed trace.
- **V4-D3.** Rows whose `IAT` is empty, before and after re-timing.
- **V4-D4.** `F0` against `F0b` on all model feature columns: what moving
  the time origin changes.

## 7. Known points where the extractor could break the claim

Listed from reading the code, before any run:

- `get_data_rate` substitutes the previous interval when an interval is zero.
- `IAT` on IP rows is left empty when the interval equals the previous one.
- 802.11 inter-arrival times use floating-point capture times, IP rows use
  exact decimal times.
- `std_duration` is computed on absolute epoch times of about 1.7e9 seconds,
  so floating-point resolution is about 2e-7 seconds.

## 8. Execution limits

At most 3 processes, low priority, one session at a time, output per
sub-file so that an interrupted run resumes. The analysis script
(`code/analyze_v4.py`) is run once after all sessions finish; it records its
timestamp and refuses a second run.

## 9. Reporting

Results go to `v4_packet_level_check/results/`. The manuscript reports V4 as
a post-freeze packet-level check in the methods and in one short results
paragraph, with the full table in the supplement.
