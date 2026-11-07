# UAV-02 v3 — post-freeze addendum (2026-11-06, written while the campaign runs)

Written after the freeze (tag `uav02-v3-freeze`, commit d5124d1, 2026-11-06T12:03:41+03:00; job list written 12:04:00) and after 29 of 360 jobs had finished. No v3 result had been analysed. It changes **no** code, arm, seed, threshold or gate; `DESIGN_V3.md` stays as frozen. It corrects the *justification and wording* of the design in response to an external review. It will be added to the repository only after the campaign ends, because the runner requires a clean repository with the freeze tag at HEAD.

## A1. Mean of products (correction to DESIGN_V3 §2)

DESIGN_V3 §2 says that the identities rate × time = packets (or bits) "hold exactly for every row". That is wrong as stated: each row is a mean over 10 packets, and the mean of the rates times the mean of the times is not, in general, the mean of the per-packet products.

The correct argument does not use products. Under a uniform re-timing of the recorded trace, every per-packet time value (IAT, flow active time, std of flow timestamps) is multiplied by c, and every per-packet time-derived rate (Srate, Drate, IP-row Rate) is divided by c. Because the row mean is linear, each row mean scales by the same factor. So the transformed row equals what the extractor would output for the re-timed trace, *given the extractor's per-packet definitions*.

The product assertions in `drift_v3.apply` are **invariance checks under the transform**. They guard against implementation errors. They do not validate the features against packet or bit counts, and they are reported as such.

## A2. 802.11 window detection (verified, not assumed)

The extractor (isot-lab 783e9bf, `Feature_extraction.py` l. 223) sets `Protocol Type = 802.11` for 802.11 packets. IP packets carry their IP protocol number, and every value in the data is ≤ 17.

The guarantee comes from two extractor facts:

- the 802.11 code is 802.11;
- a row aggregates at most 10 packets (`n_rows = 10`, l. 656).

With IP codes non-negative and ≤ 17, one 802.11 packet in a window gives a mean of at least 802.11/10 = **80.211**. A window with no 802.11 packet has a mean of at most 17. The threshold therefore separates the two by construction.

Empirical check over all 2,945,986 ISOT rows:

| Window type | Mean `Protocol Type` | Share of rows |
|---|---|---:|
| Pure IP | ≤ 17 | 92.15% |
| **Mixed** (some 802.11, some IP) | between 80.211 and 802.11 | **0 rows** |
| Pure 802.11 | exactly 802.11 | 7.85% |

The smallest value above 17 is 802.11 itself.

**Consequence for the `Rate` exception.** No window mixes IP and 802.11 packets in this dataset. On every row where `Rate` is left unchanged, `Rate` is the radiotap PHY rate of 802.11 frames only, with no time-derived component. Leaving it unchanged is therefore the re-timing-consistent value for those rows, not an approximation.

The conceptual issue of mixed windows, where the ideal transform would be the mean of R_PHY + R_time/c, is real in general. It does not arise in this data. It is still stated as a scope condition: the argument holds for this extractor's output on this dataset, and a dataset with mixed windows would need a different treatment.

## A3. `Duration`: TTL on IP rows, 0 on 802.11 rows

`Duration` is the IP TTL on IP packets. On 802.11 packets the extractor writes a frame duration field (l. 235). In the data, `Duration` is **0 on every pure-802.11 row** (max 0.00).

So:

- **Rows above 255 under ×1.6:** every one of the transformed `Duration` values above 255 in v1 comes from pure-IP rows, where the field is a TTL. They are 58.29% of pure-IP rows and 53.72% of all rows.
- **Where the TTL argument applies:** the "largest possible IP TTL is 255" argument applies exactly to the rows it was used for. No 802.11 row reaches 255, and none is given a TTL interpretation.
- **Manuscript wording:** "TTL" must be said for IP rows. The 802.11 field is identically zero in this dataset.
- **v1 ablation:** its results remain effects of editing the column, independent of the physical interpretation.
- **`td` and Duration:** `td` leaves `Duration` unchanged on both row types. This keeps packet contents fixed. It does not show that channel-reservation behavior after re-timing would be realistic.

