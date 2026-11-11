# POST-HOC (2026-11-12): MITM recall, precision and F1 change (transformed minus clean, full-strength rounds) from saved confusion matrices. Place in fl_pipeline_v3/post_hoc/ next to the frozen code.
import sys, numpy as np
from pathlib import Path
sys.dont_write_bytecode=True
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
import analyze_v3 as A, run_v3 as R
runs,_,_=A.load(Path(R.RESULTS))
def met(c,i):
    tp=c[i,i]; rec=tp/c[i].sum() if c[i].sum() else np.nan; pre=tp/c[:,i].sum() if c[:,i].sum() else np.nan
    f=2*pre*rec/(pre+rec) if pre+rec else np.nan; return rec,pre,f
chk=0
for arm in ('main_v2','main_td'):
  for algo in ('fedprox','fedavg'):
    for s in A.SCH:
      for tr in ('v2','td'):
        D=[]
        for k in R.SEEDS10:
            run=runs[(arm,k,algo,s)]; v=[]
            for r in A.FULL[s]:
                cl,dr=run[r][('validation','clean')],run[r][('validation',tr)]
                keys=list(cl[2].keys()); i=keys.index('MITM')
                a=met(cl[3],i); b=met(dr[3],i)
                chk=max(chk,abs(a[0]-cl[2]['MITM']))
                v.append([b[j]-a[j] for j in range(3)])
            D.append(np.nanmean(v,0))
        m=100*np.mean(D,0)
        print(f"{arm:8} {algo:8} {s:10} eval {tr}: recall {m[0]:+.2f} precision {m[1]:+.2f} F1 {m[2]:+.2f} pp; precision<0 in {sum(d[1]<0 for d in D)}/10")
print('recall check max abs diff',chk)
