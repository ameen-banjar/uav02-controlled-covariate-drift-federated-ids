"""
Validity check for a tabular synthetic-drift transform, run BEFORE training.

Inputs
  --features   JSON: what each feature means in the extractor, its physical
               domain, its timing role, and the rate x time relations the
               extractor ties together.
  --transform  JSON: the transform as a list of per-feature operations and,
               optionally, the intent it claims ("retime" by a factor c).
  --data       one or more CSV files of extracted rows (raw feature units),
               or --data-list with one path per line.

Three checks
  1. Meaning   every edited feature is looked up in the feature file; an edit
               of a feature whose name does not say what it holds is flagged.
  2. Range     rows that were inside the physical domain and leave it.
  3. Relations each rate x time product the extractor ties together is
               compared before and after; under a "retime" intent every
               time-role and rate-role feature must scale by c and 1/c.

Output: a Markdown report and a JSON file with the same numbers.
No model is involved.
"""
import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd


def row_mask(df, rows, spec):
    """Rows an operation or a domain applies to: all, ip or dot11."""
    if rows in (None, "all"):
        return np.ones(len(df), dtype=bool)
    col = spec["row_type"]["column"]
    is_ip = df[col].to_numpy(float) <= spec["row_type"]["ip_max"] + 1e-9
    return is_ip if rows == "ip" else ~is_ip


def apply_transform(df, tr, spec):
    out = df.copy()
    for op in tr["operations"]:
        f = op["feature"]
        if f not in out.columns:
            continue
        m = row_mask(out, op.get("rows"), spec)
        v = out[f].to_numpy(float).copy()
        if op["op"] == "mul":
            v[m] = v[m] * op["value"]
        elif op["op"] == "add":
            raw = v[m].copy()
            v[m] = raw + op["value"]
            if "floor_raw_quantile" in op:      # floor taken from the untransformed values
                floor = np.nanquantile(raw, op["floor_raw_quantile"])
                v[m] = np.maximum(v[m], floor)
        else:
            raise ValueError(f"unknown op {op['op']}")
        out[f] = v
    return out


def check(df, spec, tr):
    feats = spec["features"]
    new = apply_transform(df, tr, spec)
    edited = []
    for op in tr["operations"]:
        if op["feature"] not in edited:
            edited.append(op["feature"])
    res = {"transform": tr["name"], "rows": int(len(df)), "meaning": [], "range": [],
           "relations": [], "intent": []}

    # 1. meaning
    for f in edited:
        info = feats.get(f)
        if info is None:
            res["meaning"].append({"feature": f, "flag": True,
                                   "note": "not described in the feature file"})
            continue
        res["meaning"].append({"feature": f, "holds": info["holds"], "source": info.get("source", ""),
                               "flag": not info.get("name_matches_meaning", True),
                               "note": info.get("note", "")})

    # 2. range
    for f in edited:
        info = feats.get(f, {})
        for dom in info.get("domains", []):
            m = row_mask(df, dom.get("rows"), spec)
            r = df[f].to_numpy(float)
            n = new[f].to_numpy(float)
            lo, hi = dom.get("min", -np.inf), dom.get("max", np.inf)
            ok_raw = m & ~np.isnan(r) & (r >= lo) & (r <= hi)
            left = ok_raw & ((n < lo - 1e-12) | (n > hi + 1e-12))
            res["range"].append({"feature": f, "rows": dom.get("rows", "all"), "min": dom.get("min"),
                                 "max": dom.get("max"), "applicable_rows": int(m.sum()),
                                 "rows_leaving_domain": int(left.sum()),
                                 "share_of_all_rows": float(left.sum() / max(len(df), 1)),
                                 "share_of_applicable_rows": float(left.sum() / max(m.sum(), 1))})

    # 3. relations
    for rel in spec["relations"]:
        a, b = rel["rate"], rel["time"]
        if a not in df.columns or b not in df.columns:
            continue
        m = row_mask(df, rel.get("rows"), spec)
        before = (df[a].to_numpy(float) * df[b].to_numpy(float))[m]
        after = (new[a].to_numpy(float) * new[b].to_numpy(float))[m]
        ok = ~np.isnan(before) & (np.abs(before) > 1e-12)
        ratio = after[ok] / before[ok]
        med = float(np.median(ratio)) if ok.any() else float("nan")
        broken = int((np.abs(ratio - 1.0) > 1e-9).sum())
        res["relations"].append({"relation": f"{a} x {b}", "rows": rel.get("rows", "all"),
                                 "tied_by": rel.get("tied_by", ""), "rows_checked": int(ok.sum()),
                                 "median_factor": med, "rows_changed": broken,
                                 "flag": broken > 0})

    # intent: uniform re-timing by c
    intent = tr.get("intent")
    if intent and intent.get("kind") == "retime":
        c = intent["factor"]
        for f, info in feats.items():
            if f not in df.columns or info.get("timing_role", "none") == "none":
                continue
            for rows in info.get("timing_rows", ["all"]):
                m = row_mask(df, rows, spec)
                r = df[f].to_numpy(float)[m]
                n = new[f].to_numpy(float)[m]
                ok = ~np.isnan(r) & (np.abs(r) > 1e-12)
                want = c if info["timing_role"] == "time" else 1.0 / c
                got = float(np.median(n[ok] / r[ok])) if ok.any() else float("nan")
                res["intent"].append({"feature": f, "rows": rows, "role": info["timing_role"],
                                      "expected_factor": want, "median_factor": got,
                                      "flag": bool(ok.any() and abs(got - want) > 1e-9)})
        for f in edited:
            if feats.get(f, {}).get("timing_role", "none") == "none":
                res["intent"].append({"feature": f, "rows": "all", "role": "none",
                                      "expected_factor": 1.0, "median_factor": None, "flag": True,
                                      "note": "edited, but re-timing does not change this feature"})
    res["flags"] = (sum(x["flag"] for x in res["meaning"])
                    + sum(x["rows_leaving_domain"] > 0 for x in res["range"])
                    + sum(x["flag"] for x in res["relations"])
                    + sum(x["flag"] for x in res["intent"]))
    return res


