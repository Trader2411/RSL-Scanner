/* Shared, pure signal validation; tested independently of the interface. */
(function(root){
  'use strict';
  const LEVEL={'KEIN EINSTIEG':0,'BEOBACHTEN':1,'EINSTIEG':2};
  const LIMITS={full:90,watch:20,quote:20,fullSource:45};
  const object=x=>!!x&&typeof x==='object'&&!Array.isArray(x);
  const finite=x=>typeof x==='number'&&Number.isFinite(x);
  const knownSignal=x=>Object.prototype.hasOwnProperty.call(LEVEL,x);
  function validateSnapshot(snapshot){
    if(!object(snapshot)||snapshot.version!=='momentum-snapshot-1')return 'Datenpaket fehlt oder ist ungültig.';
    const d=snapshot.full_scan,w=snapshot.watch;
    if(!object(d)||!object(d.universes)||!Object.keys(d.universes).length||!object(w)||!object(w.candidates))return 'Datenpaket unvollständig – keine neuen Einstiege.';
    for(const u of Object.values(d.universes)){
      if(!object(u)||!object(u.candidates))return 'Kandidatenliste ungültig – keine neuen Einstiege.';
      for(const side of ['long','short']){
        if(!Array.isArray(u.candidates[side])||u.candidates[side].some(x=>!object(x)||typeof x.symbol!=='string'||!x.symbol||x.direction!==side.toUpperCase()||!knownSignal(x.signal)))return 'Kandidatenliste ungültig – keine neuen Einstiege.';
      }
    }
    return '';
  }
  function age(value,now){
    if(typeof value!=='string'||!/(Z|[+-]\d\d:\d\d)$/.test(value))return Infinity;
    const n=(now-Date.parse(value))/60000;
    return Number.isFinite(n)&&n>=-1?Math.max(0,n):Infinity;
  }
  function marketClosed(x,now){
    if(!x||typeof x.symbol!=='string'||!Number.isFinite(now))return true;
    if(x.symbol?.endsWith('-USD'))return false;
    if(x.symbol?.includes('=F'))return false; // Futures: use actual quote freshness, not US equity hours.
    const de=x.symbol?.endsWith('.DE');
    const p=Object.fromEntries(new Intl.DateTimeFormat('en-US',{timeZone:de?'Europe/Berlin':'America/New_York',weekday:'short',hour:'2-digit',minute:'2-digit',hourCycle:'h23'}).formatToParts(new Date(now)).map(z=>[z.type,z.value]));
    const minutes=Number(p.hour)*60+Number(p.minute);
    return ['Sat','Sun'].includes(p.weekday)||minutes<(de?540:240)||minutes>=(de?1050:960);
  }
  function snapshotIssue(snapshot,now=Date.now(),transportError=false){
    if(transportError)return 'Abruf fehlgeschlagen – keine bestätigten Einstiege.';
    const shape=validateSnapshot(snapshot);if(shape)return shape;
    if(snapshot.health?.errors?.length)return 'Datenverarbeitung fehlgeschlagen – keine neuen Einstiege.';
    const d=snapshot.full_scan,w=snapshot.watch;
    if(age(d.generated_at,now)>LIMITS.full)return 'Vollscan veraltet – neue Einstiege gesperrt.';
    if(w.base_scan_generated_at!==d.generated_at)return 'Kurzcheck gehört nicht zum Vollscan – Einstieg gesperrt.';
    if(age(w.generated_at,now)>LIMITS.watch)return 'Kandidatenprüfung veraltet – neue Einstiege gesperrt.';
    if(Date.parse(w.generated_at)<Date.parse(d.generated_at))return 'Reihenfolge der Datenstände ungültig – kein neuer Einstieg.';
    return '';
  }
  function assess(snapshot,x,now=Date.now(),transportError=false){
    const no=why=>({signal:'KEIN EINSTIEG',why,watch:null});
    const issue=snapshotIssue(snapshot,now,transportError);if(issue)return no(issue);
    const d=snapshot.full_scan,w=snapshot.watch;
    if(!x||typeof x.symbol!=='string'||!['LONG','SHORT'].includes(x.direction)||!knownSignal(x.signal))return no('Kein gültiges Ausgangssignal.');
    if(marketClosed(x,now))return no('Außerhalb der Handelszeit – kein neuer Einstieg.');
    if(x.data_quality_ok!==true)return no(Array.isArray(x.data_quality_issues)&&x.data_quality_issues.length?`Datenlücke: ${x.data_quality_issues.join(' · ')}`:'Datenqualität des Vollscans nicht bestätigt – kein neuer Einstieg.');
    const sectorNotApplicable=x.sector_benchmark_kind==='not_applicable'&&(x.symbol.endsWith('-USD')||x.symbol.includes('=F'));
    if(!['reference_price','day_pct','m1','m2','m3','volume_ratio','rel_index','stability'].every(k=>finite(x[k]))||(!finite(x.rel_sector)&&!sectorNotApplicable)||x.reference_price<=0||x.volume_ratio<0||x.stability<0||x.stability>100)return no('Bewertung im Vollscan unvollständig – kein neuer Einstieg.');
    if(age(x.price_asof,Date.parse(d.generated_at))>LIMITS.fullSource)return no('Ausgangskurs im Vollscan fehlt oder ist veraltet – kein neuer Einstieg.');
    const check=w.candidates?.[`${x.symbol}|${x.direction}`];
    if(!object(check))return no('Kurzcheck fehlt – kein neuer Einstieg.');
    if(check.symbol!==x.symbol||check.direction!==x.direction)return no('Kurzcheck gehört nicht zum Kandidaten – kein neuer Einstieg.');
    if(age(check.price_asof,now)>LIMITS.quote||age(check.price_asof,Date.parse(w.generated_at))>LIMITS.quote)return no('Kursdaten fehlen, sind zu alt oder zeitlich ungültig – kein neuer Einstieg.');
    if(!['price','ret_15m_pct','ret_30m_pct','ret_60m_pct'].every(k=>finite(check[k]))||check.price<=0)return no('Kursverlauf unvollständig – kein neuer Einstieg.');
    if(!knownSignal(check.watch_signal))return no('Kurzcheck ungültig – kein neuer Einstieg.');
    const signal=LEVEL[check.watch_signal]<=LEVEL[x.signal]?check.watch_signal:x.signal;
    const reason=signal===x.signal&&LEVEL[x.signal]<LEVEL[check.watch_signal]?x.reason:check.reason;
    return {signal,why:reason||x.reason||'Signal geprüft.',watch:check};
  }
  function aggregate(snapshot,items,now=Date.now(),error=false){
    const states=(Array.isArray(items)?items:[]).map(x=>assess(snapshot,x,now,error));
    return states.reduce((best,s)=>LEVEL[s.signal]>LEVEL[best]?s.signal:best,'KEIN EINSTIEG');
  }
  const api={age,assess,aggregate,marketClosed,validateSnapshot,snapshotIssue,LIMITS};
  if(typeof module!=='undefined'&&module.exports)module.exports=api;
  root.RadarState=api;
})(typeof globalThis!=='undefined'?globalThis:this);
