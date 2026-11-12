"""Verify real dashboard interactions using Playwright and installed Microsoft Edge."""

import argparse
import csv
import io
from pathlib import Path

from playwright.sync_api import expect, sync_playwright


def csv_download(page, button):
    with page.expect_download() as download:
        page.locator(button).click()
    return list(csv.DictReader(io.StringIO(Path(download.value.path()).read_text(encoding="utf-8"))))


def check(base_url: str, screenshot: bool, screenshots_dir: Path | None = None) -> None:
    errors = []
    labels = ("Market", "Motor risk", "Data")
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel="msedge", headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1000}, device_scale_factor=1)
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.on("response", lambda response: errors.append(f"HTTP {response.status}: {response.url}") if response.status >= 400 else None)
        page.goto(base_url, wait_until="networkidle")
        page.locator("#market-metrics .metric strong").first.wait_for()
        expect(page.locator("#market-metrics .metric strong").first).to_have_text("3.05T")
        expect(page.locator("#market-takeaway")).to_contain_text("24.1%")
        expect(page.locator("#market-story")).to_contain_text("63.2%")
        assert page.evaluate("document.querySelector('#market-trend .js-plotly-plot').layout.showlegend")
        assert page.locator("html").get_attribute("lang") == "en"
        assert page.locator(".sidebar-footer, .nav-copy, .nav-number").count() == 0
        assert page.evaluate("getComputedStyle(document.querySelector('.metric')).textAlign") == "center"
        assert int(page.evaluate("getComputedStyle(document.querySelector('.brand div > span')).fontWeight")) >= 700
        page.evaluate("document.fonts.ready")
        assert page.evaluate("document.fonts.check('500 14px Inter')")
        assert page.locator("#market-trend .main-svg").count() > 0
        assert page.locator("#market-trend").bounding_box()["height"] >= 290
        assert page.locator(".sidebar-data, .reading-note, .scope-note, .workspace footer").count() == 0
        for index, expected, tone in ((0, "▲ +1056.1%", "positive"), (1, "▲ +413.5%", "positive"),
                                      (2, "▼ -25.9 pp", "negative"), (3, "▲ +127.4%", "positive")):
            card = page.locator("#market-metrics .metric").nth(index)
            expect(card.locator(f".metric-change.{tone}")).to_contain_text(expected)
            assert tone in card.get_attribute("class")
        expect(page.locator("#market-metrics")).to_contain_text("Jan–Jul 2023 vs Jan–Jul 2003")
        assert page.evaluate("document.querySelector('#market-products .js-plotly-plot').layout.yaxis.ticklabelstandoff") == 18
        assert page.evaluate("document.querySelector('#market-products .js-plotly-plot').layout.yaxis.ticktext.every(t => !t.includes('<br>'))")
        assert page.locator(".chart-card").filter(has=page.locator("#market-products")).locator(".chart-footnote").count() == 0
        if screenshot:
            page.screenshot(path=str(Path(__file__).resolve().parents[1] / "dashboard/assets/preview.png"), full_page=True)
        page.locator("#market-trend").hover()
        with page.expect_download() as image_download:
            page.locator('#market-trend .modebar-btn[data-title="Download plot as a PNG"]').click()
        assert Path(image_download.value.path()).read_bytes().startswith(b"\x89PNG\r\n\x1a\n")

        # Monthly/annual charts must aggregate exactly the same selected population.
        before = page.locator("#market-metrics").inner_text()
        page.locator("#market-grain label").filter(has_text="Annual").click()
        page.wait_for_function("document.querySelector('#market-trend .js-plotly-plot').data[0].x.length === 21")
        assert before == page.locator("#market-metrics").inner_text()
        page.locator("#market-grain label").filter(has_text="Monthly").click()
        page.wait_for_function("document.querySelector('#market-trend .js-plotly-plot').data[0].x.length > 200")
        page.locator("#market-state input").fill("SP")
        page.get_by_text("SP · São Paulo", exact=True).click()
        expect(page.locator("#market-metrics")).to_contain_text("SP")
        expect(page.locator("#market-metrics .metric-change.negative").filter(has_text="-21.3 pp")).to_contain_text("▼ -21.3 pp")
        assert before != page.locator("#market-metrics").inner_text()
        start_badge = page.locator("#market-metrics .metric-change").first.inner_text()
        handle = page.locator("#market-years .rc-slider-handle-1")
        position = handle.bounding_box()
        rail = page.locator("#market-years .rc-slider-rail").bounding_box()
        page.mouse.move(position["x"] + position["width"] / 2, position["y"] + position["height"] / 2)
        page.mouse.down()
        page.mouse.move(rail["x"] + rail["width"] * .3, position["y"] + position["height"] / 2, steps=12)
        page.mouse.up()
        year = int(handle.get_attribute("aria-valuenow"))
        assert year > 2003
        expect(page.locator("#market-metrics .comparison-period").first).to_have_text(f"Jan–Jul 2023 vs Jan–Jul {year}")
        assert start_badge != page.locator("#market-metrics .metric-change").first.inner_text()
        market_rows = csv_download(page, "#market-export")
        assert market_rows and {row["state"] for row in market_rows} == {"SP"}
        assert all(year <= int(row["month"][:4]) <= 2023 for row in market_rows)
        page.locator("#market-reset").click()
        expect(page.locator("#market-metrics .metric strong").first).to_have_text("3.05T")
        expect(page.locator("#market-metrics .comparison-period").first).to_have_text("Jan–Jul 2023 vs Jan–Jul 2003")
        assert handle.get_attribute("aria-valuenow") == "2003"

        page.locator("#section label").filter(has_text=labels[1]).click()
        page.locator("#risk-metrics .metric strong").first.wait_for()
        expect(page.locator("#risk-takeaway")).to_contain_text("67.6%")
        assert page.locator("#risk-metrics .metric").count() == 3
        expect(page.locator("#risk-model-metric")).to_contain_text("20,000 filtered held-out")
        expect(page.locator("#risk-story")).to_contain_text("69.9%")
        assert page.evaluate("document.querySelector('#risk-distribution .js-plotly-plot').data[0].width") == .05
        assert page.locator("#risk-distribution .main-svg").count() > 0
        model_metrics = page.locator(".model-summary").inner_text()
        page.locator("#risk-state input").fill("SP")
        page.get_by_text("SP · São Paulo", exact=True).click()
        expect(page.locator("#risk-takeaway")).to_contain_text("45.0%")
        expect(page.locator("#risk-model-metric")).not_to_contain_text("20,000 filtered held-out")
        assert model_metrics == page.locator(".model-summary").inner_text()
        risk_rows = csv_download(page, "#risk-export")
        assert risk_rows and {row["state"] for row in risk_rows} == {"SP"}
        assert "Không rõ" not in str(risk_rows)
        page.locator("#risk-reset").click()
        expect(page.locator("#risk-takeaway")).to_contain_text("67.6%")
        assert page.locator(".sidebar-data, .reading-note, .scope-note, .workspace footer").count() == 0
        expect(page.locator(".chart-card").filter(has=page.locator("#risk-distribution"))).to_contain_text("not validated future claim probabilities")

        page.locator("#section label").filter(has_text=labels[2]).click()
        page.get_by_role("heading", name="See the data behind the platform", exact=True).wait_for()
        expect(page.locator("#data-count")).to_have_text("6,669 aggregate rows")
        expect(page.locator(".benchmark-query")).to_have_count(2)
        page.wait_for_load_state("networkidle")
        assert page.locator("#data-table tbody tr").count() == 15
        expect(page.locator("#data-table tbody tr").first).to_contain_text("2023-07")
        page.locator("#data-next").click()
        try:
            expect(page.locator("#data-page-status")).to_contain_text("Page 2")
        except AssertionError:
            print("Navigation diagnostic:", page.url, page.locator("h1").all_text_contents(), errors)
            if screenshots_dir:
                screenshots_dir.mkdir(parents=True, exist_ok=True)
                page.screenshot(path=str(screenshots_dir / "failure.png"), full_page=True)
            raise
        page.locator("#data-track label").filter(has_text="Motor risk").click()
        expect(page.locator("#data-count")).to_have_text("644 aggregate rows")
        expect(page.locator("#data-table thead")).to_contain_text("HasClaim share")
        expect(page.locator("#data-page-status")).to_contain_text("Page 1")
        page.locator("#data-state input").fill("SP")
        page.get_by_text("SP · São Paulo", exact=True).click()
        page.wait_for_function("""() => {
            const rows = [...document.querySelectorAll('#data-table tbody tr')];
            return rows.length > 0 && rows.every(row => row.cells[0].textContent === 'SP');
        }""")
        assert page.locator("#data-prev").is_disabled()
        expect(page.locator(".benchmark-card")).to_contain_text("24 September 2026")
        expect(page.locator("#benchmark-query-1")).to_contain_text("Company by month")
        expect(page.locator("#benchmark-query-1")).to_contain_text("317,528")
        expect(page.locator("#benchmark-query-1")).to_contain_text("3,364")
        expect(page.locator("#benchmark-query-2")).to_contain_text("3,734")
        page.locator("#data-state input").fill("All states")
        page.locator("#data-state .VirtualizedSelectOption").filter(has_text="All states").click()
        page.locator("#data-track label").filter(has_text="SUSEP market").click()
        expect(page.locator("#data-count")).to_have_text("6,669 aggregate rows")
        # Check real rendered hover content, including units and population.
        for graph_id, point, expected in (("risk-observed", 5, "Band size:"),
                                          ("risk-age", 2, "HasClaim count:"),
                                          ("market-companies", 9, "of all selected premiums")):
            label = labels[0] if graph_id.startswith("market") else labels[1]
            page.locator("#section label").filter(has_text=label).click()
            page.locator(f"#{graph_id} .main-svg").first.wait_for()
            page.wait_for_function("id => document.querySelector('#' + id + ' .js-plotly-plot')?.data?.length > 0", arg=graph_id)
            page.evaluate("""({id, point}) => Plotly.Fx.hover(document.querySelector('#' + id + ' .js-plotly-plot'),
                [{curveNumber: 0, pointNumber: point}])""", {"id": graph_id, "point": point})
            expect(page.locator(f"#{graph_id} .hoverlayer")).to_contain_text(expected)
            page.evaluate("id => Plotly.Fx.unhover(document.querySelector('#' + id + ' .js-plotly-plot'))", graph_id)
        for width in (390, 768, 1024, 1440, 1920):
            page.set_viewport_size({"width": width, "height": 1000})
            for label, title in zip(labels, ("Insurance market overview", "Motor risk & model insights", "See the data behind the platform")):
                page.locator("#section label").filter(has_text=label).click()
                page.get_by_role("heading", name=title, exact=True).wait_for()
                if label == "Data":
                    page.locator("#benchmark-query-1").wait_for()
                else:
                    page.locator(".chart .main-svg").first.wait_for()
                page.wait_for_function("!document.querySelector('[data-dash-is-loading=true]')")
                page.wait_for_function("""() => [...document.querySelectorAll('.js-plotly-plot')].every(
                    el => el.data?.length && el._fullLayout && Math.abs(el._fullLayout.width - el.getBoundingClientRect().width) < 2
                )""")
                assert page.evaluate("document.documentElement.scrollWidth <= innerWidth"), f"Overflow: {width}, {label}"
                assert page.locator(".snapshot-time").is_visible()
                for chart in page.locator(".chart").all():
                    assert chart.bounding_box()["width"] >= 240, f"Unusable chart width: {width}, {label}"
                assert "Không rõ" not in page.locator("body").inner_text()
                assert page.locator("#data-table").count() == (1 if label == "Data" else 0)
                assert page.locator("#risk-model-metric").count() == (1 if label == "Motor risk" else 0)
                if screenshots_dir:
                    screenshots_dir.mkdir(parents=True, exist_ok=True)
                    stem = ("market", "risk", "data")[labels.index(label)]
                    # Capture the resting view after hover, keyboard, and scrolled chart checks.
                    page.mouse.move(0, 0)
                    page.evaluate("document.activeElement?.blur(); window.scrollTo(0, 0)")
                    page.screenshot(path=str(screenshots_dir / f"{stem}-{width}.png"), full_page=True)
                    if width == 1440:
                        for chart_id in (("market-trend", "market-companies", "market-products") if stem == "market"
                                         else ("risk-distribution", "risk-observed") if stem == "risk" else ()):
                            page.locator(".chart-card").filter(has=page.locator(f"#{chart_id}")).screenshot(
                                path=str(screenshots_dir / f"{chart_id}.png"))
                        if stem == "data":
                            page.locator(".data-panel").screenshot(path=str(screenshots_dir / "data-explorer.png"))
                            page.locator(".benchmark-card").screenshot(path=str(screenshots_dir / "sql-benchmark.png"))
        assert not errors, errors
        assert page.request.get(base_url + "/healthz").json()["status"] == "ok"
        browser.close()
    print("PASS: 3 English pages; population grouping; monthly/annual totals; geography/year filters; resets; CSV/PNG exports; hover; histogram width; before/after SQL reads; fixed historical metrics; 5 widths; local font; health; no browser/HTTP errors.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8050")
    parser.add_argument("--screenshot", action="store_true")
    parser.add_argument("--screenshots-dir", type=Path, help="Optional output directory for all pages at five widths and README chart crops")
    args = parser.parse_args()
    check(args.url, args.screenshot, args.screenshots_dir)
