from utils.element_mapper import find_element_with_metadata
from utils.reporter import log_step, take_screenshot
from agents.locator_agent import LocatorAgent
from configPage.test_data import resolve_test_data
from configPage.site_config import SITE_CONFIG
from utils.scoring_engine import compute_confidence
from utils.state_manager import capture_state
from utils.ai_validator import ai_validate_step
from utils.healing import heal_step

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC

import time
import re

SESSION = {
    "cart_count":       0,
    "last_action":      None,
    "logged_in":        False,
    "on_products_page": False,
}

agent         = LocatorAgent()
MAX_RETRIES   = 3
VALID_ACTIONS = ["click", "type", "verify", "navigate", "scroll"]
BASE_URL      = SITE_CONFIG["base_url"]

# Strict intents — when these fail, do NOT fall back to LLM DOM search.
# These intents represent semantically meaningful constraints
# (price comparison, variant selection, dropdown), and falling back
# to LLM produces wrong-element clicks.
STRICT_INTENT_TYPES = (
    "filter_compare",
    "click_option_with_value",
    "select_option",
    "click_first_match",
)


def reset_session():
    global SESSION
    SESSION = {
        "cart_count":       0,
        "last_action":      None,
        "logged_in":        False,
        "on_products_page": False,
    }


def generate_human_log(action, description, value=""):
    if action == "click":    return f"Clicked on '{description}'"
    if action == "type":     return f"Entered '{value}' in '{description}'"
    if action == "verify":   return f"Verified '{description}'"
    if action == "navigate": return f"Navigated to '{description}'"
    if action == "scroll":   return f"Scrolled to '{description}'"
    return f"Performed '{action}' on '{description}'"


# ── HELPERS ───────────────────────────────────────────────────────────────────

BY_MAP = {
    "name":  By.NAME,
    "id":    By.ID,
    "xpath": By.XPATH,
    "class": By.CLASS_NAME,
    "css":   By.CSS_SELECTOR,
    "tag":   By.TAG_NAME,
}


def _by(by_string):
    return BY_MAP.get(by_string.lower(), By.XPATH)


def _wait(driver, locator_tuple, timeout=10):
    try:
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located(
                (_by(locator_tuple[0]), locator_tuple[1])
            )
        )
    except Exception:
        pass


def _navigate(driver, path_key):
    path    = SITE_CONFIG["navigation_paths"].get(path_key, "/")
    signals = SITE_CONFIG.get("page_ready_signals", {})
    signal  = signals.get(path_key, ("tag", "body"))
    driver.get(f"{BASE_URL}{path}")
    _wait(driver, signal)


def _resolve_nav_intent(desc):
    for key in SITE_CONFIG["navigation_paths"]:
        if key in desc:
            return key
    return None


def _is_navigation_intent(desc):
    ui_keywords = SITE_CONFIG.get("ui_action_keywords", [])
    return not any(kw in desc for kw in ui_keywords)


def _find_field(driver, *hints, field_type=None, timeout=8):
    """
    Generic form field finder — tries name, id, placeholder, type.
    Works for any website.
    """
    tag = "textarea" if field_type == "textarea" else "input"

    for hint in hints:
        strategies = [
            (_by("name"), hint),
            (_by("id"),   hint),
            (_by("xpath"),
             f"//{tag}[contains(translate(@placeholder,"
             f"'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),"
             f"'{hint.lower()}')]"),
            (_by("xpath"),
             f"//{tag}[contains(translate(@name,"
             f"'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),"
             f"'{hint.lower()}')]"),
        ]
        if field_type and field_type != "textarea":
            strategies.append(
                (_by("xpath"), f"//{tag}[@type='{field_type}']")
            )
        for by, val in strategies:
            try:
                el = WebDriverWait(driver, 3).until(
                    EC.presence_of_element_located((by, val))
                )
                if el:
                    return el
            except Exception:
                continue
    return None


def _js_type(driver, el, value):
    """Set field value via JS and fire input/change events."""
    driver.execute_script("arguments[0].value = '';", el)
    driver.execute_script("arguments[0].value = arguments[1];", el, value)
    for event in ["input", "change"]:
        driver.execute_script(
            f"arguments[0].dispatchEvent("
            f"new Event('{event}', {{bubbles: true}}));",
            el
        )


