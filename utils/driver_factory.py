"""
driver_factory.py — single source of truth for Chrome driver creation.

Used by both conftest.py (pytest fixture) and test_executor.py
(per-test respawn loop). Centralising the option list here ensures
both paths produce identical browser configurations.

Includes the improvements from the May 2026 conftest revision:
  - page_load_strategy = "eager" (returns when DOM is ready, not
    waiting for every image / iframe)
  - 120s page timeout (more forgiving on slow real-world pages)
  - Explicit 1920x1080 window (more reliable than --start-maximized)
  - Wrapped .get() that prints the URL and handles timeouts without
    blowing up the run.

INTENTIONALLY OMITTED: --host-resolver-rules. That option redirected
ad domains to 127.0.0.1, which caused chromedriver's renderer to hang
waiting for refused connections to time out. Removed 2026-05-31.
"""

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException


def _handle_popup(driver):
    """
    Dismiss common consent / cookie / GDPR popups.

    Strategy:
      1. Give the page up to 2 seconds to start rendering the popup
         (popups are often injected by JS after page load completes).
      2. For up to 10 seconds, repeatedly look for any clickable
         element (button, link, or div with role=button) whose text
         matches a consent keyword.
      3. Click the first match via JS (works even when overlay
         intercepts normal Selenium clicks).
    """
    import time

    keywords = [
        "consent", "accept all", "accept", "agree", "ok", "allow",
        "got it", "i understand", "continue", "dismiss",
    ]

    # Give the popup a moment to render (it's usually JS-injected)
    time.sleep(2)

    # Try for up to 10 seconds — popup may render late
    deadline = time.time() + 10
    while time.time() < deadline:
        try:
            # Look at buttons, links, AND div/span/a role=button
            # because consent UIs vary wildly in markup
            elements = driver.find_elements(
                By.XPATH,
                "//button | //a[@role='button'] | "
                "//div[@role='button'] | //span[@role='button']"
            )
            for el in elements:
                try:
                    text = (el.text or "").lower().strip()
                    if not text:
                        continue
                    if any(word in text for word in keywords):
                        driver.execute_script("arguments[0].click();", el)
                        print(f"✅ Popup dismissed: '{text[:40]}'")
                        time.sleep(0.5)
                        return True
                except Exception:
                    continue
        except Exception:
            pass
        time.sleep(0.5)

    # Didn't find anything to dismiss — return quietly
    return False
def create_driver(headless=False):
    """
    Create a fresh Chrome driver with the standard framework options.
    The returned driver has its .get() wrapped so every navigation
    auto-dismisses popups and handles load timeouts gracefully.
    """
    options = Options()

    # Faster page loading — returns when DOM is ready, doesn't wait
    # for every external resource (images, iframes, ads) to finish.
    options.page_load_strategy = "eager"

    # ── Anti-detection ───────────────────────────────────────────
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option(
        "excludeSwitches", ["enable-automation"]
    )
    options.add_experimental_option("useAutomationExtension", False)

    # Real-looking user-agent
    options.add_argument(
        "user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/148.0.7778.179 Safari/537.36"
    )

    # ── Stability flags ──────────────────────────────────────────
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-popup-blocking")
    options.add_argument("--disable-notifications")
    options.add_argument("--lang=en-GB")
    options.add_argument("--window-size=1920,1080")

    # NOTE: --host-resolver-rules deliberately omitted (renderer hangs).

    if headless:
        options.add_argument("--headless=new")

    driver = webdriver.Chrome(options=options)
    driver.set_page_load_timeout(120)
    driver.implicitly_wait(0)

    # Hide webdriver flag from JS detection
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

    # Wrap .get() so every navigation:
    #   - logs the URL it's loading
    #   - tolerates page-load timeouts without aborting the suite
    #   - dismisses the consent popup automatically
    original_get = driver.get

    def get_with_popup_handling(url):
        try:
            print(f"🌐 Loading: {url}")
            original_get(url)
        except TimeoutException:
            print("⚠️ Page load timeout reached. Continuing execution.")
        except Exception as e:
            print(f"⚠️ Navigation error: {e}")

        try:
            _handle_popup(driver)
        except Exception:
            pass

    driver.get = get_with_popup_handling

    return driver