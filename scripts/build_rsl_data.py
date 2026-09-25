import json, time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import requests
import yfinance as yf

OUT = Path("docs/data.json")
OUT.parent.mkdir(parents=True, exist_ok=True)
HEADERS = {"User-Agent": "Mozilla/5.0"}

def norm_symbol(s):
    return str(s).strip().upper().replace(".", "-")

def pct(a, b):
    try:
        if b is None or b == 0 or pd.isna(a) or pd.isna(b):
            return None
        return round((float(a) / float(b) - 1) * 100, 2)
    except Exception:
        return None

def rsl_days(s, n=26):
    s = s.dropna()
    if len(s) < n:
        return None
    avg = s.tail(n).mean()
    return None if not avg or pd.isna(avg) else float(s.iloc[-1] / avg)

def rsl_weeks(s, n=26):
    w = s.dropna().resample("W-FRI").last().dropna()
    if len(w) < n:
        return None
    avg = w.tail(n).mean()
    return None if not avg or pd.isna(avg) else float(w.iloc[-1] / avg)

def rsi14(s):
    s = s.dropna()
    if len(s) < 20:
        return None
    d = s.diff()
    gain = d.clip(lower=0).ewm(alpha=1/14, adjust=False).mean()
    loss = (-d.clip(upper=0)).ewm(alpha=1/14, adjust=False).mean()
    rs = gain / loss.replace(0, np.nan)
    v = 100 - (100 / (1 + rs))
    return round(float(v.iloc[-1]), 1) if not pd.isna(v.iloc[-1]) else None

def macd_values(s):
    s = s.dropna()
    if len(s) < 35:
        return None, None, None
    ema12 = s.ewm(span=12, adjust=False).mean()
    ema26 = s.ewm(span=26, adjust=False).mean()
    macd = ema12 - ema26
    signal = macd.ewm(span=9, adjust=False).mean()
    hist = macd - signal
    return round(float(macd.iloc[-1]), 2), round(float(signal.iloc[-1]), 2), round(float(hist.iloc[-1]), 2)

def trend_quality(s):
    s = s.dropna().tail(63)
    if len(s) < 30:
        return None
    y = np.log(s.to_numpy(dtype=float))
    x = np.arange(len(y), dtype=float)
    slope, intercept = np.polyfit(x, y, 1)
    fitted = slope * x + intercept
    ss_res = float(np.sum((y - fitted) ** 2))
    ss_tot = float(np.sum((y - np.mean(y)) ** 2))
    r2 = 0.0 if ss_tot == 0 else max(0.0, min(1.0, 1 - ss_res / ss_tot))
    return round((1 if slope >= 0 else -1) * r2, 2)

def cross_signal(s):
    s = s.dropna()
    if len(s) < 205:
        return ""
    ma50 = s.rolling(50).mean()
    ma200 = s.rolling(200).mean()
    diff = (ma50 - ma200).dropna().tail(7)
    if len(diff) < 2:
        return ""
    for i in range(1, len(diff)):
        if diff.iloc[i-1] <= 0 and diff.iloc[i] > 0:
            return "golden"
        if diff.iloc[i-1] >= 0 and diff.iloc[i] < 0:
            return "death"
    return ""

def read_tables(url):
    r = requests.get(url, headers=HEADERS, timeout=30)
    r.raise_for_status()
    return pd.read_html(r.text)

def sp500():
    t = read_tables("https://en.wikipedia.org/wiki/List_of_S%26P_500_companies")[0]
    return pd.DataFrame({"symbol": t["Symbol"].map(norm_symbol), "name": t["Security"].astype(str), "sector": t["GICS Sector"].astype(str)})

def nasdaq100():
    for t in read_tables("https://en.wikipedia.org/wiki/Nasdaq-100"):
        tc = next((c for c in t.columns if "ticker" in str(c).lower()), None)
        nc = next((c for c in t.columns if "company" in str(c).lower()), None)
        if tc is not None and nc is not None:
            sc = next((c for c in t.columns if "sector" in str(c).lower()), None)
            return pd.DataFrame({"symbol": t[tc].map(norm_symbol), "name": t[nc].astype(str), "sector": t[sc].astype(str) if sc is not None else ""})
    raise RuntimeError("NASDAQ-100 Tabelle nicht gefunden")

def dow():
    for t in read_tables("https://en.wikipedia.org/wiki/Dow_Jones_Industrial_Average"):
        tc = next((c for c in t.columns if "symbol" in str(c).lower()), None)
        nc = next((c for c in t.columns if "company" in str(c).lower()), None)
        if tc is not None and nc is not None and len(t) >= 25:
            sc = next((c for c in t.columns if "industry" in str(c).lower() or "sector" in str(c).lower()), None)
            return pd.DataFrame({"symbol": t[tc].map(norm_symbol), "name": t[nc].astype(str), "sector": t[sc].astype(str) if sc is not None else ""})
    raise RuntimeError("Dow Tabelle nicht gefunden")