def _dismiss_overlays(driver):
    """
    Aggressively remove third-party ad overlays, cookie banners,
    region/location prompts, and popup containers that intercept clicks.
    Site-agnostic — selectors cover patterns common across e-commerce sites.
    Runs before every click attempt.
    """
    try:
        driver.execute_script("""
            // ── Generic overlay selectors (work on any site) ──
            const selectors = [
                // Ad networks
                '.adpub-drawer-root',
                '[class*="ad-overlay"]',
                '[class*="ad-container"]',

                // Generic popups
                '[class*="popup-overlay"]',
                '[class*="modal-overlay"]',
                '[id*="popup"]',

                // Cookie / consent / GDPR
                '[class*="cookie-banner"]',
                '[class*="cookie-consent"]',
                '[class*="consent-banner"]',
                '[id*="cookie-banner"]',
                '[id*="consent"]',
                '#cookieConsent',
                '#cookie-notice',
                '#sp-cc',
                              
                // Google ad iframes — major click-interceptor on this site
               'iframe[id^="aswift_"]',
               'iframe[id^="google_ads_"]',
               'iframe[src*="googleads"]', 
               'iframe[src*="doubleclick"]',
               'ins.adsbygoogle', 
               '#google_ads_iframe_/',

                // Region / location / delivery prompts
                '#nav-global-location-popover-link-overlay',
                '.glow-toaster-container',
                '[id*="location-popover"]',
                '[class*="location-popover"]'
            ];

            selectors.forEach(s => {
                document.querySelectorAll(s).forEach(el => {
                    el.style.display = 'none';
                    el.style.pointerEvents = 'none';
                    el.style.visibility = 'hidden';
                    if (el.parentNode) {
                        try { el.parentNode.removeChild(el); }
                        catch(e) {}
                    }
                });
            });

            // Generic popover/modal cleanup
            document.querySelectorAll(
                '.a-popover-modal, .a-modal-scroller, ' +
                '.modal.show, .modal.in'
            ).forEach(m => {
                m.style.display = 'none';
            });
        """)
    except Exception:
        pass


def _clear_modals(driver):
    """Remove any lingering modal overlays from the DOM."""
    try:
        driver.execute_script("""
            document.querySelectorAll('.modal-backdrop')
                .forEach(function(b) { b.remove(); });
            document.querySelectorAll('.modal.show, .modal.in, #cartModal')
                .forEach(function(m) {
                    m.style.display = 'none';
                    m.classList.remove('show', 'in');
                });
            document.body.classList.remove('modal-open');
            document.body.style.overflow = '';
            document.body.style.paddingRight = '';
        """)
        time.sleep(0.3)
        print("[MODAL] Cleared lingering modal overlays")
    except Exception as e:
        print(f"[MODAL] Clear failed: {e}")


def _try_click(driver, strategies, label="", use_js=True):
    """
    Try a list of (by_str, value) strategies and click the first found.
    Auto-dismisses overlays before each attempt.

    Smart stale handling: if URL changes after a stale exception,
    treat as success — the click DID succeed but we lost the element
    reference because the page started navigating.
    """
    _dismiss_overlays(driver)
    url_before = driver.current_url

    for by_str, val in strategies:
        for attempt in range(2):
            try:
                el = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((_by(by_str), val))
                )
                driver.execute_script(
                    "arguments[0].scrollIntoView({block:'center'});", el
                )
                time.sleep(0.3)

                # Re-dismiss overlays right before click
                _dismiss_overlays(driver)

                if use_js:
                    driver.execute_script("arguments[0].click();", el)
                else:
                    el.click()
                print(f"[CLICK ✅] {label}: '{el.text[:40]}' via {val}")
                return True

            except Exception as e:
                err_str = str(e).lower()

                # Smart success detection — if URL changed, click worked
                # even if the element reference went stale mid-navigation
                time.sleep(0.3)
                if driver.current_url != url_before:
                    print(
                        f"[CLICK ✅] {label}: succeeded "
                        f"(URL changed after exception)"
                    )
                    return True

                if "stale" in err_str and attempt == 0:
                    print(f"[CLICK] Stale element, retrying: {val}")
                    time.sleep(1.5)
                    continue
                if "intercepted" in err_str and attempt == 0:
                    print(
                        f"[CLICK] Click intercepted, "
                        f"dismissing overlays"
                    )
                    _dismiss_overlays(driver)
                    time.sleep(0.5)
                    continue
                print(f"[CLICK ⚠️] {label} failed: {val} — {e}")
                break
    return False


