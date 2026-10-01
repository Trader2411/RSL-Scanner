const {test}=require('node:test');const assert=require('node:assert/strict');
const S=require('../docs/momentum-radar/state.js');
const now=Date.parse('2026-09-28T14:00:00Z');
function sample(){const stamp=new Date(now).toISOString();const x={symbol:'AAPL',direction:'LONG',signal:'EINSTIEG',data_quality_ok:true,price_asof:stamp,reference_price:100,day_pct:2,m1:1,m2:2,m3:3,volume_ratio:1,rel_index:1,rel_sector:1,stability:70};const s={version:'momentum-snapshot-1',full_scan:{generated_at:stamp,universes:{'S&P 500':{candidates:{long:[x],short:[]}}}},watch:{generated_at:stamp,base_scan_generated_at:stamp,candidates:{'AAPL|LONG':{symbol:'AAPL',direction:'LONG',watch_signal:'EINSTIEG',price:100,price_asof:stamp,ret_15m_pct:1,ret_30m_pct:1,ret_60m_pct:1}}}};return {s,x}}
test('valid signal stays green',()=>{const {s,x}=sample();assert.equal(S.assess(s,x,now).signal,'EINSTIEG')});
test('no upgrade of full-scan decision',()=>{const {s,x}=sample();x.signal='BEOBACHTEN';assert.equal(S.assess(s,x,now).signal,'BEOBACHTEN')});
test('full scan expires even with fresh watch',()=>{const {s,x}=sample();s.full_scan.generated_at=new Date(now-91*60000).toISOString();s.watch.base_scan_generated_at=s.full_scan.generated_at;assert.equal(S.assess(s,x,now).signal,'KEIN EINSTIEG')});
test('watch expires',()=>{const {s,x}=sample();s.watch.generated_at=new Date(now-21*60000).toISOString();assert.equal(S.assess(s,x,now).signal,'KEIN EINSTIEG')});
test('quote expires while browser stays open',()=>{const {s,x}=sample();assert.equal(S.assess(s,x,now+21*60000).signal,'KEIN EINSTIEG')});
test('missing or mismatched check never falls back to green',()=>{for(const change of [s=>s.watch.candidates={},s=>s.watch.base_scan_generated_at='wrong']){const {s,x}=sample();change(s);assert.equal(S.assess(s,x,now).signal,'KEIN EINSTIEG')}});
test('network failure blocks previous green',()=>{const {s,x}=sample();assert.equal(S.assess(s,x,now,true).signal,'KEIN EINSTIEG')});
test('invalid prices and horizons fail closed',()=>{for(const value of [null,NaN,-1]){const {s,x}=sample();s.watch.candidates['AAPL|LONG'].price=value;assert.equal(S.assess(s,x,now).signal,'KEIN EINSTIEG')}});
test('future timestamps and no timezone fail closed',()=>{assert.equal(S.age('2026-09-28T15:00:00Z',now),Infinity);assert.equal(S.age('2026-09-28T14:00:00',now),Infinity)});
test('German close not tied to US session',()=>{assert.equal(S.marketClosed({symbol:'BEI.DE'},Date.parse('2026-09-28T16:00Z')),true);assert.equal(S.marketClosed({symbol:'AAPL'},Date.parse('2026-09-28T16:00Z')),false)});
test('weekend US closed, crypto not closed by US clock',()=>{const t=Date.parse('2026-09-27T16:00Z');assert.equal(S.marketClosed({symbol:'AAPL'},t),true);assert.equal(S.marketClosed({symbol:'HBAR-USD'},t),false)});
test('overall cannot contradict stale cards',()=>{const {s,x}=sample();assert.equal(S.aggregate(s,[x],now+21*60000),'KEIN EINSTIEG')});
test('malformed universe payload is rejected before rendering',()=>{for(const change of [s=>s.full_scan.universes={},s=>s.full_scan.universes['S&P 500']=null,s=>s.full_scan.universes['S&P 500'].candidates.long=null,s=>s.full_scan.universes['S&P 500'].candidates.long=[null],s=>s.watch.candidates=[]]){const {s,x}=sample();change(s);assert.ok(S.validateSnapshot(s));assert.equal(S.assess(s,x,now).signal,'KEIN EINSTIEG')}});
test('missing or failed full-scan data quality blocks signals',()=>{for(const flag of [undefined,false,'true']){const {s,x}=sample();x.data_quality_ok=flag;assert.equal(S.assess(s,x,now).signal,'KEIN EINSTIEG')}});
test('missing numeric scan metrics cannot be hidden by quality flag',()=>{for(const key of ['m1','m2','m3','volume_ratio','rel_index','rel_sector','reference_price']){const {s,x}=sample();x[key]=null;assert.equal(S.assess(s,x,now).signal,'KEIN EINSTIEG')}});
test('stale source cannot be repackaged into a fresh full scan',()=>{const {s,x}=sample();x.price_asof=new Date(now-46*60000).toISOString();assert.equal(S.assess(s,x,now).signal,'KEIN EINSTIEG')});
test('full source limit applies at scan completion and preserves full-scan lifetime',()=>{const {s,x}=sample();const stamp=new Date(now-60*60000).toISOString();s.full_scan.generated_at=stamp;s.watch.base_scan_generated_at=stamp;x.price_asof=new Date(now-75*60000).toISOString();assert.equal(S.assess(s,x,now).signal,'EINSTIEG')});
test('future quote relative to check completion is invalid even if fresh now',()=>{const {s,x}=sample();s.watch.generated_at=new Date(now-5*60000).toISOString();s.full_scan.generated_at=new Date(now-10*60000).toISOString();s.watch.base_scan_generated_at=s.full_scan.generated_at;x.price_asof=s.full_scan.generated_at;assert.equal(S.assess(s,x,now).signal,'KEIN EINSTIEG')});
test('wrong candidate identity does not inherit a green watch record',()=>{const {s,x}=sample();s.watch.candidates['AAPL|LONG'].symbol='MSFT';assert.equal(S.assess(s,x,now).signal,'KEIN EINSTIEG')});
test('watch cannot predate its full scan',()=>{const {s,x}=sample();s.watch.generated_at=new Date(now-60000).toISOString();assert.equal(S.assess(s,x,now).signal,'KEIN EINSTIEG')});
test('pipeline errors produce a visible global reason',()=>{const {s,x}=sample();s.health={errors:['failure']};assert.match(S.snapshotIssue(s,now),/Datenverarbeitung/);assert.equal(S.assess(s,x,now).signal,'KEIN EINSTIEG')});
test('US session observes different US and European DST transition dates',()=>{assert.equal(S.marketClosed({symbol:'AAPL'},Date.parse('2026-10-28T19:59:00Z')),false);assert.equal(S.marketClosed({symbol:'AAPL'},Date.parse('2026-10-28T20:00:00Z')),true);assert.equal(S.marketClosed({symbol:'AAPL'},Date.parse('2026-11-03T20:59:00Z')),false);assert.equal(S.marketClosed({symbol:'AAPL'},Date.parse('2026-11-03T21:00:00Z')),true)});
test('known decision check does not accept object prototype properties',()=>{const {s,x}=sample();x.signal='toString';assert.equal(S.assess(s,x,now).signal,'KEIN EINSTIEG')});
test('sector comparison may be explicitly inapplicable only for crypto and futures',()=>{for(const symbol of ['HBAR-USD','GC=F']){const {s,x}=sample();x.symbol=symbol;x.rel_sector=null;x.sector_benchmark_kind='not_applicable';s.watch.candidates[`${symbol}|LONG`]={...s.watch.candidates['AAPL|LONG'],symbol};assert.equal(S.assess(s,x,now).signal,'EINSTIEG')}const {s,x}=sample();x.rel_sector=null;x.sector_benchmark_kind='not_applicable';assert.equal(S.assess(s,x,now).signal,'KEIN EINSTIEG')});
test('strength exposes existing independent score without changing recommendations',()=>{const {s,x}=sample();x.score=86;assert.equal(S.strength(s,x,now),86);assert.equal(S.assess(s,x,now).signal,'EINSTIEG');x.signal='BEOBACHTEN';assert.equal(S.strength(s,x,now),86);assert.equal(S.assess(s,x,now).signal,'BEOBACHTEN');s.watch.candidates['AAPL|LONG'].watch_signal='KEIN EINSTIEG';assert.equal(S.strength(s,x,now),86);assert.equal(S.assess(s,x,now).signal,'KEIN EINSTIEG');});
test('strength hides missing, malformed, expired and failed evaluations',()=>{for(const score of [undefined,null,NaN,-1,101,'86']){const {s,x}=sample();x.score=score;assert.equal(S.strength(s,x,now),null);}const {s,x}=sample();x.score=86;assert.equal(S.strength(s,x,now+21*60000),null);assert.equal(S.strength(s,x,now,true),null);});

