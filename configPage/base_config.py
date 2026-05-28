"""
base_config.py — STATIC engine contract layer.

Place this file at: configPage/base_config.py

PURPOSE
-------
This file defines the FULL set of keys the framework engine reads, with
safe defaults for every one. It is the "contract" between the engine and
any site config. It is written ONCE, by hand, and never regenerated.

A per-site config (hand-written OR produced by config_bootstrapper.py)
is merged ON TOP of this base via `build_site_config()` below. Because
this base supplies every key the engine touches, a site config can omit
anything it doesn't need and the engine will never crash on a missing key.

WHICH KEYS MATTER
-----------------
The engine hard-accesses only two keys (crash if missing):
    base_url            -> the site root
    navigation_paths    -> at least {"home": "/"} or similar

Everything else is read with .get(<default>), so this base defines
sensible empty defaults. A site only needs to override what it uses.

These defaults are GENERIC and site-agnostic — the same for any website.
Site-specific values live in the per-site layer, not here.
"""

from copy import deepcopy


# ──────────────────────────────────────────────────────────────────
#  THE STATIC CONTRACT — every key the engine reads, safe-defaulted.
# ──────────────────────────────────────────────────────────────────
BASE_CONFIG = {

    # ── HARD-REQUIRED (must be overridden by every site) ──────────
    # Left as placeholders so a forgotten override is obvious, not silent.
    "base_url": "",                 # e.g. "https://www.automationexercise.com"
    "navigation_paths": {           # at minimum a home/homepage entry
        "home": "/",
        "homepage": "/",
    },

    # ── Navigation / page-detection (generic defaults) ────────────
    # These describe HOW the engine reasons about pages. Values are
    # site-specific, but the engine tolerates them being empty.
    "page_ready_signals": {},       # {page_key: ("by", "value")}
    "page_url_fragments": {},       # {page_key: "/url-fragment"}
    "pre_navigate_for": {},         # {nav_key: ["trigger substrings"]}

    # ── Generic UI vocabulary ─────────────────────────────────────
    # Used by _is_navigation_intent to tell "go to cart" (navigation)
    # apart from "click add to cart" (a UI action). These verbs are
    # genuinely generic across e-commerce sites, so they live here.
    "ui_action_keywords": [
        "button", "click", "type", "select", "submit",
        "search", "filter", "sort",
        "add to cart", "add to basket", "buy now", "buy",
        "proceed", "checkout", "place order", "pay",
        "sign in", "sign out", "log in", "log out", "login", "logout",
        "view product", "first product", "first result",
        "view cart", "view basket", "go to cart", "go to basket",
        "rating", "price", "quantity", "size", "colour", "color",
    ],

    # ── Session-flag logic (generic, reusable) ────────────────────
    # The MEANING ("logging in makes you logged in") is universal.
    # The page keys referenced should exist in navigation_paths.
    "navigation_session_flags": {
        "logged_in":        ["home", "homepage"],
        "on_products_page": ["products"],
    },
    "navigation_reset_flags": {
        "logged_in":        ["login", "logout"],
        "on_products_page": [],
    },

    # ── Verification (site-specific values, safe-empty here) ───────
    "verify_keywords": {},          # {verify_key: ["text", "fragments"]}
    "waitable_verifications": [     # generic, reasonable default set
        "logged in", "order confirmed",
        "added to cart", "added to basket",
        "search results", "search results visible",
    ],
    "count_verifications": {},      # {verify_key: {session_var, operator, value}}

    # ── Modal / sidebar handling (off by default) ─────────────────
    "modal_buttons": {},            # {choice: ("by","val"), "modal_locator": (...)}
    "sidebar": {},                  # {label: ("by", "val")}

    # ── The site's actual actions — filled per site ───────────────
    "intent_actions": {},           # {intent_key: {...intent config...}}

    # ── Misc (read in a couple of places, safe-empty) ─────────────
    "order_success_keywords": [
        "order placed", "order confirmed", "thank you",
        "your order has been placed",
    ],
    "product_detail_url_fragment": "",
}


# ──────────────────────────────────────────────────────────────────
#  PER-INTENT KEY REFERENCE (documentation only — not enforced)
# ──────────────────────────────────────────────────────────────────
# Every per-intent key the engine reads is accessed via .get(), so an
# intent only needs the keys its `type` uses. Reference, by type:
#
#   ALL intents:        type, match
#   form_field:         field_hints, field_type, data_key, pre_navigate
#   select_option:      select_id, option_text, option_value,
#                       fallback_strategies, wait_for_url_fragment
#   click_strategies:   strategies, pre_wait, scroll_before_click,
#                       clear_modals, js_fallback, checkout_fallback,
#                       wait_after, after, count_key, wait_for_url_change,
#                       wait_for_url_fragment
#   click_first_match:  strategies, pre_wait, scroll_before_click,
#                       wait_for_url_fragment
#   filter_compare:     container_xpath, value_xpath, link_xpath,
#                       extract_pattern, operator, threshold,
#                       wait_for_url_fragment
#   click_option_with_value: option_xpaths, value_aliases, default_value,
#                       extract_pattern
#   modal_dismiss:      choice, fallback_strategies
#   listing_item_action: detail_page_url_fragment, detail_page_strategies,
#                       item_wrapper, item_action_strategies, count_key
#   js_scroll:          scroll_action, wait_after
#   custom_js:          script
# ──────────────────────────────────────────────────────────────────


# ──────────────────────────────────────────────────────────────────
#  MERGE — base layer + per-site overrides
# ──────────────────────────────────────────────────────────────────
def _deep_merge(base: dict, override: dict) -> dict:
    """
    Recursively merge `override` onto a copy of `base`.
    - dicts merge key-by-key
    - everything else (lists, strings, tuples) is replaced wholesale
      by the override (so a site fully controls e.g. its own
      ui_action_keywords list if it chooses to override it)
    """
    out = deepcopy(base)
    for k, v in override.items():
        if k in out and isinstance(out[k], dict) and isinstance(v, dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = deepcopy(v)
    return out


def build_site_config(site_overrides: dict) -> dict:
    """
    Produce a complete, engine-ready config by layering a site's
    overrides on top of the static base contract.

    Guarantees:
    - Every key the engine reads exists (no missing-key crash).
    - Site values win where provided.
    - base_url / navigation_paths are validated as non-empty so a
      forgotten override fails LOUDLY here, not mysteriously later.

    Usage (in a per-site file, e.g. site_config_automationexercise.py):

        from configPage.base_config import build_site_config
        SITE_CONFIG = build_site_config(SITE_OVERRIDES)
    """
    merged = _deep_merge(BASE_CONFIG, site_overrides)

    # Fail loudly on the two hard-required keys.
    if not merged.get("base_url"):
        raise ValueError(
            "[base_config] 'base_url' is empty — every site MUST set it."
        )
    if not merged.get("navigation_paths"):
        raise ValueError(
            "[base_config] 'navigation_paths' is empty — set at least "
            "{'home': '/'}."
        )
    return merged