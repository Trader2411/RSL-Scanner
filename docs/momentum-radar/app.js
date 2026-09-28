let DATA=null, WATCH=null, selected=null, currentUniverse=localStorage.getItem('momentumRadarUniverse')||'S&P 500';
const $=id=>document.getElementById(id);
const money=v=>new Intl.NumberFormat('de-AT',{style:'currency',currency:'EUR',maximumFractionDigits:0}).format(v||0);
const pct=v=>v==null?'—':`${v>0?'+':''}${Number(v).toFixed(2)} %`;
const vol=v=>v==null?'—':`${Number(v).toFixed(1)}×`;
const cls=v=>(v||0)>=0?'pos':'neg';
const signalClass=s=>s==='EINSTIEG'?'entry':s==='BEOBACHTEN'?'watch':'no';
const signalIcon=s=>s==='EINSTIEG'?'🟢':s==='BEOBACHTEN'?'🟡':'🔴';
const preferred=['S&P 500','S&P 400','NASDAQ 100','Dow Jones','DAX','Rohstoffe','Krypto','Emerging Markets'];
function sourceChartUrl(symbol){return `https://finance.yahoo.com/quote/${encodeURIComponent(symbol)}/chart/`;}

function watchFor(x){
  if(!WATCH?.candidates||!x?.symbol||!x?.direction)return null;
  if(WATCH.base_scan_generated_at!==DATA?.generated_at)return null;
  return WATCH.candidates[`${x.symbol}|${x.direction}`]||null;
}
function effectiveSignal(x){
  const w=watchFor(x);
  if(w?.watch_signal)return w.watch_signal;
  return x.signal;
}
function effectiveLatestBar(x){
  return watchFor(x)?.latest_bar||x.latest_bar;
}
function effectiveAgeMin(x){
  const t=effectiveLatestBar(x);
  if(!t)return Infinity;
  const ms=new Date(t).getTime();
  return Number.isFinite(ms)?(Date.now()-ms)/60000:Infinity;
}

