import json
import math
import os
import time
from datetime import datetime, timezone, time as dtime
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import yfinance as yf

ROOT = Path(__file__).resolve().parents[1]
RSL_DATA = ROOT / "docs" / "data.json"
OUT = ROOT / "docs" / "momentum-radar" / "data.json"
OUT.parent.mkdir(parents=True, exist_ok=True)

VIENNA = ZoneInfo("Europe/Vienna")
NEW_YORK = ZoneInfo("America/New_York")
BATCH_SIZE = 90
LOOKBACK = "5d"
INTERVAL = "15m"

SECTOR_ETFS = {
    "communication services": "XLC",
    "communications": "XLC",
    "consumer discretionary": "XLY",
    "consumer cyclical": "XLY",
    "consumer staples": "XLP",
    "consumer defensive": "XLP",
    "energy": "XLE",
    "financials": "XLF",
    "financial services": "XLF",
    "health care": "XLV",
    "healthcare": "XLV",
    "industrials": "XLI",
    "information technology": "XLK",
    "technology": "XLK",
    "materials": "XLB",
    "basic materials": "XLB",
    "real estate": "XLRE",
    "utilities": "XLU",
}


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def safe(v, default=None):
    try:
        if v is None or pd.isna(v) or math.isinf(float(v)):
            return default
        return float(v)
    except Exception:
        return default


def rounded(v, digits=2):
    v = safe(v)
    return None if v is None else round(v, digits)


def pct(new, old):
    new, old = safe(new), safe(old)
    if new is None or old in (None, 0):
        return None
    return (new / old - 1.0) * 100.0


def sector_etf(sector):
    s = str(sector or "").strip().lower()
    if not s:
        return "SPY"
    if s in SECTOR_ETFS:
        return SECTOR_ETFS[s]
    for key, etf in SECTOR_ETFS.items():
        if key in s or s in key:
            return etf
    return "SPY"


def load_universe():
    """Reuse the already-successful RSL scanner's current S&P 500 / NASDAQ 100 metadata."""
    if not RSL_DATA.exists():
        raise RuntimeError("RSL-Metadaten fehlen (docs/data.json)")
    payload = json.loads(RSL_DATA.read_text(encoding="utf-8"))
    indexes = payload.get("indexes", {})
    merged = {}
    for index_name in ("S&P 500", "NASDAQ 100"):
        rows = indexes.get(index_name, [])
        if len(rows) < 80:
            raise RuntimeError(f"{index_name}: zu wenige Komponenten in RSL-Metadaten")
        for row in rows:
            symbol = str(row.get("symbol", "")).strip().upper()
            if not symbol:
                continue
            item = merged.setdefault(symbol, {
                "symbol": symbol,
                "name": str(row.get("name") or symbol),
                "sector": str(row.get("sector") or ""),
                "indexes": [],
            })
            if index_name not in item["indexes"]:
                item["indexes"].append(index_name)
            if not item["sector"] and row.get("sector"):
                item["sector"] = str(row["sector"])
    return list(merged.values())


def normalize_download(df):
    if df is None or df.empty:
        return df
    idx = pd.DatetimeIndex(df.index)
    if idx.tz is None:
        idx = idx.tz_localize("UTC")
    df = df.copy()
    df.index = idx.tz_convert(NEW_YORK)
    return df


def extract_symbol_frame(data, symbol):
    if data is None or data.empty:
        return pd.DataFrame()
    fields = ["Open", "High", "Low", "Close", "Volume"]
    out = {}
    if isinstance(data.columns, pd.MultiIndex):
        lvl0 = set(map(str, data.columns.get_level_values(0)))
        lvl1 = set(map(str, data.columns.get_level_values(1)))
        for field in fields:
            try:
                if field in lvl0 and symbol in lvl1:
                    out[field] = data[(field, symbol)]
                elif symbol in lvl0 and field in lvl1:
                    out[field] = data[(symbol, field)]
            except Exception:
                pass
    else:
        if len(fields) and "Close" in data.columns:
            for field in fields:
                if field in data.columns:
                    out[field] = data[field]
    if "Close" not in out:
        return pd.DataFrame()
    frame = pd.DataFrame(out).dropna(subset=["Close"])
    if "Volume" not in frame:
        frame["Volume"] = 0.0
    return frame


