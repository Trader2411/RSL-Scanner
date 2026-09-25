let DATA=null,currentIndex="S&P 500",basis="26w",outliers=false,showIndicators=true;
const $=id=>document.getElementById(id);
const fmt=v=>v==null?"—":(v>0?"+":"")+Number(v).toFixed(2)+"%";
const chartUrl=s=>`https://finance.yahoo.com/chart/${encodeURIComponent(s)}`;
const chartLink=s=>`<a class="chart-link" href="${chartUrl(s)}" target="_blank" rel="noopener noreferrer" title="${s} Chart öffnen">${s} ↗</a>`;
async function load(){ $("status").textContent="Daten werden geladen…"; const r=await fetch("data.json?"+Date.now()); DATA=await r.json(); const names=Object.keys(DATA.indexes||{}); if(names.length&&!names.includes(currentIndex))currentIndex=names[0]; buildButtons(); render(); $("status").textContent=DATA.generated_at?"Daten geladen":"Erster Datenlauf noch offen"; }
function buildButtons(){const box=$("indexButtons");box.innerHTML="";const names=Object.keys(DATA.indexes||{});(names.length?names:["S&P 500","NASDAQ 100","Dow Jones","DAX","Krypto"]).forEach(n=>{const b=document.createElement("button");b.textContent=n;b.className=n===currentIndex?"active":"";b.onclick=()=>{currentIndex=n;buildButtons();render()};box.appendChild(b)})}
function values(){
  let a=[...(DATA.indexes?.[currentIndex]||[])];
  const raw=$("search").value.trim().toLowerCase();
  if(raw){
    const terms=raw.split(/[,;\n]+/).map(x=>x.trim()).filter(Boolean);
    a=a.filter(x=>{
      const symbol=x.symbol.toLowerCase();
      const name=x.name.toLowerCase();
      return terms.some(t=>symbol.includes(t)||name.includes(t));
    });
  }
  if(outliers)a=a.filter(x=>{const v=x[basis==="26w"?"rsl26w":"rsl26d"];return v>.35&&v<2.5});
  return a
}
function render(){const universe=[...(DATA.indexes?.[currentIndex]||[])],a=values(),total=universe.length,rk=basis==="26w"?"rank26w":"rank26d",mv=basis==="26w"?"move26w":"move26d",rv=basis==="26w"?"rsl26w":"rsl26d";$("tableIndex").textContent=currentIndex;$("moverIndex").textContent=currentIndex;$("tableBasis").textContent="Basis: "+(basis==="26w"?"26 Wochen":"26 Tage");$("updated").textContent=DATA.generated_at?"Stand: "+new Date(DATA.generated_at).toLocaleString("de-AT"):"Noch keine Kursdatei";document.body.classList.toggle("hide-indicators",!showIndicators);
const sorted=[...a].sort((x,y)=>(x[rk]||9999)-(y[rk]||9999));$("rows").innerHTML=sorted.map(x=>row(x,rk,mv,rv,total)).join("");
const movers=[...universe].filter(x=>x[mv]!=null).sort((x,y)=>y[mv]-x[mv]);$("gainers").innerHTML=movers.slice(0,3).map((x,i)=>mover(x,i+1,mv,rk,rv,true)).join("")||"<small>Keine Daten</small>";$("losers").innerHTML=movers.slice(-3).reverse().map((x,i)=>mover(x,i+1,mv,rk,rv,false)).join("")||"<small>Keine Daten</small>"}
function rankStatus(rank,total){
  if(!rank||!total)return {cls:"rank-bad",label:"—",pct:null};
  const pct=(rank/total)*100;
  if(pct<=20)return {cls:"rank-good",label:"Top 20 %",pct};
  if(pct<=30)return {cls:"rank-warn",label:"20–30 %",pct};
  return {cls:"rank-bad",label:"> 30 %",pct};
}
function row(x,rk,mv,rv,total){
  const both=x.rank26d<=5&&x.rank26w<=5,one=x.rank26d<=5||x.rank26w<=5;
  let cls=both?"topboth":one?"topone":"";
  if(x.cross==="golden") cls+=" cross-golden";
  if(x.cross==="death") cls+=" cross-death";
  const move=x[mv]||0;
  const rsiCls=(x.rsi||0)>=70?"rsi-hot":"";
  const sig=x.signal==="bullish"?"<span class='signal-bull'>↗ Bullish</span>":"<span class='signal-bear'>↘ Bearish</span>";
  const rs=rankStatus(x[rk],total);
  const status="<span class='rank-status "+rs.cls+"'>"+rs.label+"</span>";
  return `<tr class="${cls}"><td><b>${x[rk]||"—"}</b></td><td>${status}</td><td class="${move>=0?"pos":"neg"}">${move>0?"↑ ":""}${move<0?"↓ ":""}${Math.abs(move)}</td><td class="sym">${chartLink(x.symbol)}</td><td>${x.name}</td><td>${x.sector||"—"}</td><td><b>${x[rv]?.toFixed(4)||"—"}</b></td><td class="indicator"><span class="trend">${x.trendq==null?"—":(x.trendq>0?"+":"")+x.trendq.toFixed(2)}</span></td><td class="indicator ${rsiCls}">${x.rsi??"—"}</td><td class="indicator ${(x.macd_hist||0)>=0?"pos":"neg"}">${x.macd_hist==null?"—":(x.macd_hist>0?"+":"")+x.macd_hist.toFixed(2)}</td><td class="indicator">${sig}</td><td class="${(x.d1||0)>=0?"pos":"neg"}">${fmt(x.d1)}</td><td class="${(x.w1||0)>=0?"pos":"neg"}">${fmt(x.w1)}</td><td class="${(x.m1||0)>=0?"pos":"neg"}">${fmt(x.m1)}</td></tr>`
}
function mover(x,i,mv,rk,rv,up){return `<div class="mitem"><b><span>${i}. ${chartLink(x.symbol)}</span><span class="${up?"pos":"neg"}">${up?"↑":"↓"} ${Math.abs(x[mv]||0)}</span></b><small>${x.name}</small><div><small>#${x["old"+rk]||"—"} → #${x[rk]||"—"} · RSL ${x[rv]?.toFixed(2)||"—"}</small></div></div>`}
document.querySelectorAll(".basis").forEach(b=>b.onclick=()=>{basis=b.dataset.basis;document.querySelectorAll(".basis").forEach(x=>x.classList.toggle("active",x===b));render()});
$("search").oninput=render;$("outliers").onclick=()=>{outliers=!outliers;$("outliers").classList.toggle("active",outliers);render()};$("indicators").onclick=()=>{showIndicators=!showIndicators;$("indicators").classList.toggle("active",showIndicators);render()};$("refresh").onclick=load;$("print").onclick=()=>window.print();$("csv").onclick=()=>{const a=values();const s="Symbol,Name\n"+a.map(x=>`${x.symbol},"${x.name.replaceAll('"','""')}"`).join("\n");const u=URL.createObjectURL(new Blob([s],{type:"text/csv"}));const el=document.createElement("a");el.href=u;el.download="rsl-ticker.csv";el.click();URL.revokeObjectURL(u)};load().catch(e=>{$("status").textContent="Fehler: "+e.message});