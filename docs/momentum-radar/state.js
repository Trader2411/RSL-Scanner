/* Shared, pure signal validation; tested independently of the interface. */
(function(root){
  'use strict';
  const LEVEL={'KEIN EINSTIEG':0,'BEOBACHTEN':1,'EINSTIEG':2};
  const LIMITS={full:90,watch:20,quote:20};
  function age(value,now){
    if(typeof value!=='string'||!/(Z|[+-]\d\d:\d\d)$/.test(value))return Infinity;
    const n=(now-Date.parse(value))/60000;
    return Number.isFinite(n)&&n>=-1?Math.max(0,n):Infinity;
  }
  function marketClosed(x,now){
    if(x.symbol?.endsWith('-USD'))return false;
    if(x.symbol?.includes('=F'))return false; // Futures: use actual quote freshness, not US equity hours.
    const de=x.symbol?.endsWith('.DE');
    const p=Object.fromEntries(new Intl.DateTimeFormat('en-US',{timeZone:de?'Europe/Berlin':'America/New_York',weekday:'short',hour:'2-digit',minute:'2-digit',hourCycle:'h23'}).formatToParts(new Date(now)).map(z=>[z.type,z.value]));
    const minutes=Number(p.hour)*60+Number(p.minute);
    return ['Sat','Sun'].includes(p.weekday)||minutes<(de?540:240)||minutes>=(de?1050:960);
  }
  function assess(snapshot,x,now=Date.now(),transportError=false){
    const no=why=>({signal:'KEIN EINSTIEG',why,watch:null});
    if(transportError)return no('Abruf fehlgeschlagen – keine bestätigten Einstiege.');
    if(snapshot?.version!=='momentum-snapshot-1')return no('Datenpaket fehlt oder ist ungültig.');
    if(snapshot.health?.errors?.length)return no('Datenverarbeitung fehlgeschlagen – keine neuen Einstiege.');
    const d=snapshot.full_scan,w=snapshot.watch;
    if(age(d?.generated_at,now)>LIMITS.full)return no('Vollscan veraltet – neue Einstiege gesperrt.');
    if(!w||w.base_scan_generated_at!==d.generated_at)return no('Kurzcheck gehört nicht zum Vollscan – Einstieg gesperrt.');
    if(age(w.generated_at,now)>LIMITS.watch)return no('Kandidatenprüfung veraltet – neue Einstiege gesperrt.');
    if(!x||!['LONG','SHORT'].includes(x.direction)||!(x.signal in LEVEL))return no('Kein gültiges Ausgangssignal.');
    if(marketClosed(x,now))return no('Handelszeit beendet – kein neuer Einstieg.');
    const check=w.candidates?.[`${x.symbol}|${x.direction}`];
    if(!check)return no('Kurzcheck fehlt – kein neuer Einstieg.');
    if(age(check.price_asof,now)>LIMITS.quote)return no('Kursdaten zu alt – kein neuer Einstieg.');
    if(!['price','ret_15m_pct','ret_30m_pct','ret_60m_pct'].every(k=>typeof check[k]==='number'&&Number.isFinite(check[k]))||check.price<=0)return no('Kursverlauf unvollständig – kein neuer Einstieg.');
    if(!(check.watch_signal in LEVEL))return no('Kurzcheck ungültig – kein neuer Einstieg.');
    const signal=LEVEL[check.watch_signal]<=LEVEL[x.signal]?check.watch_signal:x.signal;
    return {signal,why:check.reason||x.reason||'Signal geprüft.',watch:check};
  }
  function aggregate(snapshot,items,now=Date.now(),error=false){
    const states=items.map(x=>assess(snapshot,x,now,error));
    return states.reduce((best,s)=>LEVEL[s.signal]>LEVEL[best]?s.signal:best,'KEIN EINSTIEG');
  }
  const api={age,assess,aggregate,marketClosed,LIMITS};
  if(typeof module!=='undefined'&&module.exports)module.exports=api;
  root.RadarState=api;
})(typeof globalThis!=='undefined'?globalThis:this);
