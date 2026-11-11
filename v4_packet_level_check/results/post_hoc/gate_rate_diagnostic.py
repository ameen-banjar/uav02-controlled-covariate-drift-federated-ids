"""
Post hoc diagnostic, written AFTER the frozen analysis was run (2026-11-11).
Question: in the sessions whose replication gate failed, which columns differ
between our original-epoch extraction and the distributed CSV, and do the
Rate differences coincide with Payload_Length differences?
Usage: gate_rate_diagnostic.py WORK_DIR SESSIONS_JSON OUT_JSON
"""
import glob, json, re, sys
import numpy as np, pandas as pd
work, sessions, out = sys.argv[1:4]
S = json.load(open(sessions)); res = {}
for s, info in S.items():
    fs = sorted(glob.glob(f"{work}/{s}/orig/*_features.csv"), key=lambda p: int(re.search(r"split(\d*)_", p).group(1) or 0))
    a = pd.concat([pd.read_csv(f) for f in fs]).sort_values("ts", kind="stable").reset_index(drop=True)
    b = pd.read_csv(info["distributed_csv"]).sort_values("ts", kind="stable").reset_index(drop=True)
    def bad(c):
        x, y = a[c].to_numpy(float), b[c].to_numpy(float)
        ok = (np.abs(x - y) <= 1e-9) | (np.abs(x - y) / np.maximum(np.abs(y), 1e-12) <= 1e-6) | (np.isnan(x) & np.isnan(y))
        return ~ok
    num = [c for c in a.columns if c in b.columns and a[c].dtype != object]
    diff = {c: int(bad(c).sum()) for c in num if bad(c).any()}
    r, p = bad("Rate"), bad("Payload_Length")
    res[s] = {"rows": len(a), "columns_differing": diff, "rate_bad": int(r.sum()), "payload_bad": int(p.sum()),
              "rate_bad_with_payload_bad": int((r & p).sum()), "rate_bad_without_payload_bad": int((r & ~p).sum())}
    print(s, res[s])
json.dump(res, open(out, "w"), indent=2)
