"""Validate the existing shortlist against complete 5-minute bars. Never upgrade."""
from __future__ import annotations
import json
import math
import os
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo
import pandas as pd
from momentum_delivery import atomic_json, age_minutes, LEVEL, QUOTE_LIMIT

BASE = Path(__file__).resolve().parents[1] / 'docs/momentum-radar'


def safe(value):
    try:
        number = float(value)
        return number if math.isfinite(number) else None
    except (ValueError, TypeError):
        return None


def pct(new, old):
    a, b = safe(new), safe(old)
    return (a / b - 1) * 100 if a is not None and b is not None and b > 0 else None


def frame_for(raw, symbol, now, single=False):
    if raw is None or raw.empty:
        return pd.DataFrame()
    if isinstance(raw.columns, pd.MultiIndex):
        if symbol in raw.columns.get_level_values(0):
            frame = raw[symbol].copy()
        elif symbol in raw.columns.get_level_values(1):
            frame = raw.xs(symbol, level=1, axis=1).copy()
        else:
            return pd.DataFrame()
    elif single:
        frame = raw.copy()
    else:
        return pd.DataFrame()
    if 'Close' not in frame or not isinstance(frame.index, pd.DatetimeIndex) or frame.index.tz is None:
        return pd.DataFrame()
    frame.index = frame.index.tz_convert('UTC')
    frame = frame.loc[~frame.index.duplicated(keep='last')].sort_index()
    aligned = (frame.index.minute % 5 == 0) & (frame.index.second == 0) & (frame.index.microsecond == 0)
    complete = frame.index + pd.Timedelta(minutes=5) <= pd.Timestamp(now)
    frame = frame.loc[aligned & complete]
    for field in ('Open', 'High', 'Low', 'Close', 'Volume'):
        if field in frame:
            frame[field] = pd.to_numeric(frame[field], errors='coerce')
    frame = frame.loc[frame['Close'].map(lambda value: safe(value) is not None) & (frame['Close'] > 0)]
    if all(k in frame for k in ('High', 'Low')):
        valid = (frame['Low'].map(lambda value: safe(value) is not None)
                 & frame['High'].map(lambda value: safe(value) is not None)
                 & (frame['Low'] <= frame['Close']) & (frame['High'] >= frame['Close']) & (frame['Low'] > 0))
        if 'Open' in frame:
            valid &= frame['Open'].map(lambda value: safe(value) is not None) & (frame['Low'] <= frame['Open']) & (frame['High'] >= frame['Open'])
        frame = frame.loc[valid]
    return frame


def return_at_minutes(close, minutes):
    if close is None or len(close) < 2:
        return None
    target = close.index[-1] - pd.Timedelta(minutes=minutes)
    window = close.loc[close.index >= target]
    expected = pd.date_range(target, close.index[-1], freq='5min')
    if not window.index.equals(expected) or any(safe(value) is None or value <= 0 for value in window):
        return None
    return pct(window.iloc[-1], window.iloc[0])


def monitor_signal(base, direction, age, raw15, raw30, raw60, raw_since):
    if base not in LEVEL or direction not in ('LONG', 'SHORT'):
        return 'KEIN EINSTIEG', 'Unbekanntes Signal – kein neuer Einstieg.'
    if age is None or not math.isfinite(age) or not 0 <= age <= QUOTE_LIMIT:
        return 'KEIN EINSTIEG', 'Kursdaten zu alt – kein neuer Einstieg.'
    if any(safe(v) is None for v in (raw15, raw30, raw60)):
        return 'KEIN EINSTIEG', '5-Minuten-Verlauf unvollständig – kein neuer Einstieg.'
    if safe(raw_since) is None:
        return 'KEIN EINSTIEG', 'Vergleichskurs des Vollscans fehlt – kein neuer Einstieg.'
    sign = 1 if direction == 'LONG' else -1
    d15, d30, d60 = (sign * v for v in (raw15, raw30, raw60))
    ds = None if safe(raw_since) is None else sign * raw_since
    # Retain the already approved reversal thresholds.
    if ((ds is not None and ds <= -.80) or d15 <= -.50 or d30 <= -.75):
        return 'KEIN EINSTIEG', 'Deutliche Gegenbewegung – Einstieg gesperrt.'
    if ((ds is not None and ds <= -.35) or d15 <= -.20 or d30 <= -.40 or d60 <= -.60):
        return (base if LEVEL[base] <= 1 else 'BEOBACHTEN'), 'Momentum im Kurzcheck schwächer – erst beobachten.'
    return base, 'Kurzcheck bestätigt das bestehende Signal.'