def download_intraday(symbols):
    frames = {}
    errors = []
    for i in range(0, len(symbols), BATCH_SIZE):
        batch = symbols[i:i + BATCH_SIZE]
        try:
            data = yf.download(
                tickers=batch,
                period=LOOKBACK,
                interval=INTERVAL,
                auto_adjust=False,
                progress=False,
                group_by="column",
                threads=True,
                prepost=True,
            )
            data = normalize_download(data)
            for symbol in batch:
                frame = extract_symbol_frame(data, symbol)
                if not frame.empty:
                    frames[symbol] = frame
        except Exception as exc:
            errors.append(f"Batch {i // BATCH_SIZE + 1}: {type(exc).__name__}: {exc}")
        time.sleep(0.35)
    return frames, errors


def session_rows(frame, session_date):
    if frame.empty:
        return frame
    idx = frame.index
    mask = (idx.date == session_date) & (idx.time >= dtime(4, 0)) & (idx.time <= dtime(20, 0))
    return frame.loc[mask]


def previous_regular_close(frame, session_date):
    if frame.empty:
        return None
    dates = sorted({d for d in frame.index.date if d < session_date})
    if not dates:
        return None
    prev = dates[-1]
    idx = frame.index
    mask = (idx.date == prev) & (idx.time >= dtime(9, 30)) & (idx.time <= dtime(16, 0))
    regular = frame.loc[mask]
    if regular.empty:
        regular = frame.loc[idx.date == prev]
    return safe(regular["Close"].iloc[-1]) if not regular.empty else None


def ret_at_hours(close, hours):
    if close is None or len(close) < 2:
        return None
    last_ts = close.index[-1]
    cutoff = last_ts - pd.Timedelta(hours=hours)
    before = close.loc[close.index <= cutoff]
    if before.empty:
        return None
    return pct(close.iloc[-1], before.iloc[-1])


def previous_hour_return(close):
    if close is None or len(close) < 3:
        return None
    last_ts = close.index[-1]
    t1 = last_ts - pd.Timedelta(hours=1)
    t2 = last_ts - pd.Timedelta(hours=2)
    p1 = close.loc[close.index <= t1]
    p2 = close.loc[close.index <= t2]
    if p1.empty or p2.empty:
        return None
    return pct(p1.iloc[-1], p2.iloc[-1])


def rsi14(close):
    s = close.dropna()
    if len(s) < 15:
        return None
    delta = s.diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / 14, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1 / 14, adjust=False).mean()
    rs = gain / loss.replace(0, np.nan)
    rsi = 100 - 100 / (1 + rs)
    return safe(rsi.iloc[-1])


def macd_hist(close):
    s = close.dropna()
    if len(s) < 35:
        return None
    ema12 = s.ewm(span=12, adjust=False).mean()
    ema26 = s.ewm(span=26, adjust=False).mean()
    macd = ema12 - ema26
    signal = macd.ewm(span=9, adjust=False).mean()
    return safe((macd - signal).iloc[-1])


def trend_quality(close):
    s = close.dropna().tail(13)
    if len(s) < 8:
        return None
    y = np.log(s.to_numpy(dtype=float))
    x = np.arange(len(y), dtype=float)
    slope, intercept = np.polyfit(x, y, 1)
    fitted = slope * x + intercept
    ss_res = float(np.sum((y - fitted) ** 2))
    ss_tot = float(np.sum((y - np.mean(y)) ** 2))
    r2 = 0.0 if ss_tot == 0 else clamp(1 - ss_res / ss_tot, 0.0, 1.0)
    return (1 if slope >= 0 else -1) * r2


