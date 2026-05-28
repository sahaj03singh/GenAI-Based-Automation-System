"""
config_bootstrapper.py — Semi-automatic site_config.py generator.

Place this file at: utils/config_bootstrapper.py

PURPOSE
-------
Cuts down the manual effort of writing a new site_config.py by hand.
It crawls the pages you point it at, uses an LLM (GPT-4o-mini) to
*propose* element locators semantically, and then VERIFIES every
proposed locator against the live DOM before trusting it.

DESIGN PRINCIPLE — "never silently wrong"
-----------------------------------------
The LLM only proposes. A locator is written as VERIFIED **only** if it
resolves to exactly ONE element in the live page. Anything that resolves
to zero or many elements is downgraded — never silently emitted as fact.

Output is a ready-to-edit site_config.py draft with three confidence
tiers clearly marked in comments:

    # [VERIFIED]      selector resolved to exactly 1 element  -> safe
    # [PROPOSED]      a likely candidate, but needs your eyes
    # [NEEDS_HUMAN]   could not resolve reliably -> TODO stub

WHAT IT CANNOT DO (by design — these are YOUR test-design decisions)
--------------------------------------------------------------------
- It cannot invent your intent `match` phrases.
- It cannot invent fallback ladders (e.g. the 4.5->4.4->4.3 rating
  preference in view_product). Those encode what YOU want.
- It cannot decide which intents are `strict: True`.
These are emitted as TODO stubs for you to fill in.

USAGE
-----
    python -m utils.config_bootstrapper \
        --base-url https://www.automationexercise.com \
        --pages homepage:/:role=home \
                products:/products:role=listing \
                product:/product_details/1:role=detail \
                cart:/view_cart:role=cart \
                login:/login:role=login \
        --intents search_input,search_submit,view_product,add_to_basket,view_basket,product_detail_add_to_cart,category_link,brand_link,filter_compare \
        --out site_config_DRAFT.py

    # Dry run (no LLM, heuristics + verification only):
    python -m utils.config_bootstrapper --base-url ... --no-llm

REQUIREMENTS
------------
- selenium (already in your project)
- openai  (already in your project; only used unless --no-llm)
- A webdriver setup. By default this tries to import your project's
  existing driver factory; if not found, it falls back to a plain
  Chrome webdriver.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from dataclasses import dataclass, field
from typing import Optional

# ──────────────────────────────────────────────────────────────────
# Confidence tiers
# ──────────────────────────────────────────────────────────────────
VERIFIED = "VERIFIED"
PROPOSED = "PROPOSED"
NEEDS_HUMAN = "NEEDS_HUMAN"


# ──────────────────────────────────────────────────────────────────
# A single proposed (and possibly verified) locator
# ──────────────────────────────────────────────────────────────────
@dataclass
class LocatorCandidate:
    intent: str
    by: str                      # "id" | "xpath" | "css"
    value: str
    tier: str = NEEDS_HUMAN
    match_count: int = 0
    source: str = "heuristic"    # "heuristic" | "llm"
    note: str = ""

    def as_strategy_tuple(self) -> str:
        """Render as a Python ("by", "value") tuple literal."""
        safe = self.value.replace('"', '\\"')
        return f'("{self.by}", "{safe}")'


# ──────────────────────────────────────────────────────────────────
# Driver acquisition — reuse the project's driver if available
# ──────────────────────────────────────────────────────────────────
def get_driver():
    """
    Try to reuse the project's existing driver factory. Fall back to a
    plain headless Chrome if none is found. This keeps the bootstrapper
    consistent with how the framework itself launches browsers.
    """
    # Attempt common project entry points (adjust if yours differs).
    for modpath, fname in [
        ("utils.driver_factory", "get_driver"),
        ("utils.driver_factory", "create_driver"),
        ("conftest", "make_driver"),
    ]:
        try:
            mod = __import__(modpath, fromlist=[fname])
            factory = getattr(mod, fname, None)
            if callable(factory):
                print(f"[driver] Using project factory {modpath}.{fname}()")
                return factory()
        except Exception:
            continue

    # Fallback: plain Chrome.
    print("[driver] No project factory found; using plain Chrome.")
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    opts = Options()
    opts.add_argument("--start-maximized")
    # Headful is more reliable against anti-bot; flip to headless if you prefer.
    # opts.add_argument("--headless=new")
    return webdriver.Chrome(options=opts)


# ──────────────────────────────────────────────────────────────────
# DOM verification — the heart of "never silently wrong"
# ──────────────────────────────────────────────────────────────────
def count_matches(driver, by: str, value: str) -> int:
    """Return how many elements a locator resolves to (0, 1, or many)."""
    from selenium.webdriver.common.by import By
    by_map = {
        "id": By.ID,
        "xpath": By.XPATH,
        "css": By.CSS_SELECTOR,
        "name": By.NAME,
    }
    sel = by_map.get(by)
    if sel is None:
        return 0
    try:
        els = driver.find_elements(sel, value)
        # Only count elements that are actually present (displayed where possible)
        visible = []
        for e in els:
            try:
                if e.is_displayed():
                    visible.append(e)
            except Exception:
                # Stale or detached — ignore
                pass
        # If nothing is "displayed" but elements exist, still report raw count
        return len(visible) if visible else len(els)
    except Exception:
        return 0


def verify_candidate(driver, cand: LocatorCandidate) -> LocatorCandidate:
    """
    Resolve a candidate against the live DOM and assign a confidence tier:
      exactly 1 match  -> VERIFIED
      2+ matches       -> PROPOSED (ambiguous; needs human disambiguation)
      0 matches        -> NEEDS_HUMAN
    """
    n = count_matches(driver, cand.by, cand.value)
    cand.match_count = n
    if n == 1:
        cand.tier = VERIFIED
        cand.note = "resolved to exactly one element"
    elif n >= 2:
        cand.tier = PROPOSED
        cand.note = f"ambiguous: matched {n} elements — pick or scope down"
    else:
        cand.tier = NEEDS_HUMAN
        cand.note = "no element matched — needs manual locator"
    return cand


# ──────────────────────────────────────────────────────────────────
# Heuristic candidate generation (deterministic, no cost)
# ──────────────────────────────────────────────────────────────────
# Maps a known intent to deterministic locator guesses, tried in order.
HEURISTICS: dict[str, list[tuple[str, str]]] = {
    "search_input": [
        ("css", "input[type='search']"),
        ("css", "input[name='search']"),
        ("css", "input[name='q']"),
        ("css", "input[placeholder*='earch']"),
        ("css", "input[aria-label*='earch']"),
        ("id", "search"),
    ],
    "search_submit": [
        ("css", "button[type='submit']"),
        ("css", "input[type='submit']"),
        ("css", "button[aria-label*='earch']"),
        ("xpath", "//button[contains(translate(.,'SEARCH','search'),'search')]"),
    ],
    "view_product": [
        ("css", "a[href*='/product']"),
        ("css", "a[href*='/dp/']"),
        ("css", ".product a"),
        ("css", "[data-product] a"),
    ],
    "add_to_basket": [
        ("xpath", "//*[contains(translate(.,'ADD','add'),'add to') and "
                  "(contains(translate(.,'CART','cart'),'cart') or "
                  "contains(translate(.,'BASKET','basket'),'basket'))]"),
        ("css", "button[name*='add']"),
        ("css", "a[href*='add_to_cart']"),
    ],
    "view_basket": [
        ("css", "a[href*='cart']"),
        ("css", "a[href*='basket']"),
        ("css", "[aria-label*='art']"),
    ],
    "proceed_to_checkout": [
        ("xpath", "//*[contains(translate(.,'CHECKOUT','checkout'),'checkout')]"),
        ("css", "a[href*='checkout']"),
    ],
    # ── Login intents ─────────────────────────────────────────
    # automationexercise.com provides data-qa attributes designed
    # for test automation — try those first as they are the most
    # stable, then fall back to type/name-based guesses.
    "login_email": [
        ("css", "input[data-qa='login-email']"),
        ("css", "form[action*='login'] input[type='email']"),
        ("css", "input[name='email']"),
    ],
    "login_password": [
        ("css", "input[data-qa='login-password']"),
        ("css", "form[action*='login'] input[type='password']"),
        ("css", "input[name='password']"),
    ],
    "login_button": [
        ("css", "button[data-qa='login-button']"),
        ("xpath", "//form[contains(@action,'login')]//button[@type='submit']"),
        ("xpath", "//button[contains(translate(.,'LOGIN','login'),'login')]"),
    ],
    # ── New simple intents ────────────────────────────────────
    "product_detail_add_to_cart": [
        # On a product DETAIL page (not listing), the add-to-cart
        # is usually a <button> in the buy-box, not the listing's <a>.
        ("css", "button.cart"),
        ("css", "button.btn.cart"),
        ("css", "button[type='button'].btn.cart"),
        ("xpath", "//button[contains(@class,'cart') and "
                  "(contains(.,'Add to cart') or contains(.,'Add to Cart'))]"),
        ("css", "#add-to-cart-button"),
        ("css", "button[name='add-to-cart']"),
    ],
    "category_link": [
        # Category navigation links — usually in a sidebar or nav menu.
        ("css", "a[href*='/category_products/']"),
        ("css", ".category-products a"),
        ("css", "#accordian a"),
    ],
    "brand_link": [
        # Brand navigation — site-dependent but a few common patterns.
        ("css", "a[href*='/brand_products/']"),
        ("css", ".brands_products a"),
        ("css", ".brands-name a"),
    ],
}


def heuristic_candidates(intent: str) -> list[LocatorCandidate]:
    out = []
    for by, value in HEURISTICS.get(intent, []):
        out.append(LocatorCandidate(intent=intent, by=by, value=value,
                                     source="heuristic"))
    return out


# ──────────────────────────────────────────────────────────────────
# LLM candidate generation (semantic; used unless --no-llm)
# ──────────────────────────────────────────────────────────────────
LLM_SYSTEM_PROMPT = (
    "You are a web-automation locator expert. Given the cleaned HTML of a "
    "page and a target UI element described in plain English, propose up to "
    "3 robust Selenium locators that would uniquely identify that element. "
    "Prefer stable attributes (id, name, data-*, aria-label) over brittle, "
    "auto-generated class names. Return STRICT JSON only, no prose, in the "
    "form: {\"candidates\":[{\"by\":\"id|css|xpath\",\"value\":\"...\"}]}. "
    "If you cannot find a confident locator, return an empty candidates list."
)


def _clean_html(html: str, max_chars: int = 9000) -> str:
    """
    Reduce a page's HTML to only the *interactive* elements an LLM needs to
    locate things: inputs, buttons, anchors, forms, selects. This keeps the
    payload small (so the model's JSON reply is never truncated) and focuses
    its attention on locatable controls rather than marketing copy.

    Dependency-free; falls back to a plain strip-and-truncate if extraction
    yields too little.
    """
    import re
    h = re.sub(r"<script[\s\S]*?</script>", " ", html, flags=re.I)
    h = re.sub(r"<style[\s\S]*?</style>", " ", h, flags=re.I)
    h = re.sub(r"<!--[\s\S]*?-->", " ", h)

    # Pull just the opening tags of interactive elements, with their attrs.
    tags = re.findall(
        r"<(?:input|button|a|form|select|textarea)\b[^>]*>",
        h, flags=re.I)
    extracted = " ".join(tags)

    chosen = extracted if len(extracted) > 200 else h
    chosen = re.sub(r"\s+", " ", chosen).strip()
    return chosen[:max_chars]


def llm_candidates(intent: str, description: str, page_html: str,
                   model: str = "gpt-4o-mini",
                   timeout: float = 30.0) -> list[LocatorCandidate]:
    """
    Ask the LLM to propose locators. Returns [] on any failure — the
    caller still has heuristic candidates and DOM verification, so an
    LLM hiccup never produces a wrong VERIFIED result.

    Hardened: per-call timeout so it can never hang; tolerant JSON parsing
    so a slightly malformed reply degrades to [] instead of crashing.
    """
    try:
        from openai import OpenAI
        # Fail fast instead of hanging if the API is unreachable.
        client = OpenAI(timeout=timeout, max_retries=1)
    except Exception as e:  # SDK missing or no key
        print(f"[llm]   {intent}: OpenAI unavailable ({e}); using heuristics only.")
        return []

    user = (
        f"TARGET ELEMENT (plain English): {description}\n\n"
        f"INTERACTIVE ELEMENTS ON PAGE (cleaned):\n{_clean_html(page_html)}"
    )
    try:
        print(f"[llm]   {intent}: querying {model} …", flush=True)
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": LLM_SYSTEM_PROMPT},
                {"role": "user", "content": user},
            ],
            temperature=0,
            max_tokens=400,
            response_format={"type": "json_object"},
        )
        raw = (resp.choices[0].message.content or "").strip()
        data = _safe_json(raw)
        if data is None:
            print(f"[llm]   {intent}: reply was not valid JSON; using heuristics only.")
            return []
        out = []
        for c in data.get("candidates", []):
            by = str(c.get("by", "")).lower().strip()
            value = str(c.get("value", "")).strip()
            if by in ("id", "css", "xpath", "name") and value:
                out.append(LocatorCandidate(intent=intent, by=by,
                                            value=value, source="llm"))
        print(f"[llm]   {intent}: {len(out)} candidate(s) proposed.")
        return out
    except Exception as e:
        print(f"[llm]   {intent}: generation failed ({e}); using heuristics only.")
        return []


def _safe_json(raw: str):
    """
    Parse JSON tolerantly. Returns a dict, or None if unrecoverable.
    Handles code-fences and trailing junk after the first JSON object.
    """
    import re
    if not raw:
        return None
    # Strip ```json fences if present.
    raw = re.sub(r"^```(?:json)?|```$", "", raw.strip(), flags=re.I).strip()
    try:
        return json.loads(raw)
    except Exception:
        pass
    # Try to extract the first {...} block.
    m = re.search(r"\{[\s\S]*\}", raw)
    if m:
        try:
            return json.loads(m.group(0))
        except Exception:
            return None
    return None


# Plain-English descriptions per intent, fed to the LLM.
INTENT_DESCRIPTIONS = {
    "search_input": "the main search text input box",
    "search_submit": "the button that submits the search",
    "view_product": "a link that opens an individual product's detail page",
    "add_to_basket": "the main 'add to basket' / 'add to cart' button in the "
                     "product's primary buy box (NOT one on a recommendation card)",
    "view_basket": "the link or button that opens the shopping basket/cart",
    "proceed_to_checkout": "the button that proceeds from the basket to checkout",
    # ── Login intents ────────────────────────────────────────────
    "login_email": "the EMAIL input field of the LOGIN form (the "
                   "'login to your account' form — NOT the signup form's "
                   "email field which is a separate input)",
    "login_password": "the PASSWORD input field of the LOGIN form",
    "login_button": "the submit button of the LOGIN form (labelled 'Login')",
    # ── New intents ──────────────────────────────────────────────
    "product_detail_add_to_cart": "the 'Add to cart' button on an individual "
                                  "product's detail page (typically a <button>, "
                                  "NOT the smaller add-to-cart on listing cards)",
    "category_link": "a navigation link that filters products by category "
                     "(e.g. Women, Men) — usually in a sidebar accordion",
    "brand_link": "a navigation link that filters products by brand (e.g. Polo, "
                  "Madame) — typically a list in a sidebar",
    # ── Filter pattern (handled by discover_filter_pattern, not LLM) ─
    "filter_compare": "a repeating product listing pattern from which we need "
                      "to extract: container, price/value, and product link",
}


# ──────────────────────────────────────────────────────────────────
# Page-role policy — which intents are semantically valid on which
# page roles. The bootstrapper refuses to resolve an intent on a
# page whose role is not in this allow-list — preventing the LLM
# from "verifying" a syntactically-unique but semantically-wrong
# locator (e.g. proposing `id=subscribe` for search_submit on a
# homepage, or finding a "btn-success" CTA on a homepage and
# tagging it as the product-detail add-to-cart).
#
# Roles a page can declare via `--pages name:path:role=X`:
#   home, listing, detail, cart, login, checkout, unknown
#
# 'unknown' is permissive — it allows everything (backward compat
# for the old two-field --pages syntax). To get role-gating, every
# page must declare a role.
# ──────────────────────────────────────────────────────────────────
INTENT_ALLOWED_ROLES: dict[str, set[str]] = {
    "search_input":               {"home", "listing", "unknown"},
    "search_submit":              {"home", "listing", "unknown"},
    "view_product":               {"home", "listing", "unknown"},
    "add_to_basket":              {"listing", "unknown"},
    "view_basket":                {"home", "listing", "detail", "cart",
                                   "checkout", "unknown"},
    "proceed_to_checkout":        {"cart", "unknown"},
    # ── New intents ──────────────────────────────────────────
    "product_detail_add_to_cart": {"detail", "unknown"},
    "category_link":              {"home", "listing", "unknown"},
    "brand_link":                 {"home", "listing", "unknown"},
    # ── Pattern discovery ────────────────────────────────────
    "filter_compare":             {"listing", "unknown"},
    # ── Login intents (login page only) ──────────────────────
    "login_email":                {"login", "unknown"},
    "login_password":             {"login", "unknown"},
    "login_button":               {"login", "unknown"},
}


def _intent_allowed_on(intent: str, role: str) -> bool:
    """
    Return True if `intent` is semantically meaningful on a page of
    the given `role`. Unknown intents default to allowed (so adding
    a new intent doesn't silently get gated out).
    """
    allowed = INTENT_ALLOWED_ROLES.get(intent)
    if allowed is None:
        return True   # be permissive for unrecognised intents
    return role in allowed


# ──────────────────────────────────────────────────────────────────
# Filter-compare pattern discovery (the A2 capability)
# ──────────────────────────────────────────────────────────────────
# This is the only intent type that breaks the "one intent = one
# locator" assumption. A filter_compare intent has three pieces:
#   container_xpath  — wraps each repeated item (must match N≥2)
#   value_xpath      — inside a container, finds the price/value text
#   link_xpath       — inside a container, finds the product link
#
# Verification is also different: VERIFIED means container matches
# ≥2 elements AND value/link resolve inside ≥80% of those containers.

@dataclass
class FilterPattern:
    container_xpath: str = ""
    value_xpath: str = ""
    link_xpath: str = ""
    extract_pattern: str = r"\d+"
    container_match_count: int = 0
    value_hit_ratio: float = 0.0   # fraction of containers with a value
    link_hit_ratio: float = 0.0    # fraction of containers with a link
    tier: str = NEEDS_HUMAN
    note: str = ""


# Common shapes a product-listing container takes across e-commerce sites.
# Tried in order; the bootstrapper picks the first that matches ≥2 elements
# AND yields value+link in most of them.
_CONTAINER_CANDIDATES = [
    "//div[contains(@class,'product-image-wrapper')]",  # automationexercise
    "//div[contains(@class,'product-item')]",
    "//div[contains(@class,'product-card')]",
    "//div[contains(@class,'productCard')]",
    "//li[contains(@class,'product')]",
    "//article[contains(@class,'product')]",
    "//div[@data-product-id]",
    "//div[contains(@class,'item') and .//a[contains(@href,'product')]]",
]

# Common value-text patterns (price, rating, etc.) — relative to a container.
_VALUE_CANDIDATES = [
    ".//h2[contains(text(),'Rs.')]",
    ".//h2[contains(text(),'$')]",
    ".//h2[contains(text(),'£')]",
    ".//h2[contains(text(),'€')]",
    ".//*[contains(@class,'price')]",
    ".//*[contains(@class,'Price')]",
    ".//span[contains(text(),'$') or contains(text(),'£') or contains(text(),'€') or contains(text(),'Rs.')]",
]

# Common product-link patterns — relative to a container.
_LINK_CANDIDATES = [
    ".//a[contains(@href,'/product_details/')]",
    ".//a[contains(@href,'/product/')]",
    ".//a[contains(@href,'/products/')]",
    ".//a[contains(@href,'/dp/')]",
    ".//a[contains(@href,'/p/')]",
    ".//a[1]",  # fallback: first link inside the container
]


def discover_filter_pattern(driver, min_containers: int = 3,
                            min_hit_ratio: float = 0.8) -> FilterPattern:
    """
    Discover the repeating-grid pattern on the current page.

    Algorithm:
      1. Try each candidate container XPath; keep ones matching ≥min_containers.
      2. For each viable container, sample value+link candidates and measure
         what fraction of containers each pair resolves inside of.
      3. Pick the (container, value, link) triple with the highest joint hit
         ratio. VERIFIED only if both ratios ≥ min_hit_ratio.

    Strictly DOM-driven — no LLM, fully deterministic, fully verifiable.
    """
    from selenium.webdriver.common.by import By

    best = FilterPattern()

    for container_xpath in _CONTAINER_CANDIDATES:
        try:
            containers = driver.find_elements(By.XPATH, container_xpath)
        except Exception:
            continue
        n = len(containers)
        if n < min_containers:
            continue

        # For this container, find the best value+link inside it.
        best_for_this_container = None
        for vx in _VALUE_CANDIDATES:
            v_hits = 0
            for c in containers:
                try:
                    if c.find_elements(By.XPATH, vx):
                        v_hits += 1
                except Exception:
                    pass
            v_ratio = v_hits / n if n else 0.0
            if v_ratio < 0.5:  # not worth pairing with a link
                continue
            for lx in _LINK_CANDIDATES:
                l_hits = 0
                for c in containers:
                    try:
                        if c.find_elements(By.XPATH, lx):
                            l_hits += 1
                    except Exception:
                        pass
                l_ratio = l_hits / n if n else 0.0
                if l_ratio < 0.5:
                    continue
                joint = v_ratio * l_ratio
                if (best_for_this_container is None
                        or joint > best_for_this_container[0]):
                    best_for_this_container = (joint, vx, lx, v_ratio, l_ratio)

        if best_for_this_container is None:
            continue

        joint, vx, lx, v_ratio, l_ratio = best_for_this_container
        # Compare to global best across containers.
        candidate = FilterPattern(
            container_xpath=container_xpath,
            value_xpath=vx,
            link_xpath=lx,
            extract_pattern=r"\d+",
            container_match_count=n,
            value_hit_ratio=v_ratio,
            link_hit_ratio=l_ratio,
        )
        # Score = joint hit ratio, weighted by container count up to a cap.
        candidate_score = joint * min(n, 20)
        best_score = (best.value_hit_ratio * best.link_hit_ratio
                      * min(best.container_match_count, 20))
        if candidate_score > best_score:
            best = candidate

    # Final tiering.
    if best.container_match_count >= min_containers:
        if (best.value_hit_ratio >= min_hit_ratio
                and best.link_hit_ratio >= min_hit_ratio):
            best.tier = VERIFIED
            best.note = (f"container matched {best.container_match_count} items; "
                         f"value resolved in {best.value_hit_ratio:.0%}, "
                         f"link in {best.link_hit_ratio:.0%}")
        else:
            best.tier = PROPOSED
            best.note = (f"container matched {best.container_match_count} items "
                         f"but value/link hit ratio below {min_hit_ratio:.0%} "
                         f"(value={best.value_hit_ratio:.0%}, "
                         f"link={best.link_hit_ratio:.0%})")
    else:
        best.tier = NEEDS_HUMAN
        best.note = (f"no container XPath matched ≥{min_containers} items "
                     f"on this page")
    return best



def _session_alive(driver) -> bool:
    """Return True if the browser session is still usable."""
    try:
        _ = driver.current_url
        return True
    except Exception:
        return False


def _safe_page_source(driver) -> str:
    """Get page_source without crashing if the session dropped."""
    try:
        return driver.page_source
    except Exception as e:
        print(f"[warn]  could not read page source ({e}); skipping LLM this page.")
        return ""


# ──────────────────────────────────────────────────────────────────
# DOM extractor (Version A) — synthesise ranked, stable locators
# directly from the live page instead of relying on hardcoded guesses.
# ──────────────────────────────────────────────────────────────────
# For each interactive element we build the MOST STABLE locator
# available, ranked by this attribute preference:
#   1. id            (unless it looks auto-generated)
#   2. data-qa / data-test / data-testid   (automation attributes)
#   3. name
#   4. a single unique class
#   5. type + tag    (weak; only as a scoped guess)
# We also capture per-element context (tag, type, label/text,
# placeholder, the ancestor form's id/action) so the LLM can resolve
# SAME-PAGE semantic confusion (e.g. login-email vs signup-email).

import re as _re

# ids that look machine-generated -> not stable, don't use as a locator
_AUTO_ID_RE = _re.compile(
    r"(ember\d+|react-|:r[0-9a-z]+:|^[0-9a-f]{8,}$|\d{4,}$|uid[-_]?\d+)",
    _re.IGNORECASE,
)
_AUTOMATION_ATTRS = ["data-qa", "data-test", "data-testid", "data-cy"]


def _looks_auto_generated(value: str) -> bool:
    return bool(value) and bool(_AUTO_ID_RE.search(value))


def _css_escape_attr(v: str) -> str:
    return v.replace("'", "\\'")


@dataclass
class ExtractedElement:
    by: str
    value: str
    stability: int          # lower = more stable (1 best)
    tag: str = ""
    etype: str = ""
    text: str = ""
    placeholder: str = ""
    form_ctx: str = ""      # ancestor form id/action, for LLM disambiguation


def _best_locator_for(driver, el) -> Optional[ExtractedElement]:
    """
    Given a live WebElement, synthesise the most stable locator for it,
    plus context. Returns None if we cannot build anything usable.
    """
    from selenium.webdriver.common.by import By

    def attr(name):
        try:
            return (el.get_attribute(name) or "").strip()
        except Exception:
            return ""

    tag = (el.tag_name or "").lower()
    etype = attr("type")
    text = (el.text or "").strip()[:40]
    placeholder = attr("placeholder")

    # Ancestor form context (id or action) — helps the LLM tell which
    # form an input belongs to (login vs signup vs search vs newsletter).
    form_ctx = ""
    try:
        from selenium.webdriver.common.by import By as _By2
        form = el.find_element(_By2.XPATH, "./ancestor::form[1]")
        fid = (form.get_attribute("id") or "").strip()
        faction = (form.get_attribute("action") or "").strip()
        form_ctx = fid or faction
    except Exception:
        form_ctx = ""

    common = dict(tag=tag, etype=etype, text=text,
                  placeholder=placeholder, form_ctx=form_ctx)

    # 1. id (if not auto-generated)
    eid = attr("id")
    if eid and not _looks_auto_generated(eid):
        return ExtractedElement("id", eid, 1, **common)

    # 2. automation attributes
    for a in _AUTOMATION_ATTRS:
        v = attr(a)
        if v:
            return ExtractedElement(
                "css", f"{tag}[{a}='{_css_escape_attr(v)}']", 2, **common)

    # 3. name
    nm = attr("name")
    if nm:
        return ExtractedElement(
            "css", f"{tag}[name='{_css_escape_attr(nm)}']", 3, **common)

    # 4. a single class that is unique on the page
    cls = attr("class")
    if cls:
        for token in cls.split():
            if not token or _looks_auto_generated(token):
                continue
            sel = f"{tag}.{token}"
            try:
                if len(driver.find_elements(By.CSS_SELECTOR, sel)) == 1:
                    return ExtractedElement("css", sel, 4, **common)
            except Exception:
                pass

    # 5. weak fallback: tag + type (rarely unique; LLM may still pick it)
    if etype:
        return ExtractedElement(
            "css", f"{tag}[type='{_css_escape_attr(etype)}']", 5, **common)

    return None


def extract_interactive_elements(driver, cap: int = 120
                                 ) -> list[ExtractedElement]:
    """
    Walk the live DOM, enumerate interactive elements, and synthesise a
    ranked stable locator + context for each. Deduplicated by locator.
    """
    from selenium.webdriver.common.by import By
    out: list[ExtractedElement] = []
    seen: set[tuple[str, str]] = set()
    try:
        els = driver.find_elements(
            By.CSS_SELECTOR,
            "input, button, a, select, textarea, [role='button']")
    except Exception:
        return out
    for el in els[:cap]:
        try:
            if not el.is_displayed():
                continue
        except Exception:
            continue
        ex = _best_locator_for(driver, el)
        if not ex:
            continue
        key = (ex.by, ex.value)
        if key in seen:
            continue
        seen.add(key)
        out.append(ex)
    # Most stable first.
    out.sort(key=lambda e: e.stability)
    return out


def _extracted_to_context_block(elements: list[ExtractedElement]) -> str:
    """Render extracted elements as a compact list for the LLM prompt."""
    lines = []
    for i, e in enumerate(elements):
        bits = [f"#{i}", f"<{e.tag}>"]
        if e.etype:
            bits.append(f"type={e.etype}")
        if e.text:
            bits.append(f"text='{e.text}'")
        if e.placeholder:
            bits.append(f"placeholder='{e.placeholder}'")
        if e.form_ctx:
            bits.append(f"form='{e.form_ctx}'")
        bits.append(f"locator=({e.by},{e.value})")
        lines.append(" ".join(bits))
    return "\n".join(lines)


def resolve_intent(driver, intent: str, use_llm: bool,
                   model: str) -> list[LocatorCandidate]:
    """
    Hybrid pipeline (the version that produced the clean suite result):

      Heuristics provide a SEMANTIC ANCHOR — they encode real knowledge
      of what each intent's element usually looks like, so they stay
      correct even when the right element is not on the crawled page.

      The DOM extractor + LLM-selection is used as an ENHANCEMENT, and is
      only allowed to LEAD for form-field-style intents (login_email,
      search_input, *_email, *_password, *_name, review fields …) where
      the target is reliably present on the crawled page and the extra
      per-element form context measurably helps disambiguate (e.g.
      login-email vs signup-email).

      For all other intents the extractor is demoted to a fallback, so it
      can fill gaps without overriding a good heuristic with a confident
      wrong pick (the regression we observed when the extractor led for
      navigation/action intents and chose the search box).
    """
    cands: list[LocatorCandidate] = []

    # Decide whether this intent is a "form field" intent — the only
    # class where extractor+LLM is trusted to LEAD.
    form_field_intent = (
        intent in {"search_input", "login_email", "login_password"}
        or intent.endswith(("_email", "_password", "_name"))
        or intent in {"reviewer_name", "review_text", "contact_name",
                       "contact_email", "contact_subject", "contact_message",
                       "signup_name", "signup_email"}
    )

    # Heuristic candidates (the semantic anchor) — always gathered.
    heur = heuristic_candidates(intent)

    # DOM extraction (+ optional LLM selection).
    extracted = extract_interactive_elements(driver)
    dom_cands: list[LocatorCandidate] = []
    for e in extracted:
        dom_cands.append(LocatorCandidate(
            intent=intent, by=e.by, value=e.value, source="dom",
            note=f"stability={e.stability}"
                 + (f"; form={e.form_ctx}" if e.form_ctx else "")))
    llm_cands: list[LocatorCandidate] = []
    if use_llm and extracted:
        desc = INTENT_DESCRIPTIONS.get(intent, intent.replace("_", " "))
        ctx = _extracted_to_context_block(extracted)
        llm_cands = llm_pick_from_extracted(intent, desc, ctx, extracted,
                                            model=model)

    # Assemble in priority order depending on intent class.
    if form_field_intent:
        # Extractor+LLM leads (form context disambiguation is valuable),
        # heuristics back it up, raw DOM last.
        cands = llm_cands + heur + dom_cands
    else:
        # Heuristics lead (semantic anchor), extractor only fills gaps.
        cands = heur + llm_cands + dom_cands

    # Verify everything against the live DOM.
    for c in cands:
        verify_candidate(driver, c)

    # Sort: best tier first; within a tier preserve the priority above
    # (so a VERIFIED heuristic for a nav intent beats a VERIFIED extractor
    # pick). We use list position as a stable secondary key.
    pos = {id(c): i for i, c in enumerate(cands)}
    tier_rank = {VERIFIED: 0, PROPOSED: 1, NEEDS_HUMAN: 2}
    cands.sort(key=lambda c: (tier_rank[c.tier], pos[id(c)]))

    # De-duplicate by (by, value), keeping best.
    seen, deduped = set(), []
    for c in cands:
        k = (c.by, c.value)
        if k in seen:
            continue
        seen.add(k)
        deduped.append(c)
    return deduped


def llm_pick_from_extracted(intent: str, description: str,
                            context_block: str,
                            extracted: list[ExtractedElement],
                            model: str = "gpt-4o-mini",
                            timeout: float = 30.0
                            ) -> list[LocatorCandidate]:
    """
    Ask the LLM which extracted element(s) match the intent. The LLM
    chooses by INDEX from the extracted list — it does not invent
    locators, so it cannot hallucinate a selector that isn't really on
    the page. Returns [] on any failure (DOM candidates still stand).
    """
    try:
        from openai import OpenAI
        client = OpenAI(timeout=timeout, max_retries=1)
    except Exception as e:
        print(f"[llm]   {intent}: OpenAI unavailable ({e}); DOM candidates only.")
        return []

    system = (
        "You map a plain-English UI intent to the correct on-page element. "
        "You are given a numbered list of REAL interactive elements already "
        "extracted from the page, each with a verified locator. Choose the "
        "index(es) that best match the intent. Use the form/label/placeholder "
        "context to disambiguate similar elements (e.g. a LOGIN email field "
        "versus a SIGNUP email field). Reply ONLY as JSON: "
        '{"indices": [<int>, ...]} — best first, at most 3. If none match, '
        'reply {"indices": []}.'
    )
    user = (f"INTENT: {description}\n\nEXTRACTED ELEMENTS:\n{context_block}")
    try:
        print(f"[llm]   {intent}: selecting from "
              f"{len(extracted)} extracted elements via {model} …", flush=True)
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "system", "content": system},
                      {"role": "user", "content": user}],
            temperature=0, max_tokens=80,
            response_format={"type": "json_object"},
        )
        data = _safe_json((resp.choices[0].message.content or "").strip())
        if not data:
            return []
        out = []
        for idx in data.get("indices", [])[:3]:
            if isinstance(idx, int) and 0 <= idx < len(extracted):
                e = extracted[idx]
                out.append(LocatorCandidate(
                    intent=intent, by=e.by, value=e.value,
                    source="llm",
                    note=f"LLM-picked extracted #{idx}"
                         + (f"; form={e.form_ctx}" if e.form_ctx else "")))
        print(f"[llm]   {intent}: picked {len(out)} element(s).")
        return out
    except Exception as e:
        print(f"[llm]   {intent}: selection failed ({e}); DOM candidates only.")
        return []


# ──────────────────────────────────────────────────────────────────
# Page crawling
# ──────────────────────────────────────────────────────────────────
@dataclass
class PageResult:
    name: str
    path: str
    final_url: str = ""
    title: str = ""
    ready_signal: Optional[tuple[str, str]] = None
    visible_text_sample: list[str] = field(default_factory=list)


def crawl_page(driver, base_url: str, name: str, path: str,
               settle: float = 2.0) -> PageResult:
    url = base_url.rstrip("/") + "/" + path.lstrip("/")
    print(f"[crawl] {name}: {url}")
    driver.get(url)
    time.sleep(settle)
    res = PageResult(name=name, path=path,
                     final_url=driver.current_url,
                     title=(driver.title or "").strip())
    # Propose a page_ready_signal: prefer a stable id on a form/main region.
    res.ready_signal = _propose_ready_signal(driver)
    # Sample some visible text to seed verify_keywords (proposed only).
    res.visible_text_sample = _sample_visible_text(driver)
    return res


def _propose_ready_signal(driver):
    from selenium.webdriver.common.by import By
    for by, val in [
        (By.TAG_NAME, "main"),
        (By.ID, "search"),
        (By.CSS_SELECTOR, "form[role='search']"),
        (By.TAG_NAME, "h1"),
    ]:
        try:
            els = driver.find_elements(by, val)
            if len(els) == 1:
                # Prefer an id if the element has one.
                el_id = els[0].get_attribute("id")
                if el_id:
                    return ("id", el_id)
                if by == By.TAG_NAME:
                    return ("xpath", f"//{val}")
        except Exception:
            continue
    return None


def _sample_visible_text(driver, limit: int = 12):
    """Grab short visible phrases to *propose* (never assert) verify keywords."""
    try:
        body = driver.find_element("tag name", "body")
        text = (body.text or "").lower()
    except Exception:
        return []
    phrases = []
    for line in text.splitlines():
        line = line.strip()
        if 3 <= len(line) <= 40 and line not in phrases:
            phrases.append(line)
        if len(phrases) >= limit:
            break
    return phrases


# ──────────────────────────────────────────────────────────────────
# Draft site_config.py emission
# ──────────────────────────────────────────────────────────────────
def emit_config(base_url: str, pages: list[PageResult],
                intent_results: dict[str, list[LocatorCandidate]],
                filter_pattern: FilterPattern | None = None) -> str:
    L = []
    add = L.append

    add('"""')
    add("site_config.py — DRAFT generated by config_bootstrapper.py")
    add("")
    add("CONFIDENCE TIERS (read before trusting anything):")
    add("  [VERIFIED]    selector resolved to exactly ONE live element.")
    add("  [PROPOSED]    a likely candidate; VERIFY before relying on it.")
    add("  [NEEDS_HUMAN] could not resolve; you must supply this.")
    add("")
    add("The bootstrapper does NOT invent intent semantics: `match` phrases,")
    add("`strict` flags, fallback ladders, and data_keys are TODO stubs.")
    add('"""')
    add("")
    add("SITE_CONFIG = {")
    add(f'    "base_url": "{base_url.rstrip("/")}",')
    add("")

    # Navigation paths (verified by successful navigation).
    add("    # ── Navigation paths ──────────────────────────────")
    add('    "navigation_paths": {')
    for p in pages:
        add(f'        "{p.name}": "{p.path}",  # [VERIFIED] loaded -> {p.final_url}')
    add("    },")
    add("")

    # Page ready signals.
    add("    # ── Page ready signals ────────────────────────────")
    add('    "page_ready_signals": {')
    for p in pages:
        if p.ready_signal:
            by, val = p.ready_signal
            add(f'        "{p.name}": ("{by}", "{val}"),  # [VERIFIED]')
        else:
            add(f'        # "{p.name}": (?, ?),  # [NEEDS_HUMAN] no stable signal found')
    add("    },")
    add("")

    # Proposed verify keywords (never asserted).
    add("    # ── Verify keywords (ALL [PROPOSED] — curate by hand) ──")
    add('    "verify_keywords": {')
    for p in pages:
        if p.visible_text_sample:
            kws = ", ".join(f'"{k}"' for k in p.visible_text_sample[:6])
            add(f'        # [PROPOSED] for "{p.name} loaded": [{kws}]')
    add("    },")
    add("")

    # Intent actions.
    add("    # ── Intent actions ────────────────────────────────")
    add('    "intent_actions": {')

    # Simple-locator intents (the existing path).
    for intent, cands in intent_results.items():
        add(f'        "{intent}": {{')
        add(f'            "type": "click_strategies",  '
            f'# [NEEDS_HUMAN] confirm type for this intent')
        add(f'            "match": [],  '
            f'# [NEEDS_HUMAN] add the plain-English phrases users will write')
        add(f'            "strategies": [')
        if not cands:
            add(f'                # [NEEDS_HUMAN] no candidates found at all')
        for c in cands:
            tag = f"[{c.tier}]"
            extra = f"matched {c.match_count}" if c.match_count else c.note
            add(f'                {c.as_strategy_tuple()},  '
                f'# {tag} via {c.source}; {extra}')
        add(f'            ],')
        add(f'        }},')

    # Filter-compare intents (new path — written from the discovered pattern).
    if filter_pattern is not None:
        _emit_filter_compare_intents(add, filter_pattern)

    add("    },")
    add("}")
    add("")
    return "\n".join(L)


def _emit_filter_compare_intents(add, fp: FilterPattern):
    """
    Emit the four standard filter_compare intents using the discovered
    pattern. Each one differs only by `operator` (min/max/lt/gt).
    """
    intents_spec = [
        ("select_cheapest_product", "min",
         ["cheapest product", "select the cheapest", "lowest price"]),
        ("select_most_expensive_product", "max",
         ["most expensive product", "select the most expensive",
          "highest price"]),
        ("select_product_under_price", "lt",
         ["product with price less than", "product under",
          "price less than"]),
        ("select_product_over_price", "gt",
         ["product with price more than", "product above",
          "price more than"]),
    ]
    cx = fp.container_xpath.replace('"', '\\"')
    vx = fp.value_xpath.replace('"', '\\"')
    lx = fp.link_xpath.replace('"', '\\"')
    tag = f"[{fp.tier}]"
    note = fp.note
    for name, op, matches in intents_spec:
        add(f'        "{name}": {{')
        add(f'            "type": "filter_compare",')
        add(f'            "strict": True,  '
            f'# [NEEDS_HUMAN] confirm — strict prevents silent wrong heals')
        match_lits = ", ".join(f'"{m}"' for m in matches)
        add(f'            "match": [{match_lits}],  '
            f'# [NEEDS_HUMAN] tweak the phrases your tests use')
        add(f'            "container_xpath": "{cx}",  # {tag} {note}')
        add(f'            "value_xpath": "{vx}",      # {tag} value path')
        add(f'            "link_xpath": "{lx}",       # {tag} link path')
        add(f'            "extract_pattern": r"{fp.extract_pattern}",')
        add(f'            "operator": "{op}",')
        add(f'            "wait_for_url_fragment": "/product",  '
            f'# [NEEDS_HUMAN] adjust if your site uses a different fragment')
        add(f'        }},')


# ──────────────────────────────────────────────────────────────────
# Summary report to stdout
# ──────────────────────────────────────────────────────────────────
def print_summary(intent_results: dict[str, list[LocatorCandidate]],
                  filter_pattern: FilterPattern | None = None,
                  role_gated_skips: int = 0):
    print("\n" + "=" * 60)
    print("BOOTSTRAP SUMMARY")
    print("=" * 60)
    tot = {VERIFIED: 0, PROPOSED: 0, NEEDS_HUMAN: 0}
    for intent, cands in intent_results.items():
        best = cands[0].tier if cands else NEEDS_HUMAN
        tot[best] = tot.get(best, 0) + 1
        flag = {"VERIFIED": "✅", "PROPOSED": "⚠️ ", "NEEDS_HUMAN": "❌"}[best]
        print(f"  {flag} {intent:28s} best tier: {best}")

    # Filter pattern row, if it was discovered.
    if filter_pattern is not None:
        flag = {VERIFIED: "✅", PROPOSED: "⚠️ ",
                NEEDS_HUMAN: "❌"}[filter_pattern.tier]
        tot[filter_pattern.tier] = tot.get(filter_pattern.tier, 0) + 1
        print(f"  {flag} {'filter_compare (pattern)':28s} "
              f"best tier: {filter_pattern.tier}  "
              f"({filter_pattern.container_match_count} items, "
              f"v={filter_pattern.value_hit_ratio:.0%}, "
              f"l={filter_pattern.link_hit_ratio:.0%})")

    print("-" * 60)
    print(f"  ✅ verified: {tot[VERIFIED]}   "
          f"⚠️  proposed: {tot[PROPOSED]}   "
          f"❌ needs human: {tot[NEEDS_HUMAN]}")
    if role_gated_skips > 0:
        print(f"  🛡  role-gated skips: {role_gated_skips} "
              f"(prevented semantically-wrong proposals)")
    print("=" * 60)
    print("Reminder: only [VERIFIED] locators resolved to exactly one element.")
    print("Role-gating prevents the LLM from 'verifying' a wrong element on")
    print("a page where the intent is not semantically applicable.")
    print("Everything else is for you to confirm — nothing is silently trusted.\n")


# ──────────────────────────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────────────────────────
def parse_pages(items: list[str]) -> list[tuple[str, str, str]]:
    """
    Parse --pages entries.

    Accepts two forms:
      "name:/path"               -> role defaults to "unknown" (permissive)
      "name:/path:role=ROLE"     -> role tag enforces gating

    Valid roles: home, listing, detail, cart, login, checkout, unknown
    """
    VALID_ROLES = {"home", "listing", "detail", "cart", "login",
                   "checkout", "unknown"}
    out = []
    for it in items:
        if ":" not in it:
            raise SystemExit(
                f"--pages entry '{it}' must be name:/path "
                f"or name:/path:role=ROLE")
        # Extract optional role=X tail.
        role = "unknown"
        body = it
        # role= must appear after a colon (since paths can contain colons
        # only via the leading slash, which we don't allow ':' inside).
        if ":role=" in it:
            body, _, role_part = it.rpartition(":role=")
            role = role_part.strip().lower()
            if role not in VALID_ROLES:
                raise SystemExit(
                    f"--pages entry '{it}': role '{role}' is not one of "
                    f"{sorted(VALID_ROLES)}")
        name, path = body.split(":", 1)
        out.append((name, path, role))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Generate a verified draft site_config.py for a website.")
    ap.add_argument("--base-url", required=True)
    ap.add_argument("--pages", nargs="+", required=True,
                    help="space-separated entries 'name:/path[:role=ROLE]'. "
                         "Roles: home, listing, detail, cart, login, "
                         "checkout. Role-gating prevents the LLM from "
                         "'verifying' wrong elements on pages where an "
                         "intent doesn't semantically belong. Omit the "
                         "role for permissive (legacy) behaviour. "
                         "Example: homepage:/:role=home "
                         "products:/products:role=listing")
    ap.add_argument("--intents", default=",".join(INTENT_DESCRIPTIONS.keys()),
                    help="comma-separated intents to resolve")
    ap.add_argument("--out", default="site_config_DRAFT.py")
    ap.add_argument("--model", default="gpt-4o-mini")
    ap.add_argument("--no-llm", action="store_true",
                    help="heuristics + DOM verification only (no API cost)")
    ap.add_argument("--settle", type=float, default=2.0,
                    help="seconds to wait after each page load")
    args = ap.parse_args(argv)

    use_llm = not args.no_llm
    pages_in = parse_pages(args.pages)
    intents = [i.strip() for i in args.intents.split(",") if i.strip()]

    driver = get_driver()
    pages: list[PageResult] = []
    intent_results: dict[str, list[LocatorCandidate]] = {}
    filter_pattern: FilterPattern | None = None

    def _ensure_driver(d):
        """Recreate the driver if the session has died."""
        if _session_alive(d):
            return d
        print("[driver] session lost — relaunching browser …")
        try:
            d.quit()
        except Exception:
            pass
        return get_driver()

    # Split out filter_compare since it uses a different pipeline.
    want_filter_compare = "filter_compare" in intents
    locator_intents = [i for i in intents if i != "filter_compare"]

    # Track role-gating stats so we can report them at the end. This
    # is the "how many semantically-wrong proposals were prevented"
    # number for the dissertation.
    role_gated_skips = 0

    try:
        # Crawl pages first (for navigation + ready signals + keyword seeds).
        for name, path, _role in pages_in:
            driver = _ensure_driver(driver)
            pages.append(crawl_page(driver, args.base_url, name, path,
                                    settle=args.settle))

        # Resolve simple-locator intents on each page; keep best tier per intent.
        best_per_intent: dict[str, list[LocatorCandidate]] = {
            i: [] for i in locator_intents}
        rank = {VERIFIED: 0, PROPOSED: 1, NEEDS_HUMAN: 2}
        for name, path, role in pages_in:
            driver = _ensure_driver(driver)
            url = args.base_url.rstrip("/") + "/" + path.lstrip("/")
            print(f"\n[resolve] page '{name}' (role={role}) ({url})")
            try:
                driver.get(url)
                time.sleep(args.settle)
            except Exception as e:
                print(f"[resolve] could not load {url} ({e}); skipping page.")
                continue
            for idx, intent in enumerate(locator_intents, 1):
                # ── Role gate ────────────────────────────────────
                if not _intent_allowed_on(intent, role):
                    print(f"[resolve] ({idx}/{len(locator_intents)}) "
                          f"{intent}: SKIPPED (intent not valid on "
                          f"role='{role}' pages)")
                    role_gated_skips += 1
                    continue
                print(f"[resolve] ({idx}/{len(locator_intents)}) {intent}",
                      flush=True)
                try:
                    cands = resolve_intent(driver, intent, use_llm, args.model)
                except Exception as e:
                    print(f"[resolve] {intent}: error ({e}); skipping.")
                    continue
                prev = best_per_intent[intent]
                prev_best = prev[0].tier if prev else NEEDS_HUMAN
                new_best = cands[0].tier if cands else NEEDS_HUMAN
                if rank[new_best] < rank[prev_best]:
                    best_per_intent[intent] = cands

            # ── Filter pattern discovery on this page ─────────────
            if want_filter_compare:
                if not _intent_allowed_on("filter_compare", role):
                    print(f"[filter ] SKIPPED on '{name}': filter_compare "
                          f"not valid on role='{role}' pages")
                    role_gated_skips += 1
                else:
                    print(f"[filter ] discovering listing pattern on "
                          f"'{name}' …", flush=True)
                    try:
                        fp = discover_filter_pattern(driver)
                        print(f"[filter ] result: tier={fp.tier} | {fp.note}")
                        # Keep best filter_pattern across pages.
                        if filter_pattern is None:
                            filter_pattern = fp
                        else:
                            if rank[fp.tier] < rank[filter_pattern.tier]:
                                filter_pattern = fp
                    except Exception as e:
                        print(f"[filter ] discovery error: {e}; skipping.")

        intent_results = best_per_intent

    finally:
        try:
            driver.quit()
        except Exception:
            pass

    draft = emit_config(args.base_url, pages, intent_results,
                        filter_pattern=filter_pattern)
    with open(args.out, "w", encoding="utf-8") as f:
        f.write(draft)

    print_summary(intent_results, filter_pattern=filter_pattern,
                  role_gated_skips=role_gated_skips)
    print(f"[done] Draft written to: {args.out}")
    print("       Edit the [PROPOSED]/[NEEDS_HUMAN] entries, then rename to "
          "site_config.py when satisfied.")


if __name__ == "__main__":
    main()