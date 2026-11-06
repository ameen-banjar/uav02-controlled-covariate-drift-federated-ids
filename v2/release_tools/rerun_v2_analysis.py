"""
Re-run the FROZEN v2 analysis (v2/code/fl_pipeline_v2/analyze_confirmatory_v2.py) on the
saved v2 round outputs, write it to v2/regenerated/analysis/, and compare the reports
byte for byte with the archived ones in v2/results_confirmatory/analysis/. Then regenerate
the post-hoc v2 figures and the pooled H2 table (v2/post_hoc/make_figures_v2.py) and
compare the H2 table with the archived copy. No training, no dataset.

    python3.11 v2/release_tools/rerun_v2_analysis.py
"""
import filecmp
import hashlib
import runpy
import shutil
import sys
from pathlib import Path

sys.dont_write_bytecode = True
V2 = Path(__file__).resolve().parents[1]
CODE = V2 / "code" / "fl_pipeline_v2"
RESULTS = V2 / "results_confirmatory"
OUT = V2 / "regenerated"


def check_hashes():
    ok = True
    for line in (V2 / "SHA256SUMS_v2").read_text().splitlines():
        if not line.strip():
            continue
        digest, rel = line.split(None, 1)
        rel = rel.strip()
        cand = [V2 / "code" / rel, V2 / "code" / Path(rel).name, CODE / Path(rel).name,
                V2 / "code" / "data_audit" / Path(rel).name]
        p = next((c for c in cand if c.exists()), None)
        good = p is not None and hashlib.sha256(p.read_bytes()).hexdigest() == digest
        print(f"{rel:60s} {'matches SHA256SUMS_v2' if good else 'MISMATCH or missing'}")
        ok &= good
    return ok


def main():
    ok = check_hashes()
    od = OUT / "analysis"
    od.mkdir(parents=True, exist_ok=True)
    sys.path.insert(0, str(CODE))
    sys.argv = [str(CODE / "analyze_confirmatory_v2.py"), "--results-dir", str(RESULTS), "--out-dir", str(od)]
    runpy.run_path(str(CODE / "analyze_confirmatory_v2.py"), run_name="__main__")
    print("\n" + "=" * 60)
    for name in ("summary.txt", "gates.json", "primary_by_round.csv"):
        same = filecmp.cmp(od / name, RESULTS / "analysis" / name, shallow=False)
        print(f"{name:28s} {'byte-identical to archived' if same else 'DIFFERS from archived'}")
        ok &= same

    archived_h2 = (V2 / "post_hoc" / "h2_pooled_per_seed.csv").read_bytes()
    sys.argv = [str(V2 / "post_hoc" / "make_figures_v2.py")]
    runpy.run_path(str(V2 / "post_hoc" / "make_figures_v2.py"), run_name="__main__")
    same = (V2 / "post_hoc" / "h2_pooled_per_seed.csv").read_bytes() == archived_h2
    print(f"{'h2_pooled_per_seed.csv':28s} {'identical to archived' if same else 'DIFFERS from archived'}")
    ok &= same
    shutil.rmtree(OUT / "__pycache__", ignore_errors=True)
    print("ALL CHECKS PASSED" if ok else "SOME CHECKS FAILED")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
