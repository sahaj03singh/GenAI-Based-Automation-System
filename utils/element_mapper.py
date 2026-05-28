from dom.dom_analyzer import extract_interactive_elements
from utils.locator_store import save_locator, get_locator
from selenium.webdriver.common.by import By
from openai import OpenAI
import os


def _build_dom_summary(elements):
    """Build a concise DOM summary for the LLM to reason about."""
    lines = []
    for i, el in enumerate(elements[:80]):
        parts = [f"tag={el['tag']}"]
        if el.get("text"):
            parts.append(f"text='{el['text'][:60]}'")
        if el.get("id"):
            parts.append(f"id='{el['id']}'")
        if el.get("name"):
            parts.append(f"name='{el['name']}'")
        if el.get("placeholder"):
            parts.append(f"placeholder='{el['placeholder']}'")
        lines.append(f"{i}: {', '.join(parts)}")
    return lines


def _llm_pick_element(elements, description):
    """
    Ask LLM to pick the best element AND generate a stable XPath.
    Prefers id/name over text — more stable across page loads.
    """
    dom_lines = _build_dom_summary(elements)

    prompt = f"""You are a test automation expert.
Given this list of DOM elements and a user intent, respond with a JSON object:
- "index": integer index of the best matching element
- "xpath": a reliable XPath using id or name attributes (prefer id/name over text)

Rules:
- For form fields (inputs, textareas): ONLY return input or textarea elements
- For buttons/links: ONLY return button or anchor elements
- NEVER return a button for a form field intent
- NEVER return a textarea for a click intent
- Prefer @id or @name attributes in XPath over text() matching

Return ONLY valid JSON. Example:
{{"index": 3, "xpath": "//input[@id='search_product']"}}

Intent: "{description}"

DOM Elements:
{chr(10).join(dom_lines)}
"""
    try:
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=80
        )
        import json
        raw = response.choices[0].message.content.strip()
        raw = raw.replace("```json", "").replace("```", "").strip()
        data = json.loads(raw)

        index = int(data.get("index", -1))
        xpath = data.get("xpath", "")

        if 0 <= index < len(elements) and xpath:
            return elements[index]["element"], xpath

    except Exception as e:
        print(f"⚠️ LLM element picker failed: {e}")

    return None, None


def _fuzzy_match(elements, description):
    """Fallback when LLM is unavailable — pure text scoring."""
    desc = description.lower()
    best = None
    best_score = 0

    for el in elements:
        text = el.get("text", "").lower()
        score = 0
        if desc == text:
            score += 5
        elif desc in text:
            score += 3
        for word in desc.split():
            if len(word) > 2 and word in text:
                score += 1
        if score > best_score:
            best_score = score
            best = el

    if best and best_score >= 2:
        if best.get("id"):
            xpath = f"//*[@id='{best['id']}']"
        elif best.get("name"):
            xpath = f"//*[@name='{best['name']}']"
        else:
            xpath = f"//*[contains(text(),'{best['text'][:40]}')]"
        return best["element"], xpath

    return None, None


def find_element_with_metadata(driver, description):
    desc = description.lower().strip()

    # 1. Check locators.json cache first
    saved = get_locator(desc)
    if saved:
        try:
            by_map = {
                "xpath": By.XPATH,
                "css":   By.CSS_SELECTOR,
                "id":    By.ID,
                "name":  By.NAME
            }
            by  = by_map.get(saved.get("by"), By.XPATH)
            element = driver.find_element(by, saved["value"])
            if element:
                print(f"✅ Locator cache hit: {desc}")
                return element, saved
        except Exception:
            print(f"⚠️ Cached locator stale for '{desc}', re-scanning...")

    # 2. Scan live DOM
    elements = extract_interactive_elements(driver)
    if not elements:
        return None, None

    # 3. LLM picks element + generates XPath from real DOM attributes
    element, xpath = _llm_pick_element(elements, desc)

    # 4. Fuzzy fallback if LLM fails
    if not element:
        element, xpath = _fuzzy_match(elements, desc)

    # 5. Save to cache — locator_store handles all validation/rejection
    # Do NOT print here — locator_store prints its own messages
    if element and xpath:
        save_locator(desc, "xpath", xpath, confidence=0.85)
        return element, {"by": "xpath", "value": xpath}

    return None, None