import json
import os
import re

LOCATOR_FILE = "locators/locators.json"

FORM_FIELD_TARGETS = [
    "message box", "comment", "card name", "card number",
    "cvc", "expiry month", "expiry year", "quantity",
    "email", "password", "search bar", "search input",
    "message", "comment box", "order comment",
]

CLICK_TARGETS = [
    "proceed to checkout", "place order", "pay and confirm",
    "pay and confirm order", "login button", "search button",
    "add to cart", "add to basket", "view cart",
    "continue shopping", "view product", "product with",
    "sort by", "products tab",
]

# XPaths that are wrong for form field targets
INVALID_FOR_FORM = [
    "//a[",
    "//button[",
    "[@id='subscribe']",
    "[@id='submit']",
    "[@id='cf-",
    "[@id='pay-button']",
    "[@id='scrollUp']",
    "[@id='susbscribe_email']",
    "text()='cart'",
    "text()='place order'",
    "text()='add to cart'",
    "text()='home'",
]

# XPaths that are wrong for click targets
INVALID_FOR_CLICK = [
    "//input[@type='text']",
    "//textarea",
    "[@id='search_product']",
    "text()='place order'",
    "text()='add to cart'",
    "text()='home'",

    # automationexercise / amazon — wrong nav elements
    "[@id='nav-logo-sprites']",
    "[@id='nav-logo']",
    "[@id='nav-assist-cart']",
    "[@id='nav-cart']",
    "[@id='nav-link-accountList']",

    # Hidden/utility fields
    "[@id='unifiedLocation1ClickAddress']",
    "[@id='glowValidationToken']",
    "[@id='susbscribe_email']",
    "[@id='subscribe_email']",
    "[@id='subscribe']",
    "[@id='scrollUp']",

    # Screen-reader accessibility text
    "go to review section",
    "rated 4.",
    "rated 5.",
    "out of 5 stars by",
    "review section",

    # Malformed XPath patterns (LLM common mistakes)
    "@text=",
    "@text ",
    "[@text]",
]

# Targets that should NEVER be cached or retrieved from cache.
# These are either dynamic, navigation-related, or known-volatile.
DO_NOT_CACHE = [
    # Top-level nav — these go stale across page navigations
    "products tab",
    "products page",
    "cart tab",
    "view cart",         # ← critical — was healing 10/10 times
    "view cart modal",
    "home tab",
    "homepage",          # ← prevents WARN noise on navigate

    # Sidebar — element refs go stale on page reload
    "women category",
    "men category",
    "kids category",
    "dress subcategory",
    "tops subcategory",
    "saree subcategory",
    "tshirts subcategory",
    "jeans subcategory",

    # Brand filters
    "polo brand",
    "h&m brand",
    "madame brand",
    "mast & harbour",
    "babyhug brand",
    "allen solly brand",
    "kookie kids brand",
    "biba brand",

    # Checkout / payment fields (security-sensitive)
    "proceed to checkout",
    "message box",
    "comment box",
    "order comment",
    "card name",
    "card number",
    "cvc",
    "expiry month",
    "expiry year",

    # Hallucinated targets the LLM invents
    "non-deal price",
    "deal price",
    "apply filter",
    "price filter",

    # Critical click targets — always resolve fresh
    "product with minimum",
    "product with price",
    "view product",
    "add to basket",
    "add to cart",
    "sort by price",
    "cheapest product",
    "most expensive",
    "lowest priced",
    "highest priced",
    "search button",     # ← was healing 2x, prevent further drift
]

def _is_xpath_valid(xpath):
    """
    Reject obviously malformed XPaths before saving.
    Common LLM mistakes:
    - Using @text=value instead of text()='value'
    - Unbalanced brackets or parens
    - Empty strings
    """
    if not xpath or not isinstance(xpath, str):
        return False
    xpath = xpath.strip()
    if not xpath:
        return False

    # Common malformed patterns
    if "@text=" in xpath or "@text " in xpath or "[@text]" in xpath:
        return False

    # Bracket / paren balance
    if xpath.count("[") != xpath.count("]"):
        return False
    if xpath.count("(") != xpath.count(")"):
        return False
    if xpath.count("'") % 2 != 0 and xpath.count('"') % 2 != 0:
        return False

    # Must start with / or //
    if not xpath.startswith("/") and not xpath.startswith("("):
        return False

    return True


def load():
    if not os.path.exists(LOCATOR_FILE):
        return {}
    with open(LOCATOR_FILE, "r") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}


def save_locator(target, by, value, confidence=1.0):
    target_lower = target.lower().strip()
    value_lower  = value.lower() if isinstance(value, str) else ""

    # ── Block protected targets entirely ──────────────────────────
    if any(t in target_lower for t in DO_NOT_CACHE):
        print(f"🚫 Skipping cache for '{target}': {value}")
        return

    # ── Validate XPath structure ──────────────────────────────────
    if by == "xpath" and not _is_xpath_valid(value):
        print(f"⚠️ Rejected malformed XPath for '{target}': {value}")
        return

    # ── Reject bad locators for form fields ───────────────────────
    if any(t in target_lower for t in FORM_FIELD_TARGETS):
        if any(bad in value for bad in INVALID_FOR_FORM):
            print(f"⚠️ Rejected bad locator for form '{target}': {value}")
            return

    # ── Reject bad locators for clicks ────────────────────────────
    if any(t in target_lower for t in CLICK_TARGETS):
        for bad in INVALID_FOR_CLICK:
            if bad in value or bad.lower() in value_lower:
                print(
                    f"⚠️ Rejected bad locator for click "
                    f"'{target}': {value}"
                )
                return

    os.makedirs("locators", exist_ok=True)
    data = load()
    data[target_lower] = {
        "by":         by,
        "value":      value,
        "confidence": confidence,
    }
    with open(LOCATOR_FILE, "w") as f:
        json.dump(data, f, indent=2)
    print(f"💾 Locator saved for '{target}': {value}")


def get_locator(target):
    target_lower = target.lower().strip()
    if any(t in target_lower for t in DO_NOT_CACHE):
        return None
    return load().get(target_lower)