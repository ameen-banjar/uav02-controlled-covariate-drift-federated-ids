"""
Builds the v3 client manifests (run once before the freeze; outputs are hashed).
The 18 validation and 28 held-out-test sessions of the frozen manifest are
never moved. Only the 91 training-pool sessions are re-partitioned.

  alpha_<a>.json   15 clients, session-level Dirichlet(a) for attack sessions,
                   one Regular session per client first, leftover Regular
                   sessions uniformly (the same procedure as
                   data_audit/build_federated_clients.py step 3), partition
                   seed 42; a in {0.1, 2.0, 100}.
  fresh.json       12 sessions removed from the pool as a FRESH evaluation
                   set never used for evaluation by any earlier campaign:
                   4 Regular + 1 of each attack class with >= 4 pool sessions
                   (DoS, Injection, Ip Spoofing, MITM, Manipulation, Replay,
                   Unauth, Video); selection seed 2026. Password Cracking (1
                   pool session) stays in training. The remaining 79 sessions
                   are partitioned as alpha 0.5, seed 42.
Each manifest records the exposed-client order: clients sorted by Regular
row share, descending (the rule used for the frozen manifest).
"""
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from data import MANIFEST_PATH, ALL_CATEGORIES  # noqa: E402
from data_audit_paths import DATA_DIR  # noqa: E402

OUT = HERE / "manifests"
N_CLIENTS = 15
PARTITION_SEED = 42
FRESH_SEED = 2026
FRESH_ATTACK = ["DoS", "Injection", "Ip Spoofing", "MITM", "Manipulation", "Replay", "Unauth", "Video"]


def session_lookup():
    cat, rows = {}, {}
    for cdir in sorted(DATA_DIR.iterdir()):
        if cdir.is_dir():
            for f in sorted(cdir.glob("*.csv")):
                cat[f.stem] = cdir.name
                with open(f) as fh:
                    rows[f.stem] = sum(1 for _ in fh) - 1
    return cat, rows


def partition(pool, alpha, seed, cat, rows):
    rng = np.random.RandomState(seed)
    pool = sorted(pool)
    clients = {i: [] for i in range(N_CLIENTS)}
    regular = [s for s in pool if cat[s] == "Regular"]
    rng.shuffle(regular)
    for i in range(N_CLIENTS):
        if regular:
            clients[i].append(regular.pop())
    for c in sorted({cat[s] for s in pool} - {"Regular"}):
        ss = [s for s in pool if cat[s] == c]
        rng.shuffle(ss)
        w = rng.dirichlet([alpha] * N_CLIENTS)
        for s in ss:
            clients[int(rng.choice(N_CLIENTS, p=w))].append(s)
    for s in regular:
        clients[int(rng.choice(N_CLIENTS))].append(s)
    total = sum(rows[s] for s in pool)
    out = {}
    for i, ss in clients.items():
        n = sum(rows[s] for s in ss)
        reg = sum(rows[s] for s in ss if cat[s] == "Regular")
        out[str(i)] = {"sessions": ss, "n_sessions": len(ss), "n_rows": int(n),
                       "fedavg_weight_by_rows": n / total, "regular_row_share": reg / n if n else 0.0,
                       "row_counts_by_category": {c: int(sum(rows[s] for s in ss if cat[s] == c)) for c in ALL_CATEGORIES}}
    order = sorted(out, key=lambda k: (-out[k]["regular_row_share"], int(k)))
    return out, [int(k) for k in order]


def main():
    frozen = json.loads(Path(MANIFEST_PATH).read_text())
    cat, rows = session_lookup()
    pool = sorted(s for c in frozen["clients"].values() for s in c["sessions"])
    assert len(pool) == 91
    OUT.mkdir(exist_ok=True)
    base = {k: frozen[k] for k in ("held_out_test_sessions", "validation_sessions", "validation_note")}
    frozen_order = sorted(frozen["clients"], key=lambda k: (-frozen["clients"][k]["regular_row_share"], int(k)))
    (OUT / "frozen_exposure_order.json").write_text(json.dumps([int(k) for k in frozen_order]))

    for alpha in (0.1, 2.0, 100.0):
        clients, order = partition(pool, alpha, PARTITION_SEED, cat, rows)
        m = dict(base, n_clients=N_CLIENTS, dirichlet_alpha=alpha, seed=PARTITION_SEED, clients=clients,
                 exposure_order=order, partition_description=f"v3 re-partition of the 91 frozen training-pool sessions, alpha={alpha}")
        (OUT / f"alpha_{alpha:g}.json").write_text(json.dumps(m, indent=1))

    rng = np.random.RandomState(FRESH_SEED)
    fresh = []
    reg = sorted(s for s in pool if cat[s] == "Regular")
    rng.shuffle(reg)
    fresh += reg[:4]
    for c in FRESH_ATTACK:
        ss = sorted(s for s in pool if cat[s] == c)
        assert len(ss) >= 4, c
        rng.shuffle(ss)
        fresh.append(ss[0])
    rest = sorted(set(pool) - set(fresh))
    clients, order = partition(rest, 0.5, PARTITION_SEED, cat, rows)
    m = dict(base, n_clients=N_CLIENTS, dirichlet_alpha=0.5, seed=PARTITION_SEED, clients=clients,
             exposure_order=order, fresh_eval_sessions=sorted(fresh),
             partition_description="v3 fresh-evaluation manifest: 12 pool sessions held out as a fresh evaluation set; remaining 79 re-partitioned alpha=0.5")
    (OUT / "fresh.json").write_text(json.dumps(m, indent=1))
    for f in sorted(OUT.glob("*.json")):
        print(f.name)
    print("fresh sessions:", {s: cat[s] for s in sorted(fresh)})


if __name__ == "__main__":
    main()
