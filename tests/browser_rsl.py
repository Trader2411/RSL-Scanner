"""Live mobile smoke test for the public RSL scanner (no synthetic data)."""
import json
import os
from pathlib import Path
from playwright.sync_api import sync_playwright

base = os.environ["PAGE_URL"].rstrip("/")
url = base + "/"
out = Path("qa-output")
out.mkdir(exist_ok=True)
page_errors = []
with sync_playwright() as playwright:
    browser = playwright.chromium.launch(headless=True)
    context = browser.new_context(
        viewport={"width": 390, "height": 844},
        is_mobile=True,
        has_touch=True,
        device_scale_factor=1,
        locale="de-AT",
        timezone_id="Europe/Vienna",
    )
    page = context.new_page()
    page.on("pageerror", lambda error: page_errors.append(str(error)))
    response = page.goto(url, wait_until="domcontentloaded", timeout=60000)
    assert response is not None and response.status == 200, "RSL start page is not available"
    assert page.title() == "RSL Scanner", "Wrong start page served"
    page.wait_for_function(
        "() => !!document.querySelector('#rows tr') && document.querySelector('#status').textContent.includes('Quelldaten')",
        timeout=60000,
    )
    count = page.locator("#rows tr").count()
    assert count > 0, "RSL table is empty"
    index_count = page.locator("#indexButtons button").count()
    assert index_count >= 1, "RSL index selection is missing"
    page.locator("#refresh").click()
    page.wait_for_function(
        "() => document.querySelector('#status').textContent.includes('Quelldaten') && !document.querySelector('#status').textContent.includes('geladen…') && !loading",
        timeout=60000,
    )
    assert page.locator("#rows tr").count() > 0, "RSL data disappeared after refresh"
    assert "Abruf fehlgeschlagen" not in page.locator("#status").inner_text(), "Live refresh failed"
    page.locator("#rows .chart-link").first.click()
    assert page.locator("#chartModal").get_attribute("aria-hidden") == "false", "Stock chart does not open"
    assert page.locator("#chartTitle").inner_text().strip(), "Stock chart title is missing"
    page.locator("#chartClose").click()
    assert page.locator("#chartModal").get_attribute("aria-hidden") == "true", "Stock chart does not close"
    page.screenshot(path=str(out / "rsl-mobile.png"), full_page=True)
    assert not page_errors, "RSL JavaScript errors: " + "; ".join(page_errors)
    print("RSL_BROWSER_VERIFIED " + json.dumps({
        "url": url,
        "browser": "Chromium mobile emulation",
        "indexes": index_count,
        "visible_stocks": count,
        "checks": ["load", "refresh", "index selector", "table", "chart open/close"],
        "page_errors": page_errors,
    }))
    browser.close()
