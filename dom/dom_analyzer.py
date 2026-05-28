from selenium.webdriver.common.by import By


def extract_interactive_elements(driver):
    elements = []

    try:
        all_elements = driver.find_elements(
            By.XPATH,
            "//*[self::button or self::a or self::input "
            "or self::textarea or self::select or self::label]"
        )

        for el in all_elements:
            try:
                tag = el.tag_name
                text = (el.text or "").strip()
                placeholder = el.get_attribute("placeholder") or ""
                aria = el.get_attribute("aria-label") or ""
                el_id = el.get_attribute("id") or ""
                name = el.get_attribute("name") or ""
                el_type = el.get_attribute("type") or ""
                href = el.get_attribute("href") or ""
                el_class = el.get_attribute("class") or ""
                value = el.get_attribute("value") or ""

                # Rich combined text for LLM context
                combined = " ".join(filter(None, [
                    text, placeholder, aria, el_id, name, value
                ])).lower().strip()

                if combined or el_id or name:
                    elements.append({
                        "tag":         tag,
                        "text":        combined,
                        "id":          el_id,
                        "name":        name,
                        "placeholder": placeholder,
                        "aria":        aria,
                        "type":        el_type,
                        "href":        href,
                        "class":       el_class,
                        "element":     el
                    })
            except Exception:
                continue

    except Exception as e:
        print(f"⚠️ DOM extraction failed: {e}")

    return elements