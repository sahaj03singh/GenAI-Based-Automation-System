def clean_steps(steps):
    cleaned = []

    for step in steps:
        action = step.get("action", "").lower()
        target = step.get("target", "").lower()
        value = step.get("value", "")

        if not action or not target:
            continue

        if action == "type" and target in ["add to cart", "cart", "product",
                                            "view product", "search button"]:
            action = "click"

        if target in ["success", "done", "complete"]:
            action = "verify"

        cleaned.append({"action": action, "target": target, "value": value})

    return cleaned


def remove_repetition(steps):
    seen = set()
    result = []

    for step in steps:
        key = (step.get("action"), step.get("target"), step.get("value", ""))
        if key in seen:
            continue
        seen.add(key)
        result.append(step)

    return result


def enforce_flow(steps):
    flow = []
    has_product = False
    has_cart = False
    has_checkout = False

    for step in steps:
        action = step["action"]
        target = step["target"]

        if action == "click" and target == "proceed to checkout" and not has_cart:
            continue
        if action == "click" and target == "add to cart" and not has_product:
            continue

        if target in ["view product", "add to cart"]:
            has_product = True
        if "cart" in target:
            has_cart = True
        if "checkout" in target:
            has_checkout = True

        flow.append(step)

    if not has_product:
        flow.insert(0, {"action": "click", "target": "view product", "value": ""})
    if not has_cart:
        flow.append({"action": "navigate", "target": "cart", "value": ""})
    if not has_checkout:
        flow.append({"action": "click", "target": "proceed to checkout", "value": ""})

    flow.append({"action": "verify", "target": "order confirmed", "value": ""})

    return flow
