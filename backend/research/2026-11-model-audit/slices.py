"""Residual (actual - predicted) by slice, per season, for the current model's
walk-forward replays. Only selection-relevant rows (pred >= 3) unless noted."""
import sys, numpy as np, pandas as pd
files = dict(a.split('=', 1) for a in sys.argv[1:])
def load(path):
    r = pd.read_csv(path)
    r['res'] = r.actual - r.pred
    r['double'] = r.duplicated(['player_id', 'round'], keep=False)
    prev = r[[f'prev_pts_{k}' for k in range(1, 6)]]
    r['prev_hauls'] = (prev >= 10).sum(axis=1)
    r['rank_in_gw'] = r.groupby('round')['pred'].rank(ascending=False, method='first')
    return r
S = {k: load(v) for k, v in files.items()}
slices = {
    'all relevant (pred>=3)':            lambda r: r.pred >= 3,
    'top 3 projections each week':       lambda r: r.rank_in_gw <= 3,
    'top 20 projections each week':      lambda r: r.rank_in_gw <= 20,
    'just hauled (10+ last match)':      lambda r: (r.pred >= 3) & (r.prev_pts_1 >= 10),
    ' ... and GW<=14':                   lambda r: (r.pred >= 3) & (r.prev_pts_1 >= 10) & (r['round'] <= 14),
    'blanked last match (<=2)':          lambda r: (r.pred >= 3) & (r.prev_pts_1 <= 2) & (r.prev_min_1 >= 60),
    'missed last match, played before':  lambda r: (r.pred >= 3) & (r.prev_min_1 == 0) & (r.prev_min_2 >= 60),
    'little history (<2 of last 3)':     lambda r: (r.pred >= 3) & (r.starts_avg_3 < 0.67),
    'points far above xGI (lucky?)':     lambda r: (r.pred >= 3) & (r.element_type >= 3) & (r.points_avg_5 >= 6) & (r.xgi_avg_3 < 0.3),
    'high xGI, low points (unlucky?)':   lambda r: (r.pred >= 3) & (r.element_type >= 3) & (r.xgi_avg_3 >= 0.6) & (r.points_avg_5 < 4),
    'defensive-contribution heavy':      lambda r: (r.pred >= 3) & (r.dc_avg_5 >= 8),
    'price 10.0+':                       lambda r: (r.pred >= 3) & (r.now_cost >= 100),
    'price under 5.5':                   lambda r: (r.pred >= 3) & (r.now_cost < 55),
    'double gameweek match':             lambda r: (r.pred >= 2) & r.double,
    'GW 2-10':                           lambda r: (r.pred >= 3) & (r['round'] <= 10),
    'GW 30+':                            lambda r: (r.pred >= 3) & (r['round'] >= 30),
}
rows = []
for name, f in slices.items():
    row = {'slice': name}
    for s, r in S.items():
        m = f(r)
        row[s] = f"{r.loc[m, 'res'].mean():+.2f} ({m.sum()})" if m.sum() >= 15 else f"  -  ({m.sum()})"
    rows.append(row)
print(pd.DataFrame(rows).to_string(index=False))
print("\nStart-chance calibration on relevant players (pred>=3): predicted P(60+) vs actual")
for s, r in S.items():
    m = r.pred >= 3
    print(f"  {s}: {r.loc[m,'p60'].mean():.3f} vs {(r.loc[m,'minutes']>=60).mean():.3f}  | points if 60+: {r.loc[m&(r.minutes>=60),'pts_if_60'].mean():.2f} vs {r.loc[m&(r.minutes>=60),'actual'].mean():.2f}")