def stability(close, direction):
    s = close.dropna().tail(13)
    if len(s) < 5:
        return None, 0, 0
    rets = s.pct_change().dropna() * 100
    if direction == "long":
        directional = rets > 0
    else:
        directional = rets < 0
    ratio = float(directional.mean())
    abs_sum = float(rets.abs().sum())
    jump_share = 1.0 if abs_sum == 0 else float(rets.abs().max() / abs_sum)
    tq = trend_quality(s)
    aligned_r2 = max(0.0, (tq or 0.0) if direction == "long" else -(tq or 0.0))
    score = 100 * (0.58 * ratio + 0.42 * aligned_r2) * (1 - 0.55 * jump_share)
    return clamp(score, 0.0, 100.0), int(directional.sum()), int(len(rets))


def volume_ratio(frame, current_session, now_ny):
    if current_session.empty:
        return None
    current = safe(current_session["Volume"].fillna(0).sum(), 0.0)
    if current is None:
        return None
    prior_dates = sorted({d for d in frame.index.date if d < now_ny.date()}, reverse=True)[:4]
    comps = []
    for d in prior_dates:
        rows = session_rows(frame, d)
        if rows.empty:
            continue
        rows = rows.loc[rows.index.time <= now_ny.time()]
        if not rows.empty:
            comps.append(float(rows["Volume"].fillna(0).sum()))
    base = float(np.median(comps)) if comps else 0.0
    if base <= 0:
        return None
    return current / base


def benchmark_return(frame, now_ny):
    sess = session_rows(frame, now_ny.date())
    if sess.empty:
        return None
    prev = previous_regular_close(frame, now_ny.date())
    base = prev if prev else safe(sess["Close"].iloc[0])
    return pct(sess["Close"].iloc[-1], base)


def regular_open_check(sess, direction):
    regular = sess.loc[(sess.index.time >= dtime(9, 30)) & (sess.index.time <= dtime(16, 0))]
    if len(regular) < 2:
        return None
    move = pct(regular["Close"].iloc[-1], regular["Open"].iloc[0] if "Open" in regular else regular["Close"].iloc[0])
    if move is None:
        return None
    return move if direction == "long" else -move


def score_candidate(metrics, direction):
    sign = 1 if direction == "long" else -1
    day = sign * (metrics.get("day_pct") or 0.0)
    m1 = sign * (metrics.get("m1") or 0.0)
    m2 = sign * (metrics.get("m2") or 0.0)
    m3 = sign * (metrics.get("m3") or 0.0)
    rel_i = sign * (metrics.get("rel_index") or 0.0)
    rel_s = sign * (metrics.get("rel_sector") or 0.0)
    accel = sign * (metrics.get("accel") or 0.0)
    dist = abs(metrics.get("dist_high") or 0.0) if direction == "long" else abs(metrics.get("dist_low") or 0.0)
    stab = metrics.get("stability_long") if direction == "long" else metrics.get("stability_short")
    stab = stab or 0.0
    vol = metrics.get("volume_ratio")
    vol = 0.0 if vol is None else vol
    rsi = metrics.get("rsi")
    mh = metrics.get("macd_hist")
    price = max(abs(metrics.get("price") or 1.0), 0.01)
    mh_pct = 0.0 if mh is None else sign * mh / price * 100.0

    score = 0.0
    score += 12 * clamp(day / 2.0, 0, 1)
    score += 12 * clamp(m1 / 1.0, 0, 1)
    score += 8 * clamp(m2 / 2.0, 0, 1)
    score += 8 * clamp(m3 / 3.0, 0, 1)
    score += 20 * (stab / 100.0)
    score += 10 * clamp((vol - 0.5) / 1.5, 0, 1)
    score += 8 * clamp((1.6 - dist) / 1.6, 0, 1)
    score += 5 * clamp(rel_i / 1.0, 0, 1)
    score += 5 * clamp(rel_s / 1.0, 0, 1)
    score += 5 * clamp(accel / 0.5, 0, 1)
    score += 3 * clamp(mh_pct / 0.08, 0, 1)

    if rsi is not None:
        if direction == "long":
            if 52 <= rsi <= 76:
                score += 4
            elif rsi > 84:
                score -= 4
        else:
            if 24 <= rsi <= 48:
                score += 4
            elif rsi < 16:
                score -= 4

    return clamp(score, 0, 100)


