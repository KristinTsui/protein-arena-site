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

F14A_PINS={
 'BUNDLE_MANIFEST.json':'f390c789e77babd1cec57531d2b8548eb4276cef34b3cfcda68289ac5ca0c4cd',
 'RESULTS_SCALARS.json':'a6ce16d0eed592734d7b6dd0dc73b2cf55fab92a7fd055173e19690f7c6392f1',
 'STRUCTURES.json':'4e36f66f8c0f6670fd8be2e25a77889b9ad586251080b39966b41751932cf327',
}
PREVIOUS_RATIONAL_SHA='eaa313b795d33c86ec90627a7a6d11dcdba961a787434489037ef4cf3e218a33'
PHYSICS_MEMBERS={'B5','BC-0fef1d499d46','BC-202d0f7e9723','BC-6c30f596ff4a'}
PHYSICS_UNITS={'diagnostic_complex_total_REU':'Rosetta energy units','interface_dG_REU':'Rosetta energy units','interface_dSASA_angstrom2':'angstrom^2','interface_hbonds':'count','interface_packstat':'dimensionless','interface_residue_count':'count','interface_sc':'dimensionless'}

def increment_f14a(bundle,policy_path,nomination_path,site):
 """Append exact R4 outputs to the pinned Q25A release; no molecular parsing."""
 for n,h in F14A_PINS.items():check(sha(bundle/n)==h,'Unapproved F14A input '+n)
 check(sha(policy_path)==PINS['POLICY_BASELINE.json'],'Frozen policy changed')
 check(sha(nomination_path)==PINS['NOMINATION_METADATA.json'],'Nomination changed')
 policy=json.loads(policy_path.read_text());lit=json.loads((site/'paired.json').read_text())
 check(sha(site/'paired.json')==policy['source']['sha256'],'Literature baseline changed')
 check(sha(site/'rational.json')==PREVIOUS_RATIONAL_SHA,'Expected the pinned previous Q25A release; refuse to overwrite another snapshot')
 prior=json.loads((site/'rational.json').read_text());data=copy.deepcopy(prior)
 check(data['members']==lit['members'] and data['roster_sha256']==ROSTER,'Roster changed')
 check(data['retention_policy']==policy['retention_policy']==lit['retention_policy'],'Retention policy changed')
 check(data['physics_summary']['wt_contestants_required']==23 and data['physics_summary']['wt_contestants_accepted']==22,'Physics reference changed')
 for e in ('fast','boltz'):check(data['rankings'][e]['wt_panel']==policy['frozen_wt_supported_panels'][e]==lit['rankings'][e]['wt_panel'],'WT panel changed')
 olddir=site/'rational/release_q25a';oldmanifest=json.loads((olddir/'BUNDLE_MANIFEST.json').read_text())
 for n in ('BUNDLE_MANIFEST.json','RESULTS_SCALARS.json','STRUCTURES.json'):check(sha(olddir/n)==PINS[n],'Previous Q25A manifest changed')
 old_hashes={str(f.relative_to(site)):sha(f) for f in olddir.rglob('*') if f.is_file()}
 for rel,meta in oldmanifest['files'].items():check(sha(olddir/rel)==meta['sha256'] and (olddir/rel).stat().st_size==meta['bytes'],'Previous Q25A file changed')
 raw=json.loads((bundle/'RESULTS_SCALARS.json').read_text());manifest=json.loads((bundle/'BUNDLE_MANIFEST.json').read_text());structures=json.loads((bundle/'STRUCTURES.json').read_text())
 allowed=set(manifest['files'])|{'BUNDLE_MANIFEST.json'}
 check(not any(f.is_symlink() for f in bundle.rglob('*')),'Symlink in bundle')
 check({str(f.relative_to(bundle)) for f in bundle.rglob('*') if f.is_file()}==allowed,'Bundle file allowlist mismatch')
 for rel,meta in manifest['files'].items():
  f=bundle/safe_path(rel);check(sha(f)==meta['sha256'] and f.stat().st_size==meta['bytes'],'Bundle hash/size mismatch');privacy(f.read_bytes())
 check(manifest['base_q25a_bundle_manifest_sha256']==PINS['BUNDLE_MANIFEST.json'],'Wrong previous release')
 check(len(raw['rows'])==400 and Counter(r['status'] for r in raw['rows'])=={'scored':75,FAILED:25,'pending':300},'Wrong status grid')
 check(Counter(r['physics']['status'] for r in raw['rows'])=={'accepted':4,'not_applicable_fast_engine':200,FAILED:25,'pending':171},'Wrong physics coverage')
 assets={a['asset']['path']:a for a in structures['assets']}
 check(len(assets)==54 and set(assets)=={p for p in allowed if p.startswith('assets/')},'Wrong incremental asset allowlist')
 check(sum(a['asset']['bytes'] for a in assets.values())==5545713,'Wrong incremental byte count')
 previous_raw={(r['engine'],r['member_id'],r['state_id']):r for r in json.loads((olddir/'RESULTS_SCALARS.json').read_text())['rows']}
 current={(c['engine'],c['binder'],c['antigen']):c for c in data['cells']};seen=set();used=set();redactions=0
 base='rational/release_f14a_r4/'
 def normalize_asset(a,r,stage):
  nonlocal redactions
  rel=a['path'];check(rel in assets and rel not in used,'Missing or reused incremental asset');used.add(rel);m=assets[rel];meta=m['asset']
  check((m['engine'],m['member_id'],m['state_id'],m['request_id'],m['stage'])==(r['engine'],r['member_id'],r['state_id'],r['request_id'],stage),'Asset identity join mismatch')
  for k in ('team_id','role','red_role','controls_excluded_from_ranking','contrasts_excluded_from_adversarial_ranking','chain_roles','target_position_to_native_position'):check(m[k]==r[k],'Asset role/map mismatch '+k)
  check(a['availability']=='verified_local_asset','Unverified asset')
  for k in ('sha256','public_sha256','source_sha256','bytes','transformation'):check(a[k]==meta[k],'Asset metadata mismatch '+k)
  check(a['sha256']==a['public_sha256'],'Public hash mismatch')
  if stage=='original':
   check(a['sha256']==a['source_sha256']==a['scored_coordinate_sha256']==m['scored_coordinate_sha256'],'Original coordinate hash mismatch')
   check(a['bytes']==a['source_bytes'] and a['transformation']=='none','Original bytes transformed')
   check(a['score_sha256']==m['score_sha256'] and m['review_sha256']==r['score_review_sha256'],'Common score/review join mismatch')
  else:
   check(a['source_bytes']==meta['source_bytes'] and a['transformation_proof']==meta['transformation_proof'],'Redaction proof mismatch')
   check(m['original_coordinate_sha256']==r['original']['sha256'],'Relaxed original join mismatch')
   check(m['review_sha256']==r['physics']['scalar_review_sha256'],'Physics review join mismatch')
   check(all(r['physics']['implementation'][k]==v for k,v in m['implementation'].items()),'Physics implementation join mismatch')
   check(a['transformation']=='exact_rosetta_energy_delimiter_path_metadata_redaction','Unapproved PDB change')
   proof=a['transformation_proof'];check(not proof['coordinate_transformation'] and not proof['energy_table_values_changed'],'Scientific byte transformation')
   lines=(bundle/rel).read_bytes().splitlines(keepends=True);changed={x['line_number']:x for x in proof['changed_lines']}
   check(len(changed)==2,'Wrong metadata line count');redactions+=2
   check({x['record_type'] for x in changed.values()}=={'rosetta_energy_table_begin','rosetta_energy_table_end'},'Wrong metadata record types')
   for n,x in changed.items():check(0<n<=len(lines) and hashlib.sha256(lines[n-1]).hexdigest()==x['public_line_sha256'],'Changed-line proof mismatch')
   remainder=b''.join(line for n,line in enumerate(lines,1) if n not in changed)
   check(len(remainder)==proof['unchanged_other_bytes'] and hashlib.sha256(remainder).hexdigest()==proof['unchanged_other_sha256'],'Unchanged-byte proof mismatch')
  wt=next(c for c in lit['cells'] if c['engine']==r['engine'] and c['binder']==r['member_id'] and c['antigen']=='WT')
  result=copy.deepcopy(a);result.update(url=base+rel,format='cif' if stage=='original' else 'pdb',binder_chain='A',target_chain='B',binder_residues=wt['structure']['binder_residues'],target_residues=54)
  if stage=='physics_relaxed':result['result_sha256']=m['result_sha256']
  return result
 for r in raw['rows']:
  key=(r['engine'],r['member_id'],r['state_id']);check(key in current and key not in seen,'Unexpected/duplicate cell');seen.add(key)
  old=previous_raw[key];c=current[key]
  if r['state_id']!='F14A':check(r==old,'Non-F14A row changed');continue
  # Preserve every original role, identity, map, request and biological status.
  for k,v in old.items():
   if k not in {'status','metrics','original','physics'}:check(r.get(k)==v,'Frozen cell field changed '+k)
  check(r['status']=='scored' and c['status']=='pending','Unexpected F14A transition')
  check(set(r['metrics'])==set(old['metrics']),'Metric schema changed')
  metrics={('iptm' if k=='native_iptm' else 'ptm' if k=='native_ptm' else k):v['value'] for k,v in r['metrics'].items()}
  check(all(type(v) in (float,int) and math.isfinite(v) and 0<=v<=1 for v in metrics.values()),'Invalid score')
  check(all(m['missing_reason'] is None and m['unit']=='dimensionless' for m in r['metrics'].values()),'Score units/missingness invalid')
  check(metrics['ipsae_min']==min(metrics['ipsae_binder_to_target'],metrics['ipsae_target_to_binder']),'Minimum ipSAE mismatch')
  imax=max(metrics['ipsae_binder_to_target'],metrics['ipsae_target_to_binder']);C=round(50*(metrics['iptm']+imax),6)
  limits=policy['retention_policy']['engines'][r['engine']]['thresholds'];retained=all(Decimal(str(v))>=Decimal(str(limits[k])) for k,v in [('iptm',metrics['iptm']),('ipsae_max',imax)])
  original=normalize_asset(r['original'],r,'original');physics=copy.deepcopy(r['physics']);relaxed=None
  if r['engine']=='fast':check(physics=={'status':'not_applicable_fast_engine','metrics':None,'relaxed_structure':None},'Fast physics must stay not applicable')
  elif r['member_id'] in PHYSICS_MEMBERS:
   check(physics['status']=='accepted','Missing accepted physics')
   check(set(physics['metrics'])==set(PHYSICS_UNITS),'Physics schema mismatch')
   for k,m in physics['metrics'].items():check(type(m['value']) in (int,float) and math.isfinite(m['value']) and m['missing_reason'] is None and m['unit']==PHYSICS_UNITS[k],'Invalid physics value/unit')
   check(physics['implementation']['name']=='explicit_preserved_disulfides' and physics['implementation']['detect_disulfide_in_separated_pose'] is False,'Qualified implementation mismatch')
   check(physics['chain_roles']['ORIGINAL_BOLTZ.cif']==physics['chain_roles']['RELAXED_DISPLAY.pdb']=={'A':'binder','B':'target'},'Physics display chains mismatch')
   relaxed=normalize_asset(physics['relaxed_structure'],r,'physics_relaxed')
  else:check(physics=={'status':'pending','metrics':None,'relaxed_structure':None},'Unexpected physics result')
  c.update(status='scored',**metrics,ipsae_max=imax,confidence=C,predicted_retained=retained,structure=original,relaxed_structure=relaxed,physics=physics,score_sha256=r['original']['score_sha256'],score_review_sha256=r['score_review_sha256'])
 check(len(seen)==400 and len(used)==54 and redactions==8,'Incomplete grid/assets/redactions')
 check(sum(c['structure'] is not None for c in data['cells'])==75 and sum(c['relaxed_structure'] is not None for c in data['cells'])==4,'Cumulative asset count mismatch')
 data.update(release='f14a-r4-partial-v2',updated_utc='2026-10-22T08:30:20.422943+00:00',counts=copy.deepcopy(raw['counts']))
 data['provenance']['f14a_update']=dict(raw['f14a_delta_provenance'],bundle_manifest_sha256=F14A_PINS['BUNDLE_MANIFEST.json'],scalar_sha256=F14A_PINS['RESULTS_SCALARS.json'],structures_sha256=F14A_PINS['STRUCTURES.json'],handoff_review_sha256='7a37a9aff8768d78668b36ff5477a45330e82fd097ad91ed49db3c209650f64d',requirements_sha256='7db4a23e8b61d3c473c33124591ddf6d41dcb010a3423746f0cbd41c9a564ff8',previous_rational_snapshot_sha256=PREVIOUS_RATIONAL_SHA)
 data['evaluation_provenance']['physics']='Four qualified single-replicate Boltz F14A beta_nov16 results; native disulfides preserved with separated-pose detection disabled. No Fast-derived physics. Pending and missing-original statuses remain distinct. Frozen WT physics reference incomplete; no combined ranks.'
 summary(data,lit,policy)
 payload=(json.dumps(data,indent=2,allow_nan=False)+'\n').encode();privacy(payload)
 destination=site/base;check(not destination.exists(),'Incremental destination already exists')
 for rel in allowed:
  target=destination/safe_path(rel);target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(bundle/rel,target)
 (site/'rational.json').write_bytes(payload)
 for rel,h in old_hashes.items():check(sha(site/rel)==h,'Existing Q25A file changed')
 check(sha(site/'paired.json')==policy['source']['sha256'],'Literature changed')
 print(json.dumps({'rows':400,'new_assets':54,'total_rational_assets':79,'redacted_metadata_lines':redactions,'statuses':dict(Counter(c['status'] for c in data['cells'])),'red':{e:data['rankings'][e]['red'][:2] for e in ('fast','boltz')}}))