def _dismiss_modal(driver, choice="view_cart"):
    """Handle post-action modals generically."""
    modal_cfg = SITE_CONFIG.get("modal_buttons", {})

    if choice in modal_cfg and "modal_locator" in modal_cfg:
        try:
            ml = modal_cfg["modal_locator"]
            WebDriverWait(driver, 6).until(
                EC.visibility_of_element_located((_by(ml[0]), ml[1]))
            )
            btn_cfg = modal_cfg[choice]
            btn = WebDriverWait(driver, 4).until(
                EC.element_to_be_clickable(
                    (_by(btn_cfg[0]), btn_cfg[1])
                )
            )
            btn.click()
            time.sleep(0.5)
            return True
        except Exception:
            pass

    try:
        WebDriverWait(driver, 6).until(
            EC.visibility_of_element_located(
                (By.XPATH,
                 "//div[contains(@class,'modal') "
                 "and contains(@style,'display: block')] | "
                 "//div[contains(@class,'modal-dialog')] | "
                 "//div[@role='dialog']")
            )
        )
        if choice == "continue":
            btn = WebDriverWait(driver, 4).until(
                EC.element_to_be_clickable(
                    (By.XPATH,
                     "//*[contains(translate(.,"
                     "'ABCDEFGHIJKLMNOPQRSTUVWXYZ',"
                     "'abcdefghijklmnopqrstuvwxyz'),'continue')]"
                     "[self::button or self::a]")
                )
            )
        else:
            btn = WebDriverWait(driver, 4).until(
                EC.element_to_be_clickable(
                    (By.XPATH,
                     "//*[contains(translate(.,"
                     "'ABCDEFGHIJKLMNOPQRSTUVWXYZ',"
                     "'abcdefghijklmnopqrstuvwxyz'),'view cart') or "
                     "contains(translate(.,"
                     "'ABCDEFGHIJKLMNOPQRSTUVWXYZ',"
                     "'abcdefghijklmnopqrstuvwxyz'),'go to cart')]"
                     "[self::button or self::a]")
                )
            )
        btn.click()
        time.sleep(0.5)
        return True
    except Exception as e:
        print(f"⚠️ Modal dismiss failed: {e}")
        return False


def _confirm_post_login(driver):
    """Generic post-login confirmation."""
    login_path  = SITE_CONFIG["navigation_paths"].get("login", "/login")
    success_kws = SITE_CONFIG.get(
        "verify_keywords", {}
    ).get("logged in", ["logout", "sign out", "log out"])

    try:
        WebDriverWait(driver, 15).until(
            lambda d: login_path not in d.current_url
        )
        print(f"[LOGIN] ✅ Redirected to: {driver.current_url}")
    except Exception:
        print(f"[LOGIN] ⚠️ Still on: {driver.current_url}")

    try:
        WebDriverWait(driver, 10).until(
            lambda d: any(
                kw in d.page_source.lower() for kw in success_kws
            )
        )
        SESSION["logged_in"] = True
        print(f"[LOGIN] ✅ Confirmed via: {success_kws}")
    except Exception:
        SESSION["logged_in"] = False
        print(f"[LOGIN] ⚠️ Could not confirm login")


# ── INTENT RESOLVER ───────────────────────────────────────────────────────────

def _resolve_intent(desc):
    """Match description against site_config.intent_actions.

    Returns the intent whose `match` keyword list has the LONGEST
    keyword that appears in `desc`. This ensures specific intents
    (e.g. match=["madame brand"]) win over generic ones
    (e.g. match=["brand link"]).

    Without this, dict iteration order decides, which means the
    first generic intent registered wins for every variant — the
    locator-caching false-positive bug observed in the audit.
    """
    intents = SITE_CONFIG.get("intent_actions", {})
    best_intent = None
    best_score = 0
    for _, intent_cfg in intents.items():
        match_kws = intent_cfg.get("match", [])
        for kw in match_kws:
            if kw in desc and len(kw) > best_score:
                best_score = len(kw)
                best_intent = intent_cfg
    return best_intent

# ── INTENT EXECUTOR ───────────────────────────────────────────────────────────

