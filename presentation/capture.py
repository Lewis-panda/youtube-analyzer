from playwright.sync_api import sync_playwright
import os
OUT="presentation/assets"; os.makedirs(OUT,exist_ok=True)
def panel(page, heading):
    return page.locator(f"xpath=//h3[contains(normalize-space(.), '{heading}')]/ancestor::*[(self::section or self::article) and contains(@class,'panel')][1]").first
def shot(loc, name):
    try:
        loc.scroll_into_view_if_needed(timeout=4000)
        loc.screenshot(path=f"{OUT}/{name}.png")
        print("  ok", name)
    except Exception as e:
        print("  FAIL", name, repr(e)[:80])
with sync_playwright() as p:
    b=p.chromium.launch(); pg=b.new_page(viewport={"width":1500,"height":1000},device_scale_factor=2)
    pg.goto("http://127.0.0.1:8000/", wait_until="networkidle", timeout=30000)
    pg.locator(".case-row", has_text="嘟嘟").first.click()
    pg.wait_for_selector(".channel-report-card", timeout=15000)
    pg.add_style_tag(content=".view-tabs{position:static !important} .info-tip{display:none !important}")
    pg.wait_for_timeout(1200)
    def tab(name):
        pg.locator(".view-tabs button", has_text=name).first.click(); pg.wait_for_timeout(1400)
    # overview
    shot(pg.locator(".channel-report-card").first, "ov_card")
    shot(panel(pg,"互動概況"), "ov_engagement")
    # audience
    tab("觀眾")
    shot(panel(pg,"觀眾活躍度"), "aud_tiers")
    shot(panel(pg,"觀眾類型與策略用途"), "aud_personas")
    # sentiment/conflict
    tab("情緒")
    shot(panel(pg,"整體被讚的面向"), "sent_aspect_pos")
    shot(panel(pg,"高衝突影片"), "sent_conflict")
    # content
    tab("內容")
    shot(panel(pg,"題材一覽"), "con_theme")
    shot(panel(pg,"近期影片時間軸"), "con_timeline")
    b.close()
print("done")
