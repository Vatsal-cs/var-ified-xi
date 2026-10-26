import json, collections, statistics as st, sys
S=sys.argv[1]
bs=json.load(open(f'{S}/bs3.json')); el={e['id']:e for e in bs['elements']}
picks=json.load(open(f'{S}/top/picks.json'))
live={}
for gw in range(1,9):
    lv=json.load(open(f'{S}/top/live{gw}.json'))['elements']
    live[gw]={e['id']:e['stats'] for e in lv}
def comp(p,gw):
    L=live[gw]; chip=p.get('active_chip')
    out=collections.Counter()
    for x in p['picks']:
        pts=L.get(x['element'],{}).get('total_points',0)
        m=x['multiplier']
        if m==0: out['bench_unused']+=pts; continue
        if x['position']>11 and chip=='bboost': out['chip']+=pts; continue
        out['xi']+=pts
        if m>=2: out['captain']+=pts*(1 if m==2 else 1); 
        if m==3: out['chip']+=pts
    out['hits']=-p['entry_history']['event_transfers_cost']
    out['total']=p['entry_history']['points']-p['entry_history']['event_transfers_cost']
    out['transfers']=p['entry_history']['event_transfers']
    out['value']=p['entry_history']['value']
    return out
top=[k for k in picks if not k.startswith('9927826_')]
print('per-GW averages, top-10k sample (n=50) vs you')
agg=collections.defaultdict(list); you={}
for k in top:
    e,gw=k.split('_'); gw=int(gw)
    agg[gw].append(comp(picks[k],gw))
for gw in range(1,9):
    if f'9927826_{gw}' in picks: you[gw]=comp(picks[f'9927826_{gw}'],gw)
cols=['total','xi','captain','chip','hits','transfers']
print('GW  '+'  '.join(f'{c:>9}' for c in cols)+'   | you: '+' '.join(f'{c:>6}' for c in cols))
T=collections.Counter(); Y=collections.Counter()
for gw in range(1,9):
    a={c:st.mean(x[c] for x in agg[gw]) for c in cols}
    for c in cols:
        if gw>=2: T[c]+=a[c]; Y[c]+=you.get(gw,{}).get(c,0)
    y=you.get(gw,{})
    print(f'{gw:<3} '+'  '.join(f'{a[c]:>9.1f}' for c in cols)+'   |       '+' '.join(f'{y.get(c,0):>6}' for c in cols))
print('GW2-8 '+'  '.join(f'{T[c]:>9.1f}' for c in cols)+'  | you '+' '.join(f'{Y[c]:>6}' for c in cols))
# chip timing
chips=collections.Counter((picks[k].get('active_chip'),int(k.split('_')[1])) for k in top if picks[k].get('active_chip'))
print('chips used (chip, GW): count', sorted(chips.items(), key=lambda x:(x[0][0],x[0][1])))
# captain choices
for gw in range(1,9):
    caps=collections.Counter(el[[x['element'] for x in picks[k]['picks'] if x['is_captain']][0]]['web_name'] for k in top if k.endswith(f'_{gw}'))
    yc=[el[x['element']]['web_name'] for x in picks.get(f'9927826_{gw}',{'picks':[]})['picks'] if x['is_captain']]
    print(f'GW{gw} caps', caps.most_common(4), 'you', yc, 'pts', {n:live[gw][[i for i in el if el[i]['web_name']==n][0]]['total_points'] for n,_ in caps.most_common(3)})
