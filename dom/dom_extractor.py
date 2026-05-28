from selenium.webdriver.common.by import By
import json
import os


def extract_dom(driver):
    os.makedirs("dom", exist_ok=True)
    dom_data = []

    try:
        elements = driver.find_elements(By.XPATH, "//*")

        for el in elements:
            try:
                dom_data.append({
                    "tag":         el.tag_name,
                    "text":        (el.text or "").strip()[:200],
                    "id":          el.get_attribute("id"),
                    "name":        el.get_attribute("name"),
                    "class":       el.get_attribute("class"),
                    "placeholder": el.get_attribute("placeholder"),
                    "aria_label":  el.get_attribute("aria-label"),
                    "href":        el.get_attribute("href"),
                    "type":        el.get_attribute("type"),
                })
            except Exception:
                continue

    except Exception as e:
        print(f"⚠️ DOM extraction error: {e}")

    with open("dom/dom_snapshot.json", "w", encoding="utf-8") as f:
        json.dump(dom_data, f, indent=2, ensure_ascii=False)

    print(f"📸 DOM snapshot saved: {len(dom_data)} elements")
    return dom_data
