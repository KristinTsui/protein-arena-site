"""Post-hoc diagnosis of frozen EGFR predictions; no fitting or threshold selection.
Run with the original evaluator Python. All original inputs are read only.
"""
import os
os.environ.setdefault('MPLCONFIGDIR','/tmp/proteinbase_egfr_matplotlib')
import json, hashlib, math, pathlib, collections, time
import numpy as np
from scipy.stats import rankdata
from sklearn.metrics import roc_auc_score, average_precision_score, roc_curve, precision_recall_curve
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

OUT=pathlib.Path(__file__).resolve().parent; ROOT=OUT.parent
SOURCES=['inputs.json','results.json','protocol.json','outer_splits.json','findings.json']
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
hashes={f:sha(ROOT/f) for f in SOURCES}
inputs=json.loads((ROOT/'inputs.json').read_text()); results=json.loads((ROOT/'results.json').read_text())
rows=inputs['rows']; byid={r['id']:r for r in rows}
assert len(rows)==467 and len(byid)==467
E={e['id']:e for e in results['evaluations']}
M=lambda e,k: next(m for m in E[e]['models'] if m['id']==k)
FEATURES=[
 ('ipsae','ipSAE',1,lambda r:r['features']['esmfold2_ipsae_antigen_fab_grouped']),
 ('iptm','ipTM',1,lambda r:r['features']['esmfold2_iptm_global']),
 ('foldx','FoldX energy',-1,lambda r:r['features']['foldx_interface_energy']),
 ('energy_original','Rosetta energy · original',-1,lambda r:r['original_descriptors']['interface_dG']['value']),
 ('energy_relaxed','Rosetta energy · relaxed',-1,lambda r:r['relaxed_descriptors']['interface_dG']['value']),
 ('sc_original','Shape complementarity · original',1,lambda r:r['original_descriptors']['interface_sc']['value']),
 ('sc_relaxed','Shape complementarity · relaxed',1,lambda r:r['relaxed_descriptors']['interface_sc']['value']),
 ('hbond_original','Interface H-bonds · original',1,lambda r:r['original_descriptors']['interface_hbonds']['value']),
 ('hbond_relaxed','Interface H-bonds · relaxed',1,lambda r:r['relaxed_descriptors']['interface_hbonds']['value']),
 ('binder_length','Binder length (control)',1,lambda r:r['binder_length'])]

def auc(y,s,w=None):
 if len(set(y))<2:return None
 return float(roc_auc_score(y,s,sample_weight=w))
def counts(y,selected):
 y=np.asarray(y,dtype=int); selected=np.asarray(selected,dtype=bool)
 tp=int(sum((y==1)&selected));fp=int(sum((y==0)&selected));fn=int(sum((y==1)&~selected));tn=int(sum((y==0)&~selected))
 return dict(n=len(y),binders=int(sum(y)),selected=tp+fp,tp=tp,fp=fp,tn=tn,fn=fn,recall=tp/(tp+fn),precision=tp/(tp+fp) if tp+fp else None,specificity=tn/(tn+fp))
def describe(x):
 q=np.quantile(x,[0,.25,.5,.75,1]);return dict(zip(['min','q25','median','q75','max'],map(float,q)))
def cluster_auc(y,s,groups,seed=42,B=1000):
 # Cluster bootstrap of fixed score-label pairs, not model refitting.
 unique,inv=np.unique(groups,return_inverse=True);rng=np.random.default_rng(seed)
 order=np.argsort(s,kind='stable');yy=np.asarray(y)[order];ss=np.asarray(s)[order]
 split=np.r_[0,1+np.where(ss[1:]!=ss[:-1])[0]]
 values=[]
 for _ in range(B):
  sampled=rng.integers(0,len(unique),len(unique));multiplicity=np.bincount(sampled,minlength=len(unique));w=multiplicity[inv][order]
  pos=np.add.reduceat(w*yy,split);neg=np.add.reduceat(w*(1-yy),split)
  if pos.sum()==0 or neg.sum()==0:continue
  below=np.cumsum(neg)-neg;values.append(float(np.sum(pos*(below+neg/2))/(pos.sum()*neg.sum())))
 return {'lower':float(np.quantile(values,.025)),'upper':float(np.quantile(values,.975)),'valid_resamples':len(values),'requested_resamples':B,'seed':seed}