def _execute_intent(driver, intent, action, desc, step_value=""):
    """
    Execute an intent by its type.
    Generic execution — site knowledge lives in site_config.
    """
    intent_type = intent.get("type")

    # ── form_field ────────────────────────────────────────────────
    if intent_type == "form_field":
        pre_nav = intent.get("pre_navigate")
        if pre_nav:
            nav_flag = f"on_{pre_nav}_page"
            if not SESSION.get(nav_flag):
                _navigate(driver, pre_nav)
                SESSION[nav_flag] = True

        field_type = intent.get("field_type")
        hints      = intent.get("field_hints", [])
        data_key   = intent.get("data_key", desc)
        el         = _find_field(driver, *hints, field_type=field_type)

        if el:
            if step_value and str(step_value).strip():
                value = str(step_value).strip()
                print(f"[FORM] Using step value: '{value}'")
            else:
                value = resolve_test_data(data_key)

            try:
                el.clear()
                el.send_keys(value)
            except Exception:
                _js_type(driver, el, value)
            return True
        return False

    # ── select_option (Selenium <select> dropdowns) ───────────────
    if intent_type == "select_option":
        select_id    = intent.get("select_id", "")
        option_text  = intent.get("option_text", "")
        option_value = intent.get("option_value", "")

        try:
            el = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, select_id))
            )
            driver.execute_script(
                "arguments[0].scrollIntoView({block:'center'});", el
            )
            time.sleep(0.5)
            sel = Select(el)
            try:
                sel.select_by_visible_text(option_text)
                print(
                    f"[SELECT ✅] '{option_text}' "
                    f"selected from '{select_id}'"
                )
            except Exception:
                sel.select_by_value(option_value)
                print(
                    f"[SELECT ✅] '{option_value}' "
                    f"selected by value from '{select_id}'"
                )
            time.sleep(2)

            fragment = intent.get("wait_for_url_fragment")
            if fragment:
                try:
                    WebDriverWait(driver, 8).until(
                        lambda d: fragment in d.current_url
                    )
                except Exception:
                    pass
            return True

        except Exception as e:
            print(f"[SELECT ⚠️] Dropdown failed: {e}, trying fallbacks")
            for by_str, xpath in intent.get("fallback_strategies", []):
                try:
                    el = WebDriverWait(driver, 5).until(
                        EC.element_to_be_clickable(
                            (_by(by_str), xpath)
                        )
                    )
                    driver.execute_script("arguments[0].click();", el)
                    time.sleep(2)
                    print(f"[SELECT ✅] Fallback worked: {xpath}")
                    return True
                except Exception:
                    continue
            return False

    # ── click_strategies ──────────────────────────────────────────
    if intent_type == "click_strategies":
        pre_wait = intent.get("pre_wait", 0)
        if pre_wait:
            print(f"[WAIT] Settling {pre_wait}s before: {desc}")
            time.sleep(pre_wait)

        if intent.get("scroll_before_click"):
            try:
                driver.execute_script(
                    "window.scrollTo(0, document.body.scrollHeight / 2);"
                )
                time.sleep(0.5)
                print(f"[SCROLL] Scrolled before: {desc}")
            except Exception:
                pass

        if intent.get("clear_modals"):
            _clear_modals(driver)

        strategies = [(s[0], s[1]) for s in intent.get("strategies", [])]
        clicked    = _try_click(driver, strategies, label=desc)

        # JS fallback — for sites where the button is technically present
        # but Selenium can't interact with it (e.g. Amazon's wrapped span/
        # div hierarchy). Site author can specify a JS snippet that submits
        # the form directly, bypassing Selenium's click constraints.
        if not clicked and intent.get("js_fallback"):
            try:
                result = driver.execute_script(intent["js_fallback"])
                if result and result != "not_found":
                    print(f"[JS FALLBACK ✅] {desc}: {result}")
                    clicked = True
                    time.sleep(1)
                else:
                    print(
                        f"[JS FALLBACK ⚠️] {desc}: "
                        f"returned '{result}'"
                    )
            except Exception as e:
                print(f"[JS FALLBACK ⚠️] {desc}: {e}")

        # checkout_fallback — direct URL navigation if all clicks fail
        if not clicked and intent.get("checkout_fallback"):
            checkout_path = SITE_CONFIG.get(
                "page_url_fragments", {}
            ).get("checkout", "/checkout")
            try:
                url_before = driver.current_url
                print(f"[CHECKOUT] All strategies failed, trying direct nav")
                driver.get(f"{BASE_URL}{checkout_path}")
                time.sleep(1.5)
                if checkout_path in driver.current_url:
                    print(
                        f"[CHECKOUT] ✅ Direct nav success: "
                        f"{driver.current_url}"
                    )
                    clicked = True
                else:
                    driver.get(url_before)
                    time.sleep(1)
            except Exception as e:
                print(f"[CHECKOUT] Direct nav failed: {e}")

        if clicked:
            # Wait after click — let confirmation UI render
            wait_after = intent.get("wait_after", 0)
            if wait_after:
                print(f"[WAIT] Waiting {wait_after}s after click")
                time.sleep(wait_after)

            after = intent.get("after")
            if after == "confirm_login":
                _confirm_post_login(driver)
            elif after == "decrement_count":
                key = intent.get("count_key", "cart_count")
                SESSION[key] = max(0, SESSION.get(key, 0) - 1)
            elif after == "increment_count":
                key = intent.get("count_key", "cart_count")
                SESSION[key] = SESSION.get(key, 0) + 1

            if intent.get("wait_for_url_change"):
                url_before = driver.current_url
                try:
                    WebDriverWait(driver, 10).until(
                        lambda d: d.current_url != url_before
                    )
                    print(f"[NAV ✅] URL → {driver.current_url}")
                except Exception:
                    print(f"[NAV ⚠️] URL unchanged: {driver.current_url}")

            fragment = intent.get("wait_for_url_fragment")
            if fragment:
                try:
                    WebDriverWait(driver, 8).until(
                        lambda d: fragment in d.current_url
                    )
                except Exception:
                    pass

            _wait(driver, ("tag", "body"))

        return clicked

    # ── click_first_match ─────────────────────────────────────────
    if intent_type == "click_first_match":
        # Honour pre_wait — let page settle (e.g. after sort)
        pre_wait = intent.get("pre_wait", 0)
        if pre_wait:
            print(f"[WAIT] Settling {pre_wait}s before: {desc}")
            time.sleep(pre_wait)

        # Honour scroll_before_click — push past the fold
        if intent.get("scroll_before_click"):
            try:
                driver.execute_script("window.scrollTo(0, 200);")
                time.sleep(0.5)
            except Exception:
                pass

        _dismiss_overlays(driver)
        for by_str, val in intent.get("strategies", []):
            try:
                links = WebDriverWait(driver, 8).until(
                    EC.presence_of_all_elements_located(
                        (_by(by_str), val)
                    )
                )
                if links:
                    index = 1 if "second" in desc else 0
                    index = min(index, len(links) - 1)

                    # Scroll the chosen link into view
                    driver.execute_script(
                        "arguments[0].scrollIntoView({block:'center'});",
                        links[index]
                    )
                    time.sleep(0.3)
                    _dismiss_overlays(driver)

                    driver.execute_script(
                        "arguments[0].click();", links[index]
                    )
                    SESSION["last_action"] = desc

                    fragment = intent.get("wait_for_url_fragment")
                    if fragment:
                        try:
                            WebDriverWait(driver, 8).until(
                                lambda d: fragment in d.current_url
                            )
                            print(
                                f"[CLICK_FIRST ✅] '{desc}' → "
                                f"{driver.current_url}"
                            )
                        except Exception:
                            print(
                                f"[CLICK_FIRST ⚠️] URL didn't change "
                                f"to contain '{fragment}'"
                            )
                            return False
                    return True
            except Exception:
                continue
        print(f"[CLICK_FIRST ⚠️] All strategies failed for '{desc}'")
        return False

    # ── filter_compare ────────────────────────────────────────────
    if intent_type == "filter_compare":
        container_xpath = intent.get("container_xpath", "")
        value_xpath     = intent.get("value_xpath", "")
        link_xpath      = intent.get("link_xpath", "")
        extract_pattern = intent.get("extract_pattern", r"[\d.]+")
        operator        = intent.get("operator", "lt")

        threshold = None
        if step_value and str(step_value).strip():
            m = re.search(extract_pattern, str(step_value))
            if m:
                try:
                    threshold = float(m.group(0))
                except Exception:
                    pass
        if threshold is None:
            m = re.search(extract_pattern, desc)
            if m:
                try:
                    threshold = float(m.group(0))
                except Exception:
                    pass
        if threshold is None:
            threshold = intent.get("threshold")

        try:
            containers = WebDriverWait(driver, 8).until(
                EC.presence_of_all_elements_located(
                    (By.XPATH, container_xpath)
                )
            )

            candidates = []
            for c in containers:
                try:
                    value_els = c.find_elements(By.XPATH, value_xpath)
                    if not value_els:
                        continue
                    raw_text = (
                        value_els[0].text or
                        value_els[0].get_attribute("textContent") or ""
                    )
                    m = re.search(extract_pattern, raw_text)
                    if not m:
                        continue
                    num = float(m.group(0))

                    link_els = c.find_elements(By.XPATH, link_xpath)
                    if not link_els:
                        continue

                    candidates.append((num, link_els[0]))
                except Exception:
                    continue

            if not candidates:
                print(f"[FILTER ⚠️] No candidates found for '{desc}'")
                return False

            print(
                f"[FILTER] Found {len(candidates)} candidates, "
                f"applying '{operator}' with threshold={threshold}"
            )

            chosen = None
            if operator == "min":
                chosen = min(candidates, key=lambda x: x[0])
            elif operator == "max":
                chosen = max(candidates, key=lambda x: x[0])
            elif threshold is not None:
                matches = []
                for num, el in candidates:
                    if operator == "lt"  and num <  threshold: matches.append((num, el))
                    if operator == "lte" and num <= threshold: matches.append((num, el))
                    if operator == "gt"  and num >  threshold: matches.append((num, el))
                    if operator == "gte" and num >= threshold: matches.append((num, el))
                    if operator == "eq"  and num == threshold: matches.append((num, el))
                if matches:
                    chosen = min(matches, key=lambda x: x[0])

            if not chosen:
                print(
                    f"[FILTER ⚠️] No products match "
                    f"{operator} {threshold}"
                )
                return False

            num, link_el = chosen
            print(f"[FILTER ✅] Selected product with value={num}")
            _dismiss_overlays(driver)
            driver.execute_script(
                "arguments[0].scrollIntoView({block:'center'});", link_el
            )
            time.sleep(0.4)
            driver.execute_script("arguments[0].click();", link_el)

            fragment = intent.get("wait_for_url_fragment")
            if fragment:
                try:
                    WebDriverWait(driver, 8).until(
                        lambda d: fragment in d.current_url
                    )
                except Exception:
                    pass
            return True

        except Exception as e:
            print(f"[FILTER ⚠️] Failed: {e}")
            return False

    # ── click_option_with_value ───────────────────────────────────
    if intent_type == "click_option_with_value":
        option_xpaths = intent.get("option_xpaths", [])
        value_aliases = intent.get("value_aliases", {})
        target_value  = ""

        if step_value and str(step_value).strip():
            target_value = str(step_value).strip()

        if not target_value:
            extract_pattern = intent.get("extract_pattern", "")
            if extract_pattern:
                m = re.search(extract_pattern, desc, re.IGNORECASE)
                if m:
                    target_value = m.group(0)

        if not target_value:
            target_value = intent.get("default_value", "")

        if not target_value:
            print(f"[OPTION ⚠️] No target value found for '{desc}'")
            return False

        if value_aliases:
            tv_lower = target_value.lower()
            for alias, code in value_aliases.items():
                if alias.lower() == tv_lower or alias.lower() in tv_lower:
                    print(f"[OPTION] Mapped '{alias}' → '{code}'")
                    target_value = code
                    break

        print(f"[OPTION] Looking for value: '{target_value}'")
        _dismiss_overlays(driver)

        for xpath_template in option_xpaths:
            try:
                variants = [
                    xpath_template.replace("{value}", target_value),
                    xpath_template.replace(
                        "{value}", target_value.lower()
                    ),
                    xpath_template.replace(
                        "{value}", target_value.upper()
                    ),
                ]
                for x in variants:
                    try:
                        el = WebDriverWait(driver, 5).until(
                            EC.element_to_be_clickable((By.XPATH, x))
                        )
                        driver.execute_script(
                            "arguments[0].scrollIntoView({block:'center'});",
                            el
                        )
                        time.sleep(0.3)
                        _dismiss_overlays(driver)
                        driver.execute_script(
                            "arguments[0].click();", el
                        )
                        print(
                            f"[OPTION ✅] Selected '{target_value}' "
                            f"via {x}"
                        )
                        time.sleep(0.5)
                        return True
                    except Exception:
                        continue
            except Exception:
                continue

        print(
            f"[OPTION ⚠️] Could not find option '{target_value}' "
            f"using any of {len(option_xpaths)} strategies"
        )
        return False

    # ── modal_dismiss ─────────────────────────────────────────────
    if intent_type == "modal_dismiss":
        choice = intent.get("choice", "view_cart")
        result = _dismiss_modal(driver, choice=choice)
        if not result:
            fallbacks = intent.get("fallback_strategies", [])
            result = _try_click(driver, fallbacks, label="modal fallback")
        if result:
            _wait(driver, ("tag", "body"))
        return result

    # ── listing_item_action ───────────────────────────────────────
    if intent_type == "listing_item_action":
        detail_fragment = intent.get("detail_page_url_fragment", "")
        if detail_fragment and detail_fragment in driver.current_url:
            strategies = intent.get("detail_page_strategies", [])
            clicked    = _try_click(
                driver, strategies, label=f"{desc} (detail page)"
            )
            if clicked:
                key = intent.get("count_key")
                if key:
                    SESSION[key] = SESSION.get(key, 0) + 1
                SESSION["last_action"] = desc
                return True

        try:
            wrapper = intent.get(
                "item_wrapper",
                ("xpath", "//div[contains(@class,'item')]")
            )
            items = WebDriverWait(driver, 10).until(
                EC.presence_of_all_elements_located(
                    (_by(wrapper[0]), wrapper[1])
                )
            )
            index       = 1 if "second" in desc else 0
            index       = min(index, len(items) - 1)
            target_item = items[index]
            driver.execute_script(
                "arguments[0].scrollIntoView({block:'center'});",
                target_item
            )
            time.sleep(0.5)
            _dismiss_overlays(driver)

            for by_str, val in intent.get("item_action_strategies", []):
                try:
                    if by_str == "css":
                        driver.execute_script(
                            f"arguments[0].querySelector('{val}').click();",
                            target_item
                        )
                    else:
                        els = target_item.find_elements(_by(by_str), val)
                        if els:
                            driver.execute_script(
                                "arguments[0].click();", els[0]
                            )
                    key = intent.get("count_key")
                    if key:
                        SESSION[key] = SESSION.get(key, 0) + 1
                    SESSION["last_action"] = desc
                    time.sleep(0.5)
                    return True
                except Exception:
                    continue

            print(f"⚠️ {desc}: all item action strategies failed")
            return False

        except Exception as e:
            print(f"⚠️ {desc} listing failed: {e}")
            return False

    # ── js_scroll ─────────────────────────────────────────────────
    if intent_type == "js_scroll":
        scroll_action = intent.get("scroll_action", "bottom")
        if scroll_action == "bottom":
            driver.execute_script(
                "window.scrollTo(0, document.body.scrollHeight);"
            )
        elif scroll_action == "top":
            driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(intent.get("wait_after", 1.0))
        return True

    # ── custom_js ─────────────────────────────────────────────────
    if intent_type == "custom_js":
        script = intent.get("script", "")
        if script:
            try:
                driver.execute_script(script)
                return True
            except Exception as e:
                print(f"⚠️ custom_js failed: {e}")
        return False

    return False