def signal_for(metrics, direction, now_ny, latest_age_min):
    sign = 1 if direction == "long" else -1
    score = metrics["score_long"] if direction == "long" else metrics["score_short"]
    m1 = sign * (metrics.get("m1") or 0.0)
    m2 = sign * (metrics.get("m2") or 0.0)
    day = sign * (metrics.get("day_pct") or 0.0)
    rel = sign * (metrics.get("rel_index") or 0.0)
    stab = metrics.get("stability_long") if direction == "long" else metrics.get("stability_short")
    intervals = metrics.get("intervals") or 0
    vol = metrics.get("volume_ratio")
    open_check = metrics.get("open_check_long") if direction == "long" else metrics.get("open_check_short")

    fresh = latest_age_min is not None and latest_age_min <= 45
    enough_history = intervals >= 7
    volume_ok = vol is None or vol >= 0.65
    open_ok = open_check is None or open_check > -0.45
    if fresh and enough_history and score >= 68 and day > 0 and m1 > 0 and m2 > 0 and (stab or 0) >= 60 and rel > -0.25 and volume_ok and open_ok:
        return "EINSTIEG"
    if fresh and intervals >= 3 and score >= 50 and (day > 0 or m1 > 0):
        return "BEOBACHTEN"
    return "KEIN EINSTIEG"


def momentum_change(m1, prev1, direction):
    if m1 is None or prev1 is None:
        return "noch nicht vergleichbar"
    delta = (m1 - prev1) if direction == "long" else (prev1 - m1)
    if delta > 0.15:
        return "stärker"
    if delta < -0.15:
        return "schwächer"
    return "gleich"


def reason(metrics, direction, signal):
    sign = 1 if direction == "long" else -1
    m3 = sign * (metrics.get("m3") or 0.0)
    stab = metrics.get("stability_long") if direction == "long" else metrics.get("stability_short")
    vol = metrics.get("volume_ratio")
    rel = sign * (metrics.get("rel_index") or 0.0)
    bits = []
    if m3 > 0.6 and (stab or 0) >= 65:
        bits.append("über mehrere Stunden gleichmäßig")
    elif (stab or 0) < 50:
        bits.append("Bewegung noch unruhig")
    if vol is not None and vol >= 1.25:
        bits.append(f"Volumen {vol:.1f}× normal")
    if rel >= 0.4:
        bits.append("stärker als der Index")
    change = metrics.get("momentum_change_long") if direction == "long" else metrics.get("momentum_change_short")
    if change == "schwächer":
        bits.append("Momentum lässt nach")
    if not bits:
        bits.append("Signal noch nicht klar genug" if signal != "EINSTIEG" else "Trend und Momentum bestätigen sich")
    text = ", ".join(bits[:3])
    return text[0].upper() + text[1:] + "."


