#!/usr/bin/env python3
"""Check the frozen v3 files of this repository against v3/SHA256SUMS_v3.

Added in release 3.1.0 (2026-11-12); not part of the frozen protocol.

SHA256SUMS_v3 lists paths as they were in the development workspace
(`data_audit/...` and `fl_pipeline_v3/...`). In this repository the same files
are stored under `v3/code/`:

    data_audit/<file>       ->  v3/code/<file>
    fl_pipeline_v3/<path>   ->  v3/code/fl_pipeline_v3/<path>

The three prepared CICIoT2023 data files are not redistributed, so they are
reported as "not in the repository" and do not count as failures.

Usage:  python3 v3/verify_v3_hashes.py        (from the repository root)
"""
import hashlib
import sys
from pathlib import Path

V3 = Path(__file__).resolve().parent
NOT_REDISTRIBUTED = {
    "fl_pipeline_v3/cic_prepared/train.parquet",
    "fl_pipeline_v3/cic_prepared/train_client.npy",
    "fl_pipeline_v3/cic_prepared/validation.parquet",
}


def repo_path(rel):
    if rel.startswith("data_audit/"):
        return V3 / "code" / rel[len("data_audit/"):]
    return V3 / "code" / rel


def main():
    ok = bad = absent = 0
    for line in (V3 / "SHA256SUMS_v3").read_text().splitlines():
        if not line.strip():
            continue
        digest, rel = line.split(None, 1)
        rel = rel.strip()
        p = repo_path(rel)
        if not p.exists():
            if rel in NOT_REDISTRIBUTED:
                absent += 1
                print(f"not in the repository (data, not redistributed): {rel}")
            else:
                bad += 1
                print(f"MISSING: {rel}")
            continue
        if hashlib.sha256(p.read_bytes()).hexdigest() == digest:
            ok += 1
        else:
            bad += 1
            print(f"MISMATCH: {rel}")
    print(f"{ok} files match, {absent} data files not redistributed, {bad} problems")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