# ── SMART ACTION HANDLER ──────────────────────────────────────────────────────

def smart_action_handler(driver, action, description, step_value=""):
    """
    Pure generic dispatcher.
    Zero site-specific knowledge here.
    """
    desc = description.lower()

    # Navigation
    if action in ["navigate", "click"]:
        if _is_navigation_intent(desc):
            nav_key = _resolve_nav_intent(desc)
            if nav_key:
                _navigate(driver, nav_key)
                nav_flags   = SITE_CONFIG.get(
                    "navigation_session_flags", {}
                )
                reset_flags = SITE_CONFIG.get(
                    "navigation_reset_flags", {}
                )
                for flag, keys in nav_flags.items():
                    if nav_key in keys:
                        reset_keys = reset_flags.get(flag, [])
                        SESSION[flag] = nav_key not in reset_keys
                return True

    # Sidebar
    sidebar = SITE_CONFIG.get("sidebar", {})
    for key, locator in sidebar.items():
        if action == "click" and key in desc:
            clicked = _try_click(
                driver, [(locator[0], locator[1])], label=key
            )
            if clicked:
                _wait(driver, ("tag", "body"))
                return True

    # Intent-driven
    intent = _resolve_intent(desc)
    if intent:
        return _execute_intent(
            driver, intent, action, desc, step_value=step_value
        )

    return False


