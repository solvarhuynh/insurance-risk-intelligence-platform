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


def check(base_url: str, screenshot: bool) -> None:
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
        assert page.locator("html").get_attribute("lang") == "en"
        assert page.locator(".sidebar-footer, .nav-copy, .nav-number").count() == 0
        assert page.evaluate("getComputedStyle(document.querySelector('.metric')).textAlign") == "center"
        assert int(page.evaluate("getComputedStyle(document.querySelector('.brand div > span')).fontWeight")) >= 700
        page.evaluate("document.fonts.ready")
        assert page.evaluate("document.fonts.check('500 14px Inter')")
        assert page.locator("#market-trend .main-svg").count() > 0
        assert page.locator("#market-trend").bounding_box()["height"] >= 290
        assert page.locator(".sidebar-data, .reading-note, .scope-note, .workspace footer").count() == 0
        assert page.locator("#market-metrics .metric-change.positive").count() == 2
        expect(page.locator("#market-metrics")).to_contain_text("Jan–Jul 2023 vs 2022")
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
        expect(page.locator("#market-metrics .metric-change.negative")).to_contain_text("+1.7 pp")
        assert before != page.locator("#market-metrics").inner_text()
        handle = page.locator("#market-years .rc-slider-handle-1")
        position = handle.bounding_box()
        rail = page.locator("#market-years .rc-slider-rail").bounding_box()
        page.mouse.move(position["x"] + position["width"] / 2, position["y"] + position["height"] / 2)
        page.mouse.down()
        page.mouse.move(rail["x"] + rail["width"] * .3, position["y"] + position["height"] / 2, steps=12)
        page.mouse.up()
        year = int(handle.get_attribute("aria-valuenow"))
        assert year > 2003
        expect(page.locator("#market-metrics")).to_contain_text(str(year))
        market_rows = csv_download(page, "#market-export")
        assert market_rows and {row["state"] for row in market_rows} == {"SP"}
        assert all(year <= int(row["month"][:4]) <= 2023 for row in market_rows)
        page.locator("#market-reset").click()
        expect(page.locator("#market-metrics .metric strong").first).to_have_text("3.05T")
        assert handle.get_attribute("aria-valuenow") == "2003"

        page.locator("#section label").filter(has_text=labels[1]).click()
        page.locator("#risk-metrics .metric strong").first.wait_for()
        expect(page.locator("#risk-takeaway")).to_contain_text("67.6%")
        assert page.locator("#risk-distribution .main-svg").count() > 0
        model_metrics = page.locator(".model-summary").inner_text()
        page.locator("#risk-state input").fill("SP")
        page.get_by_text("SP · São Paulo", exact=True).click()
        expect(page.locator("#risk-takeaway")).to_contain_text("45.0%")
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
        assert page.locator("#data-table tbody tr").count() == 15
        expect(page.locator("#data-table tbody tr").first).to_contain_text("2023-07")
        page.locator("#data-next").click()
        expect(page.locator("#data-page-status")).to_contain_text("Page 2")
        page.locator("#data-track label").filter(has_text="Motor risk").click()
        expect(page.locator("#data-count")).to_have_text("644 aggregate rows")
        expect(page.locator("#data-table thead")).to_contain_text("HasClaim share")
        expect(page.locator("#data-page-status")).to_contain_text("Page 1")
        page.locator("#data-state input").fill("SP")
        page.get_by_text("SP · São Paulo", exact=True).click()
        page.wait_for_function("[...document.querySelectorAll('#data-table tbody tr')].every(row => row.cells[0].textContent === 'SP')")
        assert page.locator("#data-prev").is_disabled()
        expect(page.locator(".benchmark-card")).to_contain_text("24 September 2026")
        for width in (390, 768, 1024, 1440, 1920):
            page.set_viewport_size({"width": width, "height": 1000})
            for label, title in zip(labels, ("Insurance market overview", "Motor risk & model insights", "See the data behind the platform")):
                page.locator("#section label").filter(has_text=label).click()
                page.get_by_role("heading", name=title, exact=True).wait_for()
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
        assert not errors, errors
        assert page.request.get(base_url + "/healthz").json()["status"] == "ok"
        browser.close()
    print("PASS: 3 English pages; monthly/annual totals; geography/year filters; resets; CSV/PNG exports; fixed historical metrics; 5 widths; local font; health; no browser/HTTP errors.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8050")
    parser.add_argument("--screenshot", action="store_true")
    args = parser.parse_args()
    check(args.url, args.screenshot)
