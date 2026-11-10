# Drift validity check

Checks a tabular synthetic-drift transform before any model is trained.

It needs two small JSON files and some extracted rows:

- a **feature file** that says what each edited feature holds in the
  extractor, its physical domain, its timing role, and the rate x time
  relations the extractor ties together (`specs/isot_features.json`);
- a **transform file** that lists the per-feature operations and, if there is
  one, the intent the transform claims, for example a uniform re-timing by a
  factor c (`specs/transform_*.json`).

It reports three things:

1. **Meaning.** Each edited feature with what it holds and where in the
   extractor that is defined. A feature whose name does not say what it holds
   is flagged.
2. **Range.** Rows that were inside the physical domain and leave it.
3. **Relations.** Whether each rate x time product is kept, and whether every
   timing feature scales as the stated intent requires.

Run:

```bash
python drift_validity_check.py --features specs/isot_features.json --transform specs/transform_td_full.json --data-list validation_files.txt --out reports/isot_validation_td_full
```

## Reports in this folder

Computed on the 18 ISOT validation sessions (245,526 rows), full strength.

| Transform | Flags | Main findings |
|---|---:|---|
| v1, first campaign | 11 | `Duration` holds the IP time-to-live and leaves [0, 255] in 196,163 rows (79.9%); all three rate x time products change by 0.64; `std_duration` not scaled; `Entropy` edited |
| v2, independent scaling | 8 | no range violation; all three rate x time products change by 0.64; `std_duration` not scaled; `Entropy` edited |
| td, time dilation | 0 | all products kept; every timing feature scales by c or 1/c |

The transforms written in the JSON files were compared with the study's own
code (`drift_v3.apply`) on the same rows: the largest absolute difference is
below 2e-12.

## Using it on another dataset

Write a feature file for that dataset's extractor. The tool does not know
what a column means; it reports what the feature file says and counts what
the transform does to the rows. The feature file is where the reading of the
extraction code is recorded.

## Limits

A transform with no flags is consistent with the feature file. That does not
show that a real network change would produce it. The packet-level check in
`v4_packet_level_check/` tests the time-dilation transform against re-timed
captures.
