def ai_validate_step(description, before, after):
    url_changed = before.get("url") != after.get("url")
    dom_changed = abs(
        before.get("dom_length", 0) - after.get("dom_length", 0)
    ) > 50

    changed = url_changed or dom_changed

    return {
        "valid": True,
        "confidence": 0.75 if changed else 0.5,
        "reason": (
            f"url changed: {url_changed}, dom changed: {dom_changed}"
        )
    }
