"""Validate and import the reviewed public bundle without molecular rescoring.
Usage: python3 -B source/import_final.py --bundle PUBLIC_DIR --site SITE_DIR
Requires the existing paired.json for frozen member identities and cutoff policy.
"""
import argparse, json, hashlib, shutil, shlex, math
from pathlib import Path
from paired_ranking import build

RESULT_SHA='efe4d687ec917a9db9dc5bba875a6cda059412d4abcbdb27bc3523ce4aa5d918'
STRUCTURE_SHA='c608daa170d03bbe2ed364ef13e9162b5d71d4aeb37727293cd1de0d36e79391'
ROSTER_SHA='644c2b7947951c3a7e10cd6fe83f68fb502115873b73eba92b52cbe9c165c331'
AA=dict(zip('ALA ARG ASN ASP CYS GLN GLU GLY HIS ILE LEU LYS MET PHE PRO SER THR TRP TYR VAL'.split(),'ARNDCQEGHILKMFPSTWYV'))
def sha(f): return hashlib.sha256(f.read_bytes()).hexdigest()
def geometry(path,member,target):
    text=path.read_text();assert not any(x in text for x in ('/mnt/','/Users/','/private/','/home/'))
    atoms=[];headers=[]
    for line in text.splitlines():
        if path.suffix=='.cif':
            if line.startswith('_atom_site.'):headers.append(line.strip().split('.')[1])
            elif line.startswith(('ATOM ','HETATM ')):
                fields=shlex.split(line);assert len(fields)==len(headers);a=dict(zip(headers,fields))
                atoms.append((a['label_asym_id'],int(a['label_seq_id']),a['label_comp_id'],a['label_atom_id'],a['type_symbol'],*[float(a[k]) for k in ('Cartn_x','Cartn_y','Cartn_z')]))
        elif line.startswith(('ATOM  ','HETATM')):
            atoms.append((line[21],int(line[22:26]),line[17:20].strip(),line[12:16].strip(),line[76:78].strip(),float(line[30:38]),float(line[38:46]),float(line[46:54])))
    assert atoms and {a[0] for a in atoms}=={'A','B'}
    assert all(math.isfinite(v) for a in atoms for v in a[5:])
    counts={}
    for role,chain,expected in [('binder','A',member['sequence_sha256']),('target','B',target['sequence_sha256'])]:
        ca=sorted([a for a in atoms if a[0]==chain and a[3]=='CA'],key=lambda a:a[1]);assert len({a[1] for a in ca})==len(ca)
        seq=''.join(AA[a[2]] for a in ca);assert hashlib.sha256(seq.encode()).hexdigest()==expected,(path,role)
        counts[role+'_residues']=len(ca)
    counts.update(atom_count=len(atoms),heavy_atom_count=sum(a[4] not in ('H','D') for a in atoms),disulfide_record_count=sum(l.startswith('SSBOND') for l in text.splitlines()))
    return counts

