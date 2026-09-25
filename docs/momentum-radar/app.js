let DATA=null, selected=null, currentUniverse=localStorage.getItem('momentumRadarUniverse')||'S&P 500';
const $=id=>document.getElementById(id);
const money=v=>new Intl.NumberFormat('de-AT',{style:'currency',currency:'EUR',maximumFractionDigits:0}).format(v||0);
const pct=v=>v==null?'—':`${v>0?'+':''}${Number(v).toFixed(2)} %`;
const vol=v=>v==null?'—':`${Number(v).toFixed(1)}×`;
const cls=v=>(v||0)>=0?'pos':'neg';
const signalClass=s=>s==='EINSTIEG'?'entry':s==='BEOBACHTEN'?'watch':'no';
const signalIcon=s=>s==='EINSTIEG'?'🟢':s==='BEOBACHTEN'?'🟡':'🔴';
const preferred=['S&P 500','S&P 400','NASDAQ 100','Dow Jones','DAX','Rohstoffe','Krypto','Emerging Markets'];

function universeData(){
  return DATA?.universes?.[currentUniverse]||{coverage:{universe:0,with_intraday_data:0},overall_signal:'KEIN EINSTIEG',candidates:{long:[],short:[]}};
}
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
  DATA=await r.json();
  const names=Object.keys(DATA?.universes||{});
  if(names.length&&!names.includes(currentUniverse)) currentUniverse=names[0];
  buildUniverseButtons();
  render();
}
function buildUniverseButtons(){
  const box=$('universeButtons'); box.innerHTML='';
  const names=preferred.filter(x=>DATA?.universes?.[x]).concat(Object.keys(DATA?.universes||{}).filter(x=>!preferred.includes(x)));
  names.forEach(n=>{
    const b=document.createElement('button');
    b.textContent=n;
    b.className=n===currentUniverse?'active':'';
    b.onclick=()=>{currentUniverse=n;selected=null;localStorage.setItem('momentumRadarUniverse',n);buildUniverseButtons();render()};
    box.appendChild(b);
  });
}
function render(){
  const u=universeData(), stale=isStale(), overall=displaySignal(u.overall_signal||'KEIN EINSTIEG');
  $('overallSignal').textContent=overall;
  $('signalDot').className=`dot ${signalClass(overall)}`;
  $('phase').innerHTML=`${currentUniverse} · ${DATA?.market?.phase||'—'}${DATA?.market?.special_scan?` · <span class="special">${DATA.market.special_scan}</span>`:''}`;
  $('updated').textContent=DATA?.generated_at?`Stand: ${new Date(DATA.generated_at).toLocaleString('de-AT',{dateStyle:'short',timeStyle:'short'})}`:'Noch keine Daten';
  $('staleBanner').classList.toggle('hidden',!stale);
  $('coverage').textContent=`${u.coverage?.with_intraday_data||0}/${u.coverage?.universe||0}`;
  renderList('longList',u.candidates?.long||[]);
  renderList('shortList',u.candidates?.short||[]);
  if(!selected) selected=(u.candidates?.long||[])[0]||null;
  renderTargets();
}
function renderList(id,items){
  $(id).innerHTML=items.length?items.map(card).join(''):'<div class="muted">Noch keine verwertbaren Kandidaten.</div>';
  $(id).querySelectorAll('.candidate').forEach(el=>el.onclick=()=>{
    selected=findCandidate(el.dataset.symbol,el.dataset.direction);
    document.querySelectorAll('.candidate').forEach(x=>x.classList.remove('selected'));
    el.classList.add('selected');
    renderTargets();
  });
}
function findCandidate(symbol,direction){
  const u=universeData();
  return [...(u.candidates?.long||[]),...(u.candidates?.short||[])].find(x=>x.symbol===symbol&&x.direction===direction);
}
function card(x){
  const shownSignal=isStale()?'KEIN EINSTIEG':x.signal;
  const scls=signalClass(shownSignal);
  const stab=x.stability==null?'—':`${Math.round(x.stability)} %`;
  const move=x.momentum_change||'—';
  return `<article class="candidate ${scls}${selected?.symbol===x.symbol&&selected?.direction===x.direction?' selected':''}" data-symbol="${x.symbol}" data-direction="${x.direction}">
    <div class="candidate-top"><div class="rank-name"><span class="rank">${x.rank}</span><div class="name"><b>${x.name} <span class="muted">${x.symbol}</span></b><small>${x.sector||''}${x.wkn?` · <a class="wkn-link" href="${x.wkn_url||'#'}" target="_blank" rel="noopener">WKN ${x.wkn} ↗</a>`:''}</small></div></div><span class="signal-pill ${scls}">${signalIcon(shownSignal)} ${shownSignal}</span></div>
    <div class="kpis">
      <div class="kpi"><span>Tag</span><b class="${cls(x.day_pct)}">${pct(x.day_pct)}</b></div>
      <div class="kpi"><span>1 Std.</span><b class="${cls(x.m1)}">${pct(x.m1)}</b></div>
      <div class="kpi"><span>2 Std.</span><b class="${cls(x.m2)}">${pct(x.m2)}</b></div>
      <div class="kpi"><span>3 Std.</span><b class="${cls(x.m3)}">${pct(x.m3)}</b></div>
      <div class="kpi"><span>Volumen</span><b>${vol(x.volume_ratio)}</b></div>
      <div class="kpi"><span>Stabilität</span><b>${stab}</b></div>
    </div>
    <div class="candidate-bottom"><div class="reason">${x.reason||'—'}</div><div class="momentum-change">Momentum: <b>${move}</b></div></div>
  </article>`;
}
function renderTargets(){
  const depot=Math.max(0,Number($('depot').value)||0), allocation=Math.min(100,Math.max(1,Number($('allocation').value)||50));
  localStorage.setItem('momentumRadarDepot',String(depot)); localStorage.setItem('momentumRadarAllocation',String(allocation));
  const fraction=allocation/100, maxUse=depot*fraction, target1=depot*.01, target2=depot*.02;
  $('maxUse').textContent=money(maxUse); $('target1').textContent=money(target1); $('target2').textContent=money(target2);
  $('need1').textContent=`benötigt ${fraction?(1/fraction).toFixed(1):'—'} % Kursbewegung`;
  $('need2').textContent=`benötigt ${fraction?(2/fraction).toFixed(1):'—'} % Kursbewegung`;
  if(!selected){$('progress').textContent='—';$('progressText').textContent='Kandidat antippen';return}
  const dir=selected.direction==='SHORT'?-1:1, movement=dir*(selected.day_pct||0), needed=fraction?1/fraction:Infinity, prog=Math.max(0,Math.min(100,movement/needed*100));
  $('progress').textContent=`${Math.round(prog)} %`;
  $('progressText').textContent=`${selected.symbol}: ${pct(movement)} von ${needed.toFixed(1)} % für 1 % Depotziel`;
}
$('refresh').onclick=()=>load().catch(e=>{$('updated').textContent=`Fehler: ${e.message}`});
['depot','allocation'].forEach(id=>$(id).oninput=renderTargets);
$('depot').value=localStorage.getItem('momentumRadarDepot')||'5000';
$('allocation').value=localStorage.getItem('momentumRadarAllocation')||'50';
load().catch(e=>{$('overallSignal').textContent='KEIN EINSTIEG';$('signalDot').className='dot no';$('updated').textContent=`Fehler: ${e.message}`;$('staleBanner').classList.remove('hidden')});