def candidate_record(meta, metrics, direction, rank):
    signal = metrics["signal_long"] if direction == "long" else metrics["signal_short"]
    stability_value = metrics["stability_long"] if direction == "long" else metrics["stability_short"]
    change = metrics["momentum_change_long"] if direction == "long" else metrics["momentum_change_short"]
    score = metrics["score_long"] if direction == "long" else metrics["score_short"]
    return {
        "rank": rank,
        "symbol": meta["symbol"],
        "name": meta["name"],
        "sector": meta.get("sector", ""),
        "indexes": meta.get("indexes", []),
        "direction": direction.upper(),
        "price": rounded(metrics.get("price"), 2),
        "day_pct": rounded(metrics.get("day_pct"), 2),
        "m1": rounded(metrics.get("m1"), 2),
        "m2": rounded(metrics.get("m2"), 2),
        "m3": rounded(metrics.get("m3"), 2),
        "volume_ratio": rounded(metrics.get("volume_ratio"), 2),
        "stability": rounded(stability_value, 0),
        "positive_intervals": metrics.get("positive_intervals"),
        "negative_intervals": metrics.get("negative_intervals"),
        "intervals": metrics.get("intervals"),
        "rsi": rounded(metrics.get("rsi"), 1),
        "macd_hist": rounded(metrics.get("macd_hist"), 3),
        "trend_quality": rounded(metrics.get("trend_quality"), 2),
        "rel_index": rounded(metrics.get("rel_index"), 2),
        "rel_sector": rounded(metrics.get("rel_sector"), 2),
        "dist_high": rounded(metrics.get("dist_high"), 2),
        "score": rounded(score, 0),
        "signal": signal,
        "momentum_change": change,
        "reason": reason(metrics, direction, signal),
        "latest_bar": metrics.get("latest_bar"),
    }


