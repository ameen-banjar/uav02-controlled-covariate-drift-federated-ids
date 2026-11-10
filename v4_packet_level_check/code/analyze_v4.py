"""
V4 analysis (DESIGN_V4.md, section 6). Run ONCE after all sessions finish.

For every session and sub-file it compares
  F_pcap(c)  extractor output on the re-timed sub-file, with
  F_table(c) drift_v3.apply(F0b, s, "td") on the re-based baseline F0b,
row by row, and writes results/table.csv, results/summary.md and
results/summary.json. A second run is refused unless --allow-rerun is given
(used only for the synthetic self-test, with its own output folder).
"""
import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

TD_COLS = ["IAT", "flow_active_time", "std_duration", "Srate", "Drate", "Rate"]
DROPPED = ["ts", "min_duration", "max_duration", "sum_duration", "average_duration", "flow_idle_time"]
GATE_COLS = TD_COLS + ["Protocol Type"]
REL_TOL, ABS_TOL, THRESHOLD = 1e-6, 1e-9, 0.999
IP_MAX, DOT11 = 17.0, 802.11
C_TO_S = {"c16": 1.0, "c13": 0.5}


def agree(a, b):
    a, b = np.asarray(a, float), np.asarray(b, float)
    both_nan = np.isnan(a) & np.isnan(b)
    diff = np.abs(a - b)
    rel = diff / np.maximum(np.abs(b), 1e-12)
    with np.errstate(invalid="ignore"):
        ok = (diff <= ABS_TOL) | (rel <= REL_TOL)
    ok = np.where(np.isnan(diff), both_nan, ok)
    return ok, np.where(np.isnan(diff), 0.0, diff), np.where(np.isnan(rel), 0.0, rel)


def subfile_order(name):
    tail = name[len("split"):]
    return int(tail) if tail else 0


