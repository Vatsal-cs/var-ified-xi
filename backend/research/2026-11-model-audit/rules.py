import sys, numpy as np, pandas as pd
path=sys.argv[1]; lo=int(sys.argv[2]) if len(sys.argv)>2 else 4; hi=int(sys.argv[3]) if len(sys.argv)>3 else 99
r=pd.read_csv(path)
# one row per player-round (doubles summed)
g=r.groupby(['player_id','round'],as_index=False).agg(web_name=('web_name','first'),pos=('element_type','first'),
   cost=('now_cost','first'),pred=('pred','sum'),actual=('actual','sum'),minutes=('minutes','sum'),form5=('points_avg_5','first'))
g=g.sort_values(['player_id','round'])
gp=g.groupby('player_id')
g['std_pts']=gp['actual'].transform(lambda s:s.shift().fillna(0).cumsum())   # season-to-date before this round (rounds>=2)
g['std_apps']=gp['minutes'].transform(lambda s:s.gt(0).shift().fillna(False).astype(int).cumsum())
g['rounds_before']=g['round']-g['round'].min()
g['std_pgw']=g['std_pts']/g['rounds_before'].clip(lower=1)
g=g[(g['round']>=lo)&(g['round']<=hi)]
print(f"{path.split('/')[-1]}  rounds {g['round'].min()}-{g['round'].max()}  player-weeks {len(g)}")
# 1. proven scorers: top-N by season points before the round
for N in (10,30):
    top=g[g.groupby('round')['std_pts'].rank(ascending=False,method='first')<=N]
    print(f"  top {N} season scorers so far: predicted {top.pred.mean():.2f}  scored {top.actual.mean():.2f}  gap {top.actual.mean()-top.pred.mean():+.2f}/wk")
hot=g[g['form5']>=6]
print(f"  last-5 avg 6+: predicted {hot.pred.mean():.2f}  scored {hot.actual.mean():.2f}  gap {hot.actual.mean()-hot.pred.mean():+.2f}  n {len(hot)}")
# 2. pick the best 2/5/5/3 each week by each rule (no prices) and count points
shape={1:2,2:5,3:5,4:3}
def pick(score):
    tot=0
    for rd,w in g.groupby('round'):
        for pos,k in shape.items():
            tot+=w[w.pos==pos].nlargest(k,score)['actual'].sum()
    return tot/g['round'].nunique()
print("  best 15 by each rule, points/wk:", {s:round(pick(s),1) for s in ['pred','std_pgw','form5','actual']})
# 3. captain = top of each rule
def cap(score): return g.loc[g.groupby('round')[score].idxmax(),'actual'].mean()
print("  captain (top of rule), pts/wk:", {s:round(cap(s),2) for s in ['pred','std_pgw','form5']})
# 4. by price band: are expensive players underrated?
g['band']=pd.cut(g['cost'],[0,55,75,100,200],labels=['<5.5','5.5-7.5','7.5-10','10+'])
print(g[g.minutes>=0].groupby('band',observed=True).apply(lambda d: pd.Series({'pred':d.pred.mean(),'scored':d.actual.mean(),'n':len(d)})).round(2).to_string())
