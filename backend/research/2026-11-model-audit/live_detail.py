import sys,json,numpy as np,pandas as pd
import os; S=os.path.dirname(os.path.abspath(__file__))
r=pd.read_csv(sys.argv[1])
import urllib.request
b=json.load(urllib.request.urlopen('https://fantasy.premierleague.com/api/bootstrap-static/'))
tn={t['id']:t['short_name'] for t in b['teams']}
r['teamn']=r['team'].map(tn) if sys.argv[1].find('live')>=0 else r['team']
r['res']=r['actual']-r['pred']
r['p60_hit']=(r['minutes']>=60).astype(int)
pos={1:'GK',2:'DEF',3:'MID',4:'FWD'}; r['posn']=r['element_type'].map(pos)
print("== by position (all rows) ==")
print(r.groupby('posn').agg(pred=('pred','mean'),actual=('actual','mean'),p60=('p60','mean'),played60=('p60_hit','mean'),n=('pred','size')).round(2).to_string())
print("\n== start chance calibration ==")
r['pbin']=pd.cut(r['p60'],[0,.1,.3,.5,.7,.85,.95,1.01])
print(r.groupby('pbin',observed=True).agg(pred_p60=('p60','mean'),actual_60=('p60_hit','mean'),n=('p60','size')).round(3).to_string())
print("\n== points if he plays 60+: calibration by position (players who did play 60+) ==")
p=r[r.minutes>=60]
print(p.groupby('posn').agg(pred_if60=('pts_if_60','mean'),actual=('actual','mean'),n=('actual','size')).round(2).to_string())
print("\n== relevant players only (pred>=3.5): residual by position ==")
rel=r[r.pred>=3.5]
print(rel.groupby('posn').agg(pred=('pred','mean'),actual=('actual','mean'),n=('pred','size')).round(2).to_string())
print("\n== by team, relevant players (pred>=3) ==")
t=r[r.pred>=3].groupby('teamn').agg(pred=('pred','mean'),actual=('actual','mean'),n=('pred','size'))
t['gap']=t.actual-t.pred
print(t.sort_values('gap').round(2).to_string())
print("\n== hauls (10+) the model rated under 3 ==")
h=r[(r.actual>=10)]
print(f"hauls {len(h)}, rated <3: {(h.pred<3).sum()}, rated 3-5: {((h.pred>=3)&(h.pred<5)).sum()}, rated 5+: {(h.pred>=5).sum()}")
print(h[h.pred<3].sort_values('actual',ascending=False)[['round','web_name','teamn','posn','now_cost','pred','p60','actual','minutes']].head(20).to_string(index=False))
print("\n== top projections that flopped (pred>=5, actual<=2) ==")
f=r[(r.pred>=5)]
print(f"pred 5+: {len(f)}, flopped <=2: {(f.actual<=2).sum()}, of which didn't play 60: {((f.actual<=2)&(f.minutes<60)).sum()}")
print(f[f.actual<=2].sort_values('pred',ascending=False)[['round','web_name','teamn','posn','pred','p60','actual','minutes']].head(15).to_string(index=False))
