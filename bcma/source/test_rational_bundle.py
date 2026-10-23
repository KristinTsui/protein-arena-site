"""Regression checks for the frozen partial release; no molecular computations."""
import hashlib
import json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parent.parent
read=lambda p: json.loads((ROOT/p).read_text())

class RationalRelease(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data=read('rational.json');cls.original=read('paired.json')

    def test_original_benchmark_is_exact_frozen_baseline(self):
        self.assertEqual(hashlib.sha256((ROOT/'paired.json').read_bytes()).hexdigest(),'b12827e6ffae3f52f1ecf487083dc8e80d9bf6e89d1f39e4f0b4bd90a47c4a95')
        self.assertEqual(len(self.original['cells']),250)
        self.assertEqual(sum(bool(c.get(k)) for c in self.original['cells'] for k in ['structure','relaxed_structure']),373)

    def test_complete_grid_and_missingness(self):
        cells=self.data['cells']
        self.assertEqual(len(cells),400)
        self.assertEqual(len({(c['engine'],c['binder'],c['antigen']) for c in cells}),400)
        statuses={s:sum(c['status']==s for c in cells) for s in {c['status'] for c in cells}}
        self.assertEqual(statuses,{'scored':200,'pending':139,'technical_common_scoring_unavailable':25,'not_evaluable_missing_Boltz_original':36})
        metrics=['iptm','ptm','ipsae_min','ipsae_binder_to_target','ipsae_target_to_binder']
        self.assertEqual(sum(c[k]==0 for c in cells if c['status']=='scored' and c['antigen']=='Q25A' for k in metrics),9)
        for c in cells:
            if c['status']!='scored':
                for k in metrics+['confidence','ipsae_max','predicted_retained']:
                    self.assertIsNone(c[k])
            if c['status']=='not_evaluable_missing_Boltz_original':
                self.assertEqual(c['physics']['physical_attempts'],0)
            if c['physics']['status']!='accepted':
                self.assertIsNone(c['physics']['metrics'])
                self.assertIsNone(c['relaxed_structure'])
            self.assertEqual(c['biological_surface_integrity'],'UNRESOLVED_EVIDENCE')

    def test_frozen_panels_and_ranks(self):
        for engine in ['fast','boltz']:
            ranks=self.data['rankings'][engine]
            self.assertEqual(ranks['wt_panel'],self.original['rankings'][engine]['wt_panel'])
            self.assertEqual(len(ranks['wt_panel']),12)
            self.assertEqual(len(ranks['blue']),23)
            self.assertTrue(all(r['rank'] is None for r in ranks['blue']+ranks['retention']))
            self.assertEqual(self.data['retention_policy']['engines'][engine],self.original['retention_policy']['engines'][engine])
            for r in ranks['red']:
                if r['id'] in ['Q38A','N42D']:
                    self.assertTrue(r['reference']);self.assertIsNone(r['rank'])
                if r['evaluable']<12:self.assertIsNone(r['score']);self.assertIsNone(r['count'])
        q=next(r for r in self.data['rankings']['fast']['red'] if r['id']=='Q25A')
        self.assertEqual((q['count'],q['panel_size'],q['score']),(1,12,8.333333))

    def test_exact_asset_bytes_and_scope(self):
        assets=[c[k] for c in self.data['cells'] for k in ['structure','relaxed_structure'] if c[k]]
        self.assertEqual(len(assets),308)
        for a in assets:
            raw=(ROOT/a['url']).read_bytes()
            self.assertEqual(len(raw),a['bytes']);self.assertEqual(hashlib.sha256(raw).hexdigest(),a['sha256'])
        published={str(p.relative_to(ROOT)) for folder in ['release_q25a','release_f14a_r4','release_n31d_f14a_r1','release_e12q_n31d_r1','release_y40f_e12q_200_83'] for p in (ROOT/'rational'/folder/'assets').glob('*')}
        self.assertEqual(published,{a['url'] for a in assets})
        for name,sha in {'BUNDLE_MANIFEST.json':'db52f82abfe0ad780f5ee7882ad5ef41dea4949a9e2568632dca0e7fe74cc86a','RESULTS_SCALARS.json':'bb9f136af1811464e1eaaa56eda99f7d786a8a893edfc71de8b1db75ed9d28cf','STRUCTURES.json':'72413f3056f6325ba37b3c482c6157199a29b22e32c0b977b0b6d01bdbb1a4dd'}.items():
            self.assertEqual(hashlib.sha256((ROOT/'rational/release_q25a'/name).read_bytes()).hexdigest(),sha)

    def test_incremental_raw_joins(self):
        raw=read('rational/release_y40f_e12q_200_83/RESULTS_SCALARS.json')
        cells={(c['engine'],c['binder'],c['antigen']):c for c in self.data['cells']}
        for r in raw['rows']:
            c=cells[r['engine'],r['member_id'],r['state_id']]
            self.assertEqual(c['status'],r['status']);self.assertEqual(c['physics'],r['physics'])
            for k,m in r['metrics'].items():self.assertEqual(c[{'native_iptm':'iptm','native_ptm':'ptm'}.get(k,k)],m['value'])
            if r['original']:self.assertEqual(c['structure']['sha256'],r['original']['sha256'])
            if r['physics']['relaxed_structure']:self.assertEqual(c['relaxed_structure']['transformation_proof'],r['physics']['relaxed_structure']['transformation_proof'])
        self.assertEqual(sum(c['physics']['status']=='accepted' for c in cells.values()),83)
        self.assertEqual(sum(c['physics']['status']=='pending' for c in cells.values()),81)
        self.assertEqual(sum(c['physics']['status']=='not_applicable_fast_engine' for c in cells.values()),200)

    def test_redaction_proofs_and_source_metadata(self):
        assets=[c['relaxed_structure'] for c in self.data['cells'] if c['relaxed_structure']]
        self.assertEqual(len(assets),83)
        for a in assets:
            proof=a['transformation_proof'];lines=(ROOT/a['url']).read_bytes().splitlines(keepends=True)
            changed={x['line_number']:x for x in proof['changed_lines']}
            self.assertEqual(len(changed),2)
            for i,x in changed.items():self.assertEqual(hashlib.sha256(lines[i-1]).hexdigest(),x['public_line_sha256'])
            other=b''.join(x for i,x in enumerate(lines,1) if i not in changed)
            self.assertEqual(len(other),proof['unchanged_other_bytes']);self.assertEqual(hashlib.sha256(other).hexdigest(),proof['unchanged_other_sha256'])
            self.assertFalse(proof['coordinate_transformation']);self.assertFalse(proof['energy_table_values_changed'])
            self.assertNotEqual(a['source_sha256'],a['public_sha256']);self.assertGreater(a['source_bytes'],a['bytes'])

    def test_exact_bounded_increment(self):
        from collections import Counter
        previous=read('rational/release_e12q_n31d_r1/RESULTS_SCALARS.json')
        current=read('rational/release_y40f_e12q_200_83/RESULTS_SCALARS.json')
        key=lambda r:(r['engine'],r['member_id'],r['state_id'])
        before={key(r):r for r in previous['rows']};changed=[r for r in current['rows'] if r!=before[key(r)]]
        self.assertEqual(len(changed),75)
        self.assertEqual(Counter((r['engine'],r['state_id']) for r in changed),{('fast','Y40F'):25,('boltz','Y40F'):25,('boltz','E12Q'):25})
        for r in changed:
            old=before[key(r)]
            if r['state_id']=='E12Q':self.assertEqual({k:v for k,v in r.items() if k!='physics'},{k:v for k,v in old.items() if k!='physics'})
            elif r['engine']=='fast':self.assertEqual(r['physics'],old['physics'])

    def test_exact_physics_scope(self):
        from collections import Counter
        accepted=[c for c in self.data['cells'] if c['physics']['status']=='accepted']
        self.assertEqual(Counter(c['antigen'] for c in accepted),{'F14A':25,'N31D':25,'E12Q':25,'Y40F':8})
        self.assertTrue(all(c['engine']=='boltz' for c in accepted))
        for c in self.data['cells']:
            if c['antigen']=='S29T':self.assertEqual(c['status'],'pending');self.assertIsNone(c['structure'])
        red=next(r for r in self.data['rankings']['boltz']['red'] if r['id']=='N31D')
        self.assertEqual((red['count'],red['score'],red['panel_size']),(0,0,12))

    def test_retained_unscored_is_displayable_without_invented_scores(self):
        rows=[c for c in self.data['cells'] if c['status']=='technical_common_scoring_unavailable']
        self.assertEqual(len(rows),25)
        self.assertEqual({c['binder'] for c in rows},{m['id'] for m in self.data['members']})
        for c in rows:
            self.assertEqual((c['engine'],c['antigen'],c['prediction_status'],c['common_scoring_status']),('fast','Y40F','retained','technical_unavailable'))
            self.assertTrue(c['structure']);self.assertEqual(c['structure']['provenance_kind'],'retained_original_unscored')
            for k in ['score_sha256','scored_coordinate_sha256']:self.assertIsNone(c['structure'][k])
            self.assertIsNone(c['score_sha256']);self.assertIsNone(c['score_review_sha256'])
            for k,m in c['metric_provenance'].items():
                self.assertIsNone(m['value'])
                self.assertEqual(m['missing_reason'],'native_not_yet_projected' if k.startswith('native_') else 'technical_common_scoring_unavailable_runtime_verification_timeout')
        red=next(r for r in self.data['rankings']['fast']['red'] if r['id']=='Y40F')
        self.assertEqual((red['evaluable'],red['common_unavailable'],red['pending'],red['failed']),(0,12,0,0))
        for k in ['rank','score','count']:self.assertIsNone(red[k])

if __name__=='__main__':unittest.main()
