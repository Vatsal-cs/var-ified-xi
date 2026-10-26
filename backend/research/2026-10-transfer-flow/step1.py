import pandas as pd, numpy as np
# Step-1 check: do the model's out-of-sample errors line up with net transfers made before that deadline?
for s in ['2024-25','2025-26']:
    r=pd.read_csv(f'research/2026-10-projection-bias/rows_{s}.csv')
    h=pd.read_csv(f'data/raw/historical_{s}_merged_gw.csv')
    h=h.groupby(['name','GW']).agg(tb=('transfers_balance','first'),ti=('transfers_in','first'),sel=('selected','first')).reset_index()
    mgr=h.groupby('GW').sel.sum()/15
    tot=h.groupby('GW').ti.sum()
    h['net_share']=h.tb/h.GW.map(tot)*100
    h['own']=h.sel/h.GW.map(mgr)*100
    m=r.merge(h,left_on=['web_name','round'],right_on=['name','GW'],how='left')
    m=m[m['round']>=3]
    m['res']=m.actual-m.pred
    print('==',s,'rows',len(m),'matched',m.tb.notna().mean().round(3))
    m['b']=pd.cut(m.net_share,[-100,-2,-0.5,-0.1,0.1,0.5,2,100])
    g=m.groupby('b',observed=True).agg(n=('res','size'),pred=('pred','mean'),act=('actual','mean'),res=('res','mean'),p60=('p60','mean'),played60=('minutes',lambda x:(x>=60).mean()))
    g['p60_gap']=g.played60-g.p60
    print(g.round(3).to_string())
    x=m.dropna(subset=['net_share'])
    for lab,sub in (('all',x),('pred>2',x[x.pred>2]),('pred>3.5',x[x.pred>3.5])):
        print(f'  {lab:<9} n={len(sub):>6} spearman(res, net_share)={sub.res.corr(sub.net_share,method="spearman"):+.3f}  pearson={sub.res.corr(sub.net_share):+.3f}')

print('\n--- within projection bins (players worth considering), bought vs sold vs quiet ---')
for s in ['2024-25','2025-26']:
    r=pd.read_csv(f'research/2026-10-projection-bias/rows_{s}.csv')
    h=pd.read_csv(f'data/raw/historical_{s}_merged_gw.csv')
    h=h.groupby(['name','GW']).agg(tb=('transfers_balance','first'),ti=('transfers_in','first')).reset_index()
    h['net_share']=h.tb/h.GW.map(h.groupby('GW').ti.sum())*100
    m=r.merge(h,left_on=['web_name','round'],right_on=['name','GW'],how='left'); m=m[m['round']>=3]; m['res']=m.actual-m.pred
    m['flow']=np.select([m.net_share>0.25,m.net_share<-0.25],['bought','sold'],'quiet')
    m['pb']=pd.cut(m.pred,[2,3,4,5,20])
    t=m.dropna(subset=['pb']).pivot_table(index='pb',columns='flow',values='res',aggfunc=['mean','size'],observed=True)
    print('==',s); print(t.round(2).to_string())
    rng=np.random.default_rng(0); sub=m[(m.pred>2)]
    d=sub[sub.flow=='bought'].res.mean()-sub[sub.flow=='quiet'].res.mean()
    # bootstrap by gameweek
    gws=sub['round'].unique(); bs=[]
    for _ in range(2000):
        pick=rng.choice(gws,len(gws)); b=pd.concat([sub[sub['round']==g] for g in pick])
        bs.append(b[b.flow=='bought'].res.mean()-b[b.flow=='quiet'].res.mean())
    print(f'  bought minus quiet (pred>2): {d:+.3f}  95% CI [{np.percentile(bs,2.5):+.3f}, {np.percentile(bs,97.5):+.3f}]')
