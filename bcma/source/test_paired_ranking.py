import unittest,copy,json,pathlib
from paired_ranking import build,decline,ranks
class Tests(unittest.TestCase):
 def test_decline_boundary(self):
  a=dict(iptm=.4,ipsae_binder_to_target=.4,ipsae_target_to_binder=.4);b=dict.fromkeys(a,.3)
  self.assertTrue(decline(a,b));b['iptm']=.300000001;self.assertFalse(decline(a,b))
 def test_ties(self):
  r=ranks([dict(id='a',v=10,rank=None),dict(id='b',v=10,rank=None),dict(id='c',v=5,rank=None),dict(id='d',v=None,rank=None)],'v')
  self.assertEqual([x['rank'] for x in r],[1,1,3,None])
 def test_snapshot(self):
  p=pathlib.Path(__file__).parents[1]/'paired.json';d=json.loads(p.read_text());fresh=build(copy.deepcopy(d));self.assertEqual(d['rankings'],fresh['rankings'])
  self.assertEqual(len([x for x in d['cells'] if x['engine']=='fast']),125)
  self.assertEqual(len(d['rankings']['fast']['blue']),23)
  self.assertTrue(all(x['rank'] is not None for x in d['rankings']['fast']['blue']))
  self.assertTrue(all(x['id'] not in ('B5','L10') for x in d['rankings']['fast']['blue']))
  for e in d['rankings'].values():
   self.assertTrue(all(x['rank'] is None for x in e['red'] if x['id'] in ('WT','P33S')))
 def test_missing_and_fixed_panel(self):
  p=pathlib.Path(__file__).parents[1]/'paired.json';d=json.loads(p.read_text());target=d['rankings']['fast']['wt_panel'][0]
  d['cells']=[c for c in d['cells'] if (c['engine'],c['binder'],c['antigen'])!=('fast',target,'R27P')];v=build(d)['rankings']['fast']
  self.assertIsNone(next(r for r in v['blue'] if r['id']==target)['rank'])
  self.assertIsNone(next(r for r in v['red'] if r['id']=='R27P')['rank'])
  self.assertIn(target,v['wt_panel'])
  d['cells']=[c for c in d['cells'] if (c['engine'],c['binder'],c['antigen'])!=('fast',target,'WT')];v=build(d)['rankings']['fast'];self.assertFalse(v['wt_complete']);self.assertTrue(all(r['rank'] is None for r in v['red']))
 def test_mean_and_worst(self):
  p=pathlib.Path(__file__).parents[1]/'paired.json';d=json.loads(p.read_text());target=next(m['id'] for m in d['members'] if not m['control'])
  cells=[c for c in d['cells'] if c['engine']=='fast' and c['binder']==target]
  for c,v in zip(cells,[100,100,100,100,0]):c['confidence']=v
  row=next(r for r in build(d)['rankings']['fast']['blue'] if r['id']==target);self.assertEqual(row['score'],40)
if __name__=='__main__':unittest.main()
