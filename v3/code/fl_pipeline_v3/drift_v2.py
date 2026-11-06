"""
UAV-02 v2 (corrected) controlled temporal covariate drift. Derived from the
v1 frozen drift.py (tag uav02-confirmatory-freeze-v1) with ONE design change
and one added guard; everything else (clients, schedules, magnitudes, Entropy
floor) is byte-for-byte the v1 logic.

Change 1 (design). `Duration` is REMOVED from the transformed features. In the
ISOT extractor, `Duration` holds the IP time-to-live (packet.ttl) on the IP
path and an 802.11 frame field otherwise; it is not a session/flow duration.
v1 multiplied it by 1.6 and produced values above 255 (the largest possible
IP TTL) in 79.9% of validation rows and 94.9% of the transformed clients'
training rows. A post-hoc ablation on the v1 checkpoints
(post_hoc/review_2026-11-06/) showed that this invalid edit carried almost
all of the v1 Regular-recall, MITM-redirection and H1 effects.

Change 2 (guard). apply_drift() asserts that every transformed column stays
inside its physical domain (rates/times >= 0; Entropy of a byte payload in
[0, 8] bits).

Feature meaning (checked in the ISOT extractor, commit 783e9bf):
  Rate (payload rate), Srate, Drate (packets / flow duration)  -> decrease
  IAT (time since previous packet), flow_active_time (last - first flow ts) -> increase
  Entropy (Shannon entropy of the payload bytes, bits) -> mild decrease, floored
"""
import numpy as np
import pandas as pd
import torch

DRIFT_CLIENT_IDS = [11, 1, 14, 10, 9]  # 5 highest Regular-share clients in the frozen manifest

# --- sudden: baseline -> onset -> sustained -> recovery -> recovered baseline ---
DRIFT_START_SUDDEN = 15      # onset: strength jumps 0 -> 1 at this round
DRIFT_RECOVER_SUDDEN = 30    # recovery: strength drops 1 -> 0 at this round
# rounds 1-14 clean, 15-29 drifted (15 rounds), 30-45 recovered (16 rounds)

# --- gradual: ramp up -> hold -> ramp down -> recovered baseline ---
DRIFT_RAMPUP_START_GRADUAL = 10
DRIFT_RAMPUP_END_GRADUAL = 20     # strength reaches 1.0 here
DRIFT_RAMPDOWN_START_GRADUAL = 25  # strength begins declining here (5-round hold at 1.0)
DRIFT_RAMPDOWN_END_GRADUAL = 35    # strength reaches 0.0 here
# rounds 1-9 clean, 10-20 ramp up, 20-25 hold, 25-35 ramp down, 35-45 recovered

DRIFT_RECURRING_WINDOWS = [(15, 22), (30, 37)]
NUM_ROUNDS = 45  # must match run_baselines.py's frozen budget

MULTIPLICATIVE_DOWN = ["Rate", "Srate", "Drate"]
MULTIPLICATIVE_UP = ["IAT", "flow_active_time"]   # v2: Duration removed (it is the IP TTL)
PHYSICAL_BOUNDS = {"Rate": (0, None), "Srate": (0, None), "Drate": (0, None),
                   "IAT": (0, None), "flow_active_time": (0, None), "Entropy": (0, 8.0)}
ENTROPY_COL = "Entropy"
# v3: raised from 0.40/0.35 after the v2 pilot showed too weak/noisy a signal
# for most of the drifted period (only clearly visible in the final ~2 rounds).
MAX_MULTIPLICATIVE_SHIFT = 0.60   # at strength=1.0, +-60% on the up/down feature groups
MAX_ENTROPY_SHIFT = 0.50          # at strength=1.0, Entropy drops by up to 0.50 (raw units), bounded below


def schedule_sudden(round_idx):
    if round_idx < DRIFT_START_SUDDEN:
        return 0.0
    if round_idx < DRIFT_RECOVER_SUDDEN:
        return 1.0
    return 0.0


def schedule_gradual(round_idx):
    if round_idx < DRIFT_RAMPUP_START_GRADUAL:
        return 0.0
    if round_idx < DRIFT_RAMPUP_END_GRADUAL:
        return (round_idx - DRIFT_RAMPUP_START_GRADUAL) / (DRIFT_RAMPUP_END_GRADUAL - DRIFT_RAMPUP_START_GRADUAL)
    if round_idx < DRIFT_RAMPDOWN_START_GRADUAL:
        return 1.0
    if round_idx < DRIFT_RAMPDOWN_END_GRADUAL:
        return 1.0 - (round_idx - DRIFT_RAMPDOWN_START_GRADUAL) / (DRIFT_RAMPDOWN_END_GRADUAL - DRIFT_RAMPDOWN_START_GRADUAL)
    return 0.0


def schedule_recurring(round_idx):
    return 1.0 if any(lo <= round_idx < hi for lo, hi in DRIFT_RECURRING_WINDOWS) else 0.0


SCHEDULES = {"sudden": schedule_sudden, "gradual": schedule_gradual,
             "recurring": schedule_recurring, "none": lambda r: 0.0}


def apply_drift(df: pd.DataFrame, strength: float, entropy_floor: float) -> pd.DataFrame:
    """Returns a perturbed COPY of df (raw feature units, pre-scaling). strength
    in [0,1]. entropy_floor: the 5th percentile of this client's own Entropy
    distribution, computed once before any drift (the clip bound)."""
    if strength <= 0:
        return df
    d = df.copy()
    for col in MULTIPLICATIVE_DOWN:
        if col in d.columns:
            d[col] = d[col] * (1 - MAX_MULTIPLICATIVE_SHIFT * strength)
    for col in MULTIPLICATIVE_UP:
        if col in d.columns:
            d[col] = d[col] * (1 + MAX_MULTIPLICATIVE_SHIFT * strength)
    if ENTROPY_COL in d.columns:
        shifted = d[ENTROPY_COL] - MAX_ENTROPY_SHIFT * strength
        d[ENTROPY_COL] = np.maximum(shifted, entropy_floor)
    for col, (lo, hi) in PHYSICAL_BOUNDS.items():
        if col in d.columns:
            v = d[col].to_numpy(dtype=float)
            v = v[~np.isnan(v)]
            assert lo is None or (v >= lo - 1e-12).all(), f"{col} below physical bound {lo}"
            assert hi is None or (v <= hi + 1e-12).all(), f"{col} above physical bound {hi}"
    assert "Duration" not in MULTIPLICATIVE_UP + MULTIPLICATIVE_DOWN, "Duration (IP TTL) must not be transformed"
    return d


def compute_entropy_floor(df: pd.DataFrame) -> float:
    return float(df[ENTROPY_COL].quantile(0.05)) if ENTROPY_COL in df.columns else 0.0
