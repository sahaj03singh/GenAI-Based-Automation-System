from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from dom.dom_analyzer import extract_interactive_elements


def _fuzzy_find(driver, target):
    """
    Generic healing: scan the live DOM and find the closest text match.
    No hardcoded XPaths — works for any website.
    """
    elements = extract_interactive_elements(driver)
    desc = target.lower()
    best = None
    best_score = 0

    for el in elements:
        text = el.get("text", "").lower()
        score = sum(1 for word in desc.split() if len(word) > 2 and word in text)
        if score > best_score:
            best_score = score
            best = el

    return best["element"] if best and best_score >= 1 else None


def heal_step(driver, step):
    """
    Generic self-healing:
    1. Re-scan DOM for the target element by fuzzy text match
    2. Try JS click as fallback
    3. Try scrolling into view and retrying
    """
    action = step.get("action", "").lower()
    target = step.get("target", "").lower()
    value = step.get("value", "")

    print(f"[Healing] Attempting to heal: {action} → {target}")

    # Strategy 1: fuzzy DOM re-scan
    try:
        element = _fuzzy_find(driver, target)
        if element:
            driver.execute_script(
                "arguments[0].scrollIntoView({block:'center'});", element
            )

            if action == "click":
                try:
                    element.click()
                except Exception:
                    driver.execute_script("arguments[0].click();", element)
                print(f"[Healing] ✅ Click healed via DOM re-scan: {target}")
                return True

            elif action == "type":
                element.clear()
                element.send_keys(value or "test")
                print(f"[Healing] ✅ Type healed via DOM re-scan: {target}")
                return True

    except Exception as e:
        print(f"[Healing] DOM re-scan failed: {e}")

    # Strategy 2: try any visible button/input as last resort for clicks
    if action == "click":
        try:
            buttons = driver.find_elements(By.XPATH,
                "//button[not(@disabled)] | //a[not(@disabled)]"
            )
            for btn in buttons:
                if target.split()[0] in (btn.text or "").lower():
                    driver.execute_script("arguments[0].click();", btn)
                    print(f"[Healing] ✅ Click healed via button scan: {target}")
                    return True
        except Exception as e:
            print(f"[Healing] Button scan failed: {e}")

    print(f"[Healing] ❌ All healing strategies exhausted for: {target}")
    return False