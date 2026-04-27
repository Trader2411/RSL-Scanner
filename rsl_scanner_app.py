# rsl_scanner_app_v4.py
# ------------------------------------------------------------
# RSL Trading Scanner & Portfolio Manager
# Autor: ChatGPT
#
# Start:
#   1) Python installieren
#   2) Terminal öffnen
#   3) Pakete installieren:
#        pip install streamlit yfinance pandas numpy requests beautifulsoup4 lxml plotly
#   4) App starten:
#        python -m streamlit run rsl_scanner_app.py
#
# Hinweis:
# Diese App ist ein Analysewerkzeug und keine Finanzberatung.
# Daten kommen aus frei verfügbaren Quellen/Yahoo Finance und können fehlerhaft,
# verzögert oder unvollständig sein.
# ------------------------------------------------------------

import json
import math
import time
from datetime import datetime, date
from pathlib import Path
from io import StringIO
from typing import Dict, List, Tuple, Optional

import numpy as np
import pandas as pd
import requests
import streamlit as st
import streamlit.components.v1 as components
import yfinance as yf


# ============================================================
# EINSTELLUNGEN
# ============================================================

APP_TITLE = "RSL Scanner"
RSL_WEEKS = 26
PORTFOLIO_FILE = Path("rsl_portfolio.json")
RANK_HISTORY_FILE = Path("rsl_rank_history.json")

# Bei sehr großen Scans kann Yahoo Finance drosseln.
# Batchgröße lieber konservativ lassen.
BATCH_SIZE = 60

# Auto-Refresh-Standard in Minuten.
DEFAULT_REFRESH_MINUTES = 30

# Emerging Markets Proxy:
# Yahoo-Ticker aus frei verfügbaren ETF-Holdings sind nicht immer direkt verwendbar.
# Die App versucht, ISIN/Symbol in Yahoo-Ticker umzuwandeln; nicht alle Werte werden funktionieren.
EMERGING_MARKETS_PROXY_NOTE = (
    "Emerging Markets wird als kostenloser Proxy über große MSCI-EM-ETF-Holdings gescannt. "
    "Die offizielle MSCI-Komplettliste ist meist lizenzpflichtig; einzelne EM-Ticker können bei Yahoo Finance fehlen."
)

# Optionale manuelle WKN-Tabelle.
# Kostenlose APIs liefern WKNs nicht zuverlässig. Ergänze hier nach Bedarf deine wichtigsten Werte.
# Format: "YAHOO_TICKER": "WKN"
MANUAL_WKN: Dict[str, str] = {
    "AAPL": "865985",
    "MSFT": "870747",
    "NVDA": "918422",
    "AMZN": "906866",
    "GOOGL": "A14Y6F",
    "GOOG": "A14Y6H",
    "META": "A1JWVX",
    "TSLA": "A1CX3T",
    "AVGO": "A2JG9Z",
    "NFLX": "552484",
    "COST": "888351",
    "AMD": "863186",
    "ADBE": "871981",
    "PEP": "851995",
    "CSCO": "878841",
    "INTC": "855681",
    "QCOM": "883121",
    "TXN": "852654",
    "INTU": "886053",
    "AMAT": "865177",
    "ASML": "A1J4U4",
    "LIN": "A2DSYC",
    "JPM": "850628",
    "V": "A0NC7B",
    "MA": "A0F602",
    "UNH": "869561",
    "XOM": "852549",
    "JNJ": "853260",
    "PG": "852062",
    "HD": "866953",
    "KO": "850663",
    "ABBV": "A1J84E",
    "MRK": "A0YD8Q",
    "WMT": "860853",
}


# ============================================================
# STREAMLIT SETUP & DESIGN
# ============================================================

st.set_page_config(
    page_title=APP_TITLE,
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed",
)

