"""
Portable launcher for the FROZEN UAV-02 confirmatory runner (NEW wrapper code,
2026-10-21; not part of the frozen protocol, changes no frozen file).

The frozen runner (code/fl_pipeline/run_drift_confirmatory.py) assumes the
author's development-workspace layout:
  * the dataset at code/isot_drone_dataset (via data_audit/prepare_isot.py),
  * the freeze repository at ../repositories/paper-02-controlled-concept-drift,
  * outputs at code/fl_pipeline/results_drift_confirmatory.
This launcher imports the runner from a git checkout of the freeze tag and
reassigns those module attributes in memory before calling its main():
  data.DATA_DIR / prepare_isot.DATA_DIR  <- --data-dir or $UAV02_ISOT_DATA_DIR
  run_drift_confirmatory.REPO_DIR        <- --freeze-checkout
  run_drift_confirmatory.RESULTS_DIR     <- --out (must be OUTSIDE the checkout)

The runner's own guard is NOT bypassed. It still refuses to train unless every
source file matches SHA256SUMS, the checkout has no uncommitted or untracked
changes, and HEAD carries the tag `uav02-confirmatory-freeze-v1`. Re-running
training therefore requires a checkout of that tag, e.g. from the git bundle
shipped in this package:

    git clone uav02_repository.bundle uav02-freeze
    git -C uav02-freeze checkout uav02-confirmatory-freeze-v1

Usage:
    python release_tools/run_confirmatory.py --freeze-checkout uav02-freeze \
        --data-dir /path/to/new_feature_csv --check-only
    python release_tools/run_confirmatory.py --freeze-checkout uav02-freeze \
        --data-dir /path/to/new_feature_csv --out runs/ --seed 21     # full re-training (~4-9 h per seed)

--check-only runs the frozen guard and the frozen preprocessing fit (data
loading only), then exits without training. --smoke DIR forwards the frozen
runner's own wiring test (fake seed 999, 3 rounds, no frozen-state checks); it
is never confirmatory evidence.

A re-run is not expected to be bitwise identical to the archived outputs:
the confirmatory run used PyTorch 2.10.0 on Apple MPS (see environment/).
"""
import argparse
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import _paths  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--freeze-checkout", required=True, help="git checkout whose HEAD is tag uav02-confirmatory-freeze-v1")
    ap.add_argument("--data-dir", help=f"ISOT new_feature_csv folder (or set ${_paths.ENV_VAR})")
    ap.add_argument("--out", help="output directory for round CSVs, checkpoints, provenance (outside the checkout)")
    ap.add_argument("--seed", type=int, help="one of the frozen seeds 21, 32, 43, 54, 65")
    ap.add_argument("--check-only", action="store_true", help="guard + preprocessing fit only; no training")
    ap.add_argument("--smoke", help="frozen runner's wiring test only (writes to this dir)")
    a = ap.parse_args()

    repo = Path(a.freeze_checkout).expanduser().resolve()
    code = repo / "code"
    if not (code / "fl_pipeline" / "run_drift_confirmatory.py").exists():
        sys.exit(f"{repo} does not look like a UAV-02 freeze checkout (no code/fl_pipeline/run_drift_confirmatory.py)")
    data_dir = _paths.resolve_data_dir(a.data_dir)

    for p in (code / "data_audit", code / "fl_pipeline"):
        sys.path.insert(0, str(p))
    import prepare_isot  # noqa: E402  (frozen, from the checkout)
    import data as data_mod  # noqa: E402
    prepare_isot.DATA_DIR = data_dir
    data_mod.DATA_DIR = data_dir
    import run_drift_confirmatory as rdc  # noqa: E402
    rdc.REPO_DIR = repo

    if a.check_only:
        prov = rdc.verify_frozen_state()          # exits with the runner's own REFUSING message on failure
        print(f"frozen guard passed: HEAD {prov['git_head']} tag {prov['tag']}; {len(prov['file_sha256'])} files match SHA256SUMS")
        d = data_mod.ISOTFederatedData()
        d.fit_preprocessing()
        print(f"dataset wiring OK: {len(d._cat_of)} session CSVs found under {data_dir}; {len(d.feature_cols)} features")
        print("check-only: no training performed")
        return

    if a.smoke:
        sys.argv = [rdc.__file__, "--smoke", a.smoke]
        rdc.main()
        return

    if not a.out or a.seed is None:
        sys.exit("--out and --seed are required for a training run")
    out = Path(a.out).expanduser().resolve()
    if out == repo or repo in out.parents:
        sys.exit("--out must be outside the freeze checkout (outputs inside it would make the guard fail for the next seed)")
    rdc.RESULTS_DIR = out
    status = subprocess.run(["git", "-C", str(repo), "status", "--porcelain"], capture_output=True, text=True).stdout
    if status.strip():
        print("note: the checkout is not clean; the frozen guard will refuse to run:\n" + status, file=sys.stderr)
    sys.argv = [rdc.__file__, "--seed", str(a.seed)]
    rdc.main()


if __name__ == "__main__":
    main()