def load(root, variant, sub):
    return pd.read_csv(root / variant / f"{sub}_features.csv")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", required=True)
    ap.add_argument("--sessions", required=True, help="JSON: {session: {category, distributed_csv}}")
    ap.add_argument("--drift-code", required=True, help="folder holding drift_v3.py and drift_v2.py")
    ap.add_argument("--out", required=True)
    ap.add_argument("--allow-rerun", action="store_true")
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    stamp = out / "analysis_run_timestamp.txt"
    if stamp.exists() and not a.allow_rerun:
        sys.exit("analysis already run once; refusing to run again")
    sys.path.insert(0, a.drift_code)
    import drift_v2
    import drift_v3

    sessions = json.loads(Path(a.sessions).read_text())
    rows, gates, notes = [], [], []

    def record(session, variant, check, column, rowtype, ok, diff, rel):
        n = int(len(ok))
        rows.append({"session": session, "variant": variant, "check": check, "column": column,
                     "row_type": rowtype, "rows": n, "agree": int(ok.sum()),
                     "share": float(ok.mean()) if n else float("nan"),
                     "max_abs_diff": float(diff.max()) if n else float("nan"),
                     "max_rel_diff": float(rel.max()) if n else float("nan")})

    for session, info in sessions.items():
        root = Path(a.work) / session
        meta = json.loads((root / "session_meta.json").read_text())
        subs = sorted(meta["subfiles"], key=subfile_order)

        # replication gate: original-epoch extraction vs the distributed CSV
        f0 = pd.concat([load(root, "orig", s) for s in subs], ignore_index=True)
        dist = pd.read_csv(info["distributed_csv"])
        gate = {"session": session, "category": info["category"], "subfiles": len(subs),
                "rows_ours": int(len(f0)), "rows_distributed": int(len(dist))}
        if len(f0) == len(dist):
            x = f0.sort_values("ts", kind="mergesort").reset_index(drop=True)
            y = dist.sort_values("ts", kind="mergesort").reset_index(drop=True)
            shares = {}
            for c in GATE_COLS:
                ok = np.isclose(x[c].to_numpy(float), y[c].to_numpy(float), rtol=1e-6, atol=0, equal_nan=True)
                shares[c] = float(ok.mean())
            gate["column_shares"] = shares
            gate["passed"] = bool(min(shares.values()) == 1.0)
        else:
            gate["passed"] = False
        gates.append(gate)

        # session-level entropy floor for the descriptive v2 distance
        f0b_all = pd.concat([load(root, "c10", s) for s in subs], ignore_index=True)
        floor = drift_v2.compute_entropy_floor(f0b_all)

        for sub in subs:
            f0b = load(root, "c10", sub)
            f0s = load(root, "orig", sub)
            pt = f0b["Protocol Type"].to_numpy(float)
            ip = pt <= IP_MAX + 1e-9
            mixed = (~ip) & (pt < DOT11 - 1e-6)
            d11 = (~ip) & (~mixed)
            model_cols = [c for c in f0b.columns if c not in DROPPED]
            other_cols = [c for c in model_cols if c not in TD_COLS]

            # P4: mixed slices
            ok = ~mixed
            record(session, "c10", "P4_no_mixed_slice", "Protocol Type", "all", ok, mixed.astype(float), mixed.astype(float))

            # D4: original epoch vs re-based baseline (floating-point effect of epoch-scale times)
            if len(f0s) == len(f0b):
                for c in model_cols:
                    ok, diff, rel = agree(f0s[c], f0b[c])
                    record(session, "orig_vs_c10", "D4_rebase", c, "all", ok, diff, rel)
            else:
                notes.append(f"{session}/{sub}: orig has {len(f0s)} rows, c10 has {len(f0b)}")

            for variant, s in C_TO_S.items():
                if variant not in meta["variants"]:
                    continue
                fp = load(root, variant, sub)
                if len(fp) != len(f0b):
                    notes.append(f"{session}/{sub}/{variant}: row count {len(fp)} vs baseline {len(f0b)}; "
                                 "all rows of this sub-file counted as disagreeing")
                    bad = np.zeros(len(f0b), dtype=bool)
                    for c in TD_COLS:
                        record(session, variant, "P1_td_ip", c, "ip", bad[ip], bad[ip] * 1.0, bad[ip] * 1.0)
                    continue
                ft = drift_v3.apply(f0b, s, "td")
                tag = "" if variant == "c16" else "_D1"
                for c in TD_COLS:
                    ok, diff, rel = agree(fp[c], ft[c])
                    record(session, variant, "P1_td_ip" + tag, c, "ip", ok[ip], diff[ip], rel[ip])
                    if c != "Rate":
                        record(session, variant, "P2_td_dot11" + tag, c, "dot11", ok[d11], diff[d11], rel[d11])
                ok, diff, rel = agree(fp["Rate"], f0b["Rate"])
                record(session, variant, "P2_rate_unchanged_dot11" + tag, "Rate", "dot11", ok[d11], diff[d11], rel[d11])
                for c in other_cols:
                    ok, diff, rel = agree(fp[c], f0b[c])
                    record(session, variant, "P3_unchanged" + tag, c, "all", ok, diff, rel)
                if variant == "c16":
                    # D2: independent scaling (v2) against the re-timed trace
                    fv = drift_v3.apply(f0b, 1.0, "v2", entropy_floor=floor)
                    for c in TD_COLS + ["Entropy"]:
                        ok, diff, rel = agree(fp[c], fv[c])
                        record(session, variant, "D2_v2_distance", c, "all", ok, diff, rel)
                    # D3: rows with empty IAT before and after
                    n0, n1 = f0b["IAT"].isna().to_numpy(), fp["IAT"].isna().to_numpy()
                    same = n0 == n1
                    record(session, variant, "D3_iat_empty_same", "IAT", "all", same, (~same) * 1.0, n0 * 1.0)

    table = pd.DataFrame(rows)
    table.to_csv(out / "table.csv", index=False)

    def pooled(check, by=("column",)):
        t = table[table["check"] == check]
        if t.empty:
            return pd.DataFrame()
        g = t.groupby(list(by), sort=False).agg(rows=("rows", "sum"), agree=("agree", "sum"),
                                                max_abs_diff=("max_abs_diff", "max"),
                                                max_rel_diff=("max_rel_diff", "max")).reset_index()
        g["share"] = g["agree"] / g["rows"].where(g["rows"] > 0)
        return g

    def verdict(check):
        g = pooled(check)
        if g.empty or g["rows"].sum() == 0:
            return "no rows", g
        per_session = pooled(check, by=("session", "column"))
        per_session = per_session[per_session["rows"] > 0]
        holds_pooled = bool((g.loc[g["rows"] > 0, "share"] >= THRESHOLD).all())
        holds_each = bool((per_session["share"] >= THRESHOLD).all())
        return ("holds" if holds_pooled and holds_each else
                "holds pooled, fails in at least one session" if holds_pooled else "fails"), g

    summary = {"threshold": THRESHOLD, "rel_tol": REL_TOL, "abs_tol": ABS_TOL, "gates": gates, "notes": notes,
               "predictions": {}}
    L = ["# V4 packet-level check: results", "",
         f"Agreement per row: relative difference <= {REL_TOL:g} or absolute difference <= {ABS_TOL:g}. "
         f"A prediction holds if every column reaches {100 * THRESHOLD:.1f}% of rows, pooled and in each session.", "",
         "## Replication gate (our extraction at the original epoch vs the distributed CSV)", "",
         "| Session | Category | Sub-files | Rows ours | Rows distributed | Gate |", "|---|---|---:|---:|---:|---|"]
    for g in gates:
        L.append(f"| {g['session']} | {g['category']} | {g['subfiles']} | {g['rows_ours']:,} | "
                 f"{g['rows_distributed']:,} | {'passed' if g['passed'] else 'FAILED'} |")

    def table_md(g):
        T = ["| Column | Rows | Agreeing | Share | Largest abs. diff. | Largest rel. diff. |", "|---|---:|---:|---:|---:|---:|"]
        for _, r in g.iterrows():
            share = "n/a" if r["rows"] == 0 else f"{100 * r['share']:.3f}%"
            T.append(f"| `{r['column']}` | {int(r['rows']):,} | {int(r['agree']):,} | {share} | "
                     f"{r['max_abs_diff']:.3g} | {r['max_rel_diff']:.3g} |")
        return T

    titles = [("P1_td_ip", "V4-P1. Time-dilation columns on IP rows, c = 1.6"),
              ("P2_td_dot11", "V4-P2a. Time-dilation columns on 802.11 rows, c = 1.6"),
              ("P2_rate_unchanged_dot11", "V4-P2b. `Rate` unchanged on 802.11 rows, c = 1.6"),
              ("P3_unchanged", "V4-P3. All other model features unchanged, c = 1.6"),
              ("P4_no_mixed_slice", "V4-P4. No slice mixes IP and 802.11 packets")]
    for check, title in titles:
        v, g = verdict(check)
        summary["predictions"][check] = {"verdict": v, "pooled": g.to_dict("records")}
        L += ["", f"## {title}: **{v}**", ""]
        if check == "P3_unchanged" and not g.empty:
            bad = g[g["share"] < 1.0]
            L.append(f"{len(g)} columns checked; {len(g) - len(bad)} identical in every row.")
            if len(bad):
                L += [""] + table_md(bad)
        elif not g.empty:
            L += table_md(g)
    for check, title in [("P1_td_ip_D1", "V4-D1. IP rows, c = 1.3 (single-sub-file sessions)"),
                         ("P2_td_dot11_D1", "V4-D1. 802.11 rows, c = 1.3"),
                         ("D2_v2_distance", "V4-D2. Independent scaling (v2) against the re-timed trace, c = 1.6"),
                         ("D3_iat_empty_same", "V4-D3. Rows whose `IAT` is empty: same before and after re-timing"),
                         ("D4_rebase", "V4-D4. Original epoch vs re-based baseline (floating-point effect)")]:
        g = pooled(check)
        if g.empty:
            continue
        summary.setdefault("descriptive", {})[check] = g.to_dict("records")
        L += ["", f"## {title}", ""]
        if check == "D4_rebase":
            bad = g[g["share"] < 1.0]
            L.append(f"{len(g)} model columns compared; {len(g) - len(bad)} agree in every row.")
            if len(bad):
                L += [""] + table_md(bad)
        else:
            L += table_md(g)
    if notes:
        L += ["", "## Notes", ""] + [f"- {n}" for n in notes]
    (out / "summary.md").write_text("\n".join(L) + "\n")
    (out / "summary.json").write_text(json.dumps(summary, indent=2, default=float))
    stamp.write_text(time.strftime("%Y-%m-%dT%H:%M:%S%z") + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
