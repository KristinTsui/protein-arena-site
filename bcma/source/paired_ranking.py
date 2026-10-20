"""Display-only, provisional model scoring; never an experimental binding claim."""
import json, math
from decimal import Decimal
from pathlib import Path

def ranks(rows,key):
    ordered=sorted((r for r in rows if r[key] is not None),key=lambda r:(-round(r[key],6),r['id']))
    prev=None;rank=0
    for n,r in enumerate(ordered,1):
        score=round(r[key],6)
        if score!=prev:rank=n
        r['rank']=rank;prev=score
    return rows

def decline(wt,variant):
    for key in ('iptm','ipsae_binder_to_target','ipsae_target_to_binder'):
        a,b=Decimal(str(wt[key])),Decimal(str(variant[key]))
        if a-b < max(Decimal('.10'),Decimal('.25')*a):return False
    return True

def build(data):
    ids=[m['id'] for m in data['members'] if not m['control']]
    states=[a['id'] for a in data['antigens']]
    cells={(c['engine'],c['binder'],c['antigen']):c for c in data['cells']}
    assert len(cells)==len(data['cells']) and len(ids)==23 and len(states)==5
    get=lambda e,b,s:cells.get((e,b,s))
    result={}
    for engine in ('fast','boltz'):
        blue=[]
        for b in ids:
            values=[get(engine,b,s)['confidence'] for s in states if get(engine,b,s)]
            complete=len(values)==5
            blue.append(dict(id=b,score=round((sum(values)/5+min(values))/2,6) if complete else None,mean=round(sum(values)/5,6) if complete else None,worst=min(values) if complete else None,coverage=len(values),rank=None))
        wt_complete=all(get(engine,b,'WT') for b in ids)
        panel=[b for b in ids if get(engine,b,'WT') and get(engine,b,'WT')['confidence']>=50] if wt_complete else []
        red=[]
        for s in states:
            pairs=[(get(engine,b,'WT'),get(engine,b,s)) for b in panel if get(engine,b,s)]
            count=sum(decline(a,b) for a,b in pairs) if s!='WT' else 0
            complete=wt_complete and bool(panel) and len(pairs)==len(panel)
            red.append(dict(id=s,score=round(100*count/len(panel),6) if complete and s not in ('WT','P33S') else None,count=count if complete else None,evaluable=len(pairs),panel_size=len(panel) if wt_complete else None,rank=None,reference=s in ('WT','P33S')))
        result[engine]=dict(blue=ranks(blue,'score'),red=ranks(red,'score'),wt_panel=panel,wt_complete=wt_complete)
    data['rankings']=result
    data['ranking_policy']=dict(version='bcma-paired-confidence-v1',blue_overall='0.5 × mean(C across five states) + 0.5 × min(C across five states); all five required',red='Within each engine, freeze the panel of contestants with WT C ≥ 50 after all 23 WT scores exist. Count a provisional escape signal when ipTM and both directional ipSAE each drop by at least max(0.10, 25% of WT value). Rank 100 × signals / fixed panel size only with complete panel coverage. WT and P33S remain unranked references.',interpretation='Uncalibrated confidence-loss heuristic, not established binding or biological escape. No target-integrity or physics confirmation is implied. C ≥ 50 is a provisional eligibility threshold, not a validated binding cutoff.',engine_aggregation='No cross-engine averaging',ties='Competition ranks on scores rounded to six decimals',physics='Existing confidence-plus-physics policy is unchanged; pending physics is never imputed.')
    return data

if __name__=='__main__':
    import sys
    path=Path(sys.argv[1]);data=build(json.loads(path.read_text()));path.write_text(json.dumps(data,indent=2,allow_nan=False)+'\n')
