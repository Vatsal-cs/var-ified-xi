import sys,pandas as pd,numpy as np
C=sys.argv[1]; R='research/2026-10-projection-bias'
for s in ['live','2023-24','2024-25','2025-26']:
    r=pd.read_csv(f"{C}/{s}/{R}/rows_{s}.csv")
    r=r.groupby(['player_id','round'],as_index=False).agg(pred=('pred','sum'),actual=('actual','sum'),prev1=('prev_pts_1','first'),
        cost=('now_cost','first'),pos=('element_type','first'),xgi=('xgi_avg_3','first'),p5=('points_avg_5','first'))
    r['res']=r.actual-r.pred
    r['rk']=r.groupby('round')['pred'].rank(ascending=False,method='first')
    t=r[r.rk<=10]
    hot=t.prev1>=10; early=t['round']<=14
    out=[f"{s:8}"]
    for lab,m in [('top10 hauled, GW<=14',hot&early),('top10 not hauled, GW<=14',~hot&early),('top10 hauled, GW15+',hot&~early),('top10 not hauled, GW15+',~hot&~early)]:
        out.append(f"{lab}: {t.loc[m,'res'].mean():+.2f} ({m.sum()})")
    print(" | ".join(out))
    # captain test: top projection vs top projection after removing 1.0 from early hauled players
    def cap(adj):
        rr=r.copy(); rr['adj']=rr.pred-np.where((rr.prev1>=10)&(rr['round']<=14),adj,0)
        return rr.loc[rr.groupby('round')['adj'].idxmax(),'actual'].sum()
    print(f"          captain = top projection: {cap(0)} pts over {r['round'].nunique()} GWs; after -1 for early hauled: {cap(1.0)}; -2: {cap(2.0)}")
