# V4 packet-level check: results

Agreement per row: relative difference <= 1e-06 or absolute difference <= 1e-09. A prediction holds if every column reaches 99.9% of rows, pooled and in each session.

## Replication gate (our extraction at the original epoch vs the distributed CSV)

| Session | Category | Sub-files | Rows ours | Rows distributed | Gate |
|---|---|---:|---:|---:|---|
| slowloris_5_1_15mins | DoS | 1 | 177 | 177 | passed |
| Instruction_injection_8_5_14_4mins | Injection | 1 | 359 | 359 | FAILED |
| IP_spoofing_4_5_17_1mins | Ip Spoofing | 1 | 193 | 193 | passed |
| mitm_station_mode_5_5_24 | MITM | 1 | 1,277 | 1,277 | FAILED |
| manipulate_1_5_22_10mins | Manipulation | 1 | 973 | 973 | passed |
| pwd_crack_deau_and_eqpol_1_5_6_30mins_raw | Password Cracking | 12 | 89,053 | 89,053 | passed |
| regular_16_2_5_20 | Regular | 7 | 10,442 | 10,442 | passed |
| replay_4_5_22_10mins | Replay | 1 | 888 | 888 | passed |
| unauthen_8_5_16_3mins | Unauth | 1 | 203 | 203 | FAILED |
| video_6_5_14_5mins | Video | 6 | 8,409 | 8,409 | FAILED |

## V4-P1. Time-dilation columns on IP rows, c = 1.6: **holds**

| Column | Rows | Agreeing | Share | Largest abs. diff. | Largest rel. diff. |
|---|---:|---:|---:|---:|---:|
| `IAT` | 22,921 | 22,921 | 100.000% | 1.78e-15 | 8.85e-13 |
| `flow_active_time` | 22,921 | 22,921 | 100.000% | 2.27e-13 | 2.09e-13 |
| `std_duration` | 22,921 | 22,921 | 100.000% | 8.53e-14 | 1.71e-13 |
| `Srate` | 22,921 | 22,921 | 100.000% | 4.55e-13 | 7.56e-16 |
| `Drate` | 22,921 | 22,921 | 100.000% | 7.28e-12 | 5.25e-15 |
| `Rate` | 22,921 | 22,921 | 100.000% | 2.27e-13 | 8.07e-14 |

## V4-P2a. Time-dilation columns on 802.11 rows, c = 1.6: **holds**

| Column | Rows | Agreeing | Share | Largest abs. diff. | Largest rel. diff. |
|---|---:|---:|---:|---:|---:|
| `IAT` | 89,053 | 89,053 | 100.000% | 8.88e-16 | 9.96e-13 |
| `flow_active_time` | 89,053 | 89,053 | 100.000% | 1.71e-13 | 3.09e-13 |
| `std_duration` | 89,053 | 89,053 | 100.000% | 8.53e-14 | 6.81e-13 |
| `Srate` | 89,053 | 89,053 | 100.000% | 1.46e-11 | 1.74e-15 |
| `Drate` | 89,053 | 89,053 | 100.000% | 9.09e-13 | 1.36e-14 |

## V4-P2b. `Rate` unchanged on 802.11 rows, c = 1.6: **holds**

| Column | Rows | Agreeing | Share | Largest abs. diff. | Largest rel. diff. |
|---|---:|---:|---:|---:|---:|
| `Rate` | 89,053 | 89,053 | 100.000% | 0 | 0 |

## V4-P3. All other model features unchanged, c = 1.6: **holds**

52 columns checked; 52 identical in every row.

## V4-P4. No slice mixes IP and 802.11 packets: **holds**

| Column | Rows | Agreeing | Share | Largest abs. diff. | Largest rel. diff. |
|---|---:|---:|---:|---:|---:|
| `Protocol Type` | 111,974 | 111,974 | 100.000% | 0 | 0 |

## V4-D1. IP rows, c = 1.3 (single-sub-file sessions)

| Column | Rows | Agreeing | Share | Largest abs. diff. | Largest rel. diff. |
|---|---:|---:|---:|---:|---:|
| `IAT` | 4,070 | 4,070 | 100.000% | 8.88e-16 | 9.74e-13 |
| `flow_active_time` | 4,070 | 4,070 | 100.000% | 2.27e-13 | 2.09e-13 |
| `std_duration` | 4,070 | 4,070 | 100.000% | 8.53e-14 | 2.1e-13 |
| `Srate` | 4,070 | 4,070 | 100.000% | 9.09e-13 | 4.36e-16 |
| `Drate` | 4,070 | 4,070 | 100.000% | 1.46e-11 | 4.23e-15 |
| `Rate` | 4,070 | 4,070 | 100.000% | 5.68e-14 | 7.09e-14 |

## V4-D1. 802.11 rows, c = 1.3

| Column | Rows | Agreeing | Share | Largest abs. diff. | Largest rel. diff. |
|---|---:|---:|---:|---:|---:|
| `IAT` | 0 | 0 | n/a | nan | nan |
| `flow_active_time` | 0 | 0 | n/a | nan | nan |
| `std_duration` | 0 | 0 | n/a | nan | nan |
| `Srate` | 0 | 0 | n/a | nan | nan |
| `Drate` | 0 | 0 | n/a | nan | nan |

## V4-D2. Independent scaling (v2) against the re-timed trace, c = 1.6

| Column | Rows | Agreeing | Share | Largest abs. diff. | Largest rel. diff. |
|---|---:|---:|---:|---:|---:|
| `IAT` | 111,974 | 111,974 | 100.000% | 1.78e-15 | 9.96e-13 |
| `flow_active_time` | 111,974 | 111,974 | 100.000% | 2.27e-13 | 3.09e-13 |
| `std_duration` | 111,974 | 0 | 0.000% | 99.7 | 0.6 |
| `Srate` | 111,974 | 0 | 0.000% | 4.53e+04 | 0.563 |
| `Drate` | 111,974 | 19,330 | 17.263% | 2.29e+04 | 0.563 |
| `Rate` | 111,974 | 7,265 | 6.488% | 428 | 1.5 |
| `Entropy` | 111,974 | 89,081 | 79.555% | 4.02 | 3.78e+11 |

## V4-D3. Rows whose `IAT` is empty: same before and after re-timing

| Column | Rows | Agreeing | Share | Largest abs. diff. | Largest rel. diff. |
|---|---:|---:|---:|---:|---:|
| `IAT` | 111,974 | 111,974 | 100.000% | 0 | 0 |

## V4-D4. Original epoch vs re-based baseline (floating-point effect)

58 model columns compared; 53 agree in every row.

| Column | Rows | Agreeing | Share | Largest abs. diff. | Largest rel. diff. |
|---|---:|---:|---:|---:|---:|
| `Srate` | 111,974 | 111,193 | 99.303% | 9.72e+03 | 0.0483 |
| `Drate` | 111,974 | 111,737 | 99.788% | 4.86e+03 | 0.0478 |
| `std_duration` | 111,974 | 111,734 | 99.786% | 4.54e-08 | 0.000229 |
| `IAT` | 111,974 | 34,297 | 30.629% | 7.08e-08 | 0.0187 |
| `flow_active_time` | 111,974 | 111,696 | 99.752% | 2.14e-07 | 0.000263 |
