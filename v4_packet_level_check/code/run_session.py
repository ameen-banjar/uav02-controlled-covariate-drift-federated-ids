"""
V4 driver for one capture session.

Steps (DESIGN_V4.md, section 5):
  1. split the original capture with  tcpdump -r IN -w PREFIX -C 20
  2. write re-based / re-timed copies of every sub-file (retime_pcap.py):
       c10  factor 1     (re-based baseline)
       c16  factor 16/10 (primary)
       c13  factor 13/10 (secondary; only if the session has ONE sub-file)
  3. run the unmodified extractor on every sub-file of: orig, c10, c16[, c13]

At most --workers processes (default 3), each started with low priority.
Finished sub-file CSVs are kept, so an interrupted run resumes.

Usage: run_session.py --pcap FILE --session NAME --work DIR --extractor DIR --python VENV_PYTHON
"""
import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from retime_pcap import retime  # noqa: E402

FACTORS = {"c10": (1, 1), "c16": (16, 10), "c13": (13, 10)}


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def subfile_order(name):
    tail = name[len("split"):]
    return int(tail) if tail else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pcap", required=True)
    ap.add_argument("--session", required=True)
    ap.add_argument("--work", required=True)
    ap.add_argument("--extractor", required=True)
    ap.add_argument("--python", required=True)
    ap.add_argument("--workers", type=int, default=3)
    a = ap.parse_args()
    assert a.workers <= 3, "at most 3 workers on this machine"

    root = Path(a.work) / a.session
    meta_path = root / "session_meta.json"
    meta = json.loads(meta_path.read_text()) if meta_path.exists() else {}
    (root / "orig").mkdir(parents=True, exist_ok=True)

    # 1. split (once)
    if not meta.get("split_done"):
        meta["capture"] = os.path.basename(a.pcap)
        meta["capture_bytes"] = os.path.getsize(a.pcap)
        meta["capture_sha256"] = sha256(a.pcap)
        for old in (root / "orig").glob("split*"):
            old.unlink()
        r = subprocess.run(["tcpdump", "-r", a.pcap, "-w", str(root / "orig" / "split"), "-C", "20"],
                           capture_output=True, text=True)
        meta["tcpdump_returncode"] = r.returncode
        meta["tcpdump_stderr_tail"] = r.stderr[-400:]
        meta["split_done"] = True
        meta_path.write_text(json.dumps(meta, indent=2))
    subs = sorted([p.name for p in (root / "orig").iterdir() if p.name.startswith("split") and "." not in p.name],
                  key=subfile_order)
    assert subs, "tcpdump produced no sub-file"
    meta["subfiles"] = subs

    # 2. re-timed copies
    variants = ["c10", "c16"] + (["c13"] if len(subs) == 1 else [])
    meta["variants"] = ["orig"] + variants
    for v in variants:
        (root / v).mkdir(exist_ok=True)
        num, den = FACTORS[v]
        for s in subs:
            dst = root / v / s
            if not dst.exists():
                tmp = root / v / (s + ".tmp")
                n, inexact = retime(root / "orig" / s, tmp, num, den)
                tmp.rename(dst)
                meta.setdefault("retime", {})[f"{v}/{s}"] = {"packets": n, "inexact_divisions": inexact}
    meta_path.write_text(json.dumps(meta, indent=2))

    # 3. extraction
    tasks = [(v, s) for v in ["orig"] + variants for s in subs]

    def run(task):
        v, s = task
        out_prefix = root / v / (s + "_features")
        done = Path(str(out_prefix) + ".csv")
        if done.exists():
            return v, s, 0, 0.0
        t = time.time()
        log = open(root / v / (s + ".log"), "w")
        r = subprocess.run(["nice", "-n", "15", a.python, str(HERE / "extract_one.py"),
                            a.extractor, str(root / v / s), str(out_prefix)], stdout=log, stderr=log)
        log.close()
        return v, s, r.returncode, time.time() - t

    failures = 0
    with ThreadPoolExecutor(max_workers=a.workers) as pool:
        for v, s, rc, sec in pool.map(run, tasks):
            print(f"{a.session} {v}/{s}: exit {rc} in {sec:.0f}s", flush=True)
            failures += rc != 0
    meta["extraction_failures"] = failures
    meta["finished"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    meta_path.write_text(json.dumps(meta, indent=2))
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
