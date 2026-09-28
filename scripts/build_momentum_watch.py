import json
import math
import os
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import yfinance as yf

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "docs" / "momentum-radar" / "data.json"
WATCH_PATH = ROOT / "docs" / "momentum-radar" / "watch.json"
HISTORY_DIR = ROOT / "docs" / "momentum-radar" / "watch-history"
VIENNA = ZoneInfo("Europe/Vienna")
NEW_YORK = ZoneInfo("America/New_York")


def safe(v, default=None):
    try:
        if v is None or pd.isna(v) or math.isinf(float(v)):
            return default
        return float(v)
    except Exception:
        return default


def pct(new, old):
    new, old = safe(new), safe(old)
    if new is None or old in (None, 0):
        return None
    return (new / old - 1.0) * 100.0


def rounded(v, digits=2):
    v = safe(v)
    return None if v is None else round(v, digits)


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
            if field in lvl0 and symbol in lvl1:
                out[field] = data[(field, symbol)]
            elif symbol in lvl0 and field in lvl1:
                out[field] = data[(symbol, field)]
    else:
        for field in fields:
            if field in data.columns:
                out[field] = data[field]
    if "Close" not in out:
        return pd.DataFrame()
    return pd.DataFrame(out).dropna(subset=["Close"])


def return_at_minutes(close, minutes):
    if close is None or len(close) < 2:
        return None
    target = close.index[-1] - pd.Timedelta(minutes=minutes)
    before = close.loc[close.index <= target]
    if before.empty:
        return None
    return pct(close.iloc[-1], before.iloc[-1])


def signal_level(s):
    return {"KEIN EINSTIEG": 0, "BEOBACHTEN": 1, "EINSTIEG": 2}.get(s, 0)


def min_signal(base, limit):
    return base if signal_level(base) <= signal_level(limit) else limit


def monitor_signal(base_signal, direction, age_min, raw15, raw30, raw60, raw_since_scan):
    sign = 1 if direction == "LONG" else -1
    d15 = None if raw15 is None else sign * raw15
    d30 = None if raw30 is None else sign * raw30
    d60 = None if raw60 is None else sign * raw60
    ds = None if raw_since_scan is None else sign * raw_since_scan

    hard = (
        (ds is not None and ds <= -0.80)
        or (d15 is not None and d15 <= -0.50)
        or (d30 is not None and d30 <= -0.75)
    )
    if hard:
        return "KEIN EINSTIEG", "Deutliche Gegenbewegung seit dem Vollscan – Einstieg gesperrt."

    if age_min is None or age_min > 25:
        return "KEIN EINSTIEG", "Kurzcheck veraltet – kein neuer Einstieg."

    soft = (
        (ds is not None and ds <= -0.35)
        or (d15 is not None and d15 <= -0.20)
        or (d30 is not None and d30 <= -0.40)
        or (d60 is not None and d60 <= -0.60)
    )
    if soft:
        return min_signal(base_signal, "BEOBACHTEN"), "Momentum im Kurzcheck schwächer – erst beobachten."

    return base_signal, "Kurzcheck bestätigt das bestehende Signal."


def main():
    now_utc = datetime.now(timezone.utc)
    now_vienna = now_utc.astimezone(VIENNA)
    if os.getenv("GITHUB_EVENT_NAME", "manual") == "schedule" and not (10 <= now_vienna.hour <= 22):
        print(f"Außerhalb Kurzcheck-Fenster: {now_vienna.isoformat()}")
        return

    if not DATA_PATH.exists():
        raise RuntimeError("MomentumRadar data.json fehlt")

    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    candidates = {}
    for universe_name, universe in (data.get("universes") or {}).items():
        for side in ("long", "short"):
            for row in ((universe.get("candidates") or {}).get(side) or []):
                symbol = row.get("symbol")
                direction = row.get("direction")
                if not symbol or direction not in ("LONG", "SHORT"):
                    continue
                key = f"{symbol}|{direction}"
                candidates.setdefault(key, {
                    "symbol": symbol,
                    "direction": direction,
                    "base_signal": row.get("signal") or "KEIN EINSTIEG",
                    "scan_price": safe(row.get("price")),
                    "universes": [],
                })
                if universe_name not in candidates[key]["universes"]:
                    candidates[key]["universes"].append(universe_name)

    symbols = sorted({x["symbol"] for x in candidates.values()})
    frames = {}
    errors = []
    if symbols:
        try:
            raw = yf.download(
                tickers=symbols,
                period="1d",
                interval="5m",
                auto_adjust=False,
                progress=False,
                group_by="column",
                threads=True,
                prepost=True,
            )
            raw = normalize_download(raw)
            for symbol in symbols:
                frame = extract_symbol_frame(raw, symbol)
                if not frame.empty:
                    frames[symbol] = frame
        except Exception as exc:
            errors.append(f"{type(exc).__name__}: {exc}")

    out = {}
    history_rows = []

    for key, meta in candidates.items():
        symbol = meta["symbol"]
        direction = meta["direction"]
        frame = frames.get(symbol)
        if frame is None or frame.empty:
            out[key] = {
                **meta,
                "watch_signal": "KEIN EINSTIEG",
                "reason": "Keine frischen 5-Minuten-Daten – Einstieg gesperrt.",
                "latest_bar": None,
                "age_min": None,
            }
            continue

        close = frame["Close"].dropna()
        latest_bar = close.index[-1]
        latest_price = safe(close.iloc[-1])
        age_min = max(0.0, (pd.Timestamp(now_utc) - latest_bar.tz_convert("UTC")).total_seconds() / 60.0)
        r15 = return_at_minutes(close, 15)
        r30 = return_at_minutes(close, 30)
        r60 = return_at_minutes(close, 60)
        since_scan = pct(latest_price, meta.get("scan_price"))

        watch_signal, reason = monitor_signal(
            meta["base_signal"], direction, age_min, r15, r30, r60, since_scan
        )

        rec = {
            **meta,
            "watch_signal": watch_signal,
            "reason": reason,
            "checked_at": now_utc.isoformat(),
            "checked_at_vienna": now_vienna.isoformat(),
            "latest_bar": latest_bar.isoformat(),
            "age_min": rounded(age_min, 1),
            "price": rounded(latest_price, 4),
            "move_since_scan_pct": rounded(since_scan, 2),
            "ret_15m_pct": rounded(r15, 2),
            "ret_30m_pct": rounded(r30, 2),
            "ret_60m_pct": rounded(r60, 2),
        }
        out[key] = rec
        history_rows.append(rec)

    payload = {
        "version": "momentum-radar-watch-1",
        "generated_at": now_utc.isoformat(),
        "generated_at_vienna": now_vienna.isoformat(),
        "base_scan_generated_at": data.get("generated_at"),
        "interval": "5m",
        "candidate_count": len(out),
        "candidates": out,
        "errors": errors[:8],
        "notes": [
            "Der Kurzcheck überwacht nur bestehende MomentumRadar-Kandidaten.",
            "Er kann ein Signal nur herabstufen, niemals hochstufen.",
            "Der stündliche Vollscan bleibt unverändert.",
        ],
    }

    WATCH_PATH.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    hist_path = HISTORY_DIR / f"{now_vienna.date().isoformat()}.json"
    try:
        hist = json.loads(hist_path.read_text(encoding="utf-8")) if hist_path.exists() else []
        if not isinstance(hist, list):
            hist = []
    except Exception:
        hist = []
    hist.extend(history_rows)
    hist_path.write_text(json.dumps(hist, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"MomentumRadar Kurzcheck: {len(out)} Kandidaten · {WATCH_PATH}")


if __name__ == "__main__":
    main()