## A3b. Aggregation is count-based

Rows are consecutive 10-packet slices (l. 656–671). The extractor contains no flow time-out or time-window logic (searched for timeout, idle and expiry). Re-timing a trace therefore leaves window and flow membership unchanged in this extractor. Fixed aggregation is a property of the extractor, and the manuscript states it as an assumption of `td`.

## A4. Claim scope of `td`

`td` models a **uniform re-timing of a recorded trace with packets, contents and window composition held fixed**. It does not model a slower network in full: queueing, loss, retransmission, time-outs and application reactions are not represented.

Wording to use: "a time-dilation intervention that preserves the stated scaling relations of the affected features, under fixed packets and fixed aggregation windows."

## A5. Seeds

There are ten training seeds per main combination (131–230), reused across algorithms, interventions and schedules. Two algorithms × ten seeds give twenty runs, not twenty independent seeds. Comparisons that share a seed and its none reference are paired, and therefore correlated. v1/v2 seeds are not pooled with v3.

## A6. `fresh` sessions

The 12 sessions were in the v1/v2 training pool. They were never used for *evaluation*, and in the `fresh` arm they are excluded from training and from the scaler fit.

They are "newly held-out sessions, never evaluated before". They are not "data untouched by development".

## A7. Robustness arms: what they do not show

- **Exposure k:** the change in k is confounded with which clients and classes are added (fixed Regular-share order).
- **α arms:** one partition seed (42) each.
- **α = 100:** not IID, given few sessions of unequal size.
- **arch_wide:** one wider MLP, not other model families.
- **partial10:** seeded random participation, not state-dependent dropout.
- **cic:** a different extractor with different feature definitions; only the direction is compared, and it is not a UAV field test.

## A8. TOST

- TOST is computed on per-seed paired differences: L2 and L3 use the same-seed none run (`analyze_v3.py`, `none_ref`, keyed by seed).
- The equivalence decision is the 90% t-interval inside ±0.01 macro-F1, an aggregate macro-F1 statement only. It is not a per-class or per-seed statement.
- **Margin rationale (stated now, post-freeze):** 0.01 is about one third to one half of the immediate L1 effects observed in v2 (−0.025 to −0.033). A residual that small is well below the effect the study is designed to detect. (Comparison with the between-seed SD will be reported from the v3 data, not assumed here.)
- "Equivalence not shown" is a reportable outcome. Wording before results: "we test equivalence within ±0.01".

## A9. Component decomposition

`td_time_only` and `td_rate_only` each break the joint scaling that `td` preserves. They are sensitivity probes of the components, not a causal decomposition. Non-additivity is reported, and additivity is not assumed.

## A10. Freeze

- Order of events:

  | Event | Time (+03:00) |
  |---|---|
  | Freeze commit | 12:03:41 |
  | Job list written | 12:04:00 |
  | First job logs created | 12:04:03 |

- **What had been seen when this addendum was written.** From the campaign, only completion lines, exit codes and run times had been read, by grep on `[done]` and `_done.txt`. No per-round metric, rounds/probes/H1 CSV or summary had been opened or analysed.
- The runner refuses to start without the tag at HEAD and a clean tree matching `SHA256SUMS_v3`.
- The freeze establishes order and traceability, not correctness. Any future protocol change will be a dated amendment, analysed separately from the frozen analysis.

## Revision log

- r1, 2026-11-06 ~15:20: A1–A10 written after 29 of 360 jobs.
- r2, 2026-11-06 15:27 +0300: after a second external review. A2 corrected (bound 80.211, not 80.11; mixed-window count 0); A3 rewritten (Duration = 0 on all 802.11 rows; TTL argument confined to pure-IP rows); A3b added; A10 sees-what statement added. 32 of 360 jobs complete at r2.
