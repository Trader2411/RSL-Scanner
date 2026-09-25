let DATA=null, selected=null;
const $=id=>document.getElementById(id);
const money=v=>new Intl.NumberFormat('de-AT',{style:'currency',currency:'EUR',maximumFractionDigits:0}).format(v||0);
const pct=v=>v==null?'—':`${v>0?'+':''}${Number(v).toFixed(2)} %`;
const vol=v=>v==null?'—':`${Number(v).toFixed(1)}×`;
const cls=v=>(v||0)>=0?'pos':'neg';
const signalClass=s=>s==='EINSTIEG'?'entry':s==='BEOBACHTEN'?'watch':'no';
const signalIcon=s=>s==='EINSTIEG'?'🟢':s==='BEOBACHTEN'?'🟡':'🔴';
function isStale(){
  if(!DATA?.generated_at)return true;
  const age=(Date.now()-new Date(DATA.generated_at).getTime())/60000;
  return age>90;
}
function displaySignal(raw){return isStale()?'KEIN EINSTIEG':raw}
async function load(){
  $('overallSignal').textContent='LÄDT…';
  const r=await fetch(`data.json?ts=${Date.now()}`,{cache:'no-store'});
  if(!r.ok)throw new Error(`HTTP ${r.status}`);
  DATA=await r.json(); render();
}
function render(){
  const stale=isStale();
  const raw=DATA?.market?.overall_signal||'KEIN EINSTIEG';
  const overall=displaySignal(raw);
  $('overallSignal').textContent=overall;
  $('signalDot').className=`dot ${signalClass(overall)}`;
  $('phase').innerHTML=`${DATA?.market?.phase||'—'}${DATA?.market?.special_scan?` · <span class="special">${DATA.market.special_scan}</span>`:''}`;
  $('updated').textContent=DATA?.generated_at?`Stand: ${new Date(DATA.generated_at).toLocaleString('de-AT',{dateStyle:'short',timeStyle:'short'})}`:'Noch keine Daten';
  $('staleBanner').classList.toggle('hidden',!stale);
  $('coverage').textContent=`${DATA?.coverage?.with_intraday_data||0}/${DATA?.coverage?.universe||0}`;
  renderList('longList',DATA?.candidates?.long||[]);
  renderList('shortList',DATA?.candidates?.short||[]);
  if(!selected){selected=(DATA?.candidates?.long||[])[0]||null}
  renderTargets();
}
function renderList(id,items){
  $(id).innerHTML=items.length?items.map(card).join(''):'<div class="muted">Noch keine verwertbaren Kandidaten.</div>';
  $(id).querySelectorAll('.candidate').forEach(el=>el.onclick=()=>{selected=findCandidate(el.dataset.symbol,el.dataset.direction);document.querySelectorAll('.candidate').forEach(x=>x.classList.remove('selected'));el.classList.add('selected');renderTargets()});
}
function findCandidate(symbol,direction){return [...(DATA?.candidates?.long||[]),...(DATA?.candidates?.short||[])].find(x=>x.symbol===symbol&&x.direction===direction)}
function card(x){
  const shownSignal=isStale()?'KEIN EINSTIEG':x.signal;
  const scls=signalClass(shownSignal);
  const stab=x.stability==null?'—':`${Math.round(x.stability)} %`;
  const move=x.momentum_change||'—';
  return `<article class="candidate ${scls}${selected?.symbol===x.symbol&&selected?.direction===x.direction?' selected':''}" data-symbol="${x.symbol}" data-direction="${x.direction}">
    <div class="candidate-top"><div class="rank-name"><span class="rank">${x.rank}</span><div class="name"><b>${x.name} <span class="muted">${x.symbol}</span></b><small>${x.sector||x.indexes?.join(' · ')||''}</small></div></div><span class="signal-pill ${scls}">${signalIcon(shownSignal)} ${shownSignal}</span></div>
    <div class="kpis">
      <div class="kpi"><span>Tag</span><b class="${cls(x.day_pct)}">${pct(x.day_pct)}</b></div>
      <div class="kpi"><span>1 Std.</span><b class="${cls(x.m1)}">${pct(x.m1)}</b></div>
      <div class="kpi"><span>2 Std.</span><b class="${cls(x.m2)}">${pct(x.m2)}</b></div>
      <div class="kpi"><span>3 Std.</span><b class="${cls(x.m3)}">${pct(x.m3)}</b></div>
      <div class="kpi"><span>Volumen</span><b>${vol(x.volume_ratio)}</b></div>
      <div class="kpi"><span>Stabilität</span><b>${stab}</b></div>
    </div>
    <div class="candidate-bottom"><div class="reason">${x.reason||'—'}</div><div class="momentum-change">Momentum: <b>${move}</b></div></div>
  </article>`
}
function renderTargets(){
  const depot=Math.max(0,Number($('depot').value)||0), allocation=Math.min(100,Math.max(1,Number($('allocation').value)||50));
  localStorage.setItem('momentumRadarDepot',String(depot)); localStorage.setItem('momentumRadarAllocation',String(allocation));
  const fraction=allocation/100, maxUse=depot*fraction, target1=depot*.01, target2=depot*.02;
  $('maxUse').textContent=money(maxUse); $('target1').textContent=money(target1); $('target2').textContent=money(target2);
  $('need1').textContent=`benötigt ${fraction? (1/fraction).toFixed(1):'—'} % Kursbewegung`;
  $('need2').textContent=`benötigt ${fraction? (2/fraction).toFixed(1):'—'} % Kursbewegung`;
  if(!selected){$('progress').textContent='—';$('progressText').textContent='Kandidat antippen';return}
  const dir=selected.direction==='SHORT'?-1:1, movement=dir*(selected.day_pct||0), needed=fraction?1/fraction:Infinity, prog=Math.max(0,Math.min(100,movement/needed*100));
  $('progress').textContent=`${Math.round(prog)} %`;
  $('progressText').textContent=`${selected.symbol}: ${pct(movement)} von ${needed.toFixed(1)} % für 1 % Depotziel`;
}
$('refresh').onclick=()=>load().catch(e=>{$('updated').textContent=`Fehler: ${e.message}`});
['depot','allocation'].forEach(id=>$(id).oninput=renderTargets);
$('depot').value=localStorage.getItem('momentumRadarDepot')||'5000'; $('allocation').value=localStorage.getItem('momentumRadarAllocation')||'50';
load().catch(e=>{$('overallSignal').textContent='KEIN EINSTIEG';$('signalDot').className='dot no';$('updated').textContent=`Fehler: ${e.message}`;$('staleBanner').classList.remove('hidden')});