def main():
    now_utc = datetime.now(timezone.utc)
    now_vienna = now_utc.astimezone(VIENNA)
    now_ny = now_utc.astimezone(NEW_YORK)
    event = os.getenv("GITHUB_EVENT_NAME", "manual")
    if event == "schedule" and (now_vienna.weekday() >= 5 or not (10 <= now_vienna.hour <= 22)):
        print(f"Außerhalb Scanfenster: {now_vienna.isoformat()}")
        return

    universe = load_universe()
    by_symbol = {x["symbol"]: x for x in universe}
    sector_symbols = sorted({sector_etf(x.get("sector")) for x in universe})
    helper_symbols = sorted(set(["SPY", "QQQ"] + sector_symbols))
    symbols = sorted(set(by_symbol) | set(helper_symbols))

    frames, errors = download_intraday(symbols)
    bench_returns = {s: benchmark_return(frames[s], now_ny) for s in helper_symbols if s in frames}
    scored = []

    for symbol, meta in by_symbol.items():
        frame = frames.get(symbol)
        if frame is None or frame.empty:
            continue
        sess = session_rows(frame, now_ny.date())
        if len(sess) < 2:
            continue
        close = sess["Close"].dropna()
        if len(close) < 2:
            continue
        last_ts = close.index[-1]
        latest_age_min = max(0.0, (pd.Timestamp(now_ny) - last_ts).total_seconds() / 60.0)
        prev_close = previous_regular_close(frame, now_ny.date())
        day_base = prev_close if prev_close else safe(close.iloc[0])
        price = safe(close.iloc[-1])
        day_pct = pct(price, day_base)
        m1 = ret_at_hours(close, 1)
        m2 = ret_at_hours(close, 2)
        m3 = ret_at_hours(close, 3)
        prev1 = previous_hour_return(close)
        st_long, pos_count, intervals = stability(close, "long")
        st_short, neg_count, _ = stability(close, "short")
        high = safe(sess["High"].max()) if "High" in sess else safe(close.max())
        low = safe(sess["Low"].min()) if "Low" in sess else safe(close.min())
        dist_high = pct(price, high)
        dist_low = pct(price, low)
        volr = volume_ratio(frame, sess, now_ny)
        rsi = rsi14(close)
        mh = macd_hist(close)
        tq = trend_quality(close)
        accel = None if m1 is None or prev1 is None else m1 - prev1
        index_symbol = "QQQ" if "NASDAQ 100" in meta.get("indexes", []) else "SPY"
        idx_ret = bench_returns.get(index_symbol)
        sec_symbol = sector_etf(meta.get("sector"))
        sec_ret = bench_returns.get(sec_symbol, bench_returns.get("SPY"))
        rel_index = None if day_pct is None or idx_ret is None else day_pct - idx_ret
        rel_sector = None if day_pct is None or sec_ret is None else day_pct - sec_ret

        metrics = {
            "price": price,
            "day_pct": day_pct,
            "m1": m1,
            "m2": m2,
            "m3": m3,
            "prev1": prev1,
            "accel": accel,
            "stability_long": st_long,
            "stability_short": st_short,
            "positive_intervals": pos_count,
            "negative_intervals": neg_count,
            "intervals": intervals,
            "volume_ratio": volr,
            "dist_high": dist_high,
            "dist_low": dist_low,
            "rsi": rsi,
            "macd_hist": mh,
            "trend_quality": tq,
            "rel_index": rel_index,
            "rel_sector": rel_sector,
            "open_check_long": regular_open_check(sess, "long"),
            "open_check_short": regular_open_check(sess, "short"),
            "latest_bar": last_ts.isoformat(),
            "latest_age_min": latest_age_min,
        }
        metrics["score_long"] = score_candidate(metrics, "long")
        metrics["score_short"] = score_candidate(metrics, "short")
        metrics["signal_long"] = signal_for(metrics, "long", now_ny, latest_age_min)
        metrics["signal_short"] = signal_for(metrics, "short", now_ny, latest_age_min)
        metrics["momentum_change_long"] = momentum_change(m1, prev1, "long")
        metrics["momentum_change_short"] = momentum_change(m1, prev1, "short")
        scored.append((meta, metrics))

    longs = sorted(scored, key=lambda x: x[1]["score_long"], reverse=True)[:5]
    shorts = sorted(scored, key=lambda x: x[1]["score_short"], reverse=True)[:3]
    long_records = [candidate_record(meta, metrics, "long", i + 1) for i, (meta, metrics) in enumerate(longs)]
    short_records = [candidate_record(meta, metrics, "short", i + 1) for i, (meta, metrics) in enumerate(shorts)]

    all_signals = [x["signal"] for x in long_records + short_records]
    overall = "EINSTIEG" if "EINSTIEG" in all_signals else ("BEOBACHTEN" if "BEOBACHTEN" in all_signals else "KEIN EINSTIEG")
    latest_bars = [pd.Timestamp(m["latest_bar"]) for _, m in scored if m.get("latest_bar")]
    latest_market_bar = max(latest_bars).isoformat() if latest_bars else None

    phase = "Vorbörse"
    if now_ny.time() >= dtime(16, 0):
        phase = "US-Handel beendet"
    elif now_ny.time() >= dtime(9, 30):
        phase = "US-Haupthandel"
    elif now_ny.time() < dtime(4, 0):
        phase = "Vor US-Vorbörse"

    payload = {
        "version": "momentum-radar-mvp-1",
        "generated_at": now_utc.isoformat(),
        "generated_at_vienna": now_vienna.isoformat(),
        "market": {
            "phase": phase,
            "latest_bar": latest_market_bar,
            "overall_signal": overall,
            "special_scan": "US-Eröffnung berücksichtigt" if now_ny.time() >= dtime(9, 30) else ("15:00-Fokus" if now_vienna.hour == 15 else ("14:00-Fokus" if now_vienna.hour == 14 else "")),
        },
        "coverage": {
            "universe": len(universe),
            "with_intraday_data": len(scored),
            "indexes": ["S&P 500", "NASDAQ 100"],
            "interval": INTERVAL,
            "lookback": LOOKBACK,
        },
        "candidates": {"long": long_records, "short": short_records},
        "errors": errors[:8],
        "source": "Yahoo Finance Intraday-Daten via yfinance; Universum/Metadaten aus dem RSL-Scanner",
        "notes": [
            "EINSTIEG wird nur bei ausreichend frischen Daten und mehrstündiger Kontinuität vergeben.",
            "Ein einzelner Kurssprung ohne Folgebewegung wird durch Stabilitäts- und Jump-Penalty abgewertet.",
            "Keine automatischen Echtgeldorders und keine Renditegarantie.",
        ],
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"MomentumRadar: {len(scored)}/{len(universe)} Werte · Signal {overall} · {OUT}")


if __name__ == "__main__":
    main()
