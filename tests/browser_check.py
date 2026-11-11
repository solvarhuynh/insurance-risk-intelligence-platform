"""Exercise the real Dash UI. Start the app first; optionally pass --screenshot."""
import argparse
import csv
import io
from pathlib import Path
from playwright.sync_api import sync_playwright


def check(base_url: str, screenshot: bool) -> None:
    errors = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel="msedge", headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1100}, device_scale_factor=1)
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.on("response", lambda response: errors.append(f"HTTP {response.status}: {response.url}") if response.status >= 500 else None)
        page.goto(base_url, wait_until="networkidle")
        page.locator("#market-metrics .metric strong").first.wait_for()
        assert page.locator("#market-trend .main-svg").count() > 0
        assert page.locator("#market-trend").bounding_box()["height"] >= 300
        assert "3.05" in page.locator("#market-metrics").inner_text()
        if screenshot:
            page.screenshot(path=str(Path(__file__).resolve().parents[1] / "dashboard/assets/preview.png"), full_page=True)
        before = page.locator("#market-metrics").inner_text()
        page.locator("#market-state input").fill("SP")
        page.locator("#market-state input").press("Enter")
        page.wait_for_function("document.querySelector('#market-metrics').innerText.includes('SP')")
        assert before != page.locator("#market-metrics").inner_text()
        with page.expect_download() as download:
            page.locator("#market-export").click()
        market_rows = list(csv.DictReader(io.StringIO(Path(download.value.path()).read_text(encoding="utf-8"))))
        assert market_rows and {row["state"] for row in market_rows} == {"SP"}
        # Move the year slider and verify the callback updates its population label.
        handle = page.locator("#market-years .rc-slider-handle-1")
        position = handle.bounding_box()
        rail = page.locator("#market-years .rc-slider-rail").bounding_box()
        page.mouse.move(position["x"] + position["width"]/2, position["y"] + position["height"]/2)
        page.mouse.down()
        page.mouse.move(rail["x"] + rail["width"] * .3, position["y"] + position["height"]/2, steps=10)
        page.mouse.up()
        year = handle.get_attribute("aria-valuenow")
        assert int(year) > 2003
        page.wait_for_function("year => document.querySelector('#market-metrics').innerText.includes(year)", arg=year)
        page.locator("#section label").filter(has_text="Motor Risk & ML").click()
        page.locator("#risk-metrics .metric strong").first.wait_for()
        assert page.locator("#risk-distribution .main-svg").count() > 0
        page.locator("#risk-state input").fill("SP")
        page.locator("#risk-state input").press("Enter")
        page.wait_for_timeout(1200)
        with page.expect_download() as download:
            page.locator("#risk-export").click()
        risk_rows = list(csv.DictReader(io.StringIO(Path(download.value.path()).read_text(encoding="utf-8"))))
        assert risk_rows and {row["state"] for row in risk_rows} == {"SP"}
        page.locator("#section label").filter(has_text="Chất lượng & Hiệu năng").click()
        page.get_by_text("Chất lượng nằm sau mỗi biểu đồ", exact=True).wait_for()
        assert page.locator(".reconcile-status").all_text_contents() == ["Khớp", "Khớp"]
        for width in (390, 768):
            page.set_viewport_size({"width": width, "height": 900})
            for label in ("Thị trường bảo hiểm", "Motor Risk & ML", "Chất lượng & Hiệu năng"):
                page.locator("#section label").filter(has_text=label).click()
                page.wait_for_timeout(700)
                assert page.evaluate("document.documentElement.scrollWidth <= innerWidth"), f"Overflow: {width}, {label}"
        assert not errors, errors
        assert page.request.get(base_url + "/healthz").json()["status"] == "ok"
        browser.close()
    print("PASS: three pages, state/year filters, CSV contents, health endpoint and responsive widths; no browser/HTTP500 errors.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8050")
    parser.add_argument("--screenshot", action="store_true")
    args = parser.parse_args()
    check(args.url, args.screenshot)