def to_markdown(res, tr):
    L = [f"# Drift validity report: {res['transform']}", "",
         tr.get("description", ""), "",
         f"Rows checked: {res['rows']:,}. Flags raised: **{res['flags']}**.", "",
         "## 1. Meaning of each edited feature", "",
         "| Feature | Holds | Source | Flag |", "|---|---|---|---|"]
    for x in res["meaning"]:
        flag = "NAME DOES NOT MATCH" if x["flag"] else "ok"
        L.append(f"| `{x['feature']}` | {x.get('holds', x.get('note', ''))} | {x.get('source', '')} | {flag} |")
    L += ["", "## 2. Rows leaving the physical domain", "",
          "| Feature | Row type | Domain | Rows leaving | Share of all rows | Share of that row type |",
          "|---|---|---|---:|---:|---:|"]
    for x in res["range"]:
        dom = f"[{x['min']}, {x['max'] if x['max'] is not None else 'inf'}]"
        L.append(f"| `{x['feature']}` | {x['rows']} | {dom} | {x['rows_leaving_domain']:,} | "
                 f"{100 * x['share_of_all_rows']:.1f}% | {100 * x['share_of_applicable_rows']:.1f}% |")
    L += ["", "## 3. Rate x time relations tied by the extractor", "",
          "| Relation | Row type | Median factor after transform | Rows changed | Flag |",
          "|---|---|---:|---:|---|"]
    for x in res["relations"]:
        L.append(f"| {x['relation']} | {x['rows']} | {x['median_factor']:.4f} | {x['rows_changed']:,} | "
                 f"{'BROKEN' if x['flag'] else 'kept'} |")
    if res["intent"]:
        L += ["", "## 4. Consistency with the stated intent (uniform re-timing)", "",
              "| Feature | Row type | Role | Expected factor | Median factor | Flag |",
              "|---|---|---|---:|---:|---|"]
        for x in res["intent"]:
            got = "n/a" if x["median_factor"] is None else f"{x['median_factor']:.4f}"
            L.append(f"| `{x['feature']}` | {x['rows']} | {x['role']} | {x['expected_factor']:.4f} | {got} | "
                     f"{'MISMATCH' if x['flag'] else 'ok'} |")
    return "\n".join(L) + "\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--features", required=True)
    ap.add_argument("--transform", required=True)
    ap.add_argument("--data", nargs="*", default=[])
    ap.add_argument("--data-list", help="text file with one CSV path per line")
    ap.add_argument("--out", required=True, help="output path without extension")
    a = ap.parse_args()
    spec = json.loads(Path(a.features).read_text())
    tr = json.loads(Path(a.transform).read_text())
    paths = list(a.data)
    if a.data_list:
        paths += [x for x in Path(a.data_list).read_text().splitlines() if x.strip()]
    if not paths:
        ap.error("give --data or --data-list")
    df = pd.concat([pd.read_csv(p) for p in paths], ignore_index=True)
    res = check(df, spec, tr)
    Path(a.out + ".json").write_text(json.dumps(res, indent=2))
    Path(a.out + ".md").write_text(to_markdown(res, tr))
    print(f"{res['transform']}: {res['rows']:,} rows, {res['flags']} flags -> {a.out}.md")


if __name__ == "__main__":
    main()