N31D_F14A_PINS={
 'BUNDLE_MANIFEST.json':'5c71e5c46e24cd681f555959ac4cd988ca36922de8be164ef805024f3ca3cfde',
 'RESULTS_SCALARS.json':'061c3445b27003b0831fe37b374920a234cd18818ed0442c41ed3cd6d2099bbb',
 'STRUCTURES.json':'75bef158fecf6ea5d63a7286f0fb38f599b80013614c8b9d2238528b01a8dfab',
}
PREVIOUS_F14A_RATIONAL_SHA='b42a43d48c7ccf5d4ed6e955cf29dca42d7c8d40d4dae17ba9cf6ff392778c8d'
def increment_n31d_f14a(bundle,policy_path,nomination_path,site):
 """Append exact N31D/F14A outputs to the pinned F14A release; no molecular parsing."""
 for n,h in N31D_F14A_PINS.items():check(sha(bundle/n)==h,'Unapproved F14A input '+n)
 check(sha(policy_path)==PINS['POLICY_BASELINE.json'],'Frozen policy changed')
 check(sha(nomination_path)==PINS['NOMINATION_METADATA.json'],'Nomination changed')
 policy=json.loads(policy_path.read_text());lit=json.loads((site/'paired.json').read_text())
 check(sha(site/'paired.json')==policy['source']['sha256'],'Literature baseline changed')
 check(sha(site/'rational.json')==PREVIOUS_F14A_RATIONAL_SHA,'Expected the pinned previous F14A release; refuse to overwrite another snapshot')
 prior=json.loads((site/'rational.json').read_text());data=copy.deepcopy(prior)
 check(data['members']==lit['members'] and data['roster_sha256']==ROSTER,'Roster changed')
 check(data['retention_policy']==policy['retention_policy']==lit['retention_policy'],'Retention policy changed')
 check(data['physics_summary']['wt_contestants_required']==23 and data['physics_summary']['wt_contestants_accepted']==22,'Physics reference changed')
 for e in ('fast','boltz'):check(data['rankings'][e]['wt_panel']==policy['frozen_wt_supported_panels'][e]==lit['rankings'][e]['wt_panel'],'WT panel changed')
 old_hashes={}
 for folder,pins in [('release_q25a',PINS),('release_f14a_r4',F14A_PINS)]:
  olddir=site/'rational'/folder;oldmanifest=json.loads((olddir/'BUNDLE_MANIFEST.json').read_text())
  for n in ('BUNDLE_MANIFEST.json','RESULTS_SCALARS.json','STRUCTURES.json'):check(sha(olddir/n)==pins[n],'Previous manifest changed')
  old_hashes.update({str(x.relative_to(site)):sha(x) for x in olddir.rglob('*') if x.is_file()})
  for rel,meta in oldmanifest['files'].items():check(sha(olddir/rel)==meta['sha256'] and (olddir/rel).stat().st_size==meta['bytes'],'Previous asset changed')
 raw=json.loads((bundle/'RESULTS_SCALARS.json').read_text());manifest=json.loads((bundle/'BUNDLE_MANIFEST.json').read_text());structures=json.loads((bundle/'STRUCTURES.json').read_text())
 allowed=set(manifest['files'])|{'BUNDLE_MANIFEST.json'}
 check(not any(f.is_symlink() for f in bundle.rglob('*')),'Symlink in bundle')
 check({str(f.relative_to(bundle)) for f in bundle.rglob('*') if f.is_file()}==allowed,'Bundle file allowlist mismatch')
 for rel,meta in manifest['files'].items():
  f=bundle/safe_path(rel);check(sha(f)==meta['sha256'] and f.stat().st_size==meta['bytes'],'Bundle hash/size mismatch');privacy(f.read_bytes())
 check(raw['n31d_f14a_delta_provenance']['base_sha256']==F14A_PINS['RESULTS_SCALARS.json'],'Wrong previous release')
 check(len(raw['rows'])==400 and Counter(r['status'] for r in raw['rows'])=={'scored':125,FAILED:36,'pending':239},'Wrong status grid')
 check(Counter(r['physics']['status'] for r in raw['rows'])=={'accepted':25,'not_applicable_fast_engine':200,FAILED:36,'pending':139},'Wrong physics coverage')
 assets={a['asset']['path']:a for a in structures['assets']}
 check(len(assets)==71 and set(assets)=={p for p in allowed if p.startswith('assets/')},'Wrong incremental asset allowlist')
 check(sum(a['asset']['bytes'] for a in assets.values())==9178875,'Wrong incremental byte count')
 previous_raw={(r['engine'],r['member_id'],r['state_id']):r for r in json.loads((olddir/'RESULTS_SCALARS.json').read_text())['rows']}
 current={(c['engine'],c['binder'],c['antigen']):c for c in data['cells']};seen=set();used=set();redactions=0
 base='rational/release_n31d_f14a_r1/'
 def normalize_asset(a,r,stage):
  nonlocal redactions
  rel=a['path'];check(rel in assets and rel not in used,'Missing or reused incremental asset');used.add(rel);m=assets[rel];meta=m['asset']
  check((m['engine'],m['member_id'],m['state_id'],m['request_id'],m['stage'])==(r['engine'],r['member_id'],r['state_id'],r['request_id'],stage),'Asset identity join mismatch')
  for k in ('team_id','role','red_role','controls_excluded_from_ranking','contrasts_excluded_from_adversarial_ranking','chain_roles','target_position_to_native_position'):check(m[k]==r[k],'Asset role/map mismatch '+k)
  check(a['availability']=='verified_local_asset','Unverified asset')
  for k in ('sha256','public_sha256','source_sha256','bytes','transformation'):check(a[k]==meta[k],'Asset metadata mismatch '+k)
  check(a['sha256']==a['public_sha256'],'Public hash mismatch')
  if stage=='original':
   check(a['sha256']==a['source_sha256']==a['scored_coordinate_sha256']==m['scored_coordinate_sha256'],'Original coordinate hash mismatch')
   check(a['bytes']==a['source_bytes'] and a['transformation']=='none','Original bytes transformed')
   check(a['score_sha256']==m['score_sha256'] and m['review_sha256']==r['score_review_sha256'],'Common score/review join mismatch')
  else:
   check(a['source_bytes']==meta['source_bytes'] and a['transformation_proof']==meta['transformation_proof'],'Redaction proof mismatch')
   check(m['original_coordinate_sha256']==r['original']['sha256'],'Relaxed original join mismatch')
   check(m['review_sha256']==r['physics']['scalar_review_sha256'],'Physics review join mismatch')
   check(all(r['physics']['implementation'][k]==v for k,v in m['implementation'].items()),'Physics implementation join mismatch')
   check(a['transformation']=='exact_rosetta_energy_delimiter_path_metadata_redaction','Unapproved PDB change')
   proof=a['transformation_proof'];check(not proof['coordinate_transformation'] and not proof['energy_table_values_changed'],'Scientific byte transformation')
   lines=(bundle/rel).read_bytes().splitlines(keepends=True);changed={x['line_number']:x for x in proof['changed_lines']}
   check(len(changed)==2,'Wrong metadata line count');redactions+=2
   check({x['record_type'] for x in changed.values()}=={'rosetta_energy_table_begin','rosetta_energy_table_end'},'Wrong metadata record types')
   for n,x in changed.items():check(0<n<=len(lines) and hashlib.sha256(lines[n-1]).hexdigest()==x['public_line_sha256'],'Changed-line proof mismatch')
   remainder=b''.join(line for n,line in enumerate(lines,1) if n not in changed)
   check(len(remainder)==proof['unchanged_other_bytes'] and hashlib.sha256(remainder).hexdigest()==proof['unchanged_other_sha256'],'Unchanged-byte proof mismatch')
  wt=next(c for c in lit['cells'] if c['engine']==r['engine'] and c['binder']==r['member_id'] and c['antigen']=='WT')
  result=copy.deepcopy(a);result.update(url=base+rel,format='cif' if stage=='original' else 'pdb',binder_chain='A',target_chain='B',binder_residues=wt['structure']['binder_residues'],target_residues=54)
  if stage=='physics_relaxed':result['result_sha256']=m['result_sha256']
  return result
 changes=Counter()
 def validate_physics(physics):
  check(physics['status']=='accepted' and set(physics['metrics'])==set(PHYSICS_UNITS),'Physics coverage/schema mismatch')
  for k,m in physics['metrics'].items():check(type(m['value']) in (int,float) and math.isfinite(m['value']) and m['missing_reason'] is None and m['unit']==PHYSICS_UNITS[k],'Invalid physics value/unit')
  check(physics['implementation']['name']=='explicit_preserved_disulfides' and physics['implementation']['detect_disulfide_in_separated_pose'] is False,'Qualified implementation mismatch')
  check(physics['chain_roles']['ORIGINAL_BOLTZ.cif']==physics['chain_roles']['RELAXED_DISPLAY.pdb']=={'A':'binder','B':'target'},'Physics display mapping changed')
 for r in raw['rows']:
  key=(r['engine'],r['member_id'],r['state_id']);check(key in current and key not in seen,'Unexpected/duplicate cell');seen.add(key)
  old=previous_raw[key];c=current[key]
  if r==old:continue
  if r['state_id']=='N31D':allowed_fields={'metrics','original','score_review_sha256','status'};kind='scores'
  elif r['engine']=='boltz' and r['state_id']=='F14A':allowed_fields={'physics'};kind='physics'
  elif r['engine']=='boltz' and r['state_id']=='Q38A':allowed_fields={'metrics','status','physics','disposition_review_sha256'};kind='nulls'
  else:raise ValueError('Out-of-scope scientific row change')
  check({k:v for k,v in r.items() if k not in allowed_fields}=={k:v for k,v in old.items() if k not in allowed_fields},'Frozen row fields changed')
  changes[kind]+=1
  if kind=='scores':
   check(old['status']=='pending' and r['status']=='scored','Unexpected N31D transition')
   check(set(r['metrics'])==set(old['metrics']),'Score schema changed')
   metrics={('iptm' if k=='native_iptm' else 'ptm' if k=='native_ptm' else k):v['value'] for k,v in r['metrics'].items()}
   check(all(type(v) in (int,float) and math.isfinite(v) and 0<=v<=1 for v in metrics.values()),'Invalid score')
   check(all(m['missing_reason'] is None and m['unit']=='dimensionless' for m in r['metrics'].values()),'Score units/missingness invalid')
   check(metrics['ipsae_min']==min(metrics['ipsae_binder_to_target'],metrics['ipsae_target_to_binder']),'Minimum ipSAE mismatch')
   expected_physics='not_applicable_fast_engine' if r['engine']=='fast' else 'pending'
   check(r['physics']=={'status':expected_physics,'metrics':None,'relaxed_structure':None},'No N31D physics admitted')
   imax=max(metrics['ipsae_binder_to_target'],metrics['ipsae_target_to_binder']);C=round(50*(metrics['iptm']+imax),6)
   limits=policy['retention_policy']['engines'][r['engine']]['thresholds'];retained=all(Decimal(str(v))>=Decimal(str(limits[k])) for k,v in [('iptm',metrics['iptm']),('ipsae_max',imax)])
   original=normalize_asset(r['original'],r,'original')
   c.update(status='scored',**metrics,ipsae_max=imax,confidence=C,predicted_retained=retained,structure=original,score_sha256=r['original']['score_sha256'],score_review_sha256=r['score_review_sha256'])
  elif kind=='physics':
   check(old['physics']['status']=='pending' and r['status']=='scored','Unexpected F14A physics transition')
   validate_physics(r['physics']);relaxed=normalize_asset(r['physics']['relaxed_structure'],r,'physics_relaxed')
   c.update(physics=copy.deepcopy(r['physics']),relaxed_structure=relaxed)
  else:
   check(old['status']=='pending' and r['status']==FAILED and r['original'] is None,'Unexpected Q38A null transition')
   check(set(r['metrics'])==set(old['metrics']) and all(m=={'value':None,'unit':'dimensionless','missing_reason':'upstream_technical_failure_missing_Boltz_original'} for m in r['metrics'].values()),'Null value/reason changed')
   check(r['physics']=={'status':FAILED,'metrics':None,'relaxed_structure':None,'physical_attempts':0},'Missing original cannot create physics attempt')
   check(r['disposition_review_sha256']=='36b152cf3be37d7dbf875685962256d00eb152aca79bae0ccc2dd6bff8284380','Unreviewed null')
   c.update(status=FAILED,physics=copy.deepcopy(r['physics']),disposition_review_sha256=r['disposition_review_sha256'])
 check(changes=={'scores':50,'physics':21,'nulls':11},'Wrong transition counts')
 check(len(seen)==400 and len(used)==71 and redactions==42,'Incomplete grid/assets/redactions')
 check(sum(c['structure'] is not None for c in data['cells'])==125 and sum(c['relaxed_structure'] is not None for c in data['cells'])==25,'Cumulative asset count mismatch')
 data.update(release='n31d-f14a-r1-partial-v3',updated_utc='2026-10-22T11:10:45.898713+00:00',counts=copy.deepcopy(raw['counts']))
 data['provenance']['n31d_f14a_update']=dict(raw['n31d_f14a_delta_provenance'],bundle_manifest_sha256=N31D_F14A_PINS['BUNDLE_MANIFEST.json'],scalar_sha256=N31D_F14A_PINS['RESULTS_SCALARS.json'],structures_sha256=N31D_F14A_PINS['STRUCTURES.json'],handoff_review_sha256='88be78a13c60ba436cc85a365134d0a21a5420ffa445689268ee6c59428bb2ba',requirements_sha256='ed86b2424d201d4536391c43c6d5003c38a5cde9ee336d6ba9bcc244f3f8474b',requirements_review_sha256='6d9fc1334ea4538bbfc7b16e5059df06ea78c0c66b6a8aad3e1905f20255f6f8',previous_rational_snapshot_sha256=PREVIOUS_F14A_RATIONAL_SHA)
 data['evaluation_provenance']['physics']='25 qualified single-replicate Boltz F14A beta_nov16 results; native disulfides preserved with separated-pose detection disabled. No N31D or Fast-derived physics in this snapshot. Pending and missing-original statuses remain distinct. Frozen WT physics reference incomplete; no combined ranks.'
 summary(data,lit,policy)
 payload=(json.dumps(data,indent=2,allow_nan=False)+'\n').encode();privacy(payload)
 destination=site/base;check(not destination.exists(),'Incremental destination already exists')
 for rel in allowed:
  target=destination/safe_path(rel);target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(bundle/rel,target)
 (site/'rational.json').write_bytes(payload)
 for rel,h in old_hashes.items():check(sha(site/rel)==h,'Existing Q25A file changed')
 check(sha(site/'paired.json')==policy['source']['sha256'],'Literature changed')
 print(json.dumps({'rows':400,'new_assets':71,'total_rational_assets':150,'redacted_metadata_lines':redactions,'statuses':dict(Counter(c['status'] for c in data['cells'])),'red':{e:data['rankings'][e]['red'][:3] for e in ('fast','boltz')}}))
if __name__=='__main__':
 p=argparse.ArgumentParser()
 for k in ('bundle','policy','nomination','site'):p.add_argument('--'+k,type=Path,required=True)
 mode=p.add_mutually_exclusive_group()
 mode.add_argument('--incremental-f14a',action='store_true')
 mode.add_argument('--incremental-n31d-f14a',action='store_true')
 a=p.parse_args();(increment_n31d_f14a if a.incremental_n31d_f14a else increment_f14a if a.incremental_f14a else main)(a.bundle,a.policy,a.nomination,a.site)
