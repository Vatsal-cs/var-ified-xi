import json,subprocess,sys
out=subprocess.run(['git','log','--format=%H %cI','--reverse','--','frontend/public/optimized_team.json'],capture_output=True,text=True).stdout.split('\n')
rows=[]
for line in out:
    if not line: continue
    h,t=line.split()
    try: d=json.loads(subprocess.run(['git','show',f'{h}:frontend/public/optimized_team.json'],capture_output=True,text=True).stdout)
    except Exception: continue
    rows.append((h[:8],t,d.get('gameweek'),d.get('generated_at','')[:19],d.get('deadline'),'projections' in d,len(d.get('projections') or [])))
for r in rows: print(*r)