D={'scope':'Exploratory diagnosis of frozen predictions. No model training, cutoff optimization, or molecular computation.', 'source_sha256':hashes,'feature_distributions':[], 'cohorts':{},'model_comparisons':[], 'analysis_policy':{'raw_auc':'Higher confidence / lower energy are favorable. Higher H-bond count and length are descriptive orientations, not universal binding rules. Full-cohort AUC is not held-out learned performance.','bootstrap':'1000 family-cluster resamples of fixed rows, seed42. Percentile intervals describe sampling of these families, not training uncertainty.','matched':'Transfer predictions sliced into the exact within-EGFR test folds; both AUC and AP averaged using fold sample counts.','budgets':'Exploratory prespecified 10% and 20% capacity per saved EGFR test fold. Take ceil(fraction*n); include the whole tied-score block at the boundary. Never use labels to choose cutoffs.','provenance':'Original inputs, labels, family assignments and results remain byte-identical.'}}
for antigen in ['egfr','trem2']:
 subset=[r for r in rows if r['antigen']==antigen];y=np.array([r['label'] for r in subset]);g=np.array([r['family_id'] for r in subset]);families=[]
 for fam in sorted(set(g)):
  ys=y[g==fam];families.append({'id':fam,'n':len(ys),'binders':int(sum(ys))})
 families.sort(key=lambda f:(-f['binders'],-f['n'],f['id']))
 D['cohorts'][antigen]={'n':len(y),'binders':int(sum(y)),'nonbinders':int(sum(1-y)),'prevalence':float(np.mean(y)),'families':families,'positive_families':sum(f['binders']>0 for f in families),'panels':sorted(set(r['panel'] for r in subset))}
 size=collections.Counter(g);w=np.array([1/size[f] for f in g])
 for key,label,direction,get in FEATURES:
  x=np.array([get(r) for r in subset]);assert np.all(np.isfinite(x))
  v={'antigen':antigen,'feature':key,'label':label,'direction':direction,'B':describe(x[y==1]),'NB':describe(x[y==0]),'auc':auc(y,x*direction),'family_balanced_auc':auc(y,x*direction,w),'bootstrap':cluster_auc(y,x*direction,g), 'within_largest_positive_families':[]}
  for f in families[:2]:
   mask=g==f['id'];v['within_largest_positive_families'].append({'family_id':f['id'],'n':int(sum(mask)),'binders':int(sum(y[mask])),'auc':auc(y[mask],(x*direction)[mask])})
  D['feature_distributions'].append(v)

