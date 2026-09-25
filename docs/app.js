let DATA=null,currentIndex="S&P 500",basis="26w",outliers=false,showIndicators=true;
const $=id=>document.getElementById(id);
const fmt=v=>v==null?"—":(v>0?"+":"")+Number(v).toFixed(2)+"%";
const chartLink=s=>`<a class="chart-link" href="#chart" data-symbol="${s}" title="${s} Chart öffnen">${s} ↗</a>`;

function chartNumber(v){
  if(v==null||!Number.isFinite(Number(v)))return "—";
  const n=Number(v),a=Math.abs(n);
  const d=a>=100?2:a>=1?3:a>=0.01?4:8;
  return n.toLocaleString("de-AT",{maximumFractionDigits:d});
}
function formatDateShort(iso){
  if(!iso)return "—";
  const d=new Date(iso+"T00:00:00");
  if(Number.isNaN(d.getTime()))return "—";
  return d.toLocaleDateString("de-AT",{day:"2-digit",month:"2-digit",year:"2-digit"});
}
function findRecord(symbol){
  const current=DATA?.indexes?.[currentIndex]||[];
  let hit=current.find(x=>x.symbol===symbol);
  if(hit)return hit;
  for(const items of Object.values(DATA?.indexes||{})){
    hit=items.find(x=>x.symbol===symbol);
    if(hit)return hit;
  }
  return null;
}
function openChart(symbol){
  const x=findRecord(symbol);
  if(!x)return;
  const modal=$("chartModal"), box=$("chartCanvas"), stats=$("chartStats");
  $("chartTitle").textContent=x.name+" · "+x.symbol;
  $("chartSubtitle").textContent="6 Monate · "+(x.chart_start||"—")+" bis "+(x.chart_end||"—");
  const vals=(x.chart130||[]).map(Number).filter(Number.isFinite);
  if(vals.length<2){
    stats.innerHTML="";
    box.innerHTML="<div class='chart-empty'>Chartdaten werden mit dem nächsten Datenlauf bereitgestellt.</div>";
  }else{
    const first=vals[0],last=vals[vals.length-1],low=Math.min(...vals),high=Math.max(...vals);
    const mid=low+(high-low)/2;
    const change=first?((last/first)-1)*100:0;
    stats.innerHTML=`<span>Aktuell <b>${chartNumber(last)}</b></span><span>6M <b class="${change>=0?"pos":"neg"}">${change>=0?"+":""}${change.toFixed(2)}%</b></span><span>Tief <b>${chartNumber(low)}</b></span><span>Hoch <b>${chartNumber(high)}</b></span>`;
    const W=900,H=380,L=70,R=24,T=28,B=46,range=(high-low)||1;
    const plotW=W-L-R,plotH=H-T-B;
    const pts=vals.map((v,i)=>{
      const px=L+(i/(vals.length-1))*plotW;
      const py=T+((high-v)/range)*plotH;
      return px.toFixed(1)+","+py.toFixed(1);
    }).join(" ");
    const endY=T+((high-last)/range)*plotH;
    const startDate=x.chart_start;
    const endDate=x.chart_end;
    let midDate="—";
    if(startDate&&endDate){
      const s=new Date(startDate+"T00:00:00").getTime();
      const e=new Date(endDate+"T00:00:00").getTime();
      if(Number.isFinite(s)&&Number.isFinite(e))midDate=new Date((s+e)/2).toISOString().slice(0,10);
    }
    box.innerHTML=`<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Kurschart ${x.symbol}">
      <line x1="${L}" y1="${T}" x2="${W-R}" y2="${T}" class="chart-grid"/>
      <line x1="${L}" y1="${T+plotH/2}" x2="${W-R}" y2="${T+plotH/2}" class="chart-grid"/>
      <line x1="${L}" y1="${H-B}" x2="${W-R}" y2="${H-B}" class="chart-grid"/>
      <line x1="${L}" y1="${T}" x2="${L}" y2="${H-B}" class="chart-axis"/>
      <line x1="${L}" y1="${H-B}" x2="${W-R}" y2="${H-B}" class="chart-axis"/>

      <text x="${L-10}" y="${T+4}" text-anchor="end" class="chart-label">${chartNumber(high)}</text>
      <text x="${L-10}" y="${T+plotH/2+4}" text-anchor="end" class="chart-label">${chartNumber(mid)}</text>
      <text x="${L-10}" y="${H-B+4}" text-anchor="end" class="chart-label">${chartNumber(low)}</text>

      <text x="${L}" y="${H-14}" text-anchor="start" class="chart-label">${formatDateShort(startDate)}</text>
      <text x="${L+plotW/2}" y="${H-14}" text-anchor="middle" class="chart-label">${formatDateShort(midDate)}</text>
      <text x="${W-R}" y="${H-14}" text-anchor="end" class="chart-label">${formatDateShort(endDate)}</text>

      <polyline points="${pts}" class="chart-line"/>
      <circle cx="${W-R}" cy="${endY.toFixed(1)}" r="5" class="chart-dot"/>
    </svg>`;
  }
  modal.classList.add("open");
  modal.setAttribute("aria-hidden","false");
  document.body.classList.add("modal-open");
}
function closeChart(){
  const modal=$("chartModal");
  if(!modal)return;
  modal.classList.remove("open");
  modal.setAttribute("aria-hidden","true");
  document.body.classList.remove("modal-open");
}
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
document.addEventListener("click",e=>{
  const a=e.target.closest(".chart-link");
  if(a){e.preventDefault();openChart(a.dataset.symbol)}
});
$("chartClose").onclick=closeChart;
$("chartModal").onclick=e=>{if(e.target===$("chartModal"))closeChart()};
document.addEventListener("keydown",e=>{if(e.key==="Escape")closeChart()});
document.querySelectorAll(".basis").forEach(b=>b.onclick=()=>{basis=b.dataset.basis;document.querySelectorAll(".basis").forEach(x=>x.classList.toggle("active",x===b));render()});
$("search").oninput=render;$("outliers").onclick=()=>{outliers=!outliers;$("outliers").classList.toggle("active",outliers);render()};$("indicators").onclick=()=>{showIndicators=!showIndicators;$("indicators").classList.toggle("active",showIndicators);render()};$("refresh").onclick=load;$("print").onclick=()=>window.print();$("csv").onclick=()=>{const a=values();const s="Symbol,Name\n"+a.map(x=>`${x.symbol},"${x.name.replaceAll('"','""')}"`).join("\n");const u=URL.createObjectURL(new Blob([s],{type:"text/csv"}));const el=document.createElement("a");el.href=u;el.download="rsl-ticker.csv";el.click();URL.revokeObjectURL(u)};load().catch(e=>{$("status").textContent="Fehler: "+e.message});