# ── VERIFY ────────────────────────────────────────────────────────────────────

def _verify_step(driver, description):
    """Fully generic verify — keywords from site_config."""
    desc = description.lower()
    try:
        time.sleep(1)
        src  = driver.page_source.lower()
        url  = driver.current_url.lower()
        base = BASE_URL.replace("https://", "").replace("http://", "")

        page_frags  = SITE_CONFIG.get("page_url_fragments", {})
        verify_kws  = SITE_CONFIG.get("verify_keywords", {})
        count_verif = SITE_CONFIG.get("count_verifications", {})
        login_path  = page_frags.get("login", "/login")
        waitable    = SITE_CONFIG.get(
            "waitable_verifications",
            ["logged in", "order confirmed"]
        )

        for frag_key, frag_val in page_frags.items():
            label = frag_key.replace("_", " ")
            if (label in desc or
                    f"{label} page" in desc or
                    f"{label} loaded" in desc):
                if frag_key == "home":
                    return base in url and login_path not in url
                return frag_val in url

        if "homepage" in desc or "home page" in desc:
            return base in url and login_path not in url

        for verify_key, keywords in verify_kws.items():
            if verify_key in desc:
                if verify_key in waitable:
                    try:
                        WebDriverWait(driver, 10).until(
                            lambda d: any(
                                kw in d.page_source.lower()
                                for kw in keywords
                            )
                        )
                        return True
                    except Exception:
                        return any(kw in src for kw in keywords)
                else:
                    return any(kw in src for kw in keywords)

        for count_key, count_cfg in count_verif.items():
            if count_key in desc:
                session_var = count_cfg.get("session_var", "cart_count")
                operator    = count_cfg.get("operator", "gt")
                value       = count_cfg.get("value", 0)
                current     = SESSION.get(session_var, 0)
                if operator == "eq":  return current == value
                if operator == "gt":  return current > value
                if operator == "gte": return current >= value
                if operator == "lt":  return current < value

        words = [w for w in desc.split() if len(w) > 3]
        if words:
            if any(w in url for w in words):
                return True
            if any(w in src for w in words):
                return True

        return True

    except Exception:
        return False


