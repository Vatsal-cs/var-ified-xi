import json,subprocess,urllib.request,os
S=os.path.dirname(os.path.abspath(__file__)); C=os.path.join(S,'.cache'); os.makedirs(C,exist_ok=True)
def get(u):
    p=os.path.join(C,'cache_'+u.split('api/')[1].replace('/','_')+'.json')
    if os.path.exists(p): return json.load(open(p))
    d=json.load(urllib.request.urlopen(u)); json.dump(d,open(p,'w')); return d
b=get("https://fantasy.premierleague.com/api/bootstrap-static/")
name={p['id']:p['web_name'] for p in b['elements']}
ev={e['id']:e for e in b['events']}
# last snapshot per GW committed before that GW's deadline
snaps={}
for line in open(os.path.join(S,'snapshots.txt')):
    h,t,gw,gen,dl,*_=line.split()
    if gw=='None': continue
    gw=int(gw)
    if gen<=ev[gw]['deadline_time'][:19]: snaps[gw]=h
tot={'you':0,'mxi':0,'cap':0,'crowd':0,'best':0}
print("GW | you | model XI (as given) | your cap pts | model cap | crowd cap | best possible cap | XI overlap")
for gw in range(2,11):
    live={e['id']:e['stats']['total_points'] for e in get(f"https://fantasy.premierleague.com/api/event/{gw}/live/")['elements']}
    pk=get(f"https://fantasy.premierleague.com/api/entry/9927826/event/{gw}/picks/")
    mine={p['element'] for p in pk['picks'] if p['multiplier']>0}
    mycap=next(p['element'] for p in pk['picks'] if p['is_captain'])
    d=json.loads(subprocess.run(['git','show',f"{snaps[gw]}:frontend/public/optimized_team.json"],capture_output=True,text=True).stdout)
    fh=d.get('free_hit') or {}
    xi=d['starting_xi']; cap=d['captain_id']
    mx=[p['player_id'] for p in xi]
    mxi=sum(live[i] for i in mx)+live[cap]
    crowd=ev[gw]['most_captained']
    best=max(live[i] for i in mine)
    tot['you']+=pk['entry_history']['points']; tot['mxi']+=mxi; tot['cap']+=live[mycap]; tot['crowd']+=live[crowd]; tot['best']+=best
    print(gw,pk['entry_history']['points'],mxi,f"{name[mycap]} {live[mycap]}",f"{name[cap]} {live[cap]}",f"{name[crowd]} {live[crowd]}",best,len(mine&set(mx)),'/11', d.get('mode'))
print(tot)
