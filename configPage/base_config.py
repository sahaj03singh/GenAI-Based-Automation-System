

from copy import deepcopy


BASE_CONFIG = {

   
    "base_url": "",                 # e.g. "https://www.automationexercise.com"
    "navigation_paths": {           # at minimum a home/homepage entry
        "home": "/",
        "homepage": "/",
    },

    # ── Navigation / page-detection (generic defaults)
    # These describe HOW the engine reasons about pages. Values are
    # site-specific, but the engine tolerates them being empty.
    "page_ready_signals": {},       # {page_key: ("by", "value")}
    "page_url_fragments": {},       # {page_key: "/url-fragment"}
    "pre_navigate_for": {},         # {nav_key: ["trigger substrings"]}

    # ── Generic UI vocabulary 
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

    # ── Session-flag logic (generic, reusable) 
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

    # ── Verification (site-specific values, safe-empty here) 
    "verify_keywords": {},          # {verify_key: ["text", "fragments"]}
    "waitable_verifications": [     # generic, reasonable default set
        "logged in", "order confirmed",
        "added to cart", "added to basket",
        "search results", "search results visible",
    ],
    "count_verifications": {},      # {verify_key: {session_var, operator, value}}

    # ── Modal / sidebar handling (off by default)
    "modal_buttons": {},            
    "sidebar": {},                  # {label: ("by", "val")}

   # ── The site's actual actions 
    "intent_actions": {},           # {intent_key: {...intent config...}}

    # ── Generic flow templates (used by llm/test_generator.py) ───
    # These describe the SHAPE of common multi-step flows so the
    # step generator can synthesise them when a user story implies
    # one (e.g. when login is referenced). Safe-empty here so a
    # non-e-commerce site simply omits them and nothing breaks.
    #
    # login_flow: list of step dicts to prepend when a test case
    # references login. Each step is {action, target, value}.
    # Empty list = no login flow synthesis.
    "login_flow": [],

    # checkout_flow: list of step descriptors used when a test
    # references checkout / payment / place-order. Each entry is
    # {action, target_keywords} — the generator finds the matching
    # intent in intent_actions and uses its first match phrase as
    # the target. Empty list = no checkout flow synthesis.
    "checkout_flow": [],

    # ── Domain-specific value extraction (generic mechanism) ─────
    # When a step's target matches one of the patterns below, the
    # corresponding regex is run against the step text to extract
    # a value. Lets e-commerce sites pull sizes/colours/prices, and
    # other domains define their own (dates, codes, etc.).
    # Empty dict = numeric extraction only (built-in fallback).
    "value_patterns": {},

    # ── Misc (read in a couple of places, safe-empty) 
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