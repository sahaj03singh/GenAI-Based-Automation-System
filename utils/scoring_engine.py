def compute_confidence(ai_result, element_found, state_changed,
                       action=None):
    score = 0.0
    if element_found:
        score += 0.35
    if action in ("type", "form_field"):
        score += 0.4
    elif action == "click" and element_found:
        # For clicks, give partial credit even if state didn't change
        # (e.g. modal opens but state capture misses it)
        score += 0.3 if not state_changed else 0.4
    elif state_changed:
        score += 0.4
    if isinstance(ai_result, dict):
        ai_conf = ai_result.get("confidence", 0.5)
    else:
        ai_conf = 0.5
    score += 0.25 * ai_conf
    return round(min(score, 1.0), 2)

def build_result(status, confidence, reason=""):
    return {
        "status": status,
        "confidence": confidence,
        "reason": reason
    }