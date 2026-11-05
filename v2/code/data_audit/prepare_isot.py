"""
Shared data-loading module for the ISOT Drone Dataset audit/prep scripts.

Confirmed contaminated columns (raw Unix epoch timestamps, not durations --
see isot_learnability_audit_v2.py) are dropped unconditionally here so every
downstream script inherits the fix automatically.
"""
from pathlib import Path

import numpy as np
import pandas as pd

# Path-resolution fix (2026-09-24, infrastructure only -- see
# development-workspace/REPRODUCIBILITY_NOTES.md): these were hardcoded
# absolute paths from before the project directory was renamed/moved
# (~/Desktop/maybe a paper/research-projects/... -> ~/All Project/UAV-FL/...),
# which crashed any script importing this module. Fixed to resolve relative
# to this file's own location. No data, feature, or algorithm change.
AUDIT_DIR = Path(__file__).resolve().parent
DATA_DIR = AUDIT_DIR.parent / "isot_drone_dataset"

TIMESTAMP_LEAK_COLUMNS = ["ts", "min_duration", "max_duration", "sum_duration",
                          "average_duration", "flow_idle_time"]

# Feature groups used by feature_ablation.py; kept here so every script agrees
# on the same grouping.
PAYLOAD_FEATURES = ["Payload_Length", "Var_Payload", "Entropy"]
RATE_FEATURES = ["Rate", "Srate", "Drate"]
ENV_FINGERPRINT_SUSPECTS = ["Drone_port", "DS status"]


def load_all_sessions(max_rows_per_session=None, seed=42):
    """Load every session CSV, tag with _session/_category/_is_attack, drop
    the confirmed timestamp-leak columns. If max_rows_per_session is set,
    downsample (without replacement) any session exceeding it -- used for the
    session-balanced-training check (Regular/DoS otherwise dominate 85% of rows)."""
    csv_files = sorted(p for p in DATA_DIR.rglob("*.csv"))
    rng = np.random.RandomState(seed)
    frames = []
    for f in csv_files:
        category = f.relative_to(DATA_DIR).parts[0]
        d = pd.read_csv(f)
        d = d.drop(columns=[c for c in TIMESTAMP_LEAK_COLUMNS if c in d.columns])
        if max_rows_per_session is not None and len(d) > max_rows_per_session:
            idx = rng.choice(len(d), size=max_rows_per_session, replace=False)
            d = d.iloc[np.sort(idx)]
        d["_category"] = category
        d["_session"] = f.stem
        d["_is_attack"] = 0 if category == "Regular" else 1
        frames.append(d)
    df = pd.concat(frames, ignore_index=True)
    return df


def clean_feature_columns(df):
    non_feature = {"_category", "_session", "_is_attack"}
    cols = [c for c in df.columns if c not in non_feature]
    numeric = df[cols].select_dtypes(include=[np.number]).columns.tolist()
    # sanity guard: nothing epoch-scale should ever reach a model
    still_bad = [c for c in numeric if df[c].abs().median() > 1e8]
    if still_bad:
        raise RuntimeError(f"Epoch-scale columns leaked through: {still_bad}")
    return numeric


def session_table(df):
    """One row per session: category, row count -- used for stratified splitting
    and for documenting the extreme session-size range (177 to 205k rows)."""
    return (df.groupby(["_session", "_category"])
              .size().reset_index(name="n_rows")
              .sort_values("n_rows"))


if __name__ == "__main__":
    df = load_all_sessions()
    feats = clean_feature_columns(df)
    st = session_table(df)
    print(f"rows={len(df)}  sessions={df['_session'].nunique()}  clean_features={len(feats)}")
    print(st.groupby("_category")["n_rows"].agg(["count", "min", "max", "sum"]))
