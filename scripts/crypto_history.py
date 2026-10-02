"""Recover missing UTC crypto daily closes only from complete Yahoo hourly days."""
import json
import math
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from urllib.parse import quote, urlencode
from urllib.request import Request, HTTPRedirectHandler, build_opener

DAY = 86400


def verified_closes(payload, symbol, days, now):
    try:
        chart = payload['chart']
        if chart.get('error') or len(chart['result']) != 1:
            return {}
        result = chart['result'][0]
        meta = result['meta']
        if (meta.get('symbol') != symbol or meta.get('currency') != 'USD'
                or meta.get('dataGranularity') != '1h'):
            return {}
        times = result['timestamp']
        closes = result['indicators']['quote'][0]['close']
        if len(times) != len(closes):
            return {}
        output = {}
        for day in days:
            start = int(datetime.fromisoformat(day).replace(tzinfo=timezone.utc).timestamp())
            if now.timestamp() < start + DAY + 20 * 60:
                continue
            rows = [(t, c) for t, c in zip(times, closes)
                    if isinstance(t, (int, float)) and start <= t < start + DAY]
            # Exactly 24 distinct UTC hour starts, no missing, duplicate or null bars.
            if len(rows) != 24 or sorted(t for t, _ in rows) != list(range(start, start + DAY, 3600)):
                continue
            if any(type(c) not in (int, float) or not math.isfinite(c) or c <= 0 for _, c in rows):
                continue
            output[day] = dict(rows)[start + 23 * 3600]
        return output
    except (KeyError, IndexError, TypeError, ValueError):
        return {}


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def fetch_hourly(symbol, days):
    if not re.fullmatch(r'[A-Z0-9-]+-USD', symbol) or not days:
        return {}
    start = datetime.fromisoformat(min(days)).replace(tzinfo=timezone.utc)
    end = datetime.fromisoformat(max(days)).replace(tzinfo=timezone.utc) + timedelta(days=1)
    query = urlencode(dict(interval='1h', period1=int(start.timestamp()), period2=int(end.timestamp())))
    url = 'https://query1.finance.yahoo.com/v8/finance/chart/' + quote(symbol, safe='') + '?' + query
    request = Request(url, headers={'User-Agent': 'Mozilla/5.0 (compatible; RSL-Scanner/1.0)'})
    with build_opener(NoRedirect).open(request, timeout=12) as response:
        raw = response.read(2_000_001)
        if response.status != 200 or len(raw) > 2_000_000:
            return {}
        return json.loads(raw)


def repair_crypto_prices(prices, symbols, now=None, request=fetch_hourly):
    """Only add missing recent days; never overwrite provider daily closes."""
    import pandas as pd
    now = now or datetime.now(timezone.utc)
    today = now.date()
    days = [(today - timedelta(days=n)).isoformat() for n in range(1, 8)]
    tasks = []
    for symbol in symbols:
        if not symbol.endswith('-USD') or symbol not in prices.columns:
            continue
        series = prices[symbol].dropna()
        if len(series) < 205:
            continue
        present = {t.strftime('%Y-%m-%d') for t in series.index}
        missing = [day for day in days if day not in present]
        if missing:
            tasks.append((symbol, missing))
    def recover(task):
        symbol, missing = task
        try:
            return symbol, verified_closes(request(symbol, missing), symbol, missing, now)
        except Exception:
            return symbol, {}  # visible gap remains; never fabricate a close
    restored = {}
    with ThreadPoolExecutor(max_workers=6) as executor:
        for symbol, values in executor.map(recover, tasks):
            for day, close in values.items():
                stamp = pd.Timestamp(day)
                if prices.index.tz is not None:
                    stamp = stamp.tz_localize(prices.index.tz)
                prices.loc[stamp, symbol] = close
            if values:
                restored[symbol] = sorted(values)
    return prices.sort_index(), restored