for stage in ['original','relaxed']:
 for feature_set in ['A','B','C','D','E','reference4','raw_energy','length_control','area_control']:
  key=f'{stage}_{feature_set}';within=M('within_egfr',key);transfer=M('trem2_to_egfr',key)
  transfer_pred={p['id']:p for p in transfer['folds'][0]['predictions']};folds=[]
  matched={'within':{},'transfer':{}};allpred={'within':[],'transfer':[]};budgets={str(b):{'within':[],'transfer':[]} for b in [.1,.2]}
  for f in within['folds']:
   p=f['predictions'];ids=[a['id'] for a in p];y=np.array([a['label'] for a in p]);s=np.array([a['score'] for a in p]);t=np.array([transfer_pred[i]['score'] for i in ids]);assert all(transfer_pred[i]['label']==byid[i]['label'] for i in ids)
   trgroups={byid[i]['family_id'] for i in f['train_ids']};tegroups={byid[i]['family_id'] for i in ids};assert not trgroups&tegroups
   fold={'fold':f['fold'],'n':len(y),'binders':int(sum(y)),'within':{'auroc':auc(y,s),'ap':float(average_precision_score(y,s))},'transfer':{'auroc':auc(y,t),'ap':float(average_precision_score(y,t))}}
   for typ,scores in [('within',s),('transfer',t)]:
    allpred[typ].extend([{'id':i,'label':int(yy),'score':float(sc),'fold':f['fold']} for i,yy,sc in zip(ids,y,scores)])
    for budget in [.1,.2]:
     k=math.ceil(budget*len(y));cut=sorted(scores,reverse=True)[k-1];sel=scores>=cut
     budgets[str(budget)][typ].extend(zip(map(int,y),map(bool,sel)))
     fold.setdefault('budgets',{}).setdefault(str(budget),{})[typ]=dict(cutoff=float(cut),requested_capacity=k,**counts(y,sel))
   folds.append(fold)
  for typ in ['within','transfer']:
   matched[typ]={metric:sum(f['n']*f[typ][metric] for f in folds)/378 for metric in ['auroc','ap']}
   y=[p['label'] for p in allpred[typ]];s=[p['score'] for p in allpred[typ]]
   matched[typ]['pooled_descriptive_auroc']=auc(y,s)
   if within['kind']=='logistic':matched[typ]['fixed_half']=counts(y,np.array(s)>=.5)
   matched[typ]['budgets']={b:counts([v[0] for v in values[typ]],[v[1] for v in values[typ]]) for b,values in budgets.items()}
  assert abs(matched['within']['auroc']-within['summary']['ranking_weighted']['auroc'])<1e-12
  for m in [within,transfer]:
   for f in m['folds']:
    trainfamilies={byid[i]['family_id'] for i in f['train_ids']};testfamilies={byid[i]['family_id'] for i in f['test_ids']};assert not trainfamilies&testfamilies
  fits=[]
  for name,model in [('within',within),('transfer',transfer)]:
   for f in model['folds']:
    fit=f.get('fit') or {};fit=fit.get('reproduction_fit',fit)
    fits.append({'training':name,'fold':f['fold'],'train_n':f['train_n'],'train_binders':sum(byid[i]['label'] for i in f['train_ids']),'positive_training_families':len({byid[i]['family_id'] for i in f['train_ids'] if byid[i]['label']==1}),'fit':fit,'threshold':f['threshold']})
  D['model_comparisons'].append({'stage':stage,'feature_set':feature_set,'features':within['features'],'folds':folds,'matched':matched,'fits':fits,'within_summary':within['summary'],'transfer_summary':transfer['summary'],'saved_predictions':allpred})

# Figures: raw distributions use every original row; no smoothed density assumptions.
plt.rcParams.update({'figure.facecolor':'#0c1319','axes.facecolor':'#101d26','savefig.facecolor':'#0c1319','text.color':'#e4edf3','axes.labelcolor':'#c8d6e0','xtick.color':'#aabecb','ytick.color':'#aabecb','axes.edgecolor':'#344857','grid.color':'#304552','font.size':10,'svg.fonttype':'none'})
COL={'B':'#42dcc5','NB':'#ff9d85','within':'#91b4ff','transfer':'#ffcc80'}
def save(fig,name):
 fig.savefig(OUT/f'{name}.svg',bbox_inches='tight');fig.savefig(OUT/f'{name}.png',dpi=150,bbox_inches='tight');plt.close(fig)
def ecdf(ax,x,label,color,ls="-"):
 x=np.sort(x);ax.step(x,np.arange(1,len(x)+1)/len(x),where='post',label=label,color=color,lw=2,ls=ls)
fig,axes=plt.subplots(2,3,figsize=(14,8),layout='constrained')
for ax,(key,label,direction,get) in zip(axes.ravel(),[FEATURES[i] for i in [0,1,2,3,4,5]]):
 subset=[r for r in rows if r['antigen']=='egfr']
 for y,l in [(1,'B'),(0,'NB')]:ecdf(ax,[get(r) for r in subset if r['label']==y],f'{l} (n={sum(r["label"]==y for r in subset)})',COL[l])
 v=next(v for v in D['feature_distributions'] if v['antigen']=='egfr' and v['feature']==key)
 ax.set_title(f'{label}\nDirectional AUROC {v["auc"]:.3f}',loc='left');ax.set_ylabel('Fraction of that class');ax.grid(alpha=.3);ax.set_xlabel('Raw score · '+('higher favorable' if direction==1 else 'lower favorable'))
 if 'energy' in key or key=='foldx':ax.set_xscale('symlog',linthresh=10);ax.set_xlabel(ax.get_xlabel()+'\n(symmetric log axis)')
axes[0,0].legend();fig.suptitle('EGFR binders and nonbinders overlap, but scores retain signal',fontsize=16);save(fig,'feature_overlap')

