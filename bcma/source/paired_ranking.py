"""Display-only, provisional model scoring; never an experimental binding claim."""
import json, math
from decimal import Decimal, ROUND_FLOOR
from pathlib import Path

# Frozen WT control anchors from the published 2026-10-20 snapshot. Do not refit
# to incoming contestants or variants. The 90% allowance is a policy choice.
CONTROL_ANCHORS = {
    'fast': {'iptm': 0.6727321743965149, 'ipsae_max': 0.4448034046101706},
    'boltz': {'iptm': 0.8966211676597595, 'ipsae_max': 0.7742170400793336},
}

def thresholds(engine, fraction='.90'):
    return {key: float((Decimal(str(value))*Decimal(fraction)).quantize(Decimal('.01'), rounding=ROUND_FLOOR))
            for key,value in CONTROL_ANCHORS[engine].items()}

def retained(cell, limits):
    if cell is None: return None
    return all(Decimal(str(cell[k])) >= Decimal(str(v)) for k,v in limits.items())


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
    for cell in data['cells']:
        for key in ('iptm','ipsae_binder_to_target','ipsae_target_to_binder'):
            if not math.isfinite(cell[key]) or not 0 <= cell[key] <= 1: raise ValueError('Invalid confidence component')
        cell['ipsae_max']=max(cell['ipsae_binder_to_target'],cell['ipsae_target_to_binder'])
        cell['confidence']=round(50*(cell['iptm']+cell['ipsae_max']),6)
        cell['predicted_retained']=retained(cell,thresholds(cell['engine']))
    data['confidence_formula']='C = 50 × (native ipTM + max(ipSAE binder→target, ipSAE target→binder))'
    ids=[m['id'] for m in data['members'] if not m['control']]
    states=[a['id'] for a in data['antigens']]
    cells={(c['engine'],c['binder'],c['antigen']):c for c in data['cells']}
    assert len(cells)==len(data['cells']) and len(ids)==23 and len(states)==5
    get=lambda e,b,s:cells.get((e,b,s))
    result={}
    for engine in ('fast','boltz'):
        blue=[]; retention=[]
        for b in ids:
            values=[get(engine,b,s)['confidence'] for s in states if get(engine,b,s)]
            complete=len(values)==5
            blue.append(dict(id=b,score=round((sum(values)/5+min(values))/2,6) if complete else None,mean=round(sum(values)/5,6) if complete else None,worst=min(values) if complete else None,coverage=len(values),rank=None))
            outcomes={s:retained(get(engine,b,s),thresholds(engine)) for s in states}
            sensitivity={f:sum(retained(get(engine,b,s),thresholds(engine,f)) is True for s in states) for f in ('.85','.90','.95')}
            count=sum(v is True for v in outcomes.values())
            retention.append(dict(id=b,score=count if complete else None,count=count,coverage=len(values),unknown=5-len(values),states=outcomes,sensitivity=sensitivity,rank=None))
        wt_complete=all(get(engine,b,'WT') for b in ids)
        panel=[b for b in ids if get(engine,b,'WT') and get(engine,b,'WT')['confidence']>=50] if wt_complete else []
        red=[]
        for s in states:
            pairs=[(get(engine,b,'WT'),get(engine,b,s)) for b in panel if get(engine,b,s)]
            count=sum(decline(a,b) for a,b in pairs) if s!='WT' else 0
            complete=wt_complete and bool(panel) and len(pairs)==len(panel)
            red.append(dict(id=s,score=round(100*count/len(panel),6) if complete and s not in ('WT','P33S') else None,count=count if complete else None,evaluable=len(pairs),panel_size=len(panel) if wt_complete else None,rank=None,reference=s in ('WT','P33S')))
        result[engine]=dict(blue=ranks(blue,'score'),retention=ranks(retention,'score'),red=ranks(red,'score'),wt_panel=panel,wt_complete=wt_complete)
    data['rankings']=result
    data['ranking_policy']=dict(version='bcma-paired-confidence-max-retention-v2',blue_overall='0.5 × mean(C across five states) + 0.5 × min(C across five states); all five required',red='Within each engine, freeze the panel of contestants with WT C ≥ 50 after all 23 WT scores exist. Count a provisional escape signal when ipTM and both directional ipSAE each drop by at least max(0.10, 25% of WT value). Rank 100 × signals / fixed panel size only with complete panel coverage. WT and P33S remain unranked references.',interpretation='Uncalibrated confidence-loss heuristic, not established binding or biological escape. No target-integrity or physics confirmation is implied. C ≥ 50 is a provisional eligibility threshold, not a validated binding cutoff.',engine_aggregation='No cross-engine averaging',ties='Competition ranks on scores rounded to six decimals',physics='Confidence now uses maximum directional ipSAE. Combined weights and joint confidence-plus-physics escape criterion are unchanged; pending physics is never imputed.')
    data['ranking_policy']['blue_retention']='Number of states meeting BOTH engine-specific native ipTM and maximum directional ipSAE cutoffs, out of five (including WT and P33S). All five evaluations required for a rank; missing is unknown. Equal counts share ranks; confidence does not break ties.'
    data['ranking_policy']['confidence_revision']='Maximum replaces minimum directional ipSAE for all derived confidence scores. The approved roster is unchanged. The Red WT C ≥ 50 eligibility panel is recomputed with this definition; its three-metric decline rule is unchanged.'
    data['retention_policy']={
        'version':'bcma-control-relative-retention-v1',
        'frozen_snapshot_utc':'2026-10-20T20:06:12.355340+00:00',
        'rule':'Both metrics must meet or exceed their cutoff. Count each of WT, R27P, S30del, P34del and P33S once.',
        'method':'For each metric and engine: floor(100 × 0.90 × min(B5 WT, L10 WT)) / 100. Freeze these cutoffs; do not refit to incoming pairs.',
        'interpretation':'Provisional control-relative confidence screen, not a calibrated binding classifier. No labeled nonbinder set is available here to estimate specificity. The 90% allowance and rounding are policy choices, not an experimentally learned boundary. A failed cutoff is below-screen confidence, not proof of nonbinding. Retention is not the complement of the Red escape rule.',
        'reference_controls':['B5','L10'], 'fraction':.90, 'rounding':'down to two decimals',
        'engines':{e:{'anchors':CONTROL_ANCHORS[e], 'thresholds':thresholds(e),
            'sensitivity_thresholds':{f:thresholds(e,f) for f in ('.85','.90','.95')}} for e in ('fast','boltz')},
        'sensitivity_note':'85%, 90%, and 95% of the same WT-control anchors. Counts use available pairs; unknown pairs stay unknown. This is threshold sensitivity, not a statistical confidence interval.',
    }
    if data.get('physics_summary'):
        data['ranking_policy']['physics']=data['physics_summary']['reason']+' Original 50/50 confidence/physics weights remain unchanged.'
    return data

if __name__=='__main__':
    import sys
    path=Path(sys.argv[1]);data=build(json.loads(path.read_text()));path.write_text(json.dumps(data,indent=2,allow_nan=False)+'\n')
