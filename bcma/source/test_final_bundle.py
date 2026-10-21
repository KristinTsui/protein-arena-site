import unittest,json,hashlib
from pathlib import Path
from collections import Counter
class FinalBundle(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.root=Path(__file__).parents[1];cls.d=json.loads((cls.root/'paired.json').read_text());cls.rows=json.loads((cls.root/'final/RESULTS.json').read_text())['rows'];cls.man=json.loads((cls.root/'final/STRUCTURES.json').read_text())
 def test_complete_grid_and_membership(self):
  self.assertEqual(len(self.rows),250);self.assertEqual(Counter(c['engine'] for c in self.rows),{'fast':125,'boltz':125})
  self.assertEqual(sum(m['approved_contestant'] for m in self.d['members']),23)
  self.assertEqual(Counter(m['team'] for m in self.d['members'] if m['approved_contestant']),{'bindcraft':8,'rfdiffusion':10,'prompteina':5})
  self.assertTrue(all(m['approved_contestant']!=m['control'] for m in self.d['members']))
 def test_metrics_exact_original_joins(self):
  pairs={(c['engine'],c['binder'],c['antigen']):c for c in self.d['cells']}
  for r in self.rows:
   c=pairs[r['engine'],r['member_id'],r['state_id']]
   for k,v in r['metrics'].items():self.assertEqual(c[{'native_iptm':'iptm','native_ptm':'ptm'}.get(k,k)],v['value'])
   self.assertEqual(c['structure']['sha256'],r['original']['scored_coordinate_sha256'])
   self.assertEqual(c['confidence'],round(50*(c['iptm']+max(c['ipsae_binder_to_target'],c['ipsae_target_to_binder'])),6))
   self.assertEqual(c['physics'],r['physics']['scalars'] if r['physics'] else None)
 def test_failed_nulls_no_partial_percentiles(self):
  failed=[];accepted=0
  for c in self.d['cells']:
   if c['engine']=='fast':self.assertIsNone(c['physics']);self.assertIsNone(c['relaxed_structure']);continue
   p=c['physics']
   if p['status']=='accepted':accepted+=1;self.assertIsNotNone(c['relaxed_structure'])
   else:
    failed.append((c['binder'],c['antigen']));self.assertTrue(p['missing_reason']);self.assertIsNone(c['relaxed_structure']);self.assertTrue(all(v['value'] is None for v in p['metrics'].values()))
  self.assertEqual(accepted,123);self.assertEqual(set(failed),{('BC-202d0f7e9723','WT'),('BC-202d0f7e9723','R27P')})
  self.assertIsNone(self.d['physics_summary']['physics_percentiles']);self.assertIsNone(self.d['physics_summary']['combined_ranks'])
 def test_assets_maps_hashes_and_no_private_paths(self):
  self.assertEqual(len(self.man['assets']),373);states={s['id']:s for s in self.d['antigens']}
  for a in self.man['assets']:
   f=self.root/'final'/a['asset']['path'];b=f.read_bytes();self.assertEqual(hashlib.sha256(b).hexdigest(),a['asset']['sha256']);self.assertEqual(len(b),a['asset']['bytes'])
   self.assertEqual(a['chain_roles'],{'A':'binder','B':'target'});self.assertEqual(a['target_position_to_native_position'],states[a['state_id']]['native_positions'])
   for token in [b'/mnt/',b'/Users/',b'/home/',b'/private/']:self.assertNotIn(token,b)
  self.assertEqual(len(self.man['publication_transform']['assets']),123)
 def test_controls_and_final_ranks(self):
  for e in ['fast','boltz']:
   self.assertEqual(len(self.d['rankings'][e]['blue']),23);self.assertTrue(all(r['rank'] is not None and r['coverage']==5 for r in self.d['rankings'][e]['blue']))
   self.assertTrue(all(r['id'] not in ['B5','L10'] for r in self.d['rankings'][e]['retention']))
   self.assertTrue(all(r['rank'] is None for r in self.d['rankings'][e]['red'] if r['id'] in ['WT','P33S']))
if __name__=='__main__':unittest.main()