def dax():
    for t in read_tables("https://en.wikipedia.org/wiki/DAX"):
        tc = next((c for c in t.columns if "ticker" in str(c).lower()), None)
        nc = next((c for c in t.columns if "company" in str(c).lower()), None)
        if tc is not None and nc is not None and len(t) >= 30:
            raw = t[tc].astype(str)
            sy = raw.map(lambda x: norm_symbol(x) if "." in x else norm_symbol(x) + ".DE")
            sc = next((c for c in t.columns if "industry" in str(c).lower() or "sector" in str(c).lower()), None)
            return pd.DataFrame({"symbol": sy, "name": t[nc].astype(str), "sector": t[sc].astype(str) if sc is not None else ""})
    raise RuntimeError("DAX Tabelle nicht gefunden")

def crypto():
    rows = [
        ("BTC-USD","Bitcoin","Krypto"),("ETH-USD","Ethereum","Krypto"),("SOL-USD","Solana","Krypto"),
        ("XRP-USD","XRP","Krypto"),("BNB-USD","BNB","Krypto"),("ADA-USD","Cardano","Krypto"),
        ("DOGE-USD","Dogecoin","Krypto"),("AVAX-USD","Avalanche","Krypto"),("LINK-USD","Chainlink","Krypto"),
        ("DOT-USD","Polkadot","Krypto")
    ]
    return pd.DataFrame(rows, columns=["symbol","name","sector"])

LOADERS = {"S&P 500": sp500, "NASDAQ 100": nasdaq100, "Dow Jones": dow, "DAX": dax, "Krypto": crypto}

def download_prices(symbols):
    parts = []
    for i in range(0, len(symbols), 80):
        batch = symbols[i:i+80]
        d = yf.download(batch, period="2y", interval="1d", auto_adjust=False, progress=False, group_by="column", threads=True)
        if isinstance(d.columns, pd.MultiIndex):
            close = d["Close"]
        else:
            close = d[["Close"]].rename(columns={"Close": batch[0]})
        parts.append(close)
        time.sleep(0.25)
    return pd.concat(parts, axis=1) if parts else pd.DataFrame()

def build_index(meta):
    meta = meta.drop_duplicates("symbol").reset_index(drop=True)
    prices = download_prices(meta["symbol"].tolist())
    rec = []
    for _, m in meta.iterrows():
        s = m["symbol"]
        if s not in prices.columns:
            continue
        d = prices[s].dropna()
        if len(d) < 205:
            continue
        d_old = d.iloc[:-5] if len(d) > 210 else d.iloc[:-1]
        r26d, r26w = rsl_days(d), rsl_weeks(d)
        o26d, o26w = rsl_days(d_old), rsl_weeks(d_old)
        if r26d is None or r26w is None or o26d is None or o26w is None:
            continue
        macd, macd_signal, macd_hist = macd_values(d)
        rec.append({
            "symbol": s,
            "name": str(m["name"]),
            "sector": str(m.get("sector","")),
            "price": round(float(d.iloc[-1]), 2),
            "rsl26d": round(r26d, 4),
            "rsl26w": round(r26w, 4),
            "_old26d": round(o26d, 4),
            "_old26w": round(o26w, 4),
            "trendq": trend_quality(d),
            "rsi": rsi14(d),
            "macd": macd,
            "macd_signal": macd_signal,
            "macd_hist": macd_hist,
            "signal": "bullish" if macd is not None and macd_signal is not None and macd >= macd_signal else "bearish",
            "d1": pct(d.iloc[-1], d.iloc[-2]),
            "w1": pct(d.iloc[-1], d.iloc[-6]) if len(d) > 6 else None,
            "m1": pct(d.iloc[-1], d.iloc[-22]) if len(d) > 22 else None,
            "cross": cross_signal(d)
        })

    def assign_rank(key, outkey):
        for rank, x in enumerate(sorted(rec, key=lambda z: z[key], reverse=True), 1):
            x[outkey] = rank

    assign_rank("rsl26d","rank26d")
    assign_rank("rsl26w","rank26w")
    assign_rank("_old26d","oldrank26d")
    assign_rank("_old26w","oldrank26w")

    for x in rec:
        x["move26d"] = x["oldrank26d"] - x["rank26d"]
        x["move26w"] = x["oldrank26w"] - x["rank26w"]
        del x["_old26d"]
        del x["_old26w"]
    return rec

def main():
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": "Yahoo Finance Kursdaten; Indexlisten aus öffentlichen Quellen",
        "indexes": {},
        "errors": {}
    }
    for name, loader in LOADERS.items():
        try:
            print(f"Baue {name} ...", flush=True)
            payload["indexes"][name] = build_index(loader())
        except Exception as e:
            payload["errors"][name] = f"{type(e).__name__}: {e}"
    OUT.write_text(json.dumps(payload, ensure_ascii=False, separators=(",",":")), encoding="utf-8")
    print(f"Fertig: {OUT}")

if __name__ == "__main__":
    main()
