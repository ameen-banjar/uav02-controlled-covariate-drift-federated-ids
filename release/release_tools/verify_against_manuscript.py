"""
Compare regenerated Tables 2-6 (regenerated/table<N>.md) and the key in-text
values with the numbers printed in the manuscript, cell by cell at displayed
precision (NEW release tool, 2026-10-21).

    python release_tools/verify_against_manuscript.py
    python release_tools/verify_against_manuscript.py --extract-from ../UAV02_DRAFT/manuscript.md   # author-side

The reference is expected/manuscript_tables.md, an extract of the manuscript's
table rows and in-text values (author-side `--extract-from` rewrites it).
Normalization before comparison: Unicode minus -> '-', surrounding whitespace.
Header and caption lines are not compared; only data rows.
"""
import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _paths  # noqa: E402

EXPECTED = _paths.STAGING / "expected" / "manuscript_tables.md"
TABLE_NUMS = ["2", "3", "4", "5", "6"]
# In-text values (manuscript Sections 4.3-4.4) checked against regenerated/intext_values.md
INTEXT_PATTERNS = {
    "L2 FedAvg": r"Mean exposure-period L2 macro-F1 gaps are ([+\-−]\d\.\d{4}), ([+\-−]\d\.\d{4}), and ([+\-−]\d\.\d{4}) for FedAvg",
    "L2 FedProx": r"corresponding FedProx gaps are ([+\-−]\d\.\d{4}), ([+\-−]\d\.\d{4}), and ([+\-−]\d\.\d{4})",
    "H1 FedAvg": r"Mean S is ([+\-−]\d\.\d{4}) logit-margin units for FedAvg \(SD (\d\.\d{4}); range \[([+\-−]\d\.\d{4}), ([+\-−]\d\.\d{4})\]; "
                 r"descriptive interval \[([+\-−]\d\.\d{4}), ([+\-−]\d\.\d{4})\]; d_z ([+\-−]\d\.\d{2})\)",
    "H1 FedProx": r"and ([+\-−]\d\.\d{4}) for FedProx \(SD (\d\.\d{4}); range \[([+\-−]\d\.\d{4}), ([+\-−]\d\.\d{4})\]; "
                  r"interval \[([+\-−]\d\.\d{4}), ([+\-−]\d\.\d{4})\]; d_z ([+\-−]\d\.\d{2})\)",
    "H1 drops FedAvg": r"change from ([+\-−]\d\.\d{4}) at round 15 to ([+\-−]\d\.\d{4}) at round 30 for FedAvg",
    "H1 drops FedProx": r"and from ([+\-−]\d\.\d{4}) to ([+\-−]\d\.\d{4}) for FedProx",
}


def norm(s):
    return s.replace("−", "-").strip()


def data_rows(lines):
    rows = []
    for ln in lines:
        ln = ln.strip()
        if ln.startswith("|") and not ln.startswith("|---"):
            rows.append([norm(c) for c in ln.strip("|").split("|")])
    return rows[1:]          # drop the header row


def table_blocks(text):
    blocks = {}
    for n in TABLE_NUMS:
        m = re.search(rf"^\*\*Table {n}\..*?$\n\n((?:\|.*\|\n?)+)", text, flags=re.M)
        if not m:
            sys.exit(f"Table {n} not found")
        blocks[n] = m.group(1).rstrip("\n").splitlines()
    return blocks


def numbers(s):
    return [norm(x) for x in re.findall(r"[+\-−]?\d+\.\d+", s)]


def extract(manuscript):
    text = Path(manuscript).read_text()
    out = [f"# Manuscript reference values (extracted from {Path(manuscript).name}; do not edit by hand)", ""]
    for n, rows in table_blocks(text).items():
        out += [f"**Table {n}.**", ""] + rows + [""]
    out += ["## In-text values", ""]
    for key, pat in INTEXT_PATTERNS.items():
        m = re.search(pat, text)
        if not m:
            sys.exit(f"in-text value not found in manuscript: {key}")
        out.append(f"- {key}: " + ", ".join(norm(g) for g in m.groups()))
    EXPECTED.parent.mkdir(exist_ok=True)
    EXPECTED.write_text("\n".join(out) + "\n")
    print(f"wrote {EXPECTED}")


def verify(regen_dir):
    ref = EXPECTED.read_text()
    ok_all = True
    for n in TABLE_NUMS:
        m = re.search(rf"^\*\*Table {n}\.\*\*\n\n((?:\|.*\|\n?)+)", ref, flags=re.M)
        exp = data_rows(m.group(1).splitlines())
        got = data_rows((regen_dir / f"table{n}.md").read_text().splitlines())
        diffs = []
        if len(exp) != len(got):
            diffs.append(f"row count {len(got)} vs manuscript {len(exp)}")
        for i, (e, g) in enumerate(zip(exp, got)):
            for j, (ec, gc) in enumerate(zip(e, g)):
                if ec != gc:
                    diffs.append(f"row {i + 1} col {j + 1}: regenerated '{gc}' vs manuscript '{ec}'")
        cells = sum(len(r) for r in exp)
        print(f"Table {n}: {len(exp)} rows, {cells} cells -> {'MATCH' if not diffs else 'DIFFERENCES'}")
        for d in diffs:
            print("   ", d)
        ok_all &= not diffs
    intext = (regen_dir / "intext_values.md").read_text()
    lines = {k: v for k, v in re.findall(r"^- (.+?): (.+)$", ref, flags=re.M)}
    got_nums = {
        "L2 FedAvg": numbers(re.search(r"gap, FedAvg: (.*)", intext).group(1)),
        "L2 FedProx": numbers(re.search(r"gap, FedProx: (.*)", intext).group(1)),
        "H1 FedAvg": numbers(re.search(r"H1 FedAvg: (.*?); mean drop", intext).group(1)),
        "H1 FedProx": numbers(re.search(r"H1 FedProx: (.*?); mean drop", intext).group(1)),
        "H1 drops FedAvg": numbers(re.search(r"H1 FedAvg: .*?; mean drop (.*)", intext).group(1)),
        "H1 drops FedProx": numbers(re.search(r"H1 FedProx: .*?; mean drop (.*)", intext).group(1)),
    }
    for k in INTEXT_PATTERNS:
        exp = [norm(x) for x in lines[k].split(",")]
        got = [x for x in got_nums[k] if x not in ("15", "30")]
        got = [x for x in got if re.match(r"^[+\-]?\d\.\d+$", x)]
        ok = exp == got
        print(f"In-text {k}: {'MATCH' if ok else 'DIFFERENCES'}" + ("" if ok else f"  regenerated {got} vs manuscript {exp}"))
        ok_all &= ok
    print("\nALL REGENERATED VALUES MATCH THE MANUSCRIPT" if ok_all else "\nMISMATCHES FOUND")
    return ok_all


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--extract-from", help="author-side: rebuild expected/manuscript_tables.md from manuscript.md")
    ap.add_argument("--regenerated", default=str(_paths.STAGING / "regenerated"))
    a = ap.parse_args()
    if a.extract_from:
        extract(a.extract_from)
        return
    sys.exit(0 if verify(Path(a.regenerated)) else 1)


if __name__ == "__main__":
    main()
