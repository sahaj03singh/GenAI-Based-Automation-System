def capture_state(driver):
    try:
        return {
            "url": driver.current_url,
            "title": driver.title,
            "dom_length": len(driver.page_source)
        }
    except Exception:
        return {"url": "", "title": "", "dom_length": 0}


def compare_states(before, after):
    changes = []
    if before.get("url") != after.get("url"):
        changes.append("url_changed")
    if abs(before.get("dom_length", 0) - after.get("dom_length", 0)) > 50:
        changes.append("dom_changed")
    return changes
