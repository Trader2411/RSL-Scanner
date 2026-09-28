"""One coherent publication, without changing the momentum scoring algorithm."""
from __future__ import annotations
import argparse
import json
import math
import os
import subprocess
import sys
import tempfile
from datetime import datetime, time, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'docs/momentum-radar'
LEVEL = {'KEIN EINSTIEG': 0, 'BEOBACHTEN': 1, 'EINSTIEG': 2}
FULL_LIMIT, WATCH_LIMIT, QUOTE_LIMIT = 90, 20, 20
BASE_QUOTE_LIMIT = 45


def scan_window(now):
    local = now.astimezone(ZoneInfo('Europe/Vienna'))
    return local.weekday() < 5 and time(10) <= local.time() <= time(22)


def age_minutes(value, now):
    try:
        timestamp = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
        if timestamp.tzinfo is None:
            return math.inf
        age = (now - timestamp).total_seconds() / 60
        return max(0., age) if age >= -1 else math.inf
    except (ValueError, TypeError):
        return math.inf


def finite(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def atomic_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile('w', dir=path.parent, encoding='utf-8', delete=False) as stream:
            temporary = stream.name
            json.dump(value, stream, ensure_ascii=False, separators=(',', ':'), allow_nan=False)
        os.replace(temporary, path)
    finally:
        if temporary and os.path.exists(temporary):
            os.unlink(temporary)


def read_json(path):
    value = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(value, dict):
        raise ValueError(f'{path.name}: JSON object required')
    return value


def validate_pair(data, watch, now):
    if not isinstance(data.get('universes'), dict) or not data['universes'] or not math.isfinite(age_minutes(data.get('generated_at'), now)):
        raise ValueError('Invalid full scan')
    if watch.get('base_scan_generated_at') != data.get('generated_at'):
        raise ValueError('Full scan / candidate check mismatch')
    if not isinstance(watch.get('candidates'), dict):
        raise ValueError('Candidate checks missing')
    scan_time = datetime.fromisoformat(data['generated_at'].replace('Z', '+00:00'))
    watch_age = age_minutes(watch.get('generated_at'), now)
    watch_time = datetime.fromisoformat(watch['generated_at'].replace('Z', '+00:00')) if math.isfinite(watch_age) else None
    if watch_time is not None and watch_time < scan_time:
        raise ValueError('Candidate check predates full scan')
    for universe in data['universes'].values():
        if not isinstance(universe, dict) or not isinstance(universe.get('candidates'), dict):
            raise ValueError('Malformed universe')
        for side in ('long', 'short'):
            rows = universe['candidates'].get(side, [])
            if not isinstance(rows, list):
                raise ValueError('Malformed candidate list')
            for row in rows:
                if not isinstance(row, dict) or not row.get('symbol') or row.get('direction') != side.upper():
                    raise ValueError('Malformed candidate identity')
                rec = watch['candidates'].get(f"{row['symbol']}|{row['direction']}")
                if rec is None:
                    continue  # Missing records are blocked by the browser.
                valid = isinstance(rec, dict) and all(finite(rec.get(k)) for k in ('price', 'ret_15m_pct', 'ret_30m_pct', 'ret_60m_pct'))
                if not isinstance(rec, dict):
                    watch['candidates'][f"{row['symbol']}|{row['direction']}"] = {'watch_signal': 'KEIN EINSTIEG', 'reason': 'Ungültiger Kurzcheck.'}
                    continue
                valid = valid and rec['price'] > 0
                valid = valid and row.get('data_quality_ok') is True
                valid = valid and age_minutes(row.get('price_asof'), scan_time) <= BASE_QUOTE_LIMIT
                valid = valid and age_minutes(rec.get('price_asof'), now) <= QUOTE_LIMIT
                valid = valid and watch_age <= WATCH_LIMIT
                valid = valid and watch_time is not None and math.isfinite(age_minutes(rec.get('price_asof'), watch_time))
                valid = valid and age_minutes(data.get('generated_at'), now) <= FULL_LIMIT
                valid = valid and row.get('signal') in LEVEL and rec.get('watch_signal') in LEVEL
                valid = valid and rec.get('symbol') == row['symbol'] and rec.get('direction') == row['direction']
                if not valid:
                    rec.update(watch_signal='KEIN EINSTIEG', reason='Kursdaten fehlen oder sind veraltet – kein neuer Einstieg.')
                elif LEVEL.get(rec.get('watch_signal'), 0) > LEVEL.get(row.get('signal'), 0):
                    rec['watch_signal'] = row.get('signal', 'KEIN EINSTIEG')
    return data, watch


def build_full():
    import build_momentum_data as builder
    builder.main()


def main(force_full=False):
    now = datetime.now(timezone.utc)
    if os.getenv('GITHUB_EVENT_NAME') in ('schedule', 'workflow_run') and not scan_window(now):
        print('Outside the approved weekday 10:00–22:00 Vienna scan window.')
        return
    try:
        data = read_json(BASE / 'data.json')
    except (OSError, ValueError):
        data = {}
    errors, rebuilt = [], False
    if force_full or age_minutes(data.get('generated_at'), now) >= 55:
        try:
            process = subprocess.run([sys.executable, __file__, '--build-full'], cwd=ROOT, timeout=900)
            rebuilt = process.returncode == 0
            if not rebuilt:
                errors.append('Vollscan fehlgeschlagen.')
        except subprocess.TimeoutExpired:
            errors.append('Vollscan-Zeitlimit überschritten.')
    try:
        data = read_json(BASE / 'data.json')
    except (OSError, ValueError):
        data = {'generated_at': None, 'universes': {}}
        errors.append('Keine gültige Vollscan-Datei.')
    watch = {'generated_at': None, 'base_scan_generated_at': data.get('generated_at'), 'candidates': {}}
    try:
        process = subprocess.run([sys.executable, str(ROOT / 'scripts/build_momentum_watch.py')], cwd=ROOT, timeout=360)
        if process.returncode:
            raise ValueError('Candidate check failed')
        proposed = read_json(BASE / 'watch.json')
        data, watch = validate_pair(data, proposed, datetime.now(timezone.utc))
    except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
        errors.append(f'Kurzcheck gesperrt: {type(exc).__name__}')
    finished = datetime.now(timezone.utc)
    snapshot = {
        'version': 'momentum-snapshot-1', 'id': f"{os.getenv('GITHUB_RUN_ID', 'local')}-{finished.isoformat()}",
        'generated_at': finished.isoformat(), 'full_scan': data, 'watch': watch,
        'health': {'errors': errors, 'full_scan_rebuilt': rebuilt,
                   'trigger': os.getenv('GITHUB_EVENT_NAME', 'manual'), 'code_commit': os.getenv('GITHUB_SHA'),
                   'full_scan_limit_min': FULL_LIMIT, 'watch_limit_min': WATCH_LIMIT, 'quote_limit_min': QUOTE_LIMIT,
                   'history_quality': 'Legacy outcomes require revalidation; not executed trades.'}}
    atomic_json(BASE / 'snapshot.json', snapshot)
    print(json.dumps({'snapshot': snapshot['id'], 'full_scan': data.get('generated_at'),
                      'watch': watch.get('generated_at'), 'candidates': len(watch['candidates']), 'errors': errors}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--build-full', action='store_true')
    parser.add_argument('--force-full', action='store_true')
    args = parser.parse_args()
    build_full() if args.build_full else main(args.force_full)
