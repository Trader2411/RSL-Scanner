"""Synthetic regressions for price timing and signal eligibility; no provider calls."""
import json
import math
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import build_momentum_data as full
import build_momentum_watch as watch


def bars(index, prices, volume=100.):
    return pd.DataFrame({"Open": prices, "High": np.array(prices) + .1,
                         "Low": np.array(prices) - .1, "Close": prices,
                         "Volume": volume}, index=pd.to_datetime(index))


def eligible_metrics(**updates):
    result = dict(symbol="TEST", latest_age_min=5, score_long=80, score_short=80,
                  day_pct=3, m1=1, m2=2, m3=3, rel_index=1, rel_sector=1,
                  stability_long=80, stability_short=80, intervals=12,
                  volume_ratio=1.5, open_check_long=.5, open_check_short=-.5)
    result.update(updates)
    result["data_quality_issues"] = full.data_quality_issues(result)
    result["data_quality_ok"] = not result["data_quality_issues"]
    return result


class SignalReliability(unittest.TestCase):
    def test_full_scan_excludes_unfinished_and_malformed_bars(self):
        frame = bars(["2026-09-28T14:00Z", "2026-09-28T14:15Z", "2026-09-28T14:16Z"], [100., 200., 300.])
        now = datetime(2026, 9, 28, 14, 22, tzinfo=timezone.utc)
        self.assertEqual(full.complete_bars(frame, now)["Close"].tolist(), [100.])
        frame.loc[frame.index[0], "High"] = 99.
        self.assertTrue(full.complete_bars(frame, now).empty)

    def test_unidentified_timezone_is_rejected(self):
        frame = bars(["2026-09-28T14:00"], [100.])
        self.assertTrue(full.normalize_download(frame).empty)

    def test_previous_close_does_not_include_first_postmarket_candle(self):
        frame = bars(["2026-09-25T15:45-04:00", "2026-09-25T16:00-04:00"], [100., 120.])
        self.assertEqual(full.previous_regular_close(frame, datetime(2026, 9, 28).date()), 100.)

    def test_missing_previous_regular_close_is_not_replaced_by_postmarket(self):
        frame = bars(["2026-09-25T17:00-04:00"], [120.])
        self.assertIsNone(full.previous_regular_close(frame, datetime(2026, 9, 28).date()))

    def test_dax_session_preserves_morning_bars_and_excludes_close_start(self):
        frame = bars(["2026-09-28T07:00Z", "2026-09-28T15:15Z", "2026-09-28T15:30Z"], [100., 101., 102.])
        result = full.session_rows(frame, datetime(2026, 9, 28).date(), "SAP.DE")
        self.assertEqual(result["Close"].tolist(), [100., 101.])

    def test_crypto_uses_local_calendar_day(self):
        frame = bars(["2026-09-27T21:45Z", "2026-09-27T22:00Z", "2026-09-28T21:45Z", "2026-09-28T22:00Z"], [99., 100., 101., 102.])
        result = full.session_rows(frame, datetime(2026, 9, 28).date(), "BTC-USD")
        self.assertEqual(result["Close"].tolist(), [100., 101.])

    def test_returns_have_exact_one_two_three_hour_horizons(self):
        close = pd.Series(range(100, 113), index=pd.date_range("2026-09-28T10:00Z", periods=13, freq="15min"))
        self.assertAlmostEqual(full.ret_at_hours(close, 1), (112 / 108 - 1) * 100)
        self.assertAlmostEqual(full.ret_at_hours(close, 2), (112 / 104 - 1) * 100)
        self.assertAlmostEqual(full.ret_at_hours(close, 3), 12.)
        self.assertAlmostEqual(full.previous_hour_return(close), (108 / 104 - 1) * 100)

    def test_full_scan_horizons_do_not_bridge_internal_gaps(self):
        close = pd.Series(range(100, 113), index=pd.date_range("2026-09-28T10:00Z", periods=13, freq="15min"))
        close = close.drop(close.index[-3])
        for hours in (1, 2, 3):
            self.assertIsNone(full.ret_at_hours(close, hours))
        self.assertIsNone(full.previous_hour_return(close))

    def test_watch_horizons_do_not_bridge_internal_gaps(self):
        close = pd.Series(range(100, 113), index=pd.date_range("2026-09-28T10:00Z", periods=13, freq="5min"))
        self.assertAlmostEqual(watch.return_at_minutes(close, 60), 12.)
        close = close.drop(close.index[-2])
        for minutes in (15, 30, 60):
            self.assertIsNone(watch.return_at_minutes(close, minutes))

    def test_rsi_handles_uninterrupted_rise_fall_and_flat_prices(self):
        self.assertEqual(full.rsi14(pd.Series(range(100, 120))), 100.)
        self.assertEqual(full.rsi14(pd.Series(range(120, 100, -1))), 0.)
        self.assertEqual(full.rsi14(pd.Series([100.] * 20)), 50.)

    def test_one_jump_cannot_match_persistent_momentum_stability(self):
        smooth = pd.Series(np.linspace(100, 103, 13))
        jump = pd.Series([100.] * 6 + [103.] * 7)
        self.assertGreater(full.stability(smooth, "long")[0], full.stability(jump, "long")[0] + 40)

    def test_volume_compares_only_matching_completed_period(self):
        frame = bars(["2026-09-25T10:00-04:00", "2026-09-25T10:15-04:00", "2026-09-28T10:00-04:00"], [100.] * 3)
        frame["Volume"] = [100., 900., 200.]
        sess = frame.iloc[-1:]
        now = datetime.fromisoformat("2026-09-28T10:22-04:00")
        self.assertEqual(full.volume_ratio(frame, sess, now), 2.)
        frame.loc[frame.index[-1], "Volume"] = np.nan
        self.assertIsNone(full.volume_ratio(frame, frame.iloc[-1:], now))

    def test_stale_or_unaligned_index_comparison_is_not_used(self):
        frame = bars(["2026-09-25T15:45-04:00", "2026-09-28T10:00-04:00"], [100., 101.])
        self.assertAlmostEqual(full.benchmark_return(frame, datetime.fromisoformat("2026-09-28T10:22-04:00")), 1.)
        self.assertIsNone(full.benchmark_return(frame, datetime.fromisoformat("2026-09-28T11:01-04:00")))
        self.assertIsNone(full.benchmark_return(frame, datetime.fromisoformat("2026-09-28T10:45-04:00"), asof=pd.Timestamp("2026-09-28T10:15-04:00")))

    def test_missing_core_data_blocks_entry_even_with_high_score(self):
        now = datetime.fromisoformat("2026-09-28T13:00-04:00")
        self.assertEqual(full.signal_for(eligible_metrics(), "long", now, 5), "EINSTIEG")
        for missing in ("day_pct", "m1", "m2", "m3", "volume_ratio", "rel_index", "rel_sector"):
            metrics = eligible_metrics(**{missing: None})
            self.assertEqual(full.signal_for(metrics, "long", now, 5), "KEIN EINSTIEG", missing)

    def test_unknown_equity_sector_is_missing_but_non_equity_is_not_applicable(self):
        self.assertIsNone(full.sector_etf(""))
        self.assertIsNone(full.sector_etf("unrecognized-sector"))
        self.assertEqual(full.sector_etf("Technology"), "XLK")
        equity = eligible_metrics(rel_sector=None, sector_benchmark_kind="not_applicable")
        self.assertFalse(equity["data_quality_ok"])
        for symbol in ("BTC-USD", "GC=F"):
            self.assertTrue(eligible_metrics(symbol=symbol, rel_sector=None, sector_benchmark_kind="not_applicable")["data_quality_ok"])

    def test_invalid_high_score_cannot_displace_usable_shortlist(self):
        usable = [(dict(symbol=str(i)), dict(data_quality_ok=True, score_long=60 + i)) for i in range(6)]
        blocked = [(dict(symbol="blocked"), dict(data_quality_ok=False, score_long=99))]
        ranked = full.ranked_candidates(usable + blocked, "long", 5)
        self.assertEqual([meta["symbol"] for meta, _ in ranked], ["5", "4", "3", "2", "1"])

    def test_session_and_source_age_gates_remain_fail_closed(self):
        metrics = eligible_metrics()
        for age in (-1, 46, math.inf):
            self.assertEqual(full.signal_for(metrics, "long", datetime.fromisoformat("2026-09-28T13:00-04:00"), age), "KEIN EINSTIEG")
        for stamp in ("2026-09-28T16:00-04:00", "2026-09-27T13:00-04:00"):
            self.assertEqual(full.signal_for(metrics, "long", datetime.fromisoformat(stamp), 5), "KEIN EINSTIEG")
        dax = eligible_metrics(symbol="SAP.DE")
        self.assertEqual(full.signal_for(dax, "long", datetime.fromisoformat("2026-09-28T09:30+02:00"), 5), "EINSTIEG")
        self.assertEqual(full.signal_for(dax, "long", datetime.fromisoformat("2026-09-28T17:30+02:00"), 5), "KEIN EINSTIEG")

    def test_watch_rejects_infinite_ohlc_and_missing_scan_reference(self):
        frame = bars(["2026-09-28T14:00Z"], [100.])
        frame["High"] = math.inf
        self.assertTrue(watch.frame_for(frame, "X", datetime.fromisoformat("2026-09-28T14:10+00:00"), True).empty)
        self.assertEqual(watch.monitor_signal("EINSTIEG", "LONG", 1, 1, 1, 1, None)[0], "KEIN EINSTIEG")

    def test_full_build_publishes_quality_and_completed_source_timestamp(self):
        fixed = datetime(2026, 9, 28, 17, 22, tzinfo=timezone.utc)
        class FixedDatetime(datetime):
            @classmethod
            def now(cls, tz=None):
                return fixed.astimezone(tz) if tz else fixed.replace(tzinfo=None)
        prior_index = pd.date_range("2026-09-25T04:00-04:00", "2026-09-25T15:45-04:00", freq="15min")
        today_index = pd.date_range("2026-09-28T04:00-04:00", "2026-09-28T13:15-04:00", freq="15min")
        prior = bars(prior_index, [100.] * len(prior_index))
        today = bars(today_index, np.linspace(100., 110., len(today_index)), volume=200.)
        asset = pd.concat([prior, today])
        benchmark = pd.concat([prior, bars(today_index, [100.] * len(today_index))])
        meta = {"symbol": "TEST", "name": "Synthetic fixture", "indexes": ["S&P 500"], "sector": "Technology"}
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "data.json"
            with patch.object(full, "datetime", FixedDatetime), patch.object(full, "OUT", output), patch.object(full, "load_universe", return_value=[meta]), patch.object(full, "download_intraday", return_value=({"TEST": asset, "SPY": benchmark, "XLK": benchmark}, [])), patch.object(full, "enrich_candidate_wkns", side_effect=lambda universes: universes), patch.object(full, "update_momentum_history"):
                full.main()
            payload = json.loads(output.read_text())
        row = payload["universes"]["S&P 500"]["candidates"]["long"][0]
        self.assertEqual(row["price_asof"], "2026-09-28T13:15:00-04:00")
        self.assertLess(row["reference_price"], 110.)
        self.assertTrue(row["data_quality_ok"])
        self.assertEqual(row["data_quality_issues"], [])
        self.assertEqual(payload["coverage"]["with_quality_data"], 1)
        self.assertEqual(payload["generated_at"], fixed.isoformat())


if __name__ == "__main__":
    unittest.main()
