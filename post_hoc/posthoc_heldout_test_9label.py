"""POST-HOC companion to posthoc_heldout_test.py (2026-10-19). Reads ONLY its
per-checkpoint confusion matrices; no model is loaded. Recomputes held-out-test
PH-L1 macro-F1 over the 9 labels used for validation (excluding Password
Cracking, which is absent from validation), and reports Password Cracking recall
change, to show how much of the test macro-F1 drop comes from that class."""
import csv, json, math
from pathlib import Path
import numpy as np
from scipy import stats
H = Path(__file__).resolve().parent / "heldout_test"
CATS = ["DoS","Injection","Ip Spoofing","MITM","Manipulation","Password Cracking","Regular","Replay","Unauth","Video"]
PC = CATS.index("Password Cracking"); L9 = [i for i in range(10) if i != PC]
FULL = {"sudden":[15,20,25,29],"gradual":[20,25],"recurring":[15,20,21,30,35,36]}
SEEDS = [21,32,43,54,65]
def mf1(cm, labels):
    cm = np.array(cm, float); f = []
    for i in labels:
        tp = cm[i,i]; p = cm[:,i].sum(); r = cm[i,:].sum()
        prec = tp/p if p else 0.0; rec = tp/r if r else 0.0
        f.append(2*prec*rec/(prec+rec) if prec+rec else 0.0)
    return float(np.mean(f))
def rec(cm, i):
    cm = np.array(cm, float); return cm[i,i]/cm[i,:].sum()
def summ(v):
    v=np.asarray(v,float); n,m,sd=len(v),v.mean(),v.std(ddof=1); h=stats.t.ppf(.975,n-1)*sd/math.sqrt(n)
    return f"mean={m:+.4f} sd={sd:.4f} range=[{v.min():+.4f},{v.max():+.4f}] 95%t=[{m-h:+.4f},{m+h:+.4f}] neg={int((v<0).sum())}/{n}"
D = {}
for r in csv.DictReader(open(H/"per_checkpoint_test.csv")):
    D[(r["algorithm"],r["schedule"],int(r["seed"]),int(r["round"]))] = (json.loads(r["clean_confusion_matrix_json"]), json.loads(r["drifted_confusion_matrix_json"]))
L = ["POST-HOC companion: held-out-test PH-L1 with the 9 validation labels (Password Cracking excluded) and Password Cracking recall change."]
for a in ("fedavg","fedprox"):
    for s,rr in FULL.items():
        m9 = [np.mean([mf1(D[(a,s,k,r)][1],L9)-mf1(D[(a,s,k,r)][0],L9) for r in rr]) for k in SEEDS]
        pc = [np.mean([rec(D[(a,s,k,r)][1],PC)-rec(D[(a,s,k,r)][0],PC) for r in rr]) for k in SEEDS]
        pcc = [np.mean([rec(D[(a,s,k,r)][0],PC) for r in rr]) for k in SEEDS]
        L.append(f"  {a:7s} {s:9s} macro-F1(9 labels) {summ(m9)}")
        L.append(f"  {'':7s} {'':9s} PassCrack recall Δ {summ(pc)}   (clean PC recall mean {np.mean(pcc):.3f})")
(H/"summary_9label.txt").write_text("\n".join(L)+"\n"); print("\n".join(L))
