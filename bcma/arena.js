(() => {
  'use strict';
  const $ = s => document.querySelector(s), esc = s => String(s ?? '').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const fmt=(v,n=2)=>Number.isFinite(v)?v.toFixed(n):'—';
  const names={fast:'ESMFold2-Fast',boltz:'Boltz-2'}, arms={bindcraft:'BindCraft',rfdiffusion:'RFdiffusion',prompteina:'Prompteina',controls:'Reference control'};
  let data,engine='fast',scope='overall',blueMode='confidence',metric='confidence',binder,antigen='WT',viewer,model,generation=0,loaded=null;
  const cache=new Map(), cells=new Map();
  const get=(b,s,e=engine)=>cells.get(`${e}|${b}|${s}`);
  function retentionRows(){
    const rows=data.rankings[engine].retention.map(r=>({...r}));
    if(scope!=='overall')rows.forEach(r=>{
      const c=get(r.id,scope),v=r.states[scope];r.count=Number(v===true);r.coverage=c?1:0;r.unknown=c?0:1;r.score=c?r.count:null;r.rank=null;
      r.sensitivity=Object.fromEntries(Object.entries(data.retention_policy.engines[engine].sensitivity_thresholds).map(([f,t])=>[f,Number(!!c&&c.iptm>=t.iptm&&c.ipsae_max>=t.ipsae_max)]));
    });
    rows.sort((a,b)=>(b.score??-Infinity)-(a.score??-Infinity)||a.id.localeCompare(b.id));
    let prev=null,rank=0;rows.forEach((r,i)=>{if(r.score!==null){if(r.score!==prev)rank=i+1;r.rank=rank;prev=r.score;}});return rows;
  }
  function blueRows(){
    if(blueMode==='retention')return retentionRows();
    if(scope==='overall')return data.rankings[engine].blue.map(r=>({...r})).sort((a,b)=>(a.rank??Infinity)-(b.rank??Infinity)||a.id.localeCompare(b.id));
    const rows=data.members.filter(m=>!m.control).map(m=>({id:m.id,score:get(m.id,scope)?.confidence??null,rank:null,coverage:get(m.id,scope)?1:0,iptm:get(m.id,scope)?.iptm}));
    rows.sort((a,b)=>(b.score??-Infinity)-(a.score??-Infinity)||a.id.localeCompare(b.id));let prev=null,rank=0;
    rows.forEach((r,i)=>{if(r.score!==null){if(r.score!==prev)rank=i+1;r.rank=rank;prev=r.score;}});return rows;
  }
  function stateChips(r){return '<span class="retention-states">'+data.antigens.filter(s=>scope==='overall'||s.id===scope).map(s=>{
    const v=r.states[s.id],label=v===null?'unknown':v?'meets screen':'below screen';
    return `<span class="state-chip ${v===null?'unknown':v?'pass':'below'}" title="${esc(s.id)}: ${label}" aria-label="${esc(s.id)}: ${label}">${esc(s.id)} ${v===null?'?':v?'✓':'−'}</span>`;
  }).join('')+'</span>';}
  function chooseTop(){const top=blueRows().find(r=>r.score!==null);binder=top?.id||data.members.find(m=>!m.control).id;antigen=scope==='overall'?'WT':scope;}
  function render(){
    const scored=data.cells.filter(c=>c.engine===engine).length;
    $('#arena-coverage').textContent=`${scored} / 125 pair scores · ${data.rankings[engine].blue.filter(r=>r.rank!==null).length} / 23 complete contestants`;
    $('#arena-snapshot').textContent=`Snapshot: ${new Date(data.updated_utc).toLocaleString()} · Physics results pending scientific review · Engines are evaluated separately.`;
    document.querySelectorAll('[data-engine]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.engine===engine)));
    const rows=blueRows(),retention=blueMode==='retention',denominator=scope==='overall'?5:1;
    document.querySelectorAll('[data-blue-mode]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.blueMode===blueMode)));
    $('#arena-blue-heading').textContent=retention?(scope==='overall'?'How many states meet the screen?':`Predicted retention against ${scope}`):(scope==='overall'?'Strength across the antigen panel':`Performance against ${scope}`);
    const t=data.retention_policy.engines[engine].thresholds;
    $('#arena-blue-note').textContent=retention?`${names[engine]}: ipTM ≥ ${fmt(t.iptm)} AND max ipSAE ≥ ${fmt(t.ipsae_max)}. Counts are predicted retention, not measured binding. ${scope==='overall'?'All five evaluations required for a rank.':'One selected antigen; ties share ranks.'}`:(scope==='overall'?'½ mean + ½ worst-state confidence. Five of five scores required; incomplete contestants remain unranked.':`Ranked by ${names[engine]} confidence for this antigen. Controls remain separate.`);
    $('#blue-mode-badge').textContent=retention?'Provisional screen':'Confidence only';
    $('#arena-score-heading').textContent=retention?'Retained':'Score /100';
    $('#arena-extra-heading').textContent=retention?'85% / 95% margin':scope==='overall'?'Worst state':'Native ipTM';
    $('#arena-blue-rows').innerHTML=rows.map(r=>{const m=data.members.find(m=>m.id===r.id);return `<tr data-binder-row="${esc(r.id)}"><td>${r.rank??'—'}</td><td><button class="binder-link" data-open="${esc(r.id)}">${esc(r.id)}<span class="arena-arm">${esc(arms[m.team])}</span></button>${retention?stateChips(r):''}</td><td class="numeric">${retention?(r.coverage?`${r.count}/${denominator}`:'—')+(r.unknown?`<span class="arena-arm">${r.unknown} unknown</span>`:''):fmt(r.score)}</td><td class="numeric">${retention?(r.coverage?`${r.sensitivity['.85']} / ${r.sensitivity['.95']}`:'—'):fmt(scope==='overall'?r.worst:r.iptm,scope==='overall'?2:3)}</td><td class="numeric">${r.coverage}/${denominator}</td></tr>`;}).join('');
    $('#arena-podium').innerHTML=rows.filter(r=>r.rank!==null).slice(0,3).map(r=>`<button class="podium-card" data-open="${esc(r.id)}"><span class="podium-rank">BLUE · RANK ${r.rank}</span><span class="podium-score">${retention?`${r.count}/${denominator}`:fmt(r.score,1)}</span><strong>${esc(r.id)}</strong><small>${esc(arms[data.members.find(m=>m.id===r.id).team])} / ${esc(names[engine])}</small><p>${retention?'States meeting the provisional screen':scope==='overall'?`Worst state ${fmt(r.worst,1)} · Mean ${fmt(r.mean,1)}`:`${esc(scope)} · Confidence /100`} <span aria-hidden="true">↗</span></p></button>`).join('');
    $('#retention-cutoff').textContent=`Current ${names[engine]} cutoffs: native ipTM ≥ ${fmt(t.iptm)} AND max directional ipSAE ≥ ${fmt(t.ipsae_max)}. Both must pass; a strong value cannot compensate for a weak one.`;
    const anchors=data.retention_policy.engines[engine].anchors;
    $('#retention-rationale').textContent=`Derivation: for each metric, take 90% of the lower B5/L10 WT-control value, then round down to two decimals. The frozen ${names[engine]} anchors are ipTM ${fmt(anchors.iptm,6)} and max ipSAE ${fmt(anchors.ipsae_max,6)}. The 90% allowance is a declared policy choice. Separate cutoffs reflect the engines’ different control score scales; counts are not directly calibrated across engines.`;
    const complete=data.rankings[engine].retention.filter(r=>!r.unknown),st=data.retention_policy.engines[engine].sensitivity_thresholds;
    $('#retention-sensitivity-summary').textContent=`${names[engine]} sensitivity: 85% uses ipTM ≥ ${fmt(st['.85'].iptm)}, max ipSAE ≥ ${fmt(st['.85'].ipsae_max)}; 95% uses ipTM ≥ ${fmt(st['.95'].iptm)}, max ipSAE ≥ ${fmt(st['.95'].ipsae_max)}. Among ${complete.length} complete contestants, ${complete.filter(r=>r.sensitivity['.85']===5).length} / ${complete.filter(r=>r.count===5).length} / ${complete.filter(r=>r.sensitivity['.95']===5).length} meet the screen in all five states at the 85% / 90% / 95% margins.`;
    const red=data.rankings[engine].red.slice().sort((a,b)=>Number(a.reference)-Number(b.reference)||(a.rank??Infinity)-(b.rank??Infinity)||data.antigens.findIndex(s=>s.id===a.id)-data.antigens.findIndex(s=>s.id===b.id));
    $('#arena-red-rows').innerHTML=red.map(r=>`<tr><td>${r.rank??'—'}</td><td>${esc(r.id)}${r.reference?'<span class="arena-arm">'+(r.id==='WT'?'WT baseline':'Control antigen')+'</span>':''}</td><td class="numeric">${r.count===null?'—':`${r.count} / ${r.panel_size}`}</td><td class="numeric">${r.score===null?'—':fmt(r.score,1)+'%'}</td></tr>`).join('');
    const panel=data.rankings[engine];$('#arena-red-note').textContent=panel.wt_complete?`Fixed ${names[engine]} WT panel: ${panel.wt_panel.length} of 23 contestants have C ≥ 50. ${panel.wt_panel.length?'Only complete matched panels can be ranked.':'No contestants qualify; no escape ranks are assigned.'} P33S observations are shown without a competitive rank.`:'Waiting for all 23 contestant WT scores before defining the fixed panel. Partial Boltz coverage cannot produce a Red rank.';
    renderMatrix();
    document.querySelectorAll('#arena [data-open]').forEach(b=>b.onclick=()=>{binder=b.dataset.open;antigen=scope==='overall'?'WT':scope;void selectComplex(true);});
  }
  function renderMatrix(){
    const rows=blueRows().map(r=>data.members.find(m=>m.id===r.id)).concat(data.members.filter(m=>m.control));
    const diverging=metric==='delta';$('.arena-heatmap').classList.toggle('delta-scale',diverging);$('.arena-heatmap').classList.toggle('retention-scale',metric==='retention');
    $('#heatmap-scale').textContent=metric==='retention'?'✓ Meets screen · − Below screen':diverging?'−100 loss · 0 unchanged · +100 gain':metric==='confidence'?'0 low → 100 high':'0 low → 1 high';
    let sep=false;
    $('#pair-matrix-body').innerHTML=rows.map(m=>{
      let out='';if(m.control&&!sep){sep=true;out='<tr class="control-separator"><th colspan="6">REFERENCE CONTROLS · excluded from contestant ranks</th></tr>';}
      out+=`<tr><th scope="row" class="row-label">${esc(m.id)}<span class="arena-arm">${esc(arms[m.team])}</span></th>`;
      out+=data.antigens.map(s=>{
        const c=get(m.id,s.id),wt=get(m.id,'WT');const v=metric==='delta'?(c&&wt?c.confidence-wt.confidence:null):(metric==='retention'?(c?Number(c.predicted_retained):null):(c?.[metric]??null));
        const fraction=v===null?0:Math.min(1,Math.abs(v)/(metric==='confidence'||diverging?100:1));
        const a=[22,36,53],b=diverging&&v<0?[239,126,145]:[88,226,223];const color=a.map((x,i)=>Math.round(x+(b[i]-x)*fraction));
        const label=v===null?'Pending':metric==='retention'?(v?'✓ Pass':'− Below'):fmt(v,metric==='confidence'||diverging?1:3);const detail=`${names[engine]} · ${m.id} × ${s.id} · ${metric==='delta'?'Confidence change':metric}: ${label}`;
        return `<td><button class="pair-cell ${v===null?'pending':''}" data-binder="${esc(m.id)}" data-antigen="${esc(s.id)}" aria-pressed="${binder===m.id&&antigen===s.id}" aria-label="${esc(detail)}" title="${esc(detail)}" style="${v===null?'':`background:rgb(${color.join(',')});color:${fraction>.52?'#09212b':'#edf7fb'}`}" >${label}</button></td>`;
      }).join('')+'</tr>';return out;
    }).join('');
    document.querySelectorAll('.pair-cell').forEach(b=>b.onclick=()=>{binder=b.dataset.binder;antigen=b.dataset.antigen;void selectComplex(true);});
  }
  let surfaceRevision=0,surfaceRows=[],surfaceState='off',mutationMarkers=[],mutationIndices=[];
  function clearSurfaces(){surfaceRevision++;surfaceRows=[];surfaceState='off';viewer?.removeAllSurfaces();}
  function mutationDefinition(){
    const spec={R27P:{kind:'substitution',position:27,expected:'PRO',label:'R27P · Arg27 → Pro'},P33S:{kind:'substitution',position:33,expected:'SER',label:'P33S · Pro33 → Ser'},S30del:{kind:'deletion',position:30,label:'S30 deleted'},P34del:{kind:'deletion',position:34,label:'P34 deleted'}}[antigen];
    if(!spec)return null;
    return {...spec,nativeSites:spec.kind==='deletion'?[spec.position-1,spec.position+1]:[spec.position]};
  }
  function annotateMutation(){
    viewer.removeAllLabels();mutationMarkers=[];mutationIndices=[];$('#mutation-focus').disabled=true;
    for(const atom of model.selectedAtoms({})){atom.properties=atom.properties||{};atom.properties.arenaMutation=0;}
    const spec=mutationDefinition();
    if(!spec){$('#mutation-note').textContent='WT reference: no mutation to highlight.';return;}
    const mapping=data.antigens.find(s=>s.id===antigen).native_positions;
    const ca=model.selectedAtoms({chain:'B',atom:'CA'}).sort((a,b)=>a.resi-b.resi);
    if(ca.length!==mapping.length||new Set(ca.map(a=>a.resi)).size!==mapping.length){$('#mutation-note').textContent='Residue mapping unavailable; mutation highlight withheld.';return;}
    const mapped=new Map(mapping.map((native,i)=>[native,ca[i]]));
    const sites=spec.nativeSites.map(native=>({native,ca:mapped.get(native)}));
    if(sites.some(s=>!s.ca)||(spec.kind==='substitution'&&sites[0].ca.resn!==spec.expected)||(spec.kind==='deletion'&&mapped.has(spec.position))){$('#mutation-note').textContent='Residue identity mismatch; mutation highlight withheld.';return;}
    $('#mutation-note').textContent=spec.kind==='deletion'?`${spec.label}. Gold marks the surviving flanks at native BCMA ${spec.nativeSites.join(' and ')}; the deleted residue has no atoms. Labels use native numbering.`:`${spec.label}. Gold marks the substituted residue at native BCMA position ${spec.position}.`;
    if(!$('#mutation-highlight').checked)return;
    for(const site of sites){
      const atoms=model.selectedAtoms({chain:'B',resi:site.ca.resi}).filter(a=>(a.icode||'')===(site.ca.icode||''));
      const indices=atoms.map(a=>a.index);mutationIndices.push(...indices);
      atoms.forEach(a=>{a.properties.arenaMutation=1;});
      model.setStyle({index:indices},{stick:{color:'#ffd36f',radius:.27}},true);
      model.setStyle({index:[site.ca.index]},{sphere:{color:'#ffd36f',radius:.55}},true);
      mutationMarkers.push({native:site.native,coordinateResidue:site.ca.resi,residue:site.ca.resn,atomCount:atoms.length,position:{x:site.ca.x,y:site.ca.y,z:site.ca.z},kind:spec.kind});
    }
    const position={x:0,y:0,z:0};sites.forEach(s=>{for(const key of ['x','y','z'])position[key]+=s.ca[key]/sites.length;});
    const label=spec.kind==='deletion'?`${spec.label} · flanks ${spec.nativeSites.join(' / ')}`:spec.label;
    viewer.addLabel(label,{position,font:'sans-serif',fontSize:13,fontColor:'#ffd36f',backgroundColor:'#142638',backgroundOpacity:.85,borderColor:'#ffd36f',borderThickness:1,padding:6,inFront:true});
    $('#mutation-focus').disabled=false;
  }
  function setSurfaceOpacity(){
    const opacity=Number($('#surface-opacity').value)/100;$('#surface-opacity-value').textContent=`${Math.round(opacity*100)}%`;
    if(!viewer)return;surfaceRows.forEach(s=>viewer.setSurfaceMaterialStyle(s.id,{opacity,colorscheme:{prop:'arenaMutation',map:{0:s.chain==='A'?'#58e2df':'#ff8490',1:'#ffd36f'}}}));viewer.render();
  }
  async function renderSurfaces(){
    clearSurfaces();const revision=surfaceRevision;
    if(!viewer||!model)return;
    const selections=[{chain:'A',checkbox:'#surface-binder',color:'#58e2df'},{chain:'B',checkbox:'#surface-target',color:'#ff8490'}].filter(s=>$(s.checkbox).checked);
    if(!selections.length){$('#surface-status').textContent='Surfaces off · showing the complete modeled chains.';viewer.render();return;}
    surfaceState='building';$('#surface-status').textContent='Building whole-chain surfaces…';
    try{
      const rows=await Promise.all(selections.map(async s=>{
        const selection={model:model.getID(),chain:s.chain};
        const id=await viewer.addSurface($3Dmol.SurfaceType.VDW,{opacity:Number($('#surface-opacity').value)/100,colorscheme:{prop:'arenaMutation',map:{0:s.color,1:'#ffd36f'}}},selection,selection);
        return {id,chain:s.chain};
      }));
      // Surface IDs are registered synchronously by the pinned viewer. Clearing
      // removes old IDs; stale completions must not touch a newer model's IDs.
      if(revision!==surfaceRevision)return;
      surfaceRows=rows;surfaceState='ready';setSurfaceOpacity();
      $('#surface-status').textContent=`Whole-chain van der Waals surfaces · ${rows.map(s=>s.chain==='A'?'binder':'BCMA extracellular domain').join(' + ')}`;
    }catch(error){if(revision!==surfaceRevision)return;clearSurfaces();surfaceState='error';$('#surface-status').textContent='Surface display unavailable; saved-chain ribbons remain available.';viewer?.render();}
  }
  function applyStyle(rebuildSurfaces=false){
    if(!viewer||!model)return;
    model.setStyle({},{});
    if($('#structure-ribbons').checked){model.setStyle({chain:'A'},{cartoon:{color:'#58e2df'}});model.setStyle({chain:'B'},{cartoon:{color:'#ff8490'}});}
    if($('#structure-sticks').checked){model.setStyle({chain:'A'},{stick:{color:'#58e2df',radius:.12}},true);model.setStyle({chain:'B'},{stick:{color:'#ff8490',radius:.12}},true);}
    annotateMutation();viewer.render();if(rebuildSurfaces)void renderSurfaces();
  }
  async function selectComplex(scroll=false){
    const token=++generation,c=get(binder,antigen);loaded=null;clearSurfaces();mutationMarkers=[];mutationIndices=[];$("#mutation-focus").disabled=true;$("#mutation-note").textContent="Select a scored structure to inspect the mutation.";$("#surface-status").textContent="";$('#complex-binder').value=binder;$('#complex-antigen').value=antigen;renderMatrix();
    $('#complex-title').textContent=`${binder} × BCMA ${antigen}`;$('#complex-subtitle').textContent=`${names[engine]} · Original prediction · Confidence belongs to these coordinates`;
    $('#complex-provenance').textContent=c?`SHA-256: ${c.structure.sha256}\nProducer job: ${c.source_job}\nRequest: ${c.request_id}\n${c.structure.atom_count} atoms · Binder ${c.structure.binder_residues} aa · BCMA ${c.structure.target_residues} aa`:'No scored structure is available for this exact pair and engine.';
    const mapping=data.antigens.find(s=>s.id===antigen).native_positions;const deleted=Array.from({length:54},(_,i)=>i+1).filter(n=>!mapping.includes(n));
    $('#complex-mapping').textContent=`Full modeled extracellular domain: native BCMA 1–54 (${mapping.length} residues in this construct). ${deleted.length?`Native residue ${deleted.join(', ')} is deleted; subsequent coordinate positions shift. `:''}Native BCMA numbering is preserved in the downloadable residue map.`;
    $('#complex-metrics').innerHTML=c?[['Confidence /100',c.confidence,2],['Native ipTM',c.iptm,3],['Maximum ipSAE',c.ipsae_max,3],['Native pTM',c.ptm,3],['ipSAE · binder → target',c.ipsae_binder_to_target,3],['ipSAE · target → binder',c.ipsae_target_to_binder,3]].map(([s,v,n])=>`<div><span>${s}</span><strong>${fmt(v,n)}</strong></div>`).join(''):'<p>Prediction or scoring pending. No replacement coordinates are shown.</p>';
    const link=$('#complex-download');link.hidden=!c;if(c)link.href=c.structure.url;else link.removeAttribute('href');
    if(viewer){viewer.clear();viewer.render();model=null;}
    if(scroll)$('#complex-view').scrollIntoView({behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'instant':'smooth',block:'start'});
    if(!c){$('#structure-status').textContent='Pending: no scored complex for this exact pair and engine.';return;}
    $('#structure-status').textContent='Loading and verifying original coordinates…';
    try {
      let text=cache.get(c.structure.sha256);
      if(!text){const response=await fetch(c.structure.url);if(!response.ok)throw Error('Coordinates unavailable');const bytes=await response.arrayBuffer();const hash=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes))).map(n=>n.toString(16).padStart(2,'0')).join('');if(hash!==c.structure.sha256)throw Error('Coordinate checksum mismatch');text=new TextDecoder().decode(bytes);cache.set(hash,text);}
      if(token!==generation)return;
      if(!window.$3Dmol)throw Error('Viewer library unavailable');
      if(!viewer){viewer=$3Dmol.createViewer($('#structure-canvas'),{backgroundColor:'#0d1c2c',antialias:true});new ResizeObserver(()=>{viewer.resize();viewer.zoomTo();viewer.render();}).observe($('#structure-canvas'));}
      model=viewer.addModel(text,'cif');const atoms=model.selectedAtoms({});if(atoms.length!==c.structure.atom_count)throw Error('Parsed atom count does not match source');
      if(!model.selectedAtoms({chain:'A'}).length||!model.selectedAtoms({chain:'B'}).length)throw Error('Chain mapping mismatch');
      applyStyle(true);viewer.zoomTo();viewer.render();loaded={engine,binder,antigen,sha256:c.structure.sha256,atoms:atoms.length};
      $('#structure-status').textContent=`Original CIF verified · ${atoms.length.toLocaleString()} atoms · ${names[engine]}`;
    } catch(error){if(token!==generation)return;viewer?.clear();viewer?.render();model=null;$('#structure-status').textContent=`Structure display unavailable: ${error.message}. Download the original CIF above.`;}
  }
  async function init(){try{const response=await fetch('paired.json',{cache:'no-store'});if(!response.ok)throw Error('Paired results unavailable');data=await response.json();data.cells.forEach(c=>cells.set(`${c.engine}|${c.binder}|${c.antigen}`,c));
    $('#complex-binder').innerHTML=data.members.map(m=>`<option value="${esc(m.id)}">${esc(m.id)}${m.control?' · control':''}</option>`).join('');$('#complex-antigen').innerHTML=data.antigens.map(s=>`<option>${esc(s.id)}</option>`).join('');
    document.querySelectorAll('[data-engine]').forEach(b=>b.onclick=()=>{engine=b.dataset.engine;chooseTop();render();void selectComplex();});
    document.querySelectorAll('[data-blue-mode]').forEach(b=>b.onclick=()=>{blueMode=b.dataset.blueMode;chooseTop();render();void selectComplex();});
    $('#arena-scope').onchange=e=>{scope=e.target.value;chooseTop();render();void selectComplex();};$('#heatmap-metric').onchange=e=>{metric=e.target.value;renderMatrix();};
    $('#complex-binder').onchange=e=>{binder=e.target.value;void selectComplex();};$('#complex-antigen').onchange=e=>{antigen=e.target.value;void selectComplex();};
    $('#structure-reset').onclick=()=>{viewer?.zoomTo();viewer?.render();};$('#structure-sticks').onchange=()=>applyStyle();$('#structure-ribbons').onchange=()=>applyStyle();
    $('#mutation-highlight').onchange=()=>applyStyle(true);
    $('#surface-binder').onchange=()=>void renderSurfaces();$('#surface-target').onchange=()=>void renderSurfaces();$('#surface-opacity').oninput=setSurfaceOpacity;
    $('#mutation-focus').onclick=()=>{if(viewer&&model&&mutationIndices.length){viewer.zoomTo({model:model.getID(),index:mutationIndices});viewer.zoom(.65);viewer.render();}};
    chooseTop();render();await selectComplex();
  }catch(error){$('#arena-error').hidden=false;$('#arena-error').textContent=error.message;}}
  Object.defineProperty(window,'BCMAPairedDiagnostics',{value:(includeSurfaceColors=false)=>({engine,scope,blueMode,loaded,cellCount:cells.size,selected:{binder,antigen},surfaceState,surfaces:surfaceRows.map(s=>({chain:s.chain,id:s.id})),nativeSurfaces:Object.keys(viewer?.surfaces||{}).length,mutationMarkers:structuredClone(mutationMarkers),mutationAtomCount:mutationIndices.length,renderedAtomCount:model?.selectedAtoms({}).length??0,surfaceColors:includeSurfaceColors?surfaceRows.map(s=>({chain:s.chain,colors:[...new Set(Array.from(viewer.getSurface(s.id)||[]).flatMap(part=>Array.from(part.geo.geometryGroups).flatMap(g=>Array.from({length:g.vertices},(_,i)=>[0,1,2].map(k=>Math.round(g.colorArray[3*i+k]*255).toString(16).padStart(2,'0')).join('')))))]})):[]})});
  void init();
})();
