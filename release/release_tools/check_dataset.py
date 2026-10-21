"""
Dataset identity check for UAV-02 (NEW release tool, 2026-10-21; reads data only,
no training, no model).

Verifies that a reader's local copy of the ISOT Drone Dataset `new_feature_csv`
tree contains byte-identical copies of the 137 session CSVs that the frozen
partition manifest uses, and that the per-split session/row counts match the
manuscript (91 / 18 / 28 sessions; 2,150,122 / 245,526 / 550,338 rows).

    python release_tools/check_dataset.py --data-dir /path/to/new_feature_csv
    python release_tools/check_dataset.py --data-dir ... --rows     # also count rows with pandas

`--write` regenerates dataset/isot_sessions_sha256.csv, dataset/SHA256SUMS_isot_csv
and dataset/expected_split_counts.json from a local copy (author-side only).
"""
import argparse
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _paths  # noqa: E402

TABLE = _paths.DATASET_META / "isot_sessions_sha256.csv"
SUMS = _paths.DATASET_META / "SHA256SUMS_isot_csv"
COUNTS = _paths.DATASET_META / "expected_split_counts.json"
EXPECTED = {"train_clients": (91, 2150122), "validation": (18, 245526), "held_out_test": (28, 550338)}


def split_of_sessions():
    m = json.loads((_paths.FROZEN_CODE / "data_audit" / "federated_clients_manifest.json").read_text())
    split = {}
    for cid, c in m["clients"].items():
        for s in c["sessions"]:
            split[s] = ("train_clients", int(cid))
    for s in m["validation_sessions"]:
        split[s] = ("validation", None)
    for s in m["held_out_test_sessions"]:
        split[s] = ("held_out_test", None)
    return m, split


def count_rows(path):
    import pandas as pd
    return len(pd.read_csv(path))      # same reader the frozen loader uses (data._load_session)


def write(data_dir):
    _, split = split_of_sessions()
    found = {f.stem: f for f in sorted(data_dir.glob("*/*.csv"))}
    missing = sorted(set(split) - set(found))
    if missing:
        sys.exit(f"{len(missing)} manifest sessions missing from {data_dir}: {missing[:5]}")
    rows, totals = [], {}
    for sess in sorted(split, key=lambda s: (split[s][0], found[s].parent.name, s)):
        f = found[sess]
        sp, cid = split[sess]
        n = count_rows(f)
        rows.append({"split": sp, "client_id": "" if cid is None else cid, "category": f.parent.name,
                     "session": sess, "relative_path": f"{f.parent.name}/{f.name}",
                     "size_bytes": f.stat().st_size, "rows": n, "sha256": _paths.sha256(f)})
        t = totals.setdefault(sp, [0, 0])
        t[0] += 1
        t[1] += n
    with open(TABLE, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    SUMS.write_text("".join(f"{r['sha256']}  {r['relative_path']}\n" for r in sorted(rows, key=lambda r: r["relative_path"])))
    COUNTS.write_text(json.dumps({sp: {"sessions": t[0], "rows": t[1]} for sp, t in totals.items()}, indent=2) + "\n")
    print(f"wrote {TABLE.name}, {SUMS.name}, {COUNTS.name}: {len(rows)} files; extra CSVs on disk not in manifest: "
          f"{sorted(set(found) - set(split))}")
    for sp, t in totals.items():
        print(f"  {sp}: {t[0]} sessions, {t[1]:,} rows")


def verify(data_dir, with_rows):
    table = list(csv.DictReader(open(TABLE)))
    bad, missing, totals = [], [], {}
    for r in table:
        f = data_dir / r["relative_path"]
        if not f.exists():
            missing.append(r["relative_path"])
            continue
        if _paths.sha256(f) != r["sha256"]:
            bad.append(r["relative_path"])
        t = totals.setdefault(r["split"], [0, 0])
        t[0] += 1
        if with_rows:
            t[1] += count_rows(f)
    print(f"checked {len(table)} session CSVs under {data_dir}")
    print(f"  missing: {len(missing)}  sha256 mismatch: {len(bad)}")
    for x in (missing + bad)[:10]:
        print("   ", x)
    ok = not missing and not bad
    for sp, (ns, nr) in EXPECTED.items():
        got = totals.get(sp, [0, 0])
        line = f"  {sp}: sessions {got[0]} (expected {ns})"
        ok &= got[0] == ns
        if with_rows:
            line += f", rows {got[1]:,} (expected {nr:,})"
            ok &= got[1] == nr
        print(line)
    print("DATASET IDENTITY: OK" if ok else "DATASET IDENTITY: MISMATCH")
    return ok


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data-dir", help=f"ISOT new_feature_csv folder (or set ${_paths.ENV_VAR})")
    ap.add_argument("--rows", action="store_true", help="also count rows per split with pandas (slower)")
    ap.add_argument("--write", action="store_true", help="author-side: regenerate the identity files")
    a = ap.parse_args()
    d = _paths.resolve_data_dir(a.data_dir)
    if a.write:
        write(d)
    else:
        sys.exit(0 if verify(d, a.rows) else 1)


if __name__ == "__main__":
    main()
