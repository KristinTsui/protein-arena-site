"""Import one reviewed partial rational panel; never modify the literature data.
No model, scorer, geometry/exposure analysis, or physics computation is performed.
Usage: --bundle reviewed-public-dir --policy private-baseline-json
       --nomination private-nomination-metadata-json --site site-dir
"""
import argparse, hashlib, json, math, shutil, copy
from pathlib import Path
from collections import Counter
from decimal import Decimal
from paired_ranking import ranks, decline

PINS={
 'BUNDLE_MANIFEST.json':'db52f82abfe0ad780f5ee7882ad5ef41dea4949a9e2568632dca0e7fe74cc86a',
 'RESULTS_SCALARS.json':'bb9f136af1811464e1eaaa56eda99f7d786a8a893edfc71de8b1db75ed9d28cf',
 'STRUCTURES.json':'72413f3056f6325ba37b3c482c6157199a29b22e32c0b977b0b6d01bdbb1a4dd',
 'POLICY_BASELINE.json':'0670c970c1568419a4cc29e5453c50ae53c94654d6ace5a95b096b9b2b48e1dc',
 'NOMINATION_METADATA.json':'175f9ed83916598cbe615cf4b871f797c62fa106b58e95501d8d2856f0130a86',
}
STATES=['Q25A','F14A','N31D','E12Q','Y40F','S29T','Q38A','N42D']
CONTRASTS={'Q38A','N42D'}
ROSTER='644c2b7947951c3a7e10cd6fe83f68fb502115873b73eba92b52cbe9c165c331'
FAILED='not_evaluable_missing_Boltz_original'
def sha(f):return hashlib.sha256(f.read_bytes()).hexdigest()
def check(condition,message):
 if not condition:raise ValueError(message)
def safe_path(rel):
 p=Path(rel);check(not p.is_absolute() and '..' not in p.parts and len(p.parts)<=2,'Unsafe asset path');return p
def privacy(raw):
 check(not any(x in raw for x in (b'/mnt/',b'/Users/',b'/private/',b'/home/',b'/tmp/',b'file://',b'ssh://')),'Private path in public payload')
def summary(d,literature,policy):
 """Same frozen metrics/weights, separate eight-state denominator and WT panel."""
 cells={(c['engine'],c['binder'],c['antigen']):c for c in d['cells']}
 wt={(c['engine'],c['binder']):c for c in literature['cells'] if c['antigen']=='WT'}
 ids=[m['id'] for m in d['members'] if not m['control']];result={}
 for e in ('fast','boltz'):
  threshold=policy['retention_policy']['engines'][e]['thresholds'];panel=policy['frozen_wt_supported_panels'][e]
  blue=[];retention=[];red=[]
  for b in ids:
   cs=[cells[e,b,s] for s in STATES];vals=[c['confidence'] for c in cs if c['status']=='scored'];complete=len(vals)==8
   blue.append(dict(id=b,score=round((sum(vals)/8+min(vals))/2,6) if complete else None,mean=round(sum(vals)/8,6) if complete else None,worst=min(vals) if complete else None,coverage=len(vals),rank=None))
   outcomes={c['antigen']:c['predicted_retained'] for c in cs}
   count=sum(v is True for v in outcomes.values())
   sensitivity={f:sum(c['status']=='scored' and all(Decimal(str(c[k]))>=Decimal(str(v)) for k,v in limits.items()) for c in cs) for f,limits in policy['retention_policy']['engines'][e]['sensitivity_thresholds'].items()}
   retention.append(dict(id=b,score=count if complete else None,count=count,coverage=len(vals),unknown=8-len(vals),states=outcomes,sensitivity=sensitivity,rank=None))
  for s in STATES:
   cs=[cells[e,b,s] for b in panel];scored=[c for c in cs if c['status']=='scored'];complete=len(scored)==len(panel)
   count=sum(decline(wt[e,c['binder']],c) for c in scored)
   red.append(dict(id=s,score=round(100*count/len(panel),6) if complete and s not in CONTRASTS else None,count=count if complete else None,evaluable=len(scored),pending=sum(c['status']=='pending' for c in cs),failed=sum(c['status']==FAILED for c in cs),panel_size=len(panel),rank=None,reference=s in CONTRASTS))
  result[e]=dict(blue=ranks(blue,'score'),retention=ranks(retention,'score'),red=ranks(red,'score'),wt_panel=copy.deepcopy(panel),wt_complete=True)
 d['rankings']=result
 return d