def collect_candidates(data):
    result = {}
    for name, universe in data.get('universes', {}).items():
        for side in ('long', 'short'):
            for row in universe.get('candidates', {}).get(side, []):
                symbol, direction = row.get('symbol'), row.get('direction')
                if not symbol or direction not in ('LONG', 'SHORT'):
                    continue
                key, signal = f'{symbol}|{direction}', row.get('signal', 'KEIN EINSTIEG')
                if row.get('data_quality_ok') is not True:
                    signal = 'KEIN EINSTIEG'
                reference = safe(row.get('reference_price'))
                if reference is None and (safe(row.get('price')) or 0) >= 1:
                    reference = safe(row['price'])
                if key not in result:
                    result[key] = {'symbol': symbol, 'direction': direction, 'base_signal': signal,
                                   'scan_price': reference, 'universes': []}
                elif LEVEL.get(signal, 0) < LEVEL.get(result[key]['base_signal'], 0):
                    result[key]['base_signal'] = signal
                result[key]['universes'].append(name)
    return result


def main():
    import yfinance as yf
    data = json.loads((BASE / 'data.json').read_text(encoding='utf-8'))
    candidates = collect_candidates(data)
    symbols = sorted({x['symbol'] for x in candidates.values()})
    started = datetime.now(timezone.utc)
    frames, errors = {}, []
    for offset in range(0, len(symbols), 60):
        batch = symbols[offset:offset + 60]
        try:
            raw = yf.download(tickers=batch, period='1d', interval='5m', auto_adjust=False,
                              progress=False, group_by='column', threads=8, prepost=True, timeout=15)
            received = datetime.now(timezone.utc)
            for symbol in batch:
                frame = frame_for(raw, symbol, received, single=len(batch) == 1)
                if not frame.empty:
                    frames[symbol] = frame
        except Exception as exc:
            errors.append(f'{type(exc).__name__}: Kandidatenabruf fehlgeschlagen.')
    finished, out = datetime.now(timezone.utc), {}
    for key, meta in candidates.items():
        frame = frames.get(meta['symbol'])
        rec = {**meta, 'checked_at': finished.isoformat(), 'watch_signal': 'KEIN EINSTIEG',
               'reason': 'Keine verwertbaren 5-Minuten-Kursdaten.', 'price': None,
               'latest_bar': None, 'price_asof': None, 'ret_15m_pct': None,
               'ret_30m_pct': None, 'ret_60m_pct': None, 'move_since_scan_pct': None}
        if frame is not None and not frame.empty:
            close, bar = frame['Close'], frame.index[-1]
            asof = (bar + pd.Timedelta(minutes=5)).isoformat()
            age, price = age_minutes(asof, finished), safe(close.iloc[-1])
            r15, r30, r60 = (return_at_minutes(close, minutes) for minutes in (15, 30, 60))
            since = pct(price, meta['scan_price'])
            signal, reason = monitor_signal(meta['base_signal'], meta['direction'], age, r15, r30, r60, since)
            rec.update(watch_signal=signal, reason=reason, price=price, latest_bar=bar.isoformat(),
                       price_asof=asof, age_min=round(age, 2), ret_15m_pct=r15, ret_30m_pct=r30,
                       ret_60m_pct=r60, move_since_scan_pct=since)
        out[key] = rec
    payload = {'version': 'momentum-radar-watch-2', 'generated_at': finished.isoformat(),
               'started_at': started.isoformat(), 'base_scan_generated_at': data.get('generated_at'),
               'interval': '5m', 'candidate_count': len(out), 'candidates': out, 'errors': errors}
    atomic_json(BASE / 'watch.json', payload)
    day = finished.astimezone(ZoneInfo('Europe/Vienna')).date().isoformat()
    name = finished.strftime('%H%M%S%f') + '-' + os.getenv('GITHUB_RUN_ID', 'local') + '.json'
    atomic_json(BASE / 'watch-history' / day / name, payload)
    print(json.dumps({'checked_at': finished.isoformat(), 'candidate_count': len(out),
                      'with_prices': sum(r['price'] is not None for r in out.values()), 'errors': errors}))


if __name__ == '__main__':
    main()
