const {test}=require('node:test');const assert=require('node:assert/strict');
const S=require('../docs/momentum-radar/state.js');
const now=Date.parse('2026-09-28T14:00:00Z');
function sample(){const stamp=new Date(now).toISOString();const x={symbol:'AAPL',direction:'LONG',signal:'EINSTIEG'};const s={version:'momentum-snapshot-1',full_scan:{generated_at:stamp},watch:{generated_at:stamp,base_scan_generated_at:stamp,candidates:{'AAPL|LONG':{watch_signal:'EINSTIEG',price:100,price_asof:stamp,ret_15m_pct:1,ret_30m_pct:1,ret_60m_pct:1}}}};return {s,x}}
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
