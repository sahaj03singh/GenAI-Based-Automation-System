import pytest
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


def handle_popup(driver):
    """Dismiss common consent / cookie / GDPR popups."""
    try:
        WebDriverWait(driver, 3).until(
            EC.presence_of_element_located((By.XPATH, "//button"))
        )
        keywords = [
            "consent", "accept", "agree", "ok", "allow",
            "got it", "i understand", "continue", "dismiss",
        ]
        for btn in driver.find_elements(By.XPATH, "//button"):
            try:
                text = (btn.text or "").lower().strip()
                if not text:
                    continue
                if any(w in text for w in keywords):
                    driver.execute_script(
                        "arguments[0].click();", btn
                    )
                    print(f"✅ Popup dismissed: '{text[:30]}'")
                    return True
            except Exception:
                continue
        return False
    except Exception:
        return False


@pytest.fixture(scope="function")
def driver(request):
    options = Options()

    # ── Stealth options to bypass Amazon's bot detection ──────────
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option(
        "excludeSwitches", ["enable-automation"]
    )
    options.add_experimental_option(
        "useAutomationExtension", False
    )

    # Real user-agent so Amazon doesn't serve a degraded page
    options.add_argument(
        "user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/127.0.0.0 Safari/537.36"
    )

    # Standard reliability options
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--start-maximized")
    options.add_argument("--disable-popup-blocking")
    options.add_argument("--disable-notifications")
    options.add_argument("--lang=en-GB")

    # Block third-party ad/tracker domains
    options.add_argument(
        "--host-resolver-rules="
        "MAP doubleclick.net 127.0.0.1, "
        "MAP googletagservices.com 127.0.0.1, "
        "MAP googlesyndication.com 127.0.0.1, "
        "MAP adservice.google.com 127.0.0.1"
    )

    if request.config.getoption("--headless", default=False):
        options.add_argument("--headless=new")

    driver = webdriver.Chrome(options=options)
    driver.set_page_load_timeout(30)
    driver.implicitly_wait(0)

    # ── Hide webdriver flag from Amazon's JS detection ────────────
    try:
        driver.execute_cdp_cmd(
            "Page.addScriptToEvaluateOnNewDocument",
            {
                "source": (
                    "Object.defineProperty(navigator, "
                    "'webdriver', {get: () => undefined});"
                )
            },
        )
    except Exception:
        pass

    # Wrap driver.get() to auto-dismiss popups
    original_get = driver.get

    def get_with_popup_handling(url):
        original_get(url)
        handle_popup(driver)

    driver.get = get_with_popup_handling

    yield driver

    try:
        driver.quit()
    except Exception:
        pass


def pytest_addoption(parser):
    parser.addoption(
        "--headless",
        action="store_true",
        default=False,
        help="Run Chrome in headless mode",
    )