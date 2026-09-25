"""
Run manifest for the UAV-02 confirmatory study. METADATA ONLY: reads the
runner's provenance_seed*.json files and result-file modification times; it
never opens a results CSV or log, so it cannot leak outcomes.

Compiled post hoc -- the frozen runner did not record per-run end times,
hardware, or execution mode, so those are reconstructed here from artifacts
(file mtimes, sysctl, installed packages). For runs after the first within a
seed process, start time is DERIVED (= end of the previous run in that
process); the first run's start includes data loading. Not part of the frozen
code set.
"""
import argparse
import datetime as dt
import json
import os
import platform
import subprocess
from importlib import metadata
from pathlib import Path

HERE = Path(__file__).resolve().parent
RD_DEFAULT = HERE.parent / "results_drift_confirmatory"
SEEDS = [21, 32, 43, 54, 65]
RUN_ORDER = [(a, s) for a in ("fedavg", "fedprox") for s in ("none", "sudden", "gradual", "recurring")]
LAUNCH_NOTE = ("seeds launched as separate OS processes via `xargs -P 3` (up to 3 concurrent on one machine); "
               "each process has its own RNG state (torch/numpy seeded per run) and writes only seed-prefixed files")


def iso(t):
    return dt.datetime.fromtimestamp(t).astimezone().isoformat(timespec="seconds") if t else None


def sysctl(k):
    try:
        return subprocess.run(["sysctl", "-n", k], capture_output=True, text=True).stdout.strip()
    except Exception:
        return None


def pkg(n):
    try:
        return metadata.version(n)
    except Exception:
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--results-dir", default=str(RD_DEFAULT))
    rd = Path(ap.parse_args().results_dir)

    provs = {}
    for s in SEEDS:
        p = rd / f"provenance_seed{s}.json"
        if p.exists():
            provs[s] = json.loads(p.read_text())
    heads = {(v["git_head"], v["tag"]) for v in provs.values()}
    runs, intervals = [], {}
    for s, pv in provs.items():
        prev = pv["started_unix"]
        for algo, sched in RUN_ORDER:
            f = rd / f"seed{s}_{algo}_{sched}_rounds.csv"
            end = os.stat(f).st_mtime if f.exists() else None
            runs.append({"seed": s, "algorithm": algo, "schedule": sched, "complete": end is not None,
                         "start_derived": iso(prev), "start_timestamp_kind": ("derived/inferred (runner process start, includes data loading; NOT a measured run start)" if prev == pv["started_unix"] else "derived/inferred (= end of previous run in this process; NOT measured)"), "end": iso(end),
                         "wall_seconds": round(end - prev) if end else None,
                         "frozen_commit": pv["git_head"], "tag": pv["tag"], "device": pv["device"],
                         "torch": pv["torch"]})
            if end:
                prev = end
        ends = [os.stat(rd / f"seed{s}_{a}_{sc}_rounds.csv").st_mtime for a, sc in RUN_ORDER
                if (rd / f"seed{s}_{a}_{sc}_rounds.csv").exists()]
        done = len(ends) == len(RUN_ORDER)
        intervals[s] = (pv["started_unix"], max(ends) if done else None)

    now = dt.datetime.now().timestamp()
    events = []
    for s, (a, b) in intervals.items():
        events += [(a, 1), ((b if b else now), -1)]
    cur = peak = 0
    for _, d in sorted(events):
        cur += d
        peak = max(peak, cur)

    manifest = {
        "compiled_at": iso(now),
        "compiled_post_hoc_from": "runner provenance files + file mtimes (no result contents read)",
        "frozen_commit_and_tag": sorted(heads),
        "consistent_commit_across_seeds": len(heads) == 1,
        "execution_mode": "parallel (concurrent processes), not serial",
        "launch_note": LAUNCH_NOTE,
        "measured_peak_concurrent_seed_processes": peak,
        "seed_process_intervals": {str(s): {"start": iso(a), "end": iso(b) if b else "running/incomplete"}
                                   for s, (a, b) in intervals.items()},
        "hardware": {"platform": platform.platform(), "machine": platform.machine(),
                     "cpu": sysctl("machdep.cpu.brand_string"), "logical_cpus": sysctl("hw.ncpu"),
                     "memory_bytes": sysctl("hw.memsize")},
        "backend": sorted({r["device"] for r in runs}),
        "determinism_note": "MPS backend; bitwise determinism not guaranteed. Optional single serial spot-check (QA only, never substitutes a run) may be added after the study.",
        "environment": {"python": platform.python_version(),
                        **{n: pkg(n) for n in ("torch", "numpy", "pandas", "scikit-learn", "scipy", "matplotlib")}},
        "runs": runs,
    }
    (rd / "RUN_MANIFEST.json").write_text(json.dumps(manifest, indent=2))
    lines = ["# UAV-02 confirmatory run manifest", "",
             f"- Frozen commit/tag: {sorted(heads)} (consistent across seeds: {len(heads) == 1})",
             f"- Execution: parallel; measured peak concurrent seed processes = {peak}. {LAUNCH_NOTE}",
             f"- Hardware: {manifest['hardware']['cpu']}, {manifest['hardware']['logical_cpus']} logical CPUs; backend {manifest['backend']}",
             f"- Environment: {manifest['environment']}", "- Compiled post hoc (see script docstring); start times after a seed's first run are derived.", "",
             "| seed | algorithm | schedule | start (DERIVED/INFERRED, not measured) | end (file mtime) | wall s | complete |", "|---|---|---|---|---|---|---|"]
    lines += [f"| {r['seed']} | {r['algorithm']} | {r['schedule']} | {r['start_derived']} | {r['end']} | {r['wall_seconds']} | {r['complete']} |" for r in runs]
    (rd / "RUN_MANIFEST.md").write_text("\n".join(lines))
    done = sum(r["complete"] for r in runs)
    print(f"manifest written: {done}/{len(runs)} runs complete, peak concurrency {peak}, commits {sorted(heads)}")


if __name__ == "__main__":
    main()
