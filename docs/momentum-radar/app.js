'use strict';
let SNAP=null,DATA=null,selected=null,lastFetchAt=null,loadError='',loading=false;
const $=id=>document.getElementById(id);
function saved(k,f){try{return localStorage.getItem(k)||f}catch(_){return f}}
function store(k,v){try{localStorage.setItem(k,String(v))}catch(_){}}
let currentUniverse=saved('momentumRadarUniverse','S&P 500');
const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const pct=v=>typeof v==='number'&&Number.isFinite(v)?`${v>0?'+':''}${v.toFixed(2)} %`:'—';
const money=v=>new Intl.NumberFormat('de-AT',{style:'currency',currency:'EUR',maximumFractionDigits:0}).format(v);
const num=v=>typeof v==='number'&&Number.isFinite(v)?v.toLocaleString('de-AT',{maximumFractionDigits:v<1?6:2}):'—';
const time=v=>v?new Date(v).toLocaleString('de-AT',{day:'2-digit',month:'2-digit',hour:'2-digit',minute:'2-digit'}):'—';
const sClass=s=>s==='EINSTIEG'?'entry':s==='BEOBACHTEN'?'watch':'no';
const sIcon=s=>s==='EINSTIEG'?'🟢':s==='BEOBACHTEN'?'🟡':'🔴';
function universeData(){return DATA?.universes?.[currentUniverse]||{coverage:{},candidates:{long:[],short:[]}}}
function items(){const u=universeData();return [...(u.candidates.long||[]),...(u.candidates.short||[])]}
async function load(){
  if(loading)return;
  loading=true;$('refresh').disabled=true;$('refresh').textContent='↻ Prüft…';
  const abort=new AbortController(),timer=setTimeout(()=>abort.abort(),15000);
  try{
    const response=await fetch(`snapshot.json?ts=${Date.now()}`,{cache:'no-store',signal:abort.signal});
    if(!response.ok)throw new Error(`HTTP ${response.status}`);
    const next=await response.json();
    if(next.version!=='momentum-snapshot-1'||!next.full_scan?.universes||!next.watch)throw new Error('Unvollständiges Datenpaket');
    SNAP=next;DATA=next.full_scan;lastFetchAt=new Date().toISOString();loadError='';
    const names=Object.keys(DATA.universes);
    if(!names.includes(currentUniverse))currentUniverse=names[0]||'S&P 500';
    buildUniverseButtons();
  }catch(error){loadError=error.name==='AbortError'?'Zeitüberschreitung':error.message}
  finally{clearTimeout(timer);loading=false;$('refresh').disabled=false;$('refresh').textContent='↻ Aktualisieren';render()}
}
function buildUniverseButtons(){
  const box=$('universeButtons');box.replaceChildren();
  const select=document.createElement('select');select.id='universe';select.setAttribute('aria-label','Index auswählen');
  for(const name of Object.keys(DATA?.universes||{})){const option=new Option(name,name);option.selected=name===currentUniverse;select.add(option)}
  select.onchange=()=>{currentUniverse=select.value;selected=null;store('momentumRadarUniverse',currentUniverse);render()};box.appendChild(select);
}
function render(){
  const u=universeData(),now=Date.now(),all=items();
  const overall=RadarState.aggregate(SNAP,all,now,!!loadError);
  $('overallSignal').textContent=overall;$('signalDot').className=`dot ${sClass(overall)}`;
  $('phase').textContent=currentUniverse;
  $('updated').textContent=`Vollscan ${time(DATA?.generated_at)} · Kurzcheck ${time(SNAP?.watch?.generated_at)}`;
  $('fetchStatus').textContent=loadError?`Abruf fehlgeschlagen: ${loadError}`:`Seite geprüft: ${time(lastFetchAt)} · automatische Aktualisierung bei geöffneter Seite`;
  const fullOld=RadarState.age(DATA?.generated_at,now)>RadarState.LIMITS.full;
  const watchOld=RadarState.age(SNAP?.watch?.generated_at,now)>RadarState.LIMITS.watch;
  const mismatch=SNAP?.watch?.base_scan_generated_at!==DATA?.generated_at;
  const message=loadError?'Abruf fehlgeschlagen – keine bestätigten Einstiege.':fullOld?'Vollscan überfällig – keine neuen Einstiege.':mismatch?'Datenstände passen nicht zusammen – keine neuen Einstiege.':watchOld?'Kandidatenprüfung überfällig – keine neuen Einstiege.':'';
  $('staleBanner').textContent=message?`🔴 ${message}`:'';$('staleBanner').classList.toggle('hidden',!message);
  $('coverage').textContent=`${u.coverage?.with_intraday_data||0}/${u.coverage?.universe||0}`;
  if(selected)selected=all.find(x=>x.symbol===selected.symbol&&x.direction===selected.direction)||null;
  if(!selected)selected=(u.candidates.long||[])[0]||null;
  renderList('longList',u.candidates.long||[]);renderList('shortList',u.candidates.short||[]);renderTargets();
}
function renderList(id,list){
  const query=$('search').value.trim().toLowerCase();
  const shown=list.filter(x=>!query||`${x.name} ${x.symbol} ${x.wkn||''}`.toLowerCase().includes(query));
  $(id).innerHTML=shown.length?shown.map(card).join(''):'<p class="muted">Keine passenden Kandidaten in dieser Auswahl.</p>';
  $(id).querySelectorAll('.candidate').forEach(el=>el.onclick=e=>{if(e.target.closest('a,button,summary,details'))return;selected=items().find(x=>x.symbol===el.dataset.symbol&&x.direction===el.dataset.direction);renderTargets()});
}
function card(x){
  const state=RadarState.assess(SNAP,x,Date.now(),!!loadError),w=state.watch;
  const sourceUrl=`https://finance.yahoo.com/quote/${encodeURIComponent(x.symbol)}/chart/`;
  const wknUrl=typeof x.wkn_url==='string'&&x.wkn_url.startsWith('https://www.finanzen.net/')?x.wkn_url:null;
  const sign=v=>typeof v==='number'?(v>=0?'pos':'neg'):'';
  const kpi=(name,value,raw)=>`<div class="kpi"><span>${name}</span><b class="${sign(raw)}">${value}</b></div>`;
  return `<article class="candidate ${sClass(state.signal)}" data-symbol="${esc(x.symbol)}" data-direction="${esc(x.direction)}">
    <div class="candidate-top"><div class="rank-name"><span class="rank">${esc(x.rank)}</span><div class="name"><b>${esc(x.name)}</b><small>${esc(x.symbol)} · ${esc(x.direction)}${x.wkn&&wknUrl?` · <a class="wkn-link" href="${esc(wknUrl)}" target="_blank" rel="noopener noreferrer">WKN ${esc(x.wkn)} ↗</a>`:''}</small></div></div><span class="signal-pill ${sClass(state.signal)}">${sIcon(state.signal)} ${state.signal}</span></div>
    <div class="reason">${esc(state.why)}</div>
    <div class="watch-line">${w?`Kurs ${num(w.price)} · Kursstand ${time(w.price_asof)} · <a class="source-chart-link" href="${sourceUrl}" target="_blank" rel="noopener noreferrer">Quellenchart ↗</a>`:`Kein bestätigter aktueller Kurs · <a class="source-chart-link" href="${sourceUrl}" target="_blank" rel="noopener noreferrer">Quellenchart ↗</a>`}</div>
    <div class="kpis">${kpi('15 Min.',pct(w?.ret_15m_pct),w?.ret_15m_pct)}${kpi('30 Min.',pct(w?.ret_30m_pct),w?.ret_30m_pct)}${kpi('Seit Vollscan',pct(w?.move_since_scan_pct),w?.move_since_scan_pct)}</div>
    <details><summary>Bewertung aus dem Vollscan</summary><div class="kpis">${kpi('Tag',pct(x.day_pct),x.day_pct)}${kpi('1 Std.',pct(x.m1),x.m1)}${kpi('2 Std.',pct(x.m2),x.m2)}${kpi('3 Std.',pct(x.m3),x.m3)}${kpi('Volumen',x.volume_ratio==null?'—':`${num(x.volume_ratio)}×`)}${kpi('Stabilität',x.stability==null?'—':`${Math.round(x.stability)} %`)}</div><div class="muted">Momentum im Vollscan: ${esc(x.momentum_change||'—')} · ${esc(x.reason||'')}</div></details>
  </article>`;
}
function renderTargets(){
  const depot=Math.max(0,Number($('depot').value)||0),allocation=Math.min(100,Math.max(1,Number($('allocation').value)||50));
  store('momentumRadarDepot',depot);store('momentumRadarAllocation',allocation);
  const fraction=allocation/100;$('maxUse').textContent=money(depot*fraction);$('target1').textContent=money(depot*.01);$('target2').textContent=money(depot*.02);
  $('need1').textContent=`benötigt ${(1/fraction).toFixed(1)} % auf den Einsatz`;$('need2').textContent=`benötigt ${(2/fraction).toFixed(1)} % auf den Einsatz`;
  $('progress').textContent='Nicht erfasst';$('progressText').textContent='Ohne Kauf- und Verkaufsdaten kein tatsächlicher Depotgewinn.';
}
$('refresh').onclick=load;$('search').oninput=render;
for(const id of ['depot','allocation'])$(id).oninput=renderTargets;
$('depot').value=saved('momentumRadarDepot','5000');$('allocation').value=saved('momentumRadarAllocation','50');
setInterval(()=>{if(document.visibilityState==='visible')render()},15000);
setInterval(()=>{if(document.visibilityState==='visible')load()},60000);
document.addEventListener('visibilitychange',()=>{if(document.visibilityState==='visible'){render();load()}});
window.addEventListener('pageshow',e=>{if(e.persisted){render();load()}});
load();
