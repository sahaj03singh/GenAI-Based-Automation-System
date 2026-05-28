def validate_step(driver, step):
    target = step.get("target", "").lower()
    src = driver.page_source.lower()
    url = driver.current_url.lower()

    if "logged in" in target:
        return "logout" in src
    if "login page" in target:
        return "/login" in url
    if "products page" in target:
        return "/products" in url
    if "cart" in target and "empty" not in target:
        return "/view_cart" in url or "cart" in src
    if "order confirmed" in target or "congratulations" in target:
        return "congratulations" in src or "order placed" in src
    if "error" in target:
        return "error" in src

    return True