fig,axes=plt.subplots(2,3,figsize=(14,8),layout='constrained')
for row,stage in enumerate(['original','relaxed']):
 v=next(v for v in D['model_comparisons'] if v['stage']==stage and v['feature_set']=='E')
 for name in ['within','transfer']:
  pred=v['saved_predictions'][name];y=np.array([p['label'] for p in pred]);s=np.array([p['score'] for p in pred])
  # Fold-specific curves make the weighting explicit; no mislabeled pooled curve.
  for f in v['folds']:
   pp=[p for p in pred if p['fold']==f['fold']];yy=[p['label'] for p in pp];ss=[p['score'] for p in pp];fpr,tpr,_=roc_curve(yy,ss)
   axes[row,0].plot(fpr,tpr,color=COL[name],alpha=.6,lw=1.5,ls=['-','--',':'][f['fold']-1])
  axes[row,0].plot([],[],color=COL[name],label=f'{name}: weighted AUC {v["matched"][name]["auroc"]:.3f}')
  for cl,l in [(1,'B'),(0,'NB')]:ecdf(axes[row,1],s[y==cl],f'{name} {l}',COL[name],ls='-' if cl else '--')
  xx=[];rr=[]
  for fraction in np.linspace(.01,1,100):
   tt=bb=selected=0
   for f in v['folds']:
    pp=[p for p in pred if p['fold']==f['fold']];yy=np.array([p['label'] for p in pp]);ss=np.array([p['score'] for p in pp]);cut=np.sort(ss)[-math.ceil(fraction*len(ss))];selected+=int(sum(ss>=cut));tt+=int(sum(yy[ss>=cut]));bb+=int(sum(yy))
   xx.append(selected/378);rr.append(tt/bb)
  axes[row,2].plot(xx,rr,color=COL[name],lw=2,label=name)
 axes[row,0].plot([0,1],[0,1],color='#62717d',ls=':');axes[row,0].set(xlabel='False-positive rate',ylabel='True-positive rate',title=stage.title()+' E · same test folds');axes[row,0].legend(fontsize=9)
 axes[row,1].axvline(.5,color='white',lw=1,ls=':');axes[row,1].set(xlabel='Saved predicted probability',ylabel='Fraction of each group',title='Probability scale (pooled diagnostic)');axes[row,1].legend(fontsize=8)
 axes[row,2].plot([0,1],[0,1],color='#62717d',ls=':');axes[row,2].set(xlabel='Fraction of EGFR designs selected',ylabel='Binder recall',title='Recovery at comparable screening capacity');axes[row,2].legend(fontsize=9)
 for ax in axes[row]:ax.grid(alpha=.25)
fig.suptitle('Same five features, same EGFR test designs · no retraining',fontsize=16);save(fig,'matched_prediction_diagnostics')

fig,axes=plt.subplots(1,2,figsize=(13,4.5),layout='constrained')
for ax,antigen in zip(axes,['egfr','trem2']):
 fs=[f for f in D['cohorts'][antigen]['families'] if f['binders']];ax.bar(np.arange(len(fs)),[f['binders'] for f in fs],color=COL['B']);ax.set(xlabel='Binder-containing families, sorted by count',ylabel='Number of experimentally labeled binders',title=f'{antigen.upper()}: {len(fs)} positive families');ax.grid(axis='y',alpha=.3);ax.set_xticks([])
fig.suptitle('EGFR positive evidence is concentrated in two families',fontsize=16);save(fig,'family_support')
assert all(sha(ROOT/f)==h for f,h in hashes.items())
D['verification']={'source_files_unchanged':True,'row_count':len(rows),'models_refit':0,'saved_model_comparisons':len(D['model_comparisons']),'all_recorded_train_test_family_sets_disjoint':True,'all_matched_within_auroc_reproduced':True,'script_sha256':sha(pathlib.Path(__file__))}
(OUT/'diagnostics.json').write_text(json.dumps(D,indent=2,allow_nan=False))
print(json.dumps({'cohorts':{k:{kk:v[kk] for kk in ['n','binders','positive_families']} for k,v in D['cohorts'].items()},'E':[{'stage':v['stage'],'matched':v['matched']} for v in D['model_comparisons'] if v['feature_set']=='E'],'verification':D['verification']},indent=2))
