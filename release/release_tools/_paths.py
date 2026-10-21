"""
Shared path resolution for the UAV-02 release tools (NEW wrapper code, written
2026-10-21 for the reader-facing package; not part of the frozen protocol).

Nothing here edits a frozen file. The frozen sources are imported read-only
from ../frozen_archive/code after their SHA-256 digests are checked against
../frozen_archive/SHA256SUMS.

Dataset location (never hard-coded to the author's layout):
    --data-dir PATH   (CLI flag on every tool that needs data), else
    $UAV02_ISOT_DATA_DIR
The directory must contain the ISOT `new_feature_csv` category folders
(DoS/, Injection/, ..., Video/) with the 137 session CSVs.
"""
import hashlib
import os
import sys
from pathlib import Path

sys.dont_write_bytecode = True                   # never leave __pycache__ inside the frozen code/
STAGING = Path(__file__).resolve().parent.parent   # the release/ folder (or the staging package root)
if (STAGING / "frozen_archive").is_dir():
    # staging-package layout: release tools next to a byte-identical `git archive 7ac37fa`
    FROZEN = STAGING / "frozen_archive"
    POSTHOC_ADDED = STAGING / "posthoc_added_after_results" / "post_hoc"
else:
    # repository layout: release/ sits at the repository root, next to the frozen files
    FROZEN = STAGING.parent
    POSTHOC_ADDED = FROZEN / "post_hoc"
FROZEN_CODE = FROZEN / "code"
FROZEN_SUMS = FROZEN / "SHA256SUMS"
RESULTS = FROZEN / "results_confirmatory"        # confirmatory outputs (2026-09-25) + post-hoc displays
HELDOUT = POSTHOC_ADDED / "heldout_test"
DATASET_META = STAGING / "dataset"
ENV_VAR = "UAV02_ISOT_DATA_DIR"


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_frozen_code():
    """Same check the frozen runner and post-hoc scripts perform: every file in SHA256SUMS must match."""
    bad = []
    for line in FROZEN_SUMS.read_text().splitlines():
        if line.strip():
            digest, rel = line.split(None, 1)
            if sha256(FROZEN_CODE / rel.strip()) != digest:
                bad.append(rel.strip())
    if bad:
        sys.exit(f"REFUSING: frozen code differs from SHA256SUMS: {bad}")


def add_frozen_code_to_path():
    verify_frozen_code()
    for p in (FROZEN_CODE / "data_audit", FROZEN_CODE / "fl_pipeline"):
        if str(p) not in sys.path:
            sys.path.insert(0, str(p))


def resolve_data_dir(cli_value):
    value = cli_value or os.environ.get(ENV_VAR)
    if not value:
        sys.exit(f"Dataset location not given: pass --data-dir PATH or set ${ENV_VAR} "
                 "(the folder that holds DoS/, Injection/, ..., Video/ from the ISOT new_feature_csv tree).")
    d = Path(value).expanduser().resolve()
    if not d.is_dir():
        sys.exit(f"Dataset directory does not exist: {d}")
    return d


def point_frozen_loader_at(data_dir):
    """Runtime pointer only (same technique as the post-hoc held-out script): the frozen
    data_audit/prepare_isot.py resolves DATA_DIR relative to its own location, and the
    frozen data.py copies that value at import. Both module attributes are reassigned
    in memory; no file is changed."""
    add_frozen_code_to_path()
    import prepare_isot
    import data as data_mod
    prepare_isot.DATA_DIR = data_dir
    data_mod.DATA_DIR = data_dir
    return data_mod