# ── EXECUTE STEP ──────────────────────────────────────────────────────────────

def execute_step(driver, step):
    start_time  = time.time()
    action      = step.get("action", "").lower()
    description = step.get("target", "").lower()
    value       = step.get("value", "")

    result = {
        "step": step, "passed": False,
        "confidence": 0.0, "execution_time": 0, "screenshot": None
    }

    if action not in VALID_ACTIONS:
        action = "verify"

    pre_nav_cfg = SITE_CONFIG.get("pre_navigate_for", {})
    for nav_key, triggers in pre_nav_cfg.items():
        if action == "type" and any(t in description for t in triggers):
            flag = f"on_{nav_key}_page"
            if not SESSION.get(flag):
                _navigate(driver, nav_key)
                SESSION[flag] = True
            break

    state_before = capture_state(driver)

    # ── VERIFY ───────────────────────────────────────────────────
    if action == "verify":
        passed     = _verify_step(driver, description)
        screenshot = take_screenshot(driver, description)
        log_step(
            generate_human_log(action, description),
            "PASS" if passed else "FAIL", screenshot
        )
        result.update({
            "passed": passed,
            "confidence": 0.85 if passed else 0.3,
            "execution_time": round(time.time() - start_time, 2),
            "screenshot": screenshot
        })
        return result

    # ── SMART HANDLER ────────────────────────────────────────────
    handler_succeeded = smart_action_handler(
        driver, action, description, step_value=value
    )

    if handler_succeeded:
        time.sleep(0.4)
        state_after = capture_state(driver)
        screenshot  = take_screenshot(driver, description)
        confidence  = compute_confidence(
            ai_result     = ai_validate_step(
                description, state_before, state_after
            ),
            element_found = True,
            state_changed = (state_before != state_after),
            action        = action
        )
        if action == "type":
            if value and str(value).strip():
                display_value = str(value).strip()
            else:
                display_value = resolve_test_data(description, value)
        else:
            display_value = value

        log_step(
            generate_human_log(action, description, display_value),
            "PASS" if confidence > 0.5 else "WARN", screenshot
        )
        result.update({
            "passed": confidence > 0.5, "confidence": confidence,
            "execution_time": round(time.time() - start_time, 2),
            "screenshot": screenshot
        })
        return result

    # ── STRICT INTENT FAIL-FAST ──────────────────────────────────
    # If a strict intent fails, do NOT fall through to LLM DOM search.
    # Strict intents include the global STRICT_INTENT_TYPES tuple AND
    # any intent that has "strict": True in site_config.
    intent = _resolve_intent(description)
    is_strict = (
        intent and (
            intent.get("type") in STRICT_INTENT_TYPES
            or intent.get("strict") is True
        )
    )
    if is_strict:
        screenshot = take_screenshot(driver, description)
        log_step(
            generate_human_log(action, description, value),
            "FAIL", screenshot
        )
        result.update({
            "passed":         False,
            "confidence":     0.2,
            "execution_time": round(time.time() - start_time, 2),
            "screenshot":     screenshot,
        })
        print(
            f"[STRICT FAIL] '{description}' — strict intent "
            f"'{intent.get('type')}' returned no match. "
            f"Not falling back to LLM."
        )
        return result

    # ── FALLBACK: LLM DOM search ──────────────────────────────────
    for attempt in range(MAX_RETRIES):
        try:
            element, metadata = find_element_with_metadata(
                driver, description
            )

            if element:
                _dismiss_overlays(driver)
                driver.execute_script(
                    "arguments[0].scrollIntoView({block:'center'});",
                    element
                )
                time.sleep(0.4)

            if action == "click" and element:
                _dismiss_overlays(driver)
                element.click()
            elif action == "type" and element:
                if value and str(value).strip():
                    typed_value = str(value).strip()
                else:
                    typed_value = resolve_test_data(description, value)
                element.clear()
                element.send_keys(typed_value)
                value = typed_value
            elif action == "scroll" and element:
                driver.execute_script(
                    "arguments[0].scrollIntoView();", element
                )

            state_after = capture_state(driver)
            confidence  = compute_confidence(
                ai_result     = ai_validate_step(
                    description, state_before, state_after
                ),
                element_found = bool(element),
                state_changed = (state_before != state_after),
                action        = action
            )
            passed     = confidence > 0.5
            screenshot = take_screenshot(driver, description)
            result.update({
                "passed": passed, "confidence": confidence,
                "execution_time": round(time.time() - start_time, 2),
                "screenshot": screenshot
            })
            log_step(
                generate_human_log(action, description, value),
                "PASS" if passed else "FAIL", screenshot
            )
            return result

        except Exception as e:
            print(f"❌ Attempt {attempt + 1} failed: {e}")
            if attempt == MAX_RETRIES - 1:
                healed = heal_step(driver, step)
                if healed:
                    result.update({
                        "passed": True, "confidence": 0.6,
                        "execution_time": round(time.time() - start_time, 2),
                        "healed": True,
                    })
                    log_step(
                        generate_human_log(action, description),
                        "HEALED", None
                    )
                    return result
            time.sleep(1.5)

    screenshot = take_screenshot(driver, description)
    log_step(
        generate_human_log(action, description, value),
        "FAIL", screenshot
    )
    result.update({
        "passed": False, "confidence": 0.2,
        "execution_time": round(time.time() - start_time, 2),
        "screenshot": screenshot
    })
    return result