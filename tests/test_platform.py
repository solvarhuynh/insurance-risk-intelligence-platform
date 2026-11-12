"""Checks for aggregate/filter integrity and safe operational boundaries."""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "pipeline"))

from dashboard.app import explorer_page, market_change, platform_page, ratio, update_market, update_risk
from dashboard.data import latest_market_comparison, market_frames, risk_frames, snapshot, table
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
        self.assertEqual(sum(empty[1].data[0].y), 0)
        self.assertEqual(empty[5], "No held-out scores match this selection")

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
                                "premium": [100., 200.], "claims": [50., 100.], "observations": [20, 30]})
        previous = pd.DataFrame({"month": ["2022-01-01", "2022-02-01", "2022-03-01", "2022-01-01"],
                                 "state": ["SP", "SP", "SP", "RJ"], "premium": [200., 200., 99999., 99999.],
                                 "claims": [40., 40., 0., 0.], "observations": [10, 10, 999, 999]})
        with patch("dashboard.data.table", return_value=previous):
            comparison = latest_market_comparison(current, "SP")
        self.assertEqual(comparison["period"], "Jan–Feb 2023 vs 2022")
        self.assertAlmostEqual(comparison["premium_change"], -25)
        self.assertAlmostEqual(comparison["claims_change"], 87.5)
        self.assertAlmostEqual(comparison["ratio_change_pp"], 30)
        self.assertAlmostEqual(comparison["observations_change"], 150)
        self.assertIn("negative", market_change(comparison, "premium_change").children[0].className)
        self.assertIn("positive", market_change(comparison, "ratio_change_pp", lower_is_better=True).children[0].className)
        self.assertIn("▼", market_change(comparison, "premium_change").children[0].children)
        self.assertIn("▲", market_change({"ratio_change_pp": 1.7, "period": "2023 vs 2022"}, "ratio_change_pp", lower_is_better=True).children[0].children)
        self.assertIn("positive", market_change(comparison, "claims_change").children[0].className)
        self.assertIn("positive", market_change(comparison, "observations_change").children[0].className)
        unchanged = market_change({"premium_change": -0.001, "period": "2023 vs 2022"}, "premium_change")
        self.assertIn("neutral", unchanged.children[0].className)
        self.assertIn("● 0.0%", unchanged.children[0].children)
        with patch("dashboard.data.table", return_value=previous.iloc[[0]]):
            self.assertEqual(latest_market_comparison(current, "SP"), {})
        self.assertEqual(latest_market_comparison(current.iloc[:0], "SP"), {})

    def test_data_explorer_pages_real_aggregate_rows(self):
        headings, rows, total, page, pages = explorer_page("market")
        self.assertEqual(total, len(table("market", "monthly")))
        self.assertEqual((page, len(rows), rows[0][:2]), (0, 15, ["2023-07", "AC"]))
        self.assertIn("Claims / premiums", headings)
        self.assertGreater(pages, 1)
        _, filtered, filtered_total, last, _ = explorer_page("market", "SP", 99999)
        self.assertTrue(filtered_total > 0 and all(row[1] == "SP" for row in filtered))
        self.assertTrue(last < 99999)
        headings, rows, total, _, _ = explorer_page("risk")
        self.assertEqual(total, len(table("risk", "segments")))
        self.assertEqual(len(rows), 15)
        self.assertIn("HasClaim share", headings)
        self.assertNotIn("PolicyId", headings)

    def test_score_bins_preserve_counts_and_observed_denominators(self):
        for state in ("ALL", "SP", "AC"):
            with self.subTest(state=state):
                scores = risk_frames(state)[1]
                _, distribution, observed, *_ = update_risk(state)
                self.assertEqual(len(distribution.data[0].x), 20)
                self.assertAlmostEqual(float(distribution.data[0].width), .05)
                self.assertEqual(sum(distribution.data[0].y), scores.observations.sum())
                self.assertAlmostEqual(distribution.data[0].x[0] - .025, 0)
                self.assertAlmostEqual(distribution.data[0].x[-1] + .025, 1)
                recovered_positives = recovered_scores = 0
                for count, share, mean, detail in zip(distribution.data[0].y, observed.data[0].y,
                                                       observed.data[1].y, observed.data[0].customdata):
                    self.assertEqual(count, detail[2])
                    if count:
                        recovered_positives += count * share / 100
                        recovered_scores += count * mean / 100
                    else:
                        self.assertTrue(pd.isna(share) and pd.isna(mean))
                self.assertAlmostEqual(recovered_positives, scores.positives.sum())
                self.assertAlmostEqual(recovered_scores, scores.score_sum.sum())
                self.assertFalse(observed.data[0].connectgaps)

    def test_age_reference_uses_filtered_ratio_of_sums(self):
        for state in ("ALL", "SP"):
            segments = risk_frames(state)[0]
            age = update_risk(state)[3]
            self.assertAlmostEqual(age.layout.shapes[0].y0, 100 * segments.has_claim.sum() / segments.observations.sum())
            self.assertEqual(sum(row[0] for row in age.data[0].customdata), segments.observations.sum())
            self.assertEqual(sum(row[1] for row in age.data[0].customdata), segments.has_claim.sum())

    def test_benchmark_preserves_before_after_and_reduction(self):
        cards = platform_page()[-1].children[2].children
        for card, row in zip(cards, snapshot()["performance"]):
            before, _, after = card.children[1].children
            self.assertEqual(before.children[1].children, f"{row['before_reads']:,}")
            self.assertEqual(after.children[1].children, f"{row['after_reads']:,}")
            expected = 100 * (1 - row["after_reads"] / row["before_reads"])
            self.assertEqual(card.children[2].children[0].children, f"{expected:.2f}%")

    def test_ranking_shares_use_all_premiums_not_only_top_n(self):
        result = update_market("SP", [2018, 2020])
        total = market_frames("SP", [2018, 2020])[0].premium.sum()
        for chart in result[2:4]:
            for premium_billions, detail in zip(chart.data[0].x, chart.data[0].customdata):
                self.assertAlmostEqual(float(detail[1]), 100 * premium_billions * 1e9 / total)


if __name__ == "__main__":
    unittest.main()