CUSTOM_CSS = """
<style>
:root {
    --bg: #f7f8fb;
    --bg-soft: #ffffff;
    --panel: #ffffff;
    --panel2: #f2f4f8;
    --text: #111827;
    --muted: #526173;
    --gold: #b5892f;
    --green: #0f9f6e;
    --yellow: #a66f00;
    --red: #cc294d;
    --blue: #2563eb;
    --border: rgba(17,24,39,0.11);
    --shadow: rgba(17,24,39,0.09);
}
html, body, [class*="css"] {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif;
}
.stApp {
    background:
        radial-gradient(circle at top left, rgba(216,180,106,0.16), transparent 26%),
        radial-gradient(circle at bottom right, rgba(37,99,235,0.08), transparent 30%),
        var(--bg) !important;
    color: var(--text) !important;
}
.block-container {
    padding-top: 1.1rem;
    padding-left: 1rem;
    padding-right: 1rem;
    max-width: 1180px;
}
h1, h2, h3, h4, h5, h6, p, li, span, label, div {
    color: var(--text);
}
h1, h2, h3 {
    letter-spacing: -0.03em;
}
/* Streamlit Texte im Light-Mode gut lesbar machen */
[data-testid="stMarkdownContainer"],
[data-testid="stMarkdownContainer"] p,
[data-testid="stMarkdownContainer"] li,
[data-testid="stMarkdownContainer"] span,
[data-testid="stWidgetLabel"],
[data-testid="stWidgetLabel"] p,
[data-testid="stExpander"] summary,
[data-testid="stExpander"] p {
    color: var(--text) !important;
}
/* Eingabefelder */
.stSelectbox div[data-baseweb="select"] > div,
.stTextInput input,
.stDateInput input,
.stNumberInput input,
.stSlider,
textarea {
    background: #ffffff !important;
    color: var(--text) !important;
    border-color: var(--border) !important;
}
.stSelectbox div[data-baseweb="select"] span {
    color: var(--text) !important;
}
[data-testid="stMetric"] {
    background: linear-gradient(145deg, #ffffff, #f5f7fb);
    border: 1px solid var(--border);
    padding: 14px 14px;
    border-radius: 18px;
    box-shadow: 0 10px 26px var(--shadow);
}
[data-testid="stMetric"] label,
[data-testid="stMetric"] div {
    color: var(--text) !important;
}
[data-testid="stMetricValue"] {
    color: #1f2937 !important;
    font-weight: 850;
}
[data-testid="stMetricDelta"] svg,
[data-testid="stMetricDelta"] div {
    color: var(--green) !important;
    fill: var(--green) !important;
}
div.stButton > button {
    width: 100%;
    border-radius: 16px;
    border: 1px solid rgba(181,137,47,0.35);
    background: linear-gradient(135deg, #e2bf69 0%, #b5892f 100%);
    color: #111827 !important;
    font-weight: 850;
    min-height: 46px;
    box-shadow: 0 8px 18px rgba(181,137,47,0.18);
}
div.stButton > button:hover {
    border-color: rgba(181,137,47,0.75);
    filter: brightness(0.98);
}
div.stDownloadButton > button {
    width: 100%;
    border-radius: 16px;
    min-height: 44px;
    background: #ffffff !important;
    color: var(--text) !important;
    border: 1px solid var(--border) !important;
}
.card {
    background: linear-gradient(145deg, #ffffff, #f7f9fc);
    border: 1px solid var(--border);
    border-radius: 22px;
    padding: 16px;
    margin: 10px 0;
    box-shadow: 0 14px 32px var(--shadow);
}
.card-title {
    color: var(--text) !important;
    font-size: 1.05rem;
    font-weight: 850;
    margin-bottom: 2px;
}
.card-sub {
    color: var(--muted) !important;
    font-size: 0.86rem;
}
.badge {
    display: inline-block;
    padding: 5px 10px;
    border-radius: 999px;
    font-weight: 850;
    font-size: 0.78rem;
    margin-top: 8px;
}
.badge-green { background: rgba(15,159,110,0.12); color: #05724f !important; border: 1px solid rgba(15,159,110,0.30); }
.badge-yellow { background: rgba(255,200,87,0.22); color: #805400 !important; border: 1px solid rgba(166,111,0,0.28); }
.badge-red { background: rgba(204,41,77,0.10); color: #a61f3d !important; border: 1px solid rgba(204,41,77,0.28); }
.small {
    color: var(--muted) !important;
    font-size: 0.86rem;
}
.rank {
    color: var(--gold) !important;
    font-size: 2rem;
    font-weight: 900;
    line-height: 1;
}
a {
    color: #8a651f !important;
    text-decoration: none;
    font-weight: 750;
}
a:hover {
    text-decoration: underline;
}
/* Tabs deutlicher */
button[data-baseweb="tab"] p {
    color: var(--muted) !important;
    font-weight: 750;
}
button[data-baseweb="tab"][aria-selected="true"] p {
    color: #b42318 !important;
}
[data-testid="stDataFrame"] {
    border-radius: 18px;
    overflow: hidden;
    border: 1px solid var(--border);
}
/* Fehlermeldungen bleiben sichtbar, aber nicht grell */
[data-testid="stException"], [data-testid="stAlert"] {
    border-radius: 16px;
}
@media (max-width: 700px) {
    .block-container {
        padding-left: 0.65rem;
        padding-right: 0.65rem;
    }
    h1 { font-size: 1.65rem; }
    .card { padding: 13px; border-radius: 18px; }
    .rank { font-size: 1.55rem; }
}
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# Zusätzliche Optik-Anpassung V4: heller Hintergrund, dunkle Kacheln, helle Schrift in Kacheln.
OVERRIDE_CSS = """
<style>
:root{--app-bg:#f7f8fb;--dark-card:#111827;--dark-card2:#1e293b;--light-text:#f8fafc;--light-muted:#cbd5e1;--main-text:#101828;--gold:#d6ad55;--gold-link:#f8d477;--border-dark:rgba(255,255,255,.13);--shadow:rgba(17,24,39,.14)}
.stApp{background:radial-gradient(circle at top left,rgba(214,173,85,.12),transparent 25%),radial-gradient(circle at bottom right,rgba(37,99,235,.07),transparent 32%),var(--app-bg)!important;color:var(--main-text)!important}
h1,h2,h3{color:#07111f!important;font-weight:900!important}.small{color:#526173!important}
[data-testid="stMarkdownContainer"],[data-testid="stMarkdownContainer"] p,[data-testid="stMarkdownContainer"] span,[data-testid="stWidgetLabel"],[data-testid="stWidgetLabel"] p{color:var(--main-text)!important}
.stSelectbox div[data-baseweb="select"]>div,.stTextInput input{background:#fff!important;color:var(--main-text)!important;border:1px solid rgba(17,24,39,.13)!important;border-radius:12px!important}.stSelectbox span,.stSelectbox svg{color:var(--main-text)!important;fill:var(--main-text)!important}
[data-testid="stMetric"]{background:linear-gradient(145deg,var(--dark-card),var(--dark-card2))!important;border:1px solid var(--border-dark)!important;box-shadow:0 12px 28px var(--shadow)!important}
[data-testid="stMetric"] label,[data-testid="stMetric"] label p,[data-testid="stMetric"] span,[data-testid="stMetric"] div{color:var(--light-muted)!important}[data-testid="stMetricValue"],[data-testid="stMetricValue"] div{color:var(--light-text)!important;font-weight:900!important}[data-testid="stMetricDelta"] div,[data-testid="stMetricDelta"] svg{color:#22c55e!important;fill:#22c55e!important;font-weight:850!important}
.card{background:linear-gradient(145deg,var(--dark-card),var(--dark-card2))!important;border:1px solid var(--border-dark)!important;box-shadow:0 14px 32px var(--shadow)!important;color:var(--light-text)!important}.card *,.card div,.card span,.card p{color:var(--light-text)!important}.card-title{color:var(--light-text)!important;font-weight:900!important}.card-sub,.card .small{color:var(--light-muted)!important}.card div[style*="margin-top:8px"]{color:var(--light-text)!important;font-weight:650!important}.rank,.card .rank{color:var(--gold)!important}
.card a{color:var(--gold-link)!important;font-weight:900!important}a{color:#9a6b16!important;font-weight:850!important}
.badge-green{background:rgba(34,197,94,.18)!important;color:#bbf7d0!important;border:1px solid rgba(34,197,94,.45)!important}.badge-yellow{background:rgba(245,158,11,.20)!important;color:#fde68a!important;border:1px solid rgba(245,158,11,.50)!important}.badge-red{background:rgba(239,68,68,.18)!important;color:#fecaca!important;border:1px solid rgba(239,68,68,.45)!important}.badge{font-weight:900!important}
div.stButton>button{background:linear-gradient(135deg,#f1cf78 0%,#c49435 100%)!important;color:#111827!important;font-weight:900!important;border:1px solid rgba(154,107,22,.35)!important}div.stButton>button p,div.stButton>button span{color:#111827!important;font-weight:900!important}
div.stDownloadButton>button{background:linear-gradient(145deg,var(--dark-card),var(--dark-card2))!important;color:var(--light-text)!important;border:1px solid var(--border-dark)!important;font-weight:850!important}div.stDownloadButton>button p,div.stDownloadButton>button span{color:var(--light-text)!important;font-weight:850!important}
button[data-baseweb="tab"] p{color:#475569!important;font-weight:800!important}button[data-baseweb="tab"][aria-selected="true"] p{color:#b42318!important;font-weight:900!important}

/* V5: Eigene KPI-Kacheln statt Streamlit-Metrics, damit alle Schriften sauber lesbar bleiben */
.kpi-card{
    background:linear-gradient(145deg,#111827,#1e293b)!important;
    border:1px solid rgba(255,255,255,.14)!important;
    border-radius:18px!important;
    padding:16px 17px!important;
    min-height:92px!important;
    box-shadow:0 12px 28px rgba(17,24,39,.16)!important;
    overflow:hidden!important;
}
.kpi-label{
    color:#dbeafe!important;
    font-size:.78rem!important;
    line-height:1.15rem!important;
    font-weight:850!important;
    margin-bottom:7px!important;
    letter-spacing:.01em!important;
}
.kpi-value{
    color:#ffffff!important;
    font-size:1.72rem!important;
    line-height:2.05rem!important;
    font-weight:950!important;
    letter-spacing:-.04em!important;
    white-space:nowrap!important;
    overflow:hidden!important;
    text-overflow:ellipsis!important;
}
.kpi-delta{
    color:#86efac!important;
    font-size:.78rem!important;
    line-height:1.1rem!important;
    font-weight:900!important;
    margin-top:4px!important;
}
@media (max-width:700px){
    .kpi-card{min-height:84px!important;padding:14px!important;margin-bottom:8px!important}
    .kpi-value{font-size:1.38rem!important;line-height:1.7rem!important}
    .kpi-label,.kpi-delta{font-size:.72rem!important}
}
[data-testid="stExpander"]{background:#fff!important;border:1px solid rgba(17,24,39,.13)!important;border-radius:12px!important}[data-testid="stExpander"] summary,[data-testid="stExpander"] p{color:var(--main-text)!important}
</style>
"""
st.markdown(OVERRIDE_CSS, unsafe_allow_html=True)



# ============================================================
# HILFSFUNKTIONEN
# ============================================================

def now_str() -> str:
    return datetime.now().strftime("%d.%m.%Y %H:%M")


def normalize_yahoo_symbol(symbol: str) -> str:
    """Wikipedia nutzt z.B. BRK.B; Yahoo nutzt BRK-B."""
    if not isinstance(symbol, str):
        return ""
    s = symbol.strip().upper()
    s = s.replace(".", "-")
    return s


def safe_float(x, default=np.nan):
    try:
        if x is None:
            return default
        return float(x)
    except Exception:
        return default


def wkn_link(wkn: str, ticker: str) -> str:
    """Link über Börse Frankfurt Suche; funktioniert gut für WKN/ISIN/Symbol."""
    if wkn and wkn != "—":
        return f"https://www.boerse-frankfurt.de/suchergebnisse?query={wkn}"
    return f"https://finance.yahoo.com/quote/{ticker}"


def yahoo_link(ticker: str) -> str:
    return f"https://finance.yahoo.com/quote/{ticker}"


def get_wkn(ticker: str) -> str:
    return MANUAL_WKN.get(ticker.upper(), "—")


def traffic_light(rsl: float, rank: int, total: int) -> Tuple[str, str, str]:
    """
    Ampel:
    Grün: sehr starke relative Stärke
    Gelb: solide/neutral
    Rot: schwach
    """
    if pd.isna(rsl):
        return "⚪", "Keine Daten", "Keine Handlung möglich: Daten fehlen."
    percentile = rank / max(total, 1)

    if rsl >= 1.08 and percentile <= 0.20:
        return "🟢", "Stark", "Kaufen/halten: Trend stark, nur mit Positionsgröße und Stop arbeiten."
    if rsl >= 1.00 and percentile <= 0.50:
        return "🟡", "Neutral bis positiv", "Beobachten/halten: Stärke vorhanden, Einstieg nur bei sauberem Rücksetzer."
    return "🔴", "Schwach", "Meiden/Verkauf prüfen: relative Stärke reicht aktuell nicht aus."


def rank_change_text(old_rank: Optional[int], new_rank: Optional[int]) -> str:
    if old_rank is None or new_rank is None or pd.isna(new_rank):
        return "—"
    diff = int(old_rank) - int(new_rank)
    if diff > 0:
        return f"▲ +{diff} Plätze"
    if diff < 0:
        return f"▼ {diff} Plätze"
    return "→ unverändert"


def load_json(path: Path, default):
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return default
    return default


def save_json(path: Path, data) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def portfolio_key(market: str, ticker: str) -> str:
    return f"{market}|{ticker}"


def clean_company_name(name: str, ticker: str) -> str:
    if not name or str(name).lower() in ["nan", "none"]:
        return ticker
    return str(name).strip()


# ============================================================
# INDEX-LISTEN
# ============================================================

def read_html_tables_with_browser_headers(url: str) -> List[pd.DataFrame]:
    """
    Liest HTML-Tabellen robuster als pd.read_html(url).
    Windows/Pandas bekommt bei Wikipedia manchmal HTTP 403, weil kein Browser-User-Agent
    gesendet wird. Deshalb holen wir die Seite zuerst mit requests und Browser-Headern.
    """
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7",
    }
    r = requests.get(url, headers=headers, timeout=30)
    r.raise_for_status()
    return pd.read_html(StringIO(r.text))


@st.cache_data(ttl=24 * 60 * 60, show_spinner=False)
def load_sp500_symbols() -> pd.DataFrame:
    url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    tables = read_html_tables_with_browser_headers(url)
    df = tables[0].copy()
    out = pd.DataFrame({
        "ticker": df["Symbol"].map(normalize_yahoo_symbol),
        "name": df["Security"].astype(str),
        "sector": df.get("GICS Sector", pd.Series([""] * len(df))).astype(str),
        "isin": "",
        "source": "S&P 500 / Wikipedia",
    })
    return out.drop_duplicates("ticker").reset_index(drop=True)


@st.cache_data(ttl=24 * 60 * 60, show_spinner=False)
def load_nasdaq100_symbols() -> pd.DataFrame:
    url = "https://en.wikipedia.org/wiki/Nasdaq-100"
    tables = read_html_tables_with_browser_headers(url)
    selected = None
    for t in tables:
        cols = [str(c).lower() for c in t.columns]
        if any("ticker" in c for c in cols) and any("company" in c for c in cols):
            selected = t.copy()
            break
    if selected is None:
        raise RuntimeError("Nasdaq-100-Tabelle konnte nicht gelesen werden.")

    ticker_col = [c for c in selected.columns if "ticker" in str(c).lower()][0]
    company_col = [c for c in selected.columns if "company" in str(c).lower()][0]
    sector_col = None
    for c in selected.columns:
        if "sector" in str(c).lower():
            sector_col = c
            break

    out = pd.DataFrame({
        "ticker": selected[ticker_col].map(normalize_yahoo_symbol),
        "name": selected[company_col].astype(str),
        "sector": selected[sector_col].astype(str) if sector_col else "",
        "isin": "",
        "source": "Nasdaq-100 / Wikipedia",
    })
    return out.drop_duplicates("ticker").reset_index(drop=True)

def _download_ishares_csv(url: str) -> Optional[pd.DataFrame]:
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "text/csv,application/csv,text/plain,*/*",
    }
    try:
        r = requests.get(url, headers=headers, timeout=20)
        if r.status_code != 200 or len(r.text) < 1000:
            return None

        # iShares CSV enthält oft Kopfzeilen vor der eigentlichen Tabelle.
        lines = r.text.splitlines()
        header_idx = None
        for i, line in enumerate(lines[:80]):
            lower = line.lower()
            if "ticker" in lower and ("name" in lower or "holding" in lower):
                header_idx = i
                break
        if header_idx is None:
            return None

        from io import StringIO
        csv_text = "\n".join(lines[header_idx:])
        df = pd.read_csv(StringIO(csv_text))
        return df
    except Exception:
        return None


@st.cache_data(ttl=24 * 60 * 60, show_spinner=False)
def load_emerging_markets_symbols() -> pd.DataFrame:
    """
    Kostenloser Proxy: große iShares MSCI EM ETF Holdings.
    Fallback: breit bekannte EM ADRs/US-listings, falls Download blockiert ist.
    """
    possible_urls = [
        # EEM iShares MSCI Emerging Markets ETF holdings CSV
        "https://www.ishares.com/us/products/239637/ishares-msci-emerging-markets-etf/1467271812596.ajax?fileType=csv&fileName=EEM_holdings&dataType=fund",
        # IEMG iShares Core MSCI Emerging Markets ETF holdings CSV
        "https://www.ishares.com/us/products/244050/ishares-core-msci-emerging-markets-etf/1467271812596.ajax?fileType=csv&fileName=IEMG_holdings&dataType=fund",
    ]

    raw = None
    for url in possible_urls:
        raw = _download_ishares_csv(url)
        if raw is not None and len(raw) > 50:
            break

    rows = []
    if raw is not None:
        cols = {str(c).lower(): c for c in raw.columns}
        ticker_col = None
        name_col = None
        sector_col = None
        isin_col = None
        exchange_col = None

        for c in raw.columns:
            lc = str(c).lower()
            if lc == "ticker":
                ticker_col = c
            elif "name" == lc or "holding name" in lc or lc == "name":
                name_col = c
            elif "sector" in lc:
                sector_col = c
            elif "isin" in lc:
                isin_col = c
            elif "exchange" in lc or "location" in lc:
                exchange_col = c

        if ticker_col and name_col:
            for _, row in raw.iterrows():
                sym = str(row.get(ticker_col, "")).strip()
                name = str(row.get(name_col, "")).strip()
                isin = str(row.get(isin_col, "")).strip() if isin_col else ""
                sector = str(row.get(sector_col, "")).strip() if sector_col else ""
                if not sym or sym in ["-", "nan", "Cash and/or Derivatives"]:
                    continue

                # Viele EM-Ticker benötigen Börsensuffixe. Für einige Märkte häufige Heuristik:
                yahoo = convert_em_symbol_to_yahoo(sym, name, isin)
                if yahoo:
                    rows.append({
                        "ticker": yahoo,
                        "name": name,
                        "sector": sector,
                        "isin": isin if isin.lower() != "nan" else "",
                        "source": "MSCI EM ETF Holdings Proxy",
                    })

    if len(rows) < 25:
        # Fallback mit liquiden ADRs / US-gehandelten EM-Werten
        fallback = [
            ("TSM", "Taiwan Semiconductor Manufacturing", "Technology", "US8740391003"),
            ("BABA", "Alibaba Group Holding", "Consumer Discretionary", "US01609W1027"),
            ("PDD", "PDD Holdings", "Consumer Discretionary", "US7223041028"),
            ("JD", "JD.com", "Consumer Discretionary", "US47215P1066"),
            ("BIDU", "Baidu", "Communication Services", "US0567521085"),
            ("NIO", "NIO", "Consumer Discretionary", "US62914V1061"),
            ("LI", "Li Auto", "Consumer Discretionary", "US50202M1027"),
            ("XPEV", "XPeng", "Consumer Discretionary", "US98422D1054"),
            ("INFY", "Infosys", "Information Technology", "US4567881085"),
            ("WIT", "Wipro", "Information Technology", "US97651M1099"),
            ("HDB", "HDFC Bank", "Financials", "US40415F1012"),
            ("IBN", "ICICI Bank", "Financials", "US45104G1040"),
            ("RDY", "Dr. Reddy's Laboratories", "Health Care", "US2561352038"),
            ("VALE", "Vale", "Materials", "US91912E1055"),
            ("PBR", "Petrobras", "Energy", "US71654V4086"),
            ("ITUB", "Itaú Unibanco", "Financials", "US4655621062"),
            ("BBD", "Banco Bradesco", "Financials", "US0594603039"),
            ("AMX", "América Móvil", "Communication Services", "US02364W1053"),
            ("FMX", "Fomento Económico Mexicano", "Consumer Staples", "US3444191064"),
            ("MELI", "MercadoLibre", "Consumer Discretionary", "US58733R1023"),
            ("GLOB", "Globant", "Information Technology", "LU0974299876"),
            ("SE", "Sea Limited", "Communication Services", "US81141R1005"),
            ("GRAB", "Grab Holdings", "Industrials", "KYG4124C1096"),
            ("CPNG", "Coupang", "Consumer Discretionary", "US22266T1097"),
            ("YUMC", "Yum China", "Consumer Discretionary", "US98850P1093"),
        ]
        return pd.DataFrame(fallback, columns=["ticker", "name", "sector", "isin"]).assign(
            source="EM Fallback ADR/US listings"
        )

    out = pd.DataFrame(rows)
    out = out.drop_duplicates("ticker").reset_index(drop=True)
    return out


def convert_em_symbol_to_yahoo(sym: str, name: str, isin: str = "") -> Optional[str]:
    """
    Heuristik für ETF-Holdings.
    Nicht perfekt: internationale Börsensuffixe sind nicht immer eindeutig.
    Ziel: möglichst viele Titel über Yahoo Finance downloadbar machen.
    """
    s = str(sym).strip().upper()
    if not s or s in ["-", "NAN"]:
        return None

    # Bereits US/ADR-artige Ticker
    if "." not in s and " " not in s and len(s) <= 5 and s.isalnum():
        return s

    # Hongkong oft 4-5 stellige Nummer, Yahoo: 0700.HK
    if s.isdigit() and len(s) <= 5:
        return s.zfill(4) + ".HK"

    # Taiwan: 2330 -> 2330.TW
    if s.isdigit() and len(s) == 4:
        return s + ".TW"

    # Südkorea: 005930 -> 005930.KS
    if s.isdigit() and len(s) == 6:
        return s + ".KS"

    # Manche CSV-Symbole enthalten Leerzeichen oder Länderkürzel
    first = s.split()[0].replace("/", "-")
    first = first.replace(".", "-")
    if first.isdigit() and len(first) <= 5:
        return first.zfill(4) + ".HK"
    if len(first) >= 1:
        return first
    return None


@st.cache_data(ttl=24 * 60 * 60, show_spinner=False)
def load_universe(market: str) -> pd.DataFrame:
    if market == "S&P 500":
        return load_sp500_symbols()
    if market == "Nasdaq 100":
        return load_nasdaq100_symbols()
    if market == "Emerging Markets":
        return load_emerging_markets_symbols()
    raise ValueError("Unbekannter Markt")


# ============================================================
# DATEN & RSL-BERECHNUNG
# ============================================================

@st.cache_data(ttl=20 * 60, show_spinner=False)
def download_weekly_prices(tickers: Tuple[str, ...]) -> pd.DataFrame:
    if not tickers:
        return pd.DataFrame()

    all_frames = []
    tickers_list = list(tickers)
    for i in range(0, len(tickers_list), BATCH_SIZE):
        batch = tickers_list[i:i + BATCH_SIZE]
        try:
            data = yf.download(
                tickers=batch,
                period="18mo",
                interval="1wk",
                auto_adjust=True,
                group_by="ticker",
                threads=True,
                progress=False,
                timeout=20,
            )
            if data is None or data.empty:
                continue

            # Bei nur einem Ticker ist die Struktur anders.
            if len(batch) == 1:
                close = data[["Close"]].rename(columns={"Close": batch[0]})
            else:
                close_cols = {}
                for t in batch:
                    try:
                        close_cols[t] = data[t]["Close"]
                    except Exception:
                        pass
                close = pd.DataFrame(close_cols)

            all_frames.append(close)
        except Exception:
            continue

    if not all_frames:
        return pd.DataFrame()

    prices = pd.concat(all_frames, axis=1)
    prices = prices.loc[:, ~prices.columns.duplicated()]
    prices = prices.dropna(axis=1, how="all")
    return prices


def calculate_rsl(prices: pd.DataFrame, universe: pd.DataFrame, market: str) -> pd.DataFrame:
    if prices.empty:
        return pd.DataFrame()

    records = []
    for ticker in prices.columns:
        series = prices[ticker].dropna()
        if len(series) < RSL_WEEKS + 1:
            continue

        last_close = safe_float(series.iloc[-1])
        avg_26 = safe_float(series.tail(RSL_WEEKS).mean())
        prev_close = safe_float(series.iloc[-2]) if len(series) >= 2 else np.nan
        change_1w = ((last_close / prev_close) - 1) * 100 if prev_close and not pd.isna(prev_close) else np.nan

        if pd.isna(last_close) or pd.isna(avg_26) or avg_26 == 0:
            continue

        rsl = last_close / avg_26
        meta = universe[universe["ticker"] == ticker]
        if meta.empty:
            name, sector, isin, source = ticker, "", "", ""
        else:
            row = meta.iloc[0]
            name = clean_company_name(row.get("name", ticker), ticker)
            sector = str(row.get("sector", ""))
            isin = str(row.get("isin", ""))
            source = str(row.get("source", ""))

        records.append({
            "Markt": market,
            "Rang": None,
            "Ticker": ticker,
            "Name": name,
            "Sektor": sector if sector.lower() != "nan" else "",
            "Kurs": round(last_close, 2),
            f"Ø {RSL_WEEKS} Wochen": round(avg_26, 2),
            "RSL": round(rsl, 4),
            "1W %": round(change_1w, 2) if not pd.isna(change_1w) else np.nan,
            "WKN": get_wkn(ticker),
            "ISIN": isin if isin.lower() != "nan" else "",
            "Quelle": source,
        })

    df = pd.DataFrame(records)
    if df.empty:
        return df

    df = df.sort_values("RSL", ascending=False).reset_index(drop=True)
    df["Rang"] = np.arange(1, len(df) + 1)

    total = len(df)
    ampeln = [traffic_light(row["RSL"], int(row["Rang"]), total) for _, row in df.iterrows()]
    df["Ampel"] = [a[0] for a in ampeln]
    df["Signal"] = [a[1] for a in ampeln]
    df["Handlung"] = [a[2] for a in ampeln]

    # Links
    df["WKN Link"] = df.apply(lambda r: wkn_link(r["WKN"], r["Ticker"]), axis=1)
    df["Yahoo Link"] = df["Ticker"].map(yahoo_link)
    return df


@st.cache_data(ttl=20 * 60, show_spinner=False)
def scan_market(market: str) -> pd.DataFrame:
    universe = load_universe(market)
    tickers = tuple(universe["ticker"].dropna().astype(str).unique().tolist())
    prices = download_weekly_prices(tickers)
    return calculate_rsl(prices, universe, market)


def clear_data_cache():
    st.cache_data.clear()


# ============================================================
# PORTFOLIO
# ============================================================

def load_portfolio() -> Dict:
    return load_json(PORTFOLIO_FILE, {})


def save_portfolio(portfolio: Dict) -> None:
    save_json(PORTFOLIO_FILE, portfolio)


def add_to_portfolio(market: str, row: pd.Series) -> None:
    portfolio = load_portfolio()
    key = portfolio_key(market, row["Ticker"])
    portfolio[key] = {
        "market": market,
        "ticker": row["Ticker"],
        "name": row["Name"],
        "wkn": row.get("WKN", "—"),
        "isin": row.get("ISIN", ""),
        "buy_date": str(date.today()),
        "initial_rank": int(row["Rang"]),
        "initial_rsl": float(row["RSL"]),
        "added_at": datetime.now().isoformat(timespec="seconds"),
    }
    save_portfolio(portfolio)


def add_top5_to_portfolio(market: str, df: pd.DataFrame) -> None:
    if df.empty:
        return
    for _, row in df.head(5).iterrows():
        add_to_portfolio(market, row)


def remove_from_portfolio(key: str) -> None:
    portfolio = load_portfolio()
    if key in portfolio:
        del portfolio[key]
    save_portfolio(portfolio)


def portfolio_dataframe(current_scans: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    portfolio = load_portfolio()
    rows = []

    for key, item in portfolio.items():
        market = item.get("market", "")
        ticker = item.get("ticker", "")
        current = current_scans.get(market, pd.DataFrame())
        match = current[current["Ticker"] == ticker] if not current.empty else pd.DataFrame()

        if match.empty:
            current_rank = None
            current_rsl = np.nan
            amp, sig, action = "⚪", "Keine Daten", "Aktualisiere den passenden Markt oder prüfe den Ticker."
            price = np.nan
        else:
            r = match.iloc[0]
            current_rank = int(r["Rang"])
            current_rsl = float(r["RSL"])
            amp, sig, action = r["Ampel"], r["Signal"], r["Handlung"]
            price = r["Kurs"]

        initial_rank = item.get("initial_rank")
        rows.append({
            "Key": key,
            "Markt": market,
            "Ticker": ticker,
            "Name": item.get("name", ticker),
            "WKN": item.get("wkn", "—"),
            "ISIN": item.get("isin", ""),
            "Erwerbsdatum": item.get("buy_date", ""),
            "Start-Rang": initial_rank,
            "Aktueller Rang": current_rank if current_rank is not None else "—",
            "Rangveränderung": rank_change_text(initial_rank, current_rank),
            "Start-RSL": round(float(item.get("initial_rsl", np.nan)), 4) if item.get("initial_rsl") is not None else np.nan,
            "Aktueller RSL": round(current_rsl, 4) if not pd.isna(current_rsl) else np.nan,
            "Kurs": price,
            "Ampel": amp,
            "Signal": sig,
            "Handlung": action,
            "WKN Link": wkn_link(item.get("wkn", "—"), ticker),
            "Yahoo Link": yahoo_link(ticker),
        })

    return pd.DataFrame(rows)


# ============================================================
# UI-KOMPONENTEN
# ============================================================

def top_bar():
    col1, col2 = st.columns([2, 1])
    with col1:
        st.markdown(f"# 📈 {APP_TITLE}")
        st.markdown(
            f"<div class='small'>RSL = aktueller Wochenschlusskurs / Durchschnitt der letzten "
            f"{RSL_WEEKS} Wochenschlusskurse · Letzter App-Lauf: {now_str()}</div>",
            unsafe_allow_html=True,
        )
    with col2:
        if st.button("🔄 Werte jetzt aktualisieren"):
            clear_data_cache()
            st.rerun()


def auto_refresh_control():
    with st.expander("⚙️ Automatische Aktualisierung", expanded=False):
        enabled = st.toggle("Automatische Aktualisierung aktiv", value=True)
        minutes = st.slider("Intervall in Minuten", 5, 240, DEFAULT_REFRESH_MINUTES, step=5)
        st.caption("Die App lädt sich im Browser automatisch neu. Yahoo-Daten werden zusätzlich gecacht, um Drosselung zu vermeiden.")

    if enabled:
        # JavaScript-Refresh der Browserseite.
        ms = int(minutes * 60 * 1000)
        components.html(
            f"""
            <script>
            setTimeout(function() {{
                window.parent.location.reload();
            }}, {ms});
            </script>
            """,
            height=0,
        )


def render_kpi_card(label: str, value: str, delta: str = ""):
    delta_html = f"<div class='kpi-delta'>{delta}</div>" if delta else ""
    st.markdown(
        f"""
        <div class='kpi-card'>
            <div class='kpi-label'>{label}</div>
            <div class='kpi-value'>{value}</div>
            {delta_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_kpi_cards(df: pd.DataFrame):
    if df.empty:
        return
    top = df.iloc[0]
    green = int((df["Ampel"] == "🟢").sum())
    yellow = int((df["Ampel"] == "🟡").sum())
    red = int((df["Ampel"] == "🔴").sum())

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        render_kpi_card("Gescannt", f"{len(df)} Werte")
    with c2:
        render_kpi_card("Stärkster Wert", f"{top['Ticker']}", f"↑ RSL {top['RSL']:.2f}")
    with c3:
        render_kpi_card("Grün / Gelb / Rot", f"{green} / {yellow} / {red}")
    with c4:
        render_kpi_card("Top-5 Ø RSL", f"{df.head(5)['RSL'].mean():.2f}")


def render_stock_cards(df: pd.DataFrame, market: str, limit: int = 10):
    st.markdown("### 🏆 Rangliste")
    top_df = df.head(limit).copy()
    for _, row in top_df.iterrows():
        badge_class = "badge-green" if row["Ampel"] == "🟢" else "badge-yellow" if row["Ampel"] == "🟡" else "badge-red"
        wkn = row["WKN"] if row["WKN"] != "—" else "WKN nicht frei verfügbar"
        wkn_url = row["WKN Link"]
        yahoo_url = row["Yahoo Link"]

        c1, c2 = st.columns([0.22, 0.78])
        with c1:
            st.markdown(f"<div class='card'><div class='rank'>#{int(row['Rang'])}</div><div class='small'>RSL {row['RSL']:.2f}</div></div>", unsafe_allow_html=True)
        with c2:
            st.markdown(
                f"""
                <div class='card'>
                    <div class='card-title'>{row['Ampel']} {row['Name']} <span class='small'>({row['Ticker']})</span></div>
                    <div class='card-sub'>{row.get('Sektor','')} · Kurs: {row['Kurs']} · 1W: {row['1W %']}%</div>
                    <span class='badge {badge_class}'>{row['Signal']}</span>
                    <div style='margin-top:8px'>{row['Handlung']}</div>
                    <div class='small' style='margin-top:8px'>
                        WKN: <a href='{wkn_url}' target='_blank'>{wkn}</a> ·
                        <a href='{yahoo_url}' target='_blank'>Yahoo Finance</a>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )


def render_screener_table(df: pd.DataFrame):
    show = df[[
        "Rang", "Ampel", "Ticker", "Name", "WKN", "ISIN", "Sektor",
        "Kurs", f"Ø {RSL_WEEKS} Wochen", "RSL", "1W %", "Signal", "Handlung",
        "WKN Link", "Yahoo Link"
    ]].copy()

    st.dataframe(
        show,
        use_container_width=True,
        hide_index=True,
        column_config={
            "WKN Link": st.column_config.LinkColumn("WKN Link", display_text="öffnen"),
            "Yahoo Link": st.column_config.LinkColumn("Yahoo", display_text="Chart"),
            "RSL": st.column_config.NumberColumn("RSL", format="%.4f"),
            "1W %": st.column_config.NumberColumn("1W %", format="%.2f"),
        },
    )


def render_portfolio(current_scans: Dict[str, pd.DataFrame]):
    st.markdown("## 💼 Portfolio Manager")
    st.caption("Speichert deine ausgewählten Werte lokal in der Datei `rsl_portfolio.json` im gleichen Ordner wie diese App.")

    pdf = portfolio_dataframe(current_scans)
    if pdf.empty:
        st.info("Noch keine Werte gespeichert. Gehe in den Screener und speichere die Top 5 eines Marktes.")
        return

    c1, c2, c3 = st.columns(3)
    green = int((pdf["Ampel"] == "🟢").sum())
    red = int((pdf["Ampel"] == "🔴").sum())
    with c1:
        render_kpi_card("Positionen", str(len(pdf)))
    with c2:
        render_kpi_card("Grüne Signale", str(green))
    with c3:
        render_kpi_card("Rote Signale", str(red))

    for _, row in pdf.iterrows():
        badge_class = "badge-green" if row["Ampel"] == "🟢" else "badge-yellow" if row["Ampel"] == "🟡" else "badge-red"
        st.markdown(
            f"""
            <div class='card'>
                <div class='card-title'>{row['Ampel']} {row['Name']} <span class='small'>({row['Ticker']})</span></div>
                <div class='card-sub'>
                    Markt: {row['Markt']} · Erwerbsdatum: {row['Erwerbsdatum']} ·
                    Start-Rang: {row['Start-Rang']} · Aktuell: {row['Aktueller Rang']} · {row['Rangveränderung']}
                </div>
                <span class='badge {badge_class}'>{row['Signal']}</span>
                <div style='margin-top:8px'>{row['Handlung']}</div>
                <div class='small' style='margin-top:8px'>
                    Start-RSL: {row['Start-RSL']} · Aktueller RSL: {row['Aktueller RSL']} · Kurs: {row['Kurs']}<br>
                    WKN: <a href='{row['WKN Link']}' target='_blank'>{row['WKN'] if row['WKN'] != '—' else 'WKN nicht frei verfügbar'}</a> ·
                    <a href='{row['Yahoo Link']}' target='_blank'>Yahoo Finance</a>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button(f"🗑️ {row['Ticker']} aus Portfolio entfernen", key=f"remove_{row['Key']}"):
            remove_from_portfolio(row["Key"])
            st.rerun()

    st.markdown("### Portfolio-Tabelle")
    st.dataframe(
        pdf.drop(columns=["Key"]),
        use_container_width=True,
        hide_index=True,
        column_config={
            "WKN Link": st.column_config.LinkColumn("WKN Link", display_text="öffnen"),
            "Yahoo Link": st.column_config.LinkColumn("Yahoo", display_text="Chart"),
        },
    )

    csv = pdf.drop(columns=["Key"]).to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        "⬇️ Portfolio als CSV exportieren",
        data=csv,
        file_name=f"rsl_portfolio_{date.today().isoformat()}.csv",
        mime="text/csv",
    )


def intro_box():
    st.markdown(
        f"""
        <div class='card'>
            <div class='card-title'>Methode</div>
            <div class='small'>
                Diese App berechnet RSL mit {RSL_WEEKS} Wochen:
                aktueller Wochenschlusskurs geteilt durch den Durchschnitt der letzten {RSL_WEEKS} Wochenschlusskurse.
                Höherer RSL = stärkere relative Trendstärke. Die Ampel ist eine einfache Regel, keine Anlageberatung.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ============================================================
# MAIN APP
# ============================================================

def main():
    top_bar()
    auto_refresh_control()
    intro_box()

    tab1, tab2, tab3 = st.tabs(["🔎 Screener", "💼 Portfolio Manager", "ℹ️ Hilfe"])

    current_scans: Dict[str, pd.DataFrame] = {}

    with tab1:
        market = st.selectbox(
            "Markt auswählen",
            ["S&P 500", "Nasdaq 100", "Emerging Markets"],
            index=0,
        )

        if market == "Emerging Markets":
            st.warning(EMERGING_MARKETS_PROXY_NOTE)

        top_n_cards = st.slider("Wie viele Top-Werte als Kacheln anzeigen?", 5, 30, 10, step=5)

        try:
            with st.spinner(f"{market} wird gescannt. Das kann bei großen Märkten etwas dauern..."):
                df = scan_market(market)
        except Exception as e:
            df = pd.DataFrame()
            st.error("Der Scan konnte nicht abgeschlossen werden. Bitte oben auf Aktualisieren klicken oder später erneut versuchen.")
            st.caption(f"Technische Meldung: {type(e).__name__}: {e}")

        current_scans[market] = df

        if df.empty:
            st.warning(
                "Keine Daten erhalten. Prüfe Internetverbindung/Yahoo-Finance-Verfügbarkeit. "
                "Wenn gerade viele Werte geladen werden, kann Yahoo vorübergehend drosseln."
            )
        else:
            render_kpi_cards(df)

            c1, c2 = st.columns(2)
            with c1:
                if st.button(f"⭐ Top 5 aus {market} ins Portfolio speichern"):
                    add_top5_to_portfolio(market, df)
                    st.success("Top 5 wurden im Portfolio gespeichert/aktualisiert.")
            with c2:
                csv = df.to_csv(index=False).encode("utf-8-sig")
                st.download_button(
                    "⬇️ Screener als CSV exportieren",
                    data=csv,
                    file_name=f"rsl_screener_{market.replace(' ', '_')}_{date.today().isoformat()}.csv",
                    mime="text/csv",
                )

            render_stock_cards(df, market, top_n_cards)

            st.markdown("### Komplette Tabelle")
            search = st.text_input("Suche nach Name, Ticker, WKN oder ISIN", "")
            table_df = df.copy()
            if search:
                s = search.lower().strip()
                mask = (
                    table_df["Ticker"].astype(str).str.lower().str.contains(s, na=False) |
                    table_df["Name"].astype(str).str.lower().str.contains(s, na=False) |
                    table_df["WKN"].astype(str).str.lower().str.contains(s, na=False) |
                    table_df["ISIN"].astype(str).str.lower().str.contains(s, na=False)
                )
                table_df = table_df[mask]

            render_screener_table(table_df)

            st.markdown("### Einzelwert ins Portfolio speichern")
            options = [f"#{int(r.Rang)} {r.Ticker} · {r.Name}" for r in df.itertuples()]
            selected = st.selectbox("Wert auswählen", options)
            if st.button("➕ Ausgewählten Wert speichern"):
                ticker = selected.split(" ")[1]
                row = df[df["Ticker"] == ticker].iloc[0]
                add_to_portfolio(market, row)
                st.success(f"{ticker} wurde gespeichert.")

    with tab2:
        # Für Portfolio alle Märkte aktualisieren, aber nur bei Bedarf.
        portfolio = load_portfolio()
        needed_markets = sorted(set(item.get("market", "") for item in portfolio.values() if item.get("market")))
        for m in needed_markets:
            if m not in current_scans:
                with st.spinner(f"Aktualisiere Portfolio-Daten für {m}..."):
                    current_scans[m] = scan_market(m)

        render_portfolio(current_scans)

    with tab3:
        st.markdown(
            f"""
            ### Ampelregeln

            **🟢 Grün:** RSL ≥ 1,08 und Aktie liegt in den besten 20 % des gewählten Marktes.  
            **🟡 Gelb:** RSL ≥ 1,00 und Aktie liegt mindestens in der oberen Hälfte.  
            **🔴 Rot:** RSL < 1,00 oder Aktie ist relativ schwach.

            ### Handlungsempfehlungen

            Die Empfehlungen sind regelbasiert:
            - **Kaufen/Halten:** nur bei grünem Signal, idealerweise mit Positionsgröße und Stop.
            - **Beobachten/Halten:** gelbes Signal; kein aggressiver Neueinstieg.
            - **Meiden/Verkauf prüfen:** rotes Signal; Momentum ist zu schwach.

            ### WKNs

            WKNs sind bei kostenlosen Kursdaten nicht zuverlässig vollständig verfügbar.  
            Die App enthält eine manuelle WKN-Tabelle für bekannte Werte. Du kannst sie oben in der Datei im Bereich `MANUAL_WKN` ergänzen.

            ### Emerging Markets

            {EMERGING_MARKETS_PROXY_NOTE}

            ### Installation

            ```bash
            pip install streamlit yfinance pandas numpy requests beautifulsoup4 lxml plotly
            python -m streamlit run rsl_scanner_app.py
            ```

            ### Haftungsausschluss

            Diese App ist keine Finanzberatung. Prüfe Signale immer selbst und beachte Risiko, Steuern, Gebühren und Liquidität.
            """
        )


if __name__ == "__main__":
    main()
