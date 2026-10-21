"""
Re-run the FROZEN confirmatory analysis (code/fl_pipeline/analyze_confirmatory.py)
and the archived POST-HOC reporting supplement (post_hoc/report_supplement.py)
on the saved round outputs, writing to regenerated/analysis/, then diff the
reports against the archived ones in results_confirmatory/analysis/
(NEW release tool, 2026-10-21; no training, no dataset).

    python release_tools/rerun_frozen_analysis.py
"""
import filecmp
import runpy
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import _paths  # noqa: E402


def run(script, out_dir):
    sys.argv = [str(script), "--results-dir", str(_paths.RESULTS), "--out-dir", str(out_dir)]
    runpy.run_path(str(script), run_name="__main__")


def main():
    od = _paths.STAGING / "regenerated" / "analysis"
    od.mkdir(parents=True, exist_ok=True)
    _paths.add_frozen_code_to_path()
    run(_paths.FROZEN_CODE / "fl_pipeline" / "analyze_confirmatory.py", od)       # CONFIRMATORY (frozen)
    run(_paths.FROZEN / "post_hoc" / "report_supplement.py", od)                  # POST-HOC display
    print("\n" + "=" * 60)
    ok = True
    for name in ("summary.txt", "gates.json", "primary_by_round.csv", "supplement.txt", "h2_counts_supplement.csv"):
        same = filecmp.cmp(od / name, _paths.RESULTS / "analysis" / name, shallow=False)
        print(f"{name:28s} {'byte-identical to archived' if same else 'DIFFERS from archived'}")
        ok &= same
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