test('top five are strongest first per direction, stable on ties, no fabricated rows',()=>{
 const {s,x}=sample();const rows=[20,90,70,80,60,50,90].map((score,i)=>({...x,symbol:String.fromCharCode(65+i),score}));
 for(const row of rows)s.watch.candidates[row.symbol+'|LONG']={...s.watch.candidates['AAPL|LONG'],symbol:row.symbol};
 assert.deepEqual(S.ranked(s,rows,now).map(x=>x.symbol),['B','G','D','C','E']);
 delete s.watch.candidates['B|LONG'];
 assert.deepEqual(S.ranked(s,rows,now).map(x=>x.symbol),['G','D','C','E','F']);
 assert.deepEqual(S.ranked(s,rows,now,true).map(x=>x.symbol),['B','G','D','C','E']);
 assert.equal(S.ranked(s,rows.slice(0,2),now).length,2);
 assert.deepEqual(S.ranked(s,[],now),[]);assert.equal(rows[0].symbol,'A');
});

test('Geo recommendations preserve strategy gates and shared scale boundaries',()=>{
 for(const [score,label] of [[0,'Finger weg'],[29,'Finger weg'],[30,'Neutral'],[49,'Neutral'],[50,'Beobachten'],[69,'Beobachten'],[70,'Einstieg ½'],[84,'Einstieg ½'],[85,'Einstieg voll'],[100,'Einstieg voll']]){
   const {s,x}=sample();x.score=score;assert.equal(S.recommendation(s,x,now).action,label);
   assert.equal(S.recommendation(s,x,now,true).action,'Gesperrt');
 }
 const {s,x}=sample();x.score=100;x.signal='BEOBACHTEN';assert.equal(S.recommendation(s,x,now).action,'Beobachten');
 x.signal='KEIN EINSTIEG';assert.equal(S.recommendation(s,x,now).action,'Gesperrt');
 assert.equal(S.bestRecommendation(s,[x],now),'Gesperrt');
 x.signal='EINSTIEG';assert.equal(S.bestRecommendation(s,[x],now),'Einstieg voll');
 x.score=null;assert.equal(S.recommendation(s,x,now).action,'Gesperrt');
});
