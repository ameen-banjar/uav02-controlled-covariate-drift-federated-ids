"""
CICIoT2023 arm of UAV-02 v3 (external-dataset replication of the time-dilation
analysis). Source: the cleaned, deduplicated, conflict-free, stratified
train/validation split prepared for UAV-01 item 5 (prepare_ciciot.py; global
fingerprint audit). Test rows are not used.

prepare() (run once before the freeze; outputs hashed):
  * rows with IAT < 0 are removed (a negative inter-arrival time is physically
    impossible); their count per split is written to cic_prepared/audit.json;
  * class-capped sample with seed 2023: at most 60,000 training rows and
    8,000 validation rows per class (34 classes), so that one run costs about
    the same as an ISOT run;
  * 15 clients by row-level Dirichlet(0.5) per class, seed 42 (CICIoT2023 has
    no session identifiers in the released CSVs);
  * exposure order: clients sorted by Benign_Final row share, descending.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from sklearn.preprocessing import LabelEncoder, StandardScaler

HERE = Path(__file__).resolve().parent
SRC = (HERE.parents[1] / "repositories" / "paper-01-rare-class-erosion" / "paper1_rare_class_erosion"
       / "item5_cross_domain_validation" / "prepared_data")
OUT = HERE / "cic_prepared"
SEED_SAMPLE, SEED_PART = 2023, 42
CAP_TRAIN, CAP_VAL, N_CLIENTS, ALPHA = 60_000, 8_000, 15, 0.5
BENIGN = "Benign_Final"


def _cap(df, cap, seed):
    return (df.groupby("cls", group_keys=False)
              .apply(lambda g: g.sample(n=min(len(g), cap), random_state=seed))
              .reset_index(drop=True))


def prepare():
    OUT.mkdir(exist_ok=True)
    feats = [l.strip() for l in open(SRC / "feature_columns.txt") if l.strip()]
    classes = sorted(l.strip() for l in open(SRC / "classes.txt") if l.strip())
    audit = {}
    for split, cap in (("train", CAP_TRAIN), ("validation", CAP_VAL)):
        df = pd.read_parquet(SRC / f"{split}.parquet")
        neg = df["IAT"] < 0
        audit[split] = {"rows_before": int(len(df)), "iat_negative_rows": int(neg.sum()),
                        "iat_negative_share": float(neg.mean()),
                        "ttl_above_255": int((df["Time_To_Live"] > 255).sum())}
        df = _cap(df[~neg], cap, SEED_SAMPLE)
        audit[split]["rows_after_cap"] = int(len(df))
        df.to_parquet(OUT / f"{split}.parquet", index=False)
        if split == "train":
            rng = np.random.RandomState(SEED_PART)
            client = np.empty(len(df), dtype=int)
            for c in classes:
                idx = np.where(df["cls"].to_numpy() == c)[0]
                if len(idx) == 0:
                    continue
                w = rng.dirichlet([ALPHA] * N_CLIENTS)
                client[idx] = rng.choice(N_CLIENTS, size=len(idx), p=w)
            np.save(OUT / "train_client.npy", client)
            share = {i: float((df["cls"].to_numpy()[client == i] == BENIGN).mean()) for i in range(N_CLIENTS)}
            rows = {i: int((client == i).sum()) for i in range(N_CLIENTS)}
            order = sorted(range(N_CLIENTS), key=lambda i: (-share[i], i))
            json.dump({"n_clients": N_CLIENTS, "alpha": ALPHA, "seed": SEED_PART, "rows": rows,
                       "benign_share": share, "exposure_order": order}, open(OUT / "clients.json", "w"), indent=1)
    json.dump({"features": feats, "classes": classes}, open(OUT / "meta.json", "w"), indent=1)
    json.dump(audit, open(OUT / "audit.json", "w"), indent=1)
    print(json.dumps(audit, indent=1))


class CICData:
    """Same interface subset as ISOTFederatedData that run_v3.py uses."""

    def __init__(self):
        meta = json.load(open(OUT / "meta.json"))
        self.feature_cols, self.categories = meta["features"], meta["classes"]
        self.clients_meta = json.load(open(OUT / "clients.json"))
        self.n_clients = self.clients_meta["n_clients"]
        self.label_encoder = LabelEncoder().fit(self.categories)
        self.train = pd.read_parquet(OUT / "train.parquet")
        self.val = pd.read_parquet(OUT / "validation.parquet")
        self.client_of = np.load(OUT / "train_client.npy")

    def fit_preprocessing(self):
        self.scaler = StandardScaler().fit(self.train[self.feature_cols])
        counts = self.train["cls"].value_counts().reindex(self.categories).fillna(0).values
        n, k = counts.sum(), len(self.categories)
        b = n / (k * np.maximum(counts, 1))
        self.class_weights_full_balanced = torch.tensor(b / b.mean(), dtype=torch.float32)

    def tensors_from_df(self, df):
        X = self.scaler.transform(df[self.feature_cols])
        y = self.label_encoder.transform(df["cls"])
        return torch.tensor(X, dtype=torch.float32), torch.tensor(y, dtype=torch.long)

    def client_ids(self):
        return list(range(self.n_clients))

    def get_client_raw_df(self, cid):
        return self.train[self.client_of == cid].reset_index(drop=True)

    def client_weight_rows(self, cid):
        return self.clients_meta["rows"][str(cid)] / len(self.train)

    def validation_raw(self):
        return self.val


if __name__ == "__main__":
    if sys.argv[1:] == ["prepare"]:
        prepare()
