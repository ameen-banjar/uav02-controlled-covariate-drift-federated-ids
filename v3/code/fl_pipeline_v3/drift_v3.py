"""
UAV-02 v3 interventions. Two transforms, both applied to RAW feature units
before standardization, with strength s in [0, 1]:

  "v2"  the v2 corrected intervention, unchanged (drift_v2.apply_drift):
        Rate, Srate, Drate x (1 - 0.6 s); IAT, flow_active_time x (1 + 0.6 s);
        Entropy - 0.5 s, floored at the 5th percentile. Per-feature domain
        checks only; it is NOT jointly consistent: rate x time changes by
        (1 - 0.6 s)(1 + 0.6 s) = 0.64 at s = 1, and std_duration is untouched.

  "td"  time dilation (jointly consistent). Every packet's timing is
        stretched by c(s) = 1 + 0.6 s; nothing about packet sizes, payloads,
        counts, flags or protocols changes. In the ISOT extractor
        (isot-lab repo, commit 783e9bf) each row is the MEAN over 10
        consecutive packets of per-packet values:
          IAT          = time since previous packet            -> x c
          flow_active_time = last - first timestamp of the flow -> x c
          std_duration = std of the flow's timestamps            -> x c
          Srate, Drate = packets / flow duration                 -> / c
          Rate (IP)    = payload bits / inter-packet interval    -> / c
          Rate (802.11)= radiotap PHY rate, not time-derived     -> unchanged
        A mean of per-packet values scaled by the same factor is scaled by
        that factor, so the extractor identities (rate x time = packets or
        bits) hold exactly for every row. Rows whose 10-packet window holds
        any 802.11 packet (mean Protocol Type > 17, the largest IP protocol
        number present) keep Rate unchanged, because their Rate mixes PHY
        and payload rates that cannot be separated; their share is reported.
        Entropy, Duration (= IP TTL) and all size/count features unchanged.

  "td_time_only", "td_rate_only": components of "td", for the pre-specified
        evaluation-only decomposition (never used for training).

Guards on every call: no transformed value may leave its physical domain
unless the raw value already did (raw violations are counted, not edited);
for "td", the identities are asserted row by row.
"""
import numpy as np
import pandas as pd

import drift_v2 as v2

SCHEDULES = v2.SCHEDULES
NUM_ROUNDS = v2.NUM_ROUNDS
MAX_SHIFT = v2.MAX_MULTIPLICATIVE_SHIFT          # 0.60
compute_entropy_floor = v2.compute_entropy_floor

TD_TIME = ["IAT", "flow_active_time", "std_duration"]
TD_RATE_ALWAYS = ["Srate", "Drate"]
TD_RATE_IP_ONLY = ["Rate"]
IP_PROTOCOL_MAX = 17.0
NONNEG = ["Rate", "Srate", "Drate", "IAT", "flow_active_time", "std_duration"]

# CICIoT2023 (window means over 10 or 100 packets; extractor lineage of [28,29])
CIC_TIME = ["IAT"]
CIC_RATE = ["Rate"]

TRANSFORMS = ("v2", "td", "td_time_only", "td_rate_only")


def dilation(strength):
    return 1.0 + MAX_SHIFT * strength


def _ip_only_mask(d):
    if "Protocol Type" not in d.columns:
        return np.ones(len(d), dtype=bool)
    return d["Protocol Type"].to_numpy(dtype=float) <= IP_PROTOCOL_MAX + 1e-9


def _check_domain(raw, new, cols):
    for col in cols:
        if col not in new.columns:
            continue
        r = raw[col].to_numpy(dtype=float)
        n = new[col].to_numpy(dtype=float)
        ok_raw = ~np.isnan(r) & (r >= 0)
        assert (n[ok_raw] >= -1e-12).all(), f"{col}: transform created a negative value"


def apply(df, strength, transform, entropy_floor=0.0, dataset="isot"):
    """Returns a transformed COPY of df (raw units). strength 0 returns df."""
    if strength <= 0:
        return df
    if transform == "v2":
        assert dataset == "isot", "the v2 transform is defined for ISOT only"
        return v2.apply_drift(df, strength, entropy_floor)
    c = dilation(strength)
    d = df.copy()
    for col in set(TD_TIME + TD_RATE_ALWAYS + TD_RATE_IP_ONLY + CIC_TIME + CIC_RATE) & set(d.columns):
        d[col] = d[col].astype("float64")   # float32 parquet columns would break the exact identity checks
    df = df.copy()
    for col in set(TD_TIME + TD_RATE_ALWAYS + TD_RATE_IP_ONLY + CIC_TIME + CIC_RATE) & set(df.columns):
        df[col] = df[col].astype("float64")
    if dataset == "cic":
        if transform in ("td", "td_time_only"):
            for col in CIC_TIME:
                d[col] = d[col] * c
        if transform in ("td", "td_rate_only"):
            for col in CIC_RATE:
                d[col] = d[col] / c
        _check_domain(df, d, CIC_TIME + CIC_RATE)
        if transform == "td":
            prod_raw = df["Rate"].to_numpy(float) * df["IAT"].to_numpy(float)
            prod_new = d["Rate"].to_numpy(float) * d["IAT"].to_numpy(float)
            assert np.allclose(prod_new, prod_raw, rtol=1e-9, atol=1e-12, equal_nan=True), "CIC rate x IAT identity"
        return d
    ip = _ip_only_mask(d)
    if transform in ("td", "td_time_only"):
        for col in TD_TIME:
            if col in d.columns:
                d[col] = d[col] * c
    if transform in ("td", "td_rate_only"):
        for col in TD_RATE_ALWAYS:
            if col in d.columns:
                d[col] = d[col] / c
        for col in TD_RATE_IP_ONLY:
            if col in d.columns:
                v = d[col].to_numpy(dtype=float).copy()
                v[ip] = v[ip] / c
                d[col] = v
    _check_domain(df, d, NONNEG)
    if transform == "td":
        for rc, tc in (("Srate", "flow_active_time"), ("Drate", "flow_active_time")):
            if rc in d.columns and tc in d.columns:
                a = df[rc].to_numpy(float) * df[tc].to_numpy(float)
                b = d[rc].to_numpy(float) * d[tc].to_numpy(float)
                assert np.allclose(a, b, rtol=1e-9, atol=1e-12, equal_nan=True), f"identity {rc} x {tc}"
        if "Rate" in d.columns and "IAT" in d.columns:
            a = (df["Rate"].to_numpy(float) * df["IAT"].to_numpy(float))[ip]
            b = (d["Rate"].to_numpy(float) * d["IAT"].to_numpy(float))[ip]
            assert np.allclose(a, b, rtol=1e-9, atol=1e-12, equal_nan=True), "identity Rate x IAT (IP rows)"
        for col in ("Duration", "Entropy", "Payload_Length", "Tot size", "Number"):
            if col in d.columns:
                assert d[col].equals(df[col]), f"{col} must be unchanged by time dilation"
    return d


def audit_counts(df, dataset="isot"):
    """Raw-data domain violations and the share of rows with mixed/802.11 windows."""
    cols = NONNEG if dataset == "isot" else CIC_TIME + CIC_RATE
    out = {"rows": int(len(df))}
    for col in cols:
        if col in df.columns:
            v = df[col].to_numpy(dtype=float)
            out[f"{col}_negative_share"] = float(np.mean(v < 0))
            out[f"{col}_nan_share"] = float(np.mean(np.isnan(v)))
    if dataset == "isot" and "Protocol Type" in df.columns:
        out["rows_with_80211_packets_share"] = float(np.mean(~_ip_only_mask(df)))
    return out
