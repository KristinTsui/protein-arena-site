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
        self.assertEqual(statuses,{'scored':25,'pending':350,'not_evaluable_missing_Boltz_original':25})
        metrics=['iptm','ptm','ipsae_min','ipsae_binder_to_target','ipsae_target_to_binder']
        self.assertEqual(sum(c[k]==0 for c in cells if c['status']=='scored' for k in metrics),9)
        for c in cells:
            if c['status']!='scored':
                for k in metrics+['confidence','ipsae_max','predicted_retained','structure']:
                    self.assertIsNone(c[k])
            if c['status']=='not_evaluable_missing_Boltz_original':
                self.assertEqual(c['physics']['physical_attempts'],0)
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
        assets=[c['structure'] for c in self.data['cells'] if c['structure']]
        self.assertEqual(len(assets),25)
        for a in assets:
            raw=(ROOT/a['url']).read_bytes()
            self.assertEqual(len(raw),a['bytes']);self.assertEqual(hashlib.sha256(raw).hexdigest(),a['sha256'])
        published={str(p.relative_to(ROOT)) for p in (ROOT/'rational/release_q25a/assets').glob('*')}
        self.assertEqual(published,{a['url'] for a in assets})
        for name,sha in {'BUNDLE_MANIFEST.json':'db52f82abfe0ad780f5ee7882ad5ef41dea4949a9e2568632dca0e7fe74cc86a','RESULTS_SCALARS.json':'bb9f136af1811464e1eaaa56eda99f7d786a8a893edfc71de8b1db75ed9d28cf','STRUCTURES.json':'72413f3056f6325ba37b3c482c6157199a29b22e32c0b977b0b6d01bdbb1a4dd'}.items():
            self.assertEqual(hashlib.sha256((ROOT/'rational/release_q25a'/name).read_bytes()).hexdigest(),sha)

if __name__=='__main__':unittest.main()
