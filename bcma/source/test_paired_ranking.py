import unittest,copy,json,pathlib
from paired_ranking import build,decline,ranks,retained,thresholds,CONTROL_ANCHORS
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
  self.assertEqual(len([x for x in d['cells'] if x['engine']=='boltz']),125)
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
  for c,v in zip(cells,[1,1,1,1,0]):
   for k in ('iptm','ipsae_binder_to_target','ipsae_target_to_binder'):c[k]=v
  row=next(r for r in build(d)['rankings']['fast']['blue'] if r['id']==target);self.assertEqual(row['score'],40)
 def test_maximum_direction_and_missing_retention(self):
  p=pathlib.Path(__file__).parents[1]/'paired.json';d=json.loads(p.read_text());target=next(m['id'] for m in d['members'] if not m['control'])
  cells=[c for c in d['cells'] if c['engine']=='fast' and c['binder']==target]
  for i,c in enumerate(cells):c.update(iptm=.8 if i<2 else .59,ipsae_binder_to_target=.05,ipsae_target_to_binder=.7)
  d=build(d);self.assertEqual(cells[0]['confidence'],75)
  r=next(r for r in d['rankings']['fast']['retention'] if r['id']==target)
  self.assertEqual((r['count'],r['coverage'],r['unknown']),(2,5,0));self.assertIsNotNone(r['rank'])
  removed=cells[2];d['cells'].remove(removed);d=build(d)
  r=next(r for r in d['rankings']['fast']['retention'] if r['id']==target)
  self.assertEqual((r['count'],r['coverage'],r['unknown']),(2,4,1));self.assertIsNone(r['rank']);self.assertIsNone(r['states'][removed['antigen']])
 def test_retention_requires_both_metrics_at_exact_boundary(self):
  t=thresholds('fast');self.assertEqual(t,dict(iptm=.6,ipsae_max=.4))
  self.assertEqual(thresholds('boltz'),dict(iptm=.8,ipsae_max=.69))
  self.assertTrue(retained(dict(iptm=.6,ipsae_max=.4),t))
  self.assertFalse(retained(dict(iptm=.599999999,ipsae_max=1),t))
  self.assertFalse(retained(dict(iptm=1,ipsae_max=.399999999),t))
  self.assertIsNone(retained(None,t))
 def test_frozen_anchors_match_wt_controls(self):
  d=json.loads((pathlib.Path(__file__).parents[1]/'paired.json').read_text())
  for e in ('fast','boltz'):
   controls=[c for c in d['cells'] if c['engine']==e and c['binder'] in ('B5','L10') and c['antigen']=='WT']
   self.assertEqual(len(controls),2)
   for key in ('iptm','ipsae_max'):self.assertEqual(CONTROL_ANCHORS[e][key],min(c[key] for c in controls))
 def test_retention_ties_and_sensitivity(self):
  d=build(json.loads((pathlib.Path(__file__).parents[1]/'paired.json').read_text()))
  for engine in ('fast','boltz'):
   rows=d['rankings'][engine]['retention']
   for r in rows:
    self.assertGreaterEqual(r['sensitivity']['.85'],r['count']);self.assertGreaterEqual(r['count'],r['sensitivity']['.95'])
    self.assertEqual(r['unknown']+r['coverage'],5)
    if r['rank'] is not None:
     self.assertEqual(r['rank'],1+sum(x['score'] is not None and x['score']>r['score'] for x in rows))
   for c in d['cells']:
    if c['engine']==engine:self.assertEqual(c['predicted_retained'],retained(c,thresholds(engine)))
if __name__=='__main__':unittest.main()
