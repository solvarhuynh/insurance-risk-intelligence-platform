"""Checks for aggregate/filter integrity and safe operational boundaries."""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "pipeline"))

from dashboard.app import market_change, ratio, update_market, update_risk
from dashboard.data import latest_market_comparison, market_frames, risk_frames, snapshot
from manage import migration_paths, sql_batches


class PlatformTests(unittest.TestCase):
    def test_warehouse_snapshot_reconciles(self):
        data = snapshot()
        monthly, companies, products = market_frames("ALL", [2003, 2023])
        self.assertEqual(monthly.observations.sum(), data["counts"]["market_fact"])
        for frame in (companies, products):
            self.assertAlmostEqual(frame.premium.sum() / monthly.premium.sum(), 1, places=10)
            self.assertAlmostEqual(frame.claims.sum() / monthly.claims.sum(), 1, places=10)
        segments, scores = risk_frames("ALL")
        self.assertEqual(segments.observations.sum(), data["counts"]["risk_fact"])
        self.assertEqual(scores.observations.sum(), 20_000)

    def test_market_filters_keep_rankings_in_same_population(self):
        monthly, companies, products = market_frames("SP", [2018, 2020])
        for frame in (monthly, companies, products):
            self.assertEqual(set(frame.state), {"SP"})
            self.assertTrue(frame.year.between(2018, 2020).all())
            self.assertAlmostEqual(frame.premium.sum() / monthly.premium.sum(), 1, places=10)
        self.assertLess(monthly.observations.sum(), snapshot()["counts"]["market_fact"])

    def test_risk_filter_and_empty_population(self):
        segments, scores = risk_frames("SP")
        self.assertEqual(set(segments.state), {"SP"})
        self.assertEqual(set(scores.state), {"SP"})
        self.assertLess(scores.observations.sum(), 20_000)
        empty = update_risk("UNKNOWN_STATE")
        self.assertEqual(len(empty[1].data[0].y), 0)
        self.assertEqual(empty[-1], "No held-out scores match this selection")

    def test_ratio_and_callback_figures(self):
        self.assertIsNone(ratio(4, 0))
        self.assertIsNone(ratio(4, -1))
        self.assertEqual(ratio(4, 8), .5)
        monthly = update_market("SP", [2020, 2021])
        annual = update_market("SP", [2020, 2021], "annual")
        source = market_frames("SP", [2020, 2021])[0]
        self.assertEqual(len(monthly[1].data[0].y), 24)
        self.assertEqual(len(annual[1].data[0].y), 2)
        for result in (monthly, annual):
            self.assertAlmostEqual(sum(result[1].data[0].y), source.premium.sum() / 1e9, places=6)
        risk = update_risk("SP")
        self.assertEqual(sum(risk[1].data[0].y), risk_frames("SP")[1].observations.sum())

    def test_numeric_migration_order_and_go_boundary(self):
        self.assertEqual([int(p.name.split("__")[0][1:]) for p in migration_paths()], list(range(1, 15)))
        self.assertEqual(sql_batches("SELECT 'GO';\nGO\nSELECT 2;\nGO -- comment\n"), ["SELECT 'GO';", "SELECT 2;"])

    def test_latest_year_comparison_matches_months_and_geography(self):
        current = pd.DataFrame({"month": ["2023-01-01", "2023-02-01"], "year": [2023, 2023],
                                "premium": [100., 200.], "claims": [50., 100.]})
        previous = pd.DataFrame({"month": ["2022-01-01", "2022-02-01", "2022-03-01", "2022-01-01"],
                                 "state": ["SP", "SP", "SP", "RJ"], "premium": [200., 200., 99999., 99999.],
                                 "claims": [40., 40., 0., 0.]})
        with patch("dashboard.data.table", return_value=previous):
            comparison = latest_market_comparison(current, "SP")
        self.assertEqual(comparison["period"], "Jan–Feb 2023 vs 2022")
        self.assertAlmostEqual(comparison["premium_change"], -25)
        self.assertAlmostEqual(comparison["ratio_change_pp"], 30)
        self.assertIn("negative", market_change(comparison, "premium_change").children[0].className)
        self.assertIn("negative", market_change(comparison, "ratio_change_pp", lower_is_better=True).children[0].className)
        with patch("dashboard.data.table", return_value=previous.iloc[[0]]):
            self.assertEqual(latest_market_comparison(current, "SP"), {})
        self.assertEqual(latest_market_comparison(current.iloc[:0], "SP"), {})


if __name__ == "__main__":
    unittest.main()
