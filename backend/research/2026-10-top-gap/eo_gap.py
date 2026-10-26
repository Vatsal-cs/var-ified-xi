import json, subprocess, collections, sys
S=sys.argv[1]
bs=json.load(open(f'{S}/bs3.json')); el={e['id']:e for e in bs['elements']}; ev={e['id']:e for e in bs['events']}
picks=json.load(open(f'{S}/top/picks.json'))
name=lambda i: el.get(i,{}).get('web_name',str(i))
def model_picks(gw):
    h=subprocess.run(["git","log","-1","--format=%h","--before",ev[gw]["deadline_time"],"--","frontend/public/optimized_team.json"],capture_output=True,text=True).stdout.strip()
    d=json.loads(subprocess.run(["git","show",f"{h}:frontend/public/optimized_team.json"],capture_output=True,text=True).stdout)
    xi=[p["player_id"] for p in d["starting_xi"]]; bench=[p["player_id"] for p in d["bench"]]
    return xi,bench,d['captain_id'],d.get('vice_captain_id'),{p['player_id']:p['predicted_points'] for p in d['starting_xi']+d['bench']}
def ok(ids):
    c=collections.Counter(el[i]['element_type'] for i in ids)
    return c[1]==1 and c[2]>=3 and c[3]>=2 and c[4]>=1
def mults(xi,bench,cap,vice,mins):
    xi=list(xi)
    for b in bench:
        for k,s in enumerate(xi):
            if mins.get(s,0)==0 and mins.get(b,0)>0 and el[s]['element_type']!=1 and el[b]['element_type']!=1:
                t=xi[:k]+[b]+xi[k+1:]
                if ok(t): xi=t; break
        else: continue
    gk_xi=[i for i in xi if el[i]['element_type']==1]
    m={i:1 for i in xi}
    c=cap if mins.get(cap,0)>0 else vice
    if c in m: m[c]=2
    return m
tot=collections.Counter(); per_player=collections.Counter(); per_player_cap=collections.Counter()
rows=[]
for gw in range(2,9):
    lv=json.load(open(f'{S}/top/live{gw}.json'))['elements']
    pts={e['id']:e['stats']['total_points'] for e in lv}; mins={e['id']:e['stats']['minutes'] for e in lv}
    xi,bench,cap,vice,proj=model_picks(gw)
    mm=mults(xi,bench,cap,vice,mins)
    # top-10k average multiplier per player (excluding chip-only effects: count TC as 2, BB bench as 0 -> chips reported separately)
    top=[k for k in picks if k.endswith(f'_{gw}') and not k.startswith('9927826_')]
    avg=collections.Counter(); avgcap=collections.Counter()
    for k in top:
        p=picks[k]
        for x in p['picks']:
            mlt=min(x['multiplier'],2)
            if x['position']>11 and p.get('active_chip')=='bboost': mlt=0
            if mlt: avg[x['element']]+=1/len(top)
            if mlt==2: avgcap[x['element']]+=1/len(top)
    you=picks[f'9927826_{gw}']; ym={x['element']:x['multiplier'] for x in you['picks'] if x['multiplier']}
    model_pts=sum(pts.get(i,0)*m for i,m in mm.items())
    for i in set(avg)|set(mm):
        base_gap=((1 if i in mm else 0)-avg[i])*pts.get(i,0)
        cap_gap=((1 if mm.get(i)==2 else 0)-avgcap[i])*pts.get(i,0)
        per_player[(name(i))]+=base_gap; per_player_cap[name(i)]+=cap_gap
        tot['xi']+=base_gap; tot['cap']+=cap_gap
    rows.append((gw,model_pts,name(cap),pts.get(cap,0)))
print('model picks per GW (pts, captain, cap pts):', rows, 'sum', sum(r[1] for r in rows))
print('model vs top-10k, GW2-8, players (base) %+.1f captain %+.1f'%(tot['xi'],tot['cap']))
print('biggest base-ownership gaps (model minus top avg, points):')
for n,v in sorted(per_player.items(), key=lambda x:x[1])[:12]: print(f'   {n:<14}{v:+6.1f}')
print('  ...biggest gains:'); 
for n,v in sorted(per_player.items(), key=lambda x:-x[1])[:8]: print(f'   {n:<14}{v:+6.1f}')
print('captaincy gaps:')
for n,v in sorted(per_player_cap.items(), key=lambda x:x[1])[:6]: print(f'   {n:<14}{v:+6.1f}')
for n,v in sorted(per_player_cap.items(), key=lambda x:-x[1])[:4]: print(f'   {n:<14}{v:+6.1f}')
