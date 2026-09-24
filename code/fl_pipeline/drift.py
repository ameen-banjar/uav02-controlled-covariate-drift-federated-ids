"""
Controlled temporal concept drift injection for the ISOT federated pipeline.

Terminology (binding, per README): this is CONTROLLED/INJECTED drift, never
described as "real-world" or "natural" drift -- no natural-drift audit was
run for ISOT and none is claimed.

Design:
  - Drift is a physically-motivated covariate-space perturbation applied to
    the CLIENT's entire local feature matrix (every row, regardless of that
    row's attack-family label) -- it models the physical RF/network channel
    degrading over time (e.g. increasing interference, distance from base
    station), which affects every packet on that channel, not just benign
    traffic specifically. Labels are never touched.
  - Only a designated subset of HONEST clients drift (chosen as the 5
    highest-Regular-share clients in the frozen manifest: 11, 1, 14, 10, 9)
    -- consistent with the original protocol ("Drift applied to honest
    clients only").
  - Drift strength follows one of three temporal schedules over the FIXED
    45-round communication budget (frozen in Phase 1): sudden, gradual,
    recurring. A schedule returns strength in [0, 1] for a given round.
  - Revision (v3, after single-seed v2 pilot review): "sudden" and "gradual"
    now each include an explicit recovery phase (the channel returns to
    strength 0 partway through the budget) instead of remaining drifted
    through round 45. The v2 pilot showed the channel-degradation signal was
    only clearly visible in the final ~2 rounds of each schedule and gave no
    post-drift window to measure adaptation/recovery at all for these two
    schedules -- both fixed here rather than carried into the multi-seed run.
  - The perturbed features are standardized (StandardScaler already fit in
    Phase 1) BEFORE scaling is applied downstream by data.py's pipeline, so
    perturbation magnitudes here are expressed in raw-feature units.

Feature choice and direction (documented, not arbitrary):
  - Rate, Srate, Drate (throughput-like): decrease  -- degraded channel
    carries less effective throughput.
  - IAT (inter-arrival time): increase -- packets more spaced out under
    interference/congestion.
  - flow_active_time, Duration: increase -- sessions take longer to
    complete under degraded conditions.
  - Entropy: mild decrease, CLIPPED to never go below the 5th percentile of
    the class's own pre-drift Entropy distribution -- large enough to be a
    genuine covariate shift, deliberately bounded so it cannot cross into
    DoS/Password-Cracking's near-zero Entropy range and become
    indistinguishable from an attack signature (that specific "drift
    mimics attack" edge case is reserved for the adaptive-attacker phase,
    not introduced accidentally here).
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
MULTIPLICATIVE_UP = ["IAT", "flow_active_time", "Duration"]
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
    return d


def compute_entropy_floor(df: pd.DataFrame) -> float:
    return float(df[ENTROPY_COL].quantile(0.05)) if ENTROPY_COL in df.columns else 0.0
