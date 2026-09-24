# Paper 2 — Controlled Concept Drift in Federated UAV Intrusion Detection

**Status:** Design frozen; confirmatory execution pending/in progress. See `DESIGN_FROZEN.md`
(calibration vs confirmatory phases, endpoints, gates, seed policy, change log).

- `code/` — frozen copy of the exact source used for the confirmatory run (same relative layout as the
  development workspace; the dataset itself is not included). `SHA256SUMS` pins every file; the runner refuses to
  execute unless the sources match it and this repo is clean and tagged `uav02-confirmatory-freeze-v1`.
- Calibration pilots (v2/v3, seed 11) are NOT confirmatory evidence. Confirmatory seeds: 21, 32, 43, 54, 65.
