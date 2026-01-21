import pytest
from playwright.sync_api import sync_playwright

@pytest.mark.parametrize("browser_name", ["chromium"])
def test_playwright_browser_launch(browser_name):
    """
    Playwright에서 각 브라우저를 실행할 수 있는지 테스트
    """
    try:
        with sync_playwright() as p:
            if browser_name == "chromium":
                browser = p.chromium.launch(headless=False)
            else:
                pytest.fail(f"Unknown browser: {browser_name}")

            # 간단한 페이지 열기 테스트
            page = browser.new_page()
            page.goto("https://google.com")
            assert "Google" in page.title()
            browser.close()
    except Exception as e:
        pytest.fail(f"{browser_name} failed to launch: {e}")