def main(bundle,policy_path,nomination_path,site):
 for n in ('BUNDLE_MANIFEST.json','RESULTS_SCALARS.json','STRUCTURES.json'):check(sha(bundle/n)==PINS[n],n+' differs from reviewed release')
 check(sha(policy_path)==PINS['POLICY_BASELINE.json'],'Policy baseline hash mismatch')
 check(sha(nomination_path)==PINS['NOMINATION_METADATA.json'],'Nomination metadata hash mismatch')
 policy=json.loads(policy_path.read_text());nom=json.loads(nomination_path.read_text());lit_path=site/'paired.json';lit_sha=sha(lit_path);lit=json.loads(lit_path.read_text())
 check(lit_sha==policy['source']['sha256'],'Literature snapshot differs from frozen baseline')
 check(lit['roster_sha256']==nom['roster_sha256']==ROSTER,'Frozen roster mismatch')
 for e in ('fast','boltz'):
  check(lit['rankings'][e]['wt_panel']==policy['frozen_wt_supported_panels'][e] and len(policy['frozen_wt_supported_panels'][e])==12,'WT panel mismatch')
 check(lit['retention_policy']==policy['retention_policy'],'Retention policy changed')
 check(lit['physics_summary']['wt_contestants_required']==23 and lit['physics_summary']['wt_contestants_accepted']==22,'Frozen physics cohort mismatch')
 manifest=json.loads((bundle/'BUNDLE_MANIFEST.json').read_text());raw=json.loads((bundle/'RESULTS_SCALARS.json').read_text());structures=json.loads((bundle/'STRUCTURES.json').read_text())
 allowed=set(manifest['files'])|{'BUNDLE_MANIFEST.json'}
 check({str(f.relative_to(bundle)) for f in bundle.rglob('*') if f.is_file()}==allowed,'Unexpected bundle files')
 for rel,meta in manifest['files'].items():
  path=bundle/safe_path(rel);check(path.is_file() and not path.is_symlink(),'Non-regular asset');check(sha(path)==meta['sha256'] and path.stat().st_size==meta['bytes'],'Bundle checksum/bytes mismatch');privacy(path.read_bytes())
 check(len(raw['rows'])==400 and len(structures['assets'])==25,'Partial release dimensions changed')
 check(Counter(r['status'] for r in raw['rows'])=={'scored':25,FAILED:25,'pending':350},'Partial statuses changed')
 members={m['id']:m for m in lit['members']};states={s['state_id']:s for s in nom['states']};check(set(states)==set(STATES),'Antigen membership mismatch')
 assetmap={a['asset']['path']:a for a in structures['assets']};check(len(assetmap)==25,'Duplicate asset')
 check(set(assetmap)=={p for p in allowed if p.startswith('assets/')},'Asset allowlist mismatch')
 base='rational/release_q25a/';seen=set();used=set();cells=[]
 for r in raw['rows']:
  e,b,s=r['engine'],r['member_id'],r['state_id'];key=(e,b,s)
  check(e in ('fast','boltz') and b in members and s in states and key not in seen,'Invalid/duplicate pair');seen.add(key)
  ctrl=members[b]['control'];contrast=s in CONTRASTS
  check(r['team_id']==members[b]['team'] and r['controls_excluded_from_ranking']==ctrl,'Member role mismatch')
  check(r['contrasts_excluded_from_adversarial_ranking']==contrast and r['red_role']==('antigen_contrast_control' if contrast else 'rational_challenge'),'Contrast role mismatch')
  check(r['role']==('experimental_binding_control_not_nominee' if ctrl else 'contestant'),'Row role mismatch')
  check(r['chain_roles']=={'A':'binder','B':'target'},'Chain roles mismatch')
  check(r['target_position_to_native_position']==states[s]['sequence_position_to_native_position']==list(range(1,55)),'Native map mismatch')
  check(r['binder_sequence_sha256']==members[b]['sequence_sha256'] and r['target_sequence_sha256']==states[s]['sequence_sha256'],'Sequence identity hash mismatch')
  check(r['biological_surface_integrity']=='UNRESOLVED_EVIDENCE' and r['scientific_acceptance'] is None,'Unexpected biological claim')
  metrics={('iptm' if k=='native_iptm' else 'ptm' if k=='native_ptm' else k):v['value'] for k,v in r['metrics'].items()}
  check(set(metrics)=={'iptm','ptm','ipsae_min','ipsae_binder_to_target','ipsae_target_to_binder'},'Metric schema mismatch')
  p=r['physics'];check(p['metrics'] is None and p['relaxed_structure'] is None,'No rational physics metrics or relaxed assets admitted')
  if e=='fast':check(p['status']=='not_applicable_fast_engine','Fast physics must be not applicable')
  elif r['status']==FAILED:check(p['status']==FAILED and p['physical_attempts']==0,'Failed original cannot create physics attempt')
  else:check(p['status']=='pending','Boltz pending physics must stay pending')
  structure=None;C=None;imax=None;retained=None
  if r['status']=='scored':
   check(e=='fast' and s=='Q25A','Only Fast Q25A scored in this release')
   check(all(type(v) in (float,int) and math.isfinite(v) and 0<=v<=1 for v in metrics.values()),'Invalid valid metric')
   check(all(v['missing_reason'] is None for v in r['metrics'].values()),'Scored value has missing reason')
   check(metrics['ipsae_min']==min(metrics['ipsae_binder_to_target'],metrics['ipsae_target_to_binder']),'Minimum ipSAE mismatch')
   a=r['original'];check(a and a['availability']=='verified_local_asset','Original not verified');rel=a['path'];check(rel in assetmap and rel not in used,'Asset missing or reused');used.add(rel);m=assetmap[rel]
   check((m['engine'],m['member_id'],m['state_id'],m['request_id'])==(e,b,s,r['request_id']),'Asset pair/request join mismatch')
   check(a['sha256']==a['scored_coordinate_sha256']==m['asset']['sha256']==m['scored_coordinate_sha256'],'Coordinate hash mismatch')
   check(a['bytes']==m['asset']['bytes'] and a['score_sha256']==m['score_sha256'],'Score or byte join mismatch')
   check(m['chain_roles']==r['chain_roles'] and m['target_position_to_native_position']==r['target_position_to_native_position'],'Asset role/map mismatch')
   check(m['controls_excluded_from_ranking']==ctrl and m['contrasts_excluded_from_adversarial_ranking']==contrast,'Asset exclusions mismatch')
   wt=next(c for c in lit['cells'] if c['engine']==e and c['binder']==b and c['antigen']=='WT')
   # Residue counts come from reviewed metadata; parsing/rendering is left to the browser.
   structure=dict(url=base+rel,sha256=a['sha256'],bytes=a['bytes'],format='cif',binder_chain='A',target_chain='B',binder_residues=wt['structure']['binder_residues'],target_residues=54)
   imax=max(metrics['ipsae_binder_to_target'],metrics['ipsae_target_to_binder']);C=round(50*(metrics['iptm']+imax),6)
   limits=policy['retention_policy']['engines'][e]['thresholds'];retained=all(Decimal(str(v))>=Decimal(str(limits[k])) for k,v in [('iptm',metrics['iptm']),('ipsae_max',imax)])
  else:
   check(r['original'] is None and all(v is None for v in metrics.values()),'Missing result has invented scores or structure')
   expected='pending' if r['status']=='pending' else 'upstream_technical_failure_missing_Boltz_original'
   check(all(v['missing_reason']==expected for v in r['metrics'].values()),'Missing reason mismatch')
   if r['status']==FAILED:check(e=='boltz' and s=='Q25A','Unexpected failed pair')
  cells.append(dict(engine=e,binder=b,antigen=s,status=r['status'],approved_contestant=not ctrl,red_role=r['red_role'],contrast=contrast,**metrics,ipsae_max=imax,confidence=C,predicted_retained=retained,structure=structure,relaxed_structure=None,physics=copy.deepcopy(p),request_id=r['request_id'],protocol_sha256=r['protocol_sha256'],score_sha256=r['original']['score_sha256'] if r['original'] else None,score_review_sha256=r.get('score_review_sha256'),disposition_review_sha256=r.get('disposition_review_sha256'),biological_surface_integrity=r['biological_surface_integrity'],scientific_acceptance=None))
 check(len(seen)==400 and len(used)==25,'Coverage incomplete')
 # Whitelist nomination fields: never copy private manifests/reviews or their paths.
 antigens=[dict(id=s,native_positions=states[s]['sequence_position_to_native_position'],sequence_sha256=states[s]['sequence_sha256'],red_role=states[s]['red_role'],contrast=s in CONTRASTS,mutation=dict(position=states[s]['position'],reference=states[s]['from'],alternate=states[s]['to']),rationale=states[s]['rationale'],uncertainty=states[s]['uncertainty'],evidence_sha256=states[s]['evidence_sha256']) for s in STATES]
 public_policy={k:copy.deepcopy(policy[k]) for k in ('confidence_formula','ranking_policy','retention_policy','physics_status','frozen_wt_supported_panels','extension_reporting')}
 public_policy['source_sha256']=lit_sha;public_policy['private_baseline_sha256']=PINS['POLICY_BASELINE.json']
 data=dict(schema='bcma.arena.rational.partial.v1',cohort=raw['cohort'],release='fast-q25a-partial-v1',partial=True,updated_utc='2026-10-21T21:41:53.968882+00:00',members=copy.deepcopy(lit['members']),antigens=antigens,cells=cells,counts=copy.deepcopy(raw['counts']),roster_sha256=ROSTER,confidence_formula=policy['confidence_formula'],retention_policy=copy.deepcopy(policy['retention_policy']),physics_summary=copy.deepcopy(lit['physics_summary']),ranking_policy=dict(version='rational-partial-frozen-policy-v1',blue_overall='Same 0.5 mean + 0.5 worst confidence weights across this separate eight-state cohort; all eight required.',blue_retention='Count qualifying states out of eight, including two labelled contrast controls. All eight evaluations required for an overall rank. Original literature denominator remains five.',red='Use the exact frozen engine-specific 12-member WT panel, comparing all three raw metrics to their original WT. Complete fixed-panel coverage required per antigen. Contrasts excluded from competitive ranks.',physics=policy['ranking_policy']['physics'],ties=policy['ranking_policy']['ties']),frozen_policy=public_policy,nomination=dict(information_boundary='Anonymous, unweighted target-epitope membership plus permitted target chemistry, reference exposure and history. No Blue identities, arms, lineages, confidence, outcomes, scores or contact-frequency weighting were available to the isolated nominator. Full-roster reporting occurs downstream of nomination.',biological_surface_integrity='UNRESOLVED_EVIDENCE',recommendation_sha256='0bb4fa1c64e8fc6908104f8864c49e5c460c4aba522df8c948615ab1c9a3651e',recommendation_review_sha256='ca8b9dd897c344df9528bb24a367f01ed28fe51c365e7c672f8a028bc20ef672',admitted_metadata_sha256=PINS['NOMINATION_METADATA.json'],admission_review_sha256='55d12c53a08b9295c0a79912e1b68fc71a6a152a2663b328db68c621a1b4f478',protected_native_cysteines=[8,21,24,28,37,41]),provenance=dict(raw['provenance'],local_handoff_review_sha256='baf7ee40c170bfdbbf42ce04626180cedc26fd852a52b44078e8acc7afde8828',bundle_manifest_sha256=PINS['BUNDLE_MANIFEST.json'],scalar_sha256=PINS['RESULTS_SCALARS.json'],structures_sha256=PINS['STRUCTURES.json'],literature_snapshot_sha256=lit_sha),evaluation_provenance=dict(boltz=lit['evaluation_provenance']['boltz'],fast=dict(seed=17,samples=1,loops=10,steps=68,lm_dropout=.3,msa_column_mask_rate=.1,msa_maxdepth=2048,msa='single-sequence',software='frozen reviewed checkpoint/software'),common_ipsae_scorer_sha256=lit['evaluation_provenance']['common_ipsae_scorer_sha256'],physics='No Fast-derived physics. Boltz pending versus missing-original not-evaluable statuses remain distinct; no rational physics results in this release.',new_scientific_computations=0))
 summary(data,lit,policy)
 payload=(json.dumps(data,indent=2,allow_nan=False)+'\n').encode();privacy(payload)
 destination=site/base;destination.mkdir(parents=True,exist_ok=True)
 for rel in allowed:
  target=destination/safe_path(rel);target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(bundle/rel,target)
 (site/'rational.json').write_bytes(payload)
 (site/'rational/FROZEN_POLICY.json').write_text(json.dumps(public_policy,indent=2)+'\n')
 check(sha(lit_path)==lit_sha,'Literature snapshot modified')
 print(json.dumps({'rows':400,'assets':25,'bytes':2284963,'statuses':dict(Counter(c['status'] for c in cells)),'red_fast_Q25A':data['rankings']['fast']['red'][0],'literature_unchanged':lit_sha}))
if __name__=='__main__':
 p=argparse.ArgumentParser()
 for k in ('bundle','policy','nomination','site'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();main(a.bundle,a.policy,a.nomination,a.site)
