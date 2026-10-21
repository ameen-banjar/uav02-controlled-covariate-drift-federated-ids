"""
Optionally RE-EXECUTE the POST-HOC held-out-test scripts (added 2026-10-19 and
2026-10-21, after the confirmatory results were seen) on the archived frozen
checkpoints (NEW release tool, 2026-10-21). Inference only: no training, no
fine-tuning, no checkpoint selection. Needs the dataset. Not needed to
regenerate Table 6, which make_tables.py builds from the saved outputs.

    python release_tools/rerun_heldout_posthoc.py --script h1_margins --data-dir /path/to/new_feature_csv   # ~1 min
    python release_tools/rerun_heldout_posthoc.py --script heldout    --data-dir ...                        # ~30 min, CPU
    python release_tools/rerun_heldout_posthoc.py --script 9label                                           # no dataset

The scripts locate code, checkpoints and dataset relative to their own file in
the author's layout (REPO = script/.., dataset = REPO/../../development-workspace/
isot_drone_dataset). Rather than editing them, this tool builds a throw-away
"layout view" under --work-dir:
    <work>/development-workspace/isot_drone_dataset -> symlink to --data-dir
    <work>/repositories/paper-02-controlled-concept-drift/
        code -> symlink to frozen_archive/code;  results_confirmatory -> symlink
        SHA256SUMS (copy);  post_hoc/<script>.py (byte-identical copy, hash-checked)
and runs the copied script there. Outputs land in <work>/.../post_hoc/heldout_test/
and are compared with the archived ones in posthoc_added_after_results/.
The default --work-dir is in the system temp folder, deliberately outside this
package, because the view contains a symlink to the raw (non-redistributable) data.
"""
import argparse
import filecmp
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _paths  # noqa: E402

SCRIPTS = {"heldout": ("posthoc_heldout_test.py", ["per_checkpoint_test.csv", "run_info.json"]),
           "9label": ("posthoc_heldout_test_9label.py", ["summary_9label.txt"]),
           "h1_margins": ("posthoc_heldout_test_h1_margins.py", ["h1_margins_test_per_seed.csv", "summary_h1_margins.txt"])}


def link(dst, src):
    if dst.is_symlink() or dst.exists():
        dst.unlink()
    os.symlink(src, dst)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--script", required=True, choices=list(SCRIPTS))
    ap.add_argument("--data-dir", help=f"ISOT new_feature_csv folder (or set ${_paths.ENV_VAR}); not needed for 9label")
    ap.add_argument("--work-dir", default=str(Path(tempfile.gettempdir()) / "uav02_heldout_view"),
                    help="throw-away layout view (keep it OUTSIDE the package: it symlinks the raw dataset)")
    a = ap.parse_args()
    _paths.verify_frozen_code()
    name, outputs = SCRIPTS[a.script]
    work = Path(a.work_dir).resolve()
    repo = work / "repositories" / "paper-02-controlled-concept-drift"
    ph = repo / "post_hoc"
    (ph / "heldout_test").mkdir(parents=True, exist_ok=True)
    (work / "development-workspace").mkdir(parents=True, exist_ok=True)
    if a.script != "9label":
        link(work / "development-workspace" / "isot_drone_dataset", _paths.resolve_data_dir(a.data_dir))
    link(repo / "code", _paths.FROZEN_CODE)
    link(repo / "results_confirmatory", _paths.RESULTS)
    shutil.copyfile(_paths.FROZEN_SUMS, repo / "SHA256SUMS")
    src = _paths.POSTHOC_ADDED / name
    shutil.copyfile(src, ph / name)
    assert _paths.sha256(src) == _paths.sha256(ph / name)
    if a.script == "9label" and not (ph / "heldout_test" / "per_checkpoint_test.csv").exists():
        shutil.copyfile(_paths.HELDOUT / "per_checkpoint_test.csv", ph / "heldout_test" / "per_checkpoint_test.csv")

    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    rc = subprocess.run([sys.executable, str(ph / name)], cwd=str(work), env=env).returncode
    if rc:
        sys.exit(rc)
    print("\ncomparison with archived post-hoc outputs:")
    for o in outputs:
        same = filecmp.cmp(ph / "heldout_test" / o, _paths.HELDOUT / o, shallow=False)
        print(f"  {o:30s} {'byte-identical' if same else 'DIFFERS (inspect; float/backend differences are possible)'}")


if __name__ == "__main__":
    main()
