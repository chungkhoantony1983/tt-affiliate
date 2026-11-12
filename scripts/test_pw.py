raise SystemExit("Paused: Shopee work is on hold, see TODO.md")

from playwright.sync_api import sync_playwright

def test():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto("https://shopee.vn/search?keyword=may+hut+bui+mini")
        page.wait_for_selector(".shopee-search-item-result__item", timeout=10000)
        items = page.locator(".shopee-search-item-result__item a[data-sqe='link']").all()
        for item in items[:5]:
            print(item.get_attribute("href"))
        browser.close()

if __name__ == "__main__":
    test()