def main(bundle,site):
    assert sha(bundle/'RESULTS.json')==RESULT_SHA and sha(bundle/'STRUCTURES.json')==STRUCTURE_SHA
    results=json.loads((bundle/'RESULTS.json').read_text());manifest=json.loads((bundle/'STRUCTURES.json').read_text());d=json.loads((site/'paired.json').read_text())
    assert d['roster_sha256']==ROSTER_SHA
    members={m['id']:m for m in d['members']};states={a['id']:a for a in d['antigens']}
    assets={x['asset']['path']:x for x in manifest['assets']};assert len(assets)==373
    assert {str(f.relative_to(bundle)) for f in (bundle/'assets').iterdir()}==set(assets)
    target_dir=site/'final';target_dir.mkdir(exist_ok=True);(target_dir/'assets').mkdir(exist_ok=True)
    # Redact only absolute paths on the two Rosetta energy-table comment markers.
    # Coordinate, bond and energy records remain byte-for-byte unchanged.
    replacements={};public_bytes={};transform=[]
    for rel,a in assets.items():
        src=bundle/rel;assert sha(src)==a['asset']['sha256'] and src.stat().st_size==a['asset']['bytes']
        raw=src.read_bytes();lines=raw.splitlines(keepends=True);out=[];changed=0
        for line in lines:
            if any(x in line for x in (b'/mnt/',b'/Users/',b'/private/',b'/home/')):
                assert line.startswith((b'#BEGIN_POSE_ENERGIES_TABLE ',b'#END_POSE_ENERGIES_TABLE ')),rel
                line=line.split(b' ',1)[0]+b' RELAXED_DISPLAY.pdb'+(b'\n' if line.endswith(b'\n') else b'');changed+=1
            out.append(line)
        cooked=b''.join(out)
        if changed:
            assert changed==2 and a['stage']=='physics_relaxed'
            new_sha=hashlib.sha256(cooked).hexdigest();replacements[a['asset']['sha256']]=new_sha
            transform.append(dict(path=rel,reviewed_source_sha256=a['asset']['sha256'],public_sha256=new_sha,redacted_comment_lines=2))
        public_bytes[rel]=cooked
        (target_dir/rel).write_bytes(cooked)
    assert len(transform)==123
    def update(obj):
        if isinstance(obj,dict):
            result={k:update(v) for k,v in obj.items()}
            if set(('path','sha256','bytes')).issubset(result) and result['path'] in public_bytes:result['bytes']=len(public_bytes[result['path']])
            return result
        if isinstance(obj,list):return [update(x) for x in obj]
        return replacements.get(obj,obj) if isinstance(obj,str) else obj
    manifest=update(manifest);results=update(results)
    manifest['publication_transform']={'reviewed_manifest_sha256':STRUCTURE_SHA,'operation':'Private absolute paths removed only from two Rosetta energy-table comment markers per relaxed PDB; all other bytes including coordinates, disulfide and energy records unchanged.','assets':transform}
    (target_dir/'STRUCTURES.json').write_text(json.dumps(manifest,indent=2)+'\n')
    results['provenance']['structures_sha256']=sha(target_dir/'STRUCTURES.json')
    results['publication_transform']={'reviewed_results_sha256':RESULT_SHA,'operation':'Relaxed display asset hashes and byte counts updated for comment-only path redaction; all scalar values unchanged.'}
    (target_dir/'RESULTS.json').write_text(json.dumps(results,indent=2)+'\n')
    assets={x['asset']['path']:x for x in manifest['assets']}
    metadata={}
    for rel,a in assets.items():
        assert rel.startswith('assets/') and Path(rel).name==rel.split('/')[1]
        assert a['chain_roles']=={'A':'binder','B':'target'}
        assert a['target_position_to_native_position']==states[a['state_id']]['native_positions']
        assert a['controls_excluded_from_ranking']==members[a['member_id']]['control']
        src=target_dir/rel;assert sha(src)==a['asset']['sha256'] and src.stat().st_size==a['asset']['bytes']
        g=geometry(src,members[a['member_id']],states[a['state_id']])
        metadata[rel]=dict(url='final/'+rel,sha256=a['asset']['sha256'],bytes=a['asset']['bytes'],format=src.suffix[1:],binder_chain='A',target_chain='B',**g)
        if src.resolve()!=(target_dir/rel).resolve():shutil.copy2(src,target_dir/rel)
    old={(c['engine'],c['binder'],c['antigen']):c for c in d['cells']};cells=[];seen=set();relaxed=0;failed=[]
    for row in results['rows']:
        key=(row['engine'],row['member_id'],row['state_id']);assert key not in seen;seen.add(key)
        e,b,s=key;assert e in ('fast','boltz') and b in members and s in states
        a=row['original'];assert a==assets[a['asset']['path']]
        assert (a['engine'],a['member_id'],a['state_id'],a['stage'])==(*key,'original')
        assert a['scored_coordinate_sha256']==a['asset']['sha256']
        metrics={('iptm' if k=='native_iptm' else 'ptm' if k=='native_ptm' else k):v['value'] for k,v in row['metrics'].items()}
        assert all(v is not None and math.isfinite(v) and 0<=v<=1 for v in metrics.values())
        assert metrics['ipsae_min']==min(metrics['ipsae_binder_to_target'],metrics['ipsae_target_to_binder'])
        if key in old:
            assert all(old[key][k]==v for k,v in metrics.items()),key
            assert old[key]['structure']['sha256']==a['asset']['sha256'],key
        cell=dict(engine=e,binder=b,antigen=s,status='scored',approved_contestant=not members[b]['control'],**metrics,request_id=a['request_id'],score_sha256=a['score_sha256'],structure=metadata[a['asset']['path']],binder_sequence_sha256=members[b]['sequence_sha256'],target_sequence_sha256=states[s]['sequence_sha256'],physics=None,relaxed_structure=None)
        if key in old and 'source_job' in old[key]:cell['source_job']=old[key]['source_job']
        if e=='fast':assert row['physics'] is None
        else:
            p=row['physics']['scalars'];assert (p['member_id'],p['state_id'])==(b,s);cell['physics']=p
            assert p['target_position_to_native_position']==states[s]['native_positions']
            r=row['physics']['relaxed_display']
            if p['status']=='accepted':
                assert r==assets[r['asset']['path']] and r['original_coordinate_sha256']==a['asset']['sha256']
                assert r['request_id']==a['request_id']==p['request_id']
                assert p['artifact_sha256']['RELAXED_DISPLAY.pdb']==r['asset']['sha256']
                assert p['artifact_sha256']['ORIGINAL_BOLTZ.cif']==a['asset']['sha256']
                assert all(v['value'] is not None for v in p['metrics'].values())
                cell['relaxed_structure']=dict(metadata[r['asset']['path']],coordinate_relationship=r['coordinate_relationship']);relaxed+=1
            else:
                assert r is None and all(v['value'] is None for v in p['metrics'].values()) and p['missing_reason']
                failed.append([b,s])
        cells.append(cell)
    assert len(cells)==250 and len(seen)==250 and relaxed==123 and sorted(failed)==[['BC-202d0f7e9723','R27P'],['BC-202d0f7e9723','WT']]
    assert all((e,b,s) in seen for e in ('fast','boltz') for b in members for s in states)
    for m in d['members']:m['approved_contestant']=not m['control']
    d.update(cells=cells,updated_utc='2026-10-21T07:26:48.301816+00:00',physics_status='Final reviewed dispositions: 123 accepted, 2 failed-null. WT reference incomplete; physics percentiles and combined ranks unavailable.',final_bundle={'results_url':'final/RESULTS.json','results_sha256':sha(target_dir/'RESULTS.json'),'structures_url':'final/STRUCTURES.json','structures_sha256':sha(target_dir/'STRUCTURES.json'),'asset_count':373,'asset_bytes':sum(len(v) for v in public_bytes.values()),'reviewed_source_results_sha256':RESULT_SHA,'reviewed_source_structures_sha256':STRUCTURE_SHA,'comment_paths_sanitized':123},evaluation_provenance={'boltz':{'seed':17,'recycles':3,'steps':200,'samples':1,'msa':'single-sequence'},'common_ipsae_scorer_sha256':'547e05340f1627925f7aa652b93b97393061b811497f8dfeb60f24ed3cff8fde','fast':'The 23 contestant WT rows reuse the original evaluations; remaining exact pairs use their own reviewed Fast outputs.','physics':'Single beta_nov16 Boltz-derived PyRosetta relaxation and interface assessment. Accepted is technical review, not experimental binding.','new_computations_for_site':0},physics_summary={'accepted':123,'failed':2,'controls_accepted':10,'contestants_accepted':113,'wt_contestants_accepted':22,'wt_contestants_required':23,'failed_pairs':failed,'physics_percentiles':None,'combined_ranks':None,'reason':'One required contestant WT physics evaluation failed. The frozen 23-contestant reference cannot be reduced; no partial-cohort percentiles or combined ranks.'})
    build(d);d['ranking_policy']['physics']=d['physics_summary']['reason']+' Original 50/50 confidence/physics weights remain unchanged.'
    (site/'paired.json').write_text(json.dumps(d,indent=2,allow_nan=False)+'\n')
    print(json.dumps({'rows':len(cells),'assets':len(assets),'relaxed':relaxed,'failed':failed,'all_original_metrics_preserved':len(old),'fast_red_panel':len(d['rankings']['fast']['wt_panel']),'boltz_red_panel':len(d['rankings']['boltz']['wt_panel'])}))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--bundle',type=Path,required=True);p.add_argument('--site',type=Path,required=True);a=p.parse_args();main(a.bundle,a.site)