function universeData(){
  return DATA?.universes?.[currentUniverse]||{coverage:{universe:0,with_intraday_data:0},overall_signal:'KEIN EINSTIEG',candidates:{long:[],short:[]}};
}
function isStale(){
  if(!DATA?.generated_at)return true;
  const age=(Date.now()-new Date(DATA.generated_at).getTime())/60000;
  return age>90;
}
function isMarketClosed(){
  const usSessionUniverses=['S&P 500','S&P 400','NASDAQ 100','Dow Jones','Emerging Markets'];
  return usSessionUniverses.includes(currentUniverse) && DATA?.market?.phase==='US-Handel beendet';
}
function candidateDataAgeMin(x){
  return effectiveAgeMin(x);
}
function candidateIsStale(x){
  return candidateDataAgeMin(x)>20;
}
function displaySignal(raw){
  if(isMarketClosed()) return 'MARKT GESCHLOSSEN';
  return isStale()?'KEIN EINSTIEG':raw;
}
async function load(){
  $('overallSignal').textContent='LÄDT…';
  const ts=Date.now();
  const [dataResult,watchResult]=await Promise.allSettled([
    fetch(`data.json?ts=${ts}`,{cache:'no-store'}),
    fetch(`watch.json?ts=${ts}`,{cache:'no-store'})
  ]);
  if(dataResult.status!=='fulfilled'||!dataResult.value.ok)throw new Error('Vollscan konnte nicht geladen werden');
  DATA=await dataResult.value.json();
  WATCH=null;
  if(watchResult.status==='fulfilled'&&watchResult.value.ok){
    try{WATCH=await watchResult.value.json()}catch(_){}
  }
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
  const u=universeData(), stale=isStale(), closed=isMarketClosed(), overall=displaySignal(u.overall_signal||'KEIN EINSTIEG');
  $('overallSignal').textContent=overall;
  $('signalDot').className=`dot ${signalClass(overall)}`;
  $('phase').innerHTML=`${currentUniverse} · ${DATA?.market?.phase||'—'}${DATA?.market?.special_scan?` · <span class="special">${DATA.market.special_scan}</span>`:''}`;
  const fmtTime=v=>v?new Date(v).toLocaleTimeString('de-AT',{hour:'2-digit',minute:'2-digit'}):'—';
  const watchValid=WATCH?.base_scan_generated_at===DATA?.generated_at;
  $('updated').textContent=DATA?.generated_at?`Vollscan ${fmtTime(DATA.generated_at)} · Kandidaten ${watchValid?fmtTime(WATCH.generated_at):'wartet'} · geprüft ${fmtTime(new Date().toISOString())}`:'Noch keine Daten';
  $('staleBanner').textContent=closed?'🔴 Markt geschlossen – neue Einstiege gesperrt.':'🔴 Daten sind zu alt – neue Einstiege gesperrt.';
  $('staleBanner').classList.toggle('hidden',!stale&&!closed);
  $('coverage').textContent=`${u.coverage?.with_intraday_data||0}/${u.coverage?.universe||0}`;
  renderList('longList',u.candidates?.long||[]);
  renderList('shortList',u.candidates?.short||[]);
  if(!selected) selected=(u.candidates?.long||[])[0]||null;
  renderTargets();
}
function renderList(id,items){
  $(id).innerHTML=items.length?items.map(card).join(''):'<div class="muted">Noch keine verwertbaren Kandidaten.</div>';
  $(id).querySelectorAll('.candidate').forEach(el=>el.onclick=e=>{
    if(e.target.closest('a,button')) return;
    selected=findCandidate(el.dataset.symbol,el.dataset.direction);
    document.querySelectorAll('.candidate').forEach(x=>x.classList.remove('selected'));
    el.classList.add('selected');
    renderTargets();
  });
  $(id).querySelectorAll('.wkn-link').forEach(a=>a.addEventListener('click',e=>e.stopPropagation()));
}
function findCandidate(symbol,direction){
  const u=universeData();
  return [...(u.candidates?.long||[]),...(u.candidates?.short||[])].find(x=>x.symbol===symbol&&x.direction===direction);
}
function card(x){
  const w=watchFor(x);
  const candidateStale=candidateIsStale(x);
  const shownSignal=candidateStale?'KEIN EINSTIEG':displaySignal(effectiveSignal(x));
  const scls=signalClass(shownSignal);
  const stab=x.stability==null?'—':`${Math.round(x.stability)} %`;
  const move=x.momentum_change||'—';
  const reasonText=candidateStale?`Kursdaten zu alt (${Math.round(candidateDataAgeMin(x))} Min.) – kein neuer Einstieg.`:(w?.reason||x.reason||'—');
  const watchText=w?`Kurzcheck: 15m ${pct(w.ret_15m_pct)} · 30m ${pct(w.ret_30m_pct)} · seit Scan ${pct(w.move_since_scan_pct)}`:'Kurzcheck wartet';
  return `<article class="candidate ${scls}${selected?.symbol===x.symbol&&selected?.direction===x.direction?' selected':''}" data-symbol="${x.symbol}" data-direction="${x.direction}">
    <div class="candidate-top"><div class="rank-name"><span class="rank">${x.rank}</span><div class="name"><b>${x.name} <span class="muted">${x.symbol}</span></b><small>${x.sector||''}${x.wkn?` · <a class="wkn-link" href="${x.wkn_url||'#'}" target="_blank" rel="noopener">WKN ${x.wkn} ↗</a>`:''} · <a class="source-chart-link" href="${sourceChartUrl(x.symbol)}" target="_blank" rel="noopener">Chart Kursquelle ↗</a></small></div></div><span class="signal-pill ${scls}">${signalIcon(shownSignal)} ${shownSignal}</span></div>
    <div class="kpis">
      <div class="kpi"><span>Tag</span><b class="${cls(x.day_pct)}">${pct(x.day_pct)}</b></div>
      <div class="kpi"><span>1 Std.</span><b class="${cls(x.m1)}">${pct(x.m1)}</b></div>
      <div class="kpi"><span>2 Std.</span><b class="${cls(x.m2)}">${pct(x.m2)}</b></div>
      <div class="kpi"><span>3 Std.</span><b class="${cls(x.m3)}">${pct(x.m3)}</b></div>
      <div class="kpi"><span>Volumen</span><b>${vol(x.volume_ratio)}</b></div>
      <div class="kpi"><span>Stabilität</span><b>${stab}</b></div>
    </div>
    <div class="candidate-bottom"><div><div class="reason">${reasonText}</div><div class="watch-line">${watchText}</div></div><div class="momentum-change">Momentum: <b>${move}</b></div></div>
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