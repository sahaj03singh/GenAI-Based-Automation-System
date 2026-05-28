# ══════════════════════════════════════════════════════════════════════
# HOW TO ADAPT THIS FILE FOR A NEW WEBSITE  —  READ BEFORE EDITING
# ══════════════════════════════════════════════════════════════════════
#
# This file is the ONLY file you change to target a new site. The engine
# code (actions.py, test_executor.py, test_generator.py) and base_config.py
# stay exactly as they are.
#
# RECOMMENDED WORKFLOW:
#   1. Run the bootstrapper against the new site to auto-discover and
#      DOM-verify most of the locators below:
#
#        python -m utils.config_bootstrapper \
#            --base-url https://YOUR-SITE.com \
#            --pages homepage:/:role=home \
#                    products:/PATH:role=listing \
#                    product:/PATH:role=detail \
#                    cart:/PATH:role=cart \
#                    login:/PATH:role=login \
#            --intents search_input,search_submit,view_product,add_to_basket,view_basket,product_detail_add_to_cart,category_link,brand_link,filter_compare \
#            --out site_config_DRAFT.py
#
#   2. Copy the verified locators from the draft into this file.
#   3. Hand-edit the items listed under "MUST UPDATE" below.
#   4. Verify the merge:  python -c "from configPage.site_config import SITE_CONFIG; print(SITE_CONFIG['base_url'])"
#
# ──────────────────────────────────────────────────────────────────────
# MUST UPDATE for a new site (the bootstrapper CANNOT fill these in):
# ──────────────────────────────────────────────────────────────────────
#
#   [A] base_url            -> the new site's root URL.
#
#   [B] navigation_paths    -> the URL path for each named page. Keep the
#                              KEYS (homepage/products/product/cart/login)
#                              the engine looks these up by name; change
#                              only the PATHS.
#
#   [C] page_ready_signals  -> one stable element per page that proves the
#                              page has loaded (an id or unique css). The
#                              bootstrapper marks these NEEDS_HUMAN — you
#                              must supply them by inspecting each page.
#
#   [D] page_url_fragments  -> a URL substring that identifies each page
#                              type (used by verify steps).
#
#   [E] verify_keywords     -> for each named state, 3-6 short phrases that
#                              appear ONLY on that page (used to confirm a
#                              step landed correctly). Pick phrases unique
#                              to each page, not generic nav text.
#
#   [F] intent_actions[*]["match"]
#                           -> the plain-English phrases your test cases
#                              use for each action (e.g. "add to cart").
#                              The bootstrapper leaves these blank — they
#                              are YOUR test vocabulary, not discoverable
#                              from the DOM.
#
#   [G] intent_actions[*]["type"]
#                           -> the action kind. Common values:
#                                "form_field"        -> type text into a field
#                                "click_strategies"  -> click one element
#                                "click_first_match" -> click the first of many
#                                "filter_compare"    -> pick by price/value
#                              The bootstrapper defaults everything to
#                              "click_strategies" — fix any that differ.
#
#   [H] filter_compare intents -> after pasting the bootstrap-discovered
#                              container/value/link XPaths, set:
#                                "wait_for_url_fragment" -> the real product
#                                   detail URL substring (bootstrapper
#                                   defaults to "/product" — usually too loose)
#                                "operator" -> min / max / lt / gt
#                                "extract_pattern" -> regex for the number
#                                   inside the value text (default r"\d+")
#
#   [I] data_key / field_hints / field_type  (form_field intents only)
#                           -> data_key links the field to a value in
#                              test_data.py (e.g. "search"). field_hints are
#                              id/name substrings to locate the field.
#
# ──────────────────────────────────────────────────────────────────────
# CHECK CAREFULLY (bootstrapper may produce these, but they can be WRONG):
# ──────────────────────────────────────────────────────────────────────
#
#   * A locator tagged [VERIFIED] means it resolved to exactly ONE live
#     element — NOT that it is the RIGHT element. The bootstrapper has been
#     observed to verify semantically-wrong elements that happen to be
#     unique on a valid page (e.g. a newsletter "subscribe" button getting
#     proposed for the search-submit action). ALWAYS eyeball each
#     [VERIFIED] locator and discard ones pointing at the wrong thing.
#
#   * "add to cart" usually needs selectors for BOTH the product-listing
#     page AND the product-detail page, because a test may add from either.
#     List detail-page selectors first, then listing-page ones.
#
#   * Elements that only appear AFTER an action (e.g. a "View Cart" modal
#     that pops up after adding to cart) will NOT be found by the
#     bootstrapper's static crawl. Add those selectors by hand.
#
# ──────────────────────────────────────────────────────────────────────
# DO NOT NEED TO CHANGE:
# ──────────────────────────────────────────────────────────────────────
#   * The "strict": True flags (they make wrong matches fail honestly
#     instead of silently clicking the wrong element — keep them).
#   * The build_site_config(...) call at the bottom.
#   * Anything in base_config.py.
# ══════════════════════════════════════════════════════════════════════

from configPage.base_config import build_site_config


SITE_OVERRIDES = {

    # [BOOTSTRAP-VERIFIED] page loaded during the bootstrap run
    "base_url": "https://www.automationexercise.com",

    # ── Navigation paths ──────────────────────────────────────────
    # [BOOTSTRAP-VERIFIED] all five URLs loaded successfully.
    # [MANUAL] added 'home'/'basket' aliases (engine looks these keys
    #         up; they need not appear in the bootstrap --pages list).
    "navigation_paths": {
        "homepage": "/",
        "home":     "/",
        "products": "/products",
        "product":  "/product_details/1",
        "login":    "/login",
        "cart":     "/view_cart",
        "basket":   "/view_cart",
    },

    # ── Page ready signals ────────────────────────────────────────
    # [MANUAL] The bootstrapper's ready-signal heuristic found no
    # stable single-element signal and correctly marked all five
    # NEEDS_HUMAN. These are the actual stable elements per page.
    "page_ready_signals": {
        "homepage": ("id",  "search_product"),
        "home":     ("id",  "search_product"),
        "products": ("css", ".features_items"),
        "product":  ("id",  "search_product"),
        "login":    ("css", "input[data-qa='login-email']"),
        "cart":     ("id",  "cart_info"),
        "basket":   ("id",  "cart_info"),
    },

    # ── URL fragments for page detection in verify ────────────────
    # [MANUAL] URL substrings, not DOM locators — site knowledge.
    "page_url_fragments": {
        "products":       "/products",
        "product_detail": "/product_details/",
        "cart":           "/view_cart",
        "basket":         "/view_cart",
        "login":          "/login",
        "home":           "automationexercise.com",
    },

    # ── Verify keywords ───────────────────────────────────────────
    # [MANUAL] The bootstrapper's visible-text sampler returned the
    # same generic nav phrases ("home", "products", "cart") for every
    # page, which cannot distinguish states. These are the actual
    # unique phrases that identify each page.
    "verify_keywords": {
        "homepage loaded": [
            "automationexercise", "full-fledged practice website",
            "features items", "cart", "signup / login",
        ],
        "home page": [
            "automationexercise", "features items", "cart",
        ],
        "products loaded": [
            "all products", "search product", "features items",
        ],
        "products page": [
            "all products", "search product", "features items",
        ],
        "search results": [
            "searched products", "search product",
        ],
        "search results visible": [
            "searched products", "search product",
        ],
        "product detail page": [
            "category:", "availability:", "condition:", "brand:",
            "write your review", "quantity",
        ],
        "category page": [
            "category", "features items", "search product",
        ],
        "brand page": [
            "brand", "features items", "search product",
        ],
        "added to cart": [
            "added!", "your product has been added to cart",
            "view cart", "continue shopping",
        ],
        "added to basket": [
            "added!", "your product has been added to cart",
            "view cart", "continue shopping",
        ],
        "cart contains item": [
            "shopping cart", "cart_info", "total",
            "proceed to checkout",
        ],
        "logged in": [
            "logged in as", "logout", "delete account",
        ],
    },

    # ──────────────────────────────────────────────────────────────
    # INTENT ACTIONS
    # ──────────────────────────────────────────────────────────────
    "intent_actions": {

        # ── Search box ────────────────────────────────────────────
        "search_input": {
            "type": "form_field",          # [MANUAL] intent type
            "match": [                      # [MANUAL] intent semantics
                "search bar", "search box", "search field",
                "search input", "search for", "type in search bar",
            ],
            # [BOOTSTRAP-VERIFIED] id=search_product and name=search
            # both matched 1 element on home + listing pages.
            "field_hints": ["search_product", "search"],
            "field_type": "text",
            "data_key": "search",
        },

        # ── Search submit ─────────────────────────────────────────
        "search_submit": {
            "type": "click_strategies",
            "match": [
                "search button", "search submit",
                "click search", "go button",
            ],
            "strategies": [
                # [BOOTSTRAP-VERIFIED] LLM scoped this to the search
                # form specifically (matched 1) — the cleanest choice.
                ("css", "form.searchform button[type='submit']"),
                # [BOOTSTRAP-VERIFIED] heuristic generic submit (1).
                ("css", "button[type='submit']"),
                # [BOOTSTRAP-DISCARDED] the bootstrapper also VERIFIED
                #   ("id", "subscribe")
                # which resolves to exactly one element — but it is the
                # NEWSLETTER subscribe button, not the search submit.
                # This is the *same-page* semantic-confusion class that
                # role-gating cannot fix (both buttons live on the
                # homepage, a valid role for search_submit). Discarded
                # by human review. Documented as a dissertation finding.
            ],
            "wait_for_url_fragment": "/products",
        },

        # ── Open a product (listing -> detail) ────────────────────
        "view_product": {
            "type": "click_first_match",   # [MANUAL] intent type
            "match": [
                "view product", "click product", "select product",
                "first product", "first result",
            ],
            "pre_wait": 1,
            "scroll_before_click": True,
            "strategies": [
                # [BOOTSTRAP-VERIFIED] heuristic, matched 1.
                ("css", "a[href*='/product_details/']"),
                ("css", "a[href*='/product']"),
                # [BOOTSTRAP-DISCARDED] the LLM also proposed an XPath
                # keyed on inline style (contains(@style,'color: brown'))
                # which matched 34 — brittle presentational selector,
                # discarded in favour of the stable href selectors.
            ],
            "wait_for_url_fragment": "/product_details/",
        },

        # ── Add to cart [BOOTSTRAP-MERGED] ────────────────────────
        # Combines two role-separated bootstrap intents:
        #   product_detail_add_to_cart (role=detail) — the single
        #     <button> in the buy box on a product detail page; and
        #   add_to_basket (role=listing) — the per-card add-to-cart
        #     links on a product listing page.
        # Tests just say "add to cart"; the engine tries detail-page
        # selectors first, then listing-page ones.
        "add_to_basket": {
            "type": "click_strategies",
            "strict": True,                # [MANUAL] honest fail-fast
            "match": [
                "add to cart", "add to basket", "add this to cart",
            ],
            "pre_wait": 1,
            "scroll_before_click": True,
            "wait_after": 2,
            "strategies": [
                # ── Product DETAIL page ───────────────────────────
                # [BOOTSTRAP-VERIFIED] all four matched 1 on the
                # /product_details/1 page (role=detail). These are the
                # correct buy-box button.
                ("css", "button.cart"),
                ("css", "button.btn.cart"),
                ("css", "button[type='button'].btn.cart"),
                ("xpath", "//button[contains(@class,'cart') and "
                          "(contains(.,'Add to cart') or "
                          "contains(.,'Add to Cart'))]"),
                # [BOOTSTRAP-DISCARDED] on the detail page the
                # bootstrapper also VERIFIED ("id","button-review") and
                # a 'close-modal' button — both resolve to one element
                # but are the wrong buttons (review / modal-close).
                # Same-page semantic confusion; discarded by review.
                #
                # ── Product LISTING page ──────────────────────────
                # [BOOTSTRAP-VERIFIED] (PROPOSED tier in the draft
                # because there are many per-card buttons — which is
                # correct for a listing). The engine clicks the first
                # match. These are the listing add-to-cart links.
                ("css", "a.add-to-cart"),
                ("xpath", "//a[contains(@class,'add-to-cart')]"),
            ],
            "after": "increment_count",
            "count_key": "cart_count",
        },

        # ── View cart ─────────────────────────────────────────────
        "view_basket": {
            "type": "click_strategies",
            "match": [
                "view cart", "view basket", "go to cart",
                "go to basket", "see cart", "open cart",
                "view cart modal",
            ],
            "strategies": [
                # [BOOTSTRAP-VERIFIED] both matched 1.
                ("css", "a[href='/view_cart']"),
                ("xpath", "//a[@href='/view_cart']"),
                # [MANUAL] post-add modal's "View Cart" link sits inside
                # <u> tags; the bootstrapper never sees this because the
                # modal only appears after an add-to-cart action, which
                # a static crawl does not trigger.
                ("xpath", "//u[text()='View Cart']/parent::a"),
            ],
            "wait_for_url_fragment": "/view_cart",
        },

        # ── Category navigation ───────────────────────────────────
        # [BOOTSTRAP-VERIFIED] on home + listing pages.
        "category_link": {
            "type": "click_first_match",   # [MANUAL] intent type
            "match": [
                "category", "women category", "men category",
                "kids category", "category link",
            ],
            "pre_wait": 1,
            "scroll_before_click": True,
            "strategies": [
                ("css", ".category-products a"),
                ("css", "#accordian a"),
                ("css", "a[href*='/category_products/']"),
            ],
        },

        # ── Brand navigation ──────────────────────────────────────
        # [BOOTSTRAP-VERIFIED] on home + listing pages.
        "brand_link": {
            "type": "click_first_match",   # [MANUAL] intent type
            "match": [
                "brand", "polo brand", "madame brand", "brand link",
            ],
            "pre_wait": 1,
            "scroll_before_click": True,
            "strategies": [
                ("css", "a[href*='/brand_products/']"),
                ("css", ".brands_products a"),
                ("css", ".brands-name a"),
            ],
        },

        # ── Filter-compare intents [BOOTSTRAP-VERIFIED pattern] ───
        # The repeating-grid pattern was discovered on the listing
        # page (role=listing): container matched 34 items, value+link
        # resolved in 100% of them.
        # [MANUAL] wait_for_url_fragment tightened from the
        # bootstrapper default "/product" to "/product_details/"
        # (the bootstrapper marks this NEEDS_HUMAN by design — it
        # cannot infer the exact URL pattern from page structure).

        "select_cheapest_product": {
            "type": "filter_compare",
            "strict": True,
            "match": [
                "cheapest product", "select the cheapest",
                "select cheapest", "lowest price product",
                "lowest price",
            ],
            "container_xpath": "//div[contains(@class,"
                               "'product-image-wrapper')]",
            "value_xpath": ".//h2[contains(text(),'Rs.')]",
            "link_xpath": ".//a[contains(@href,'/product_details/')]",
            "extract_pattern": r"\d+",
            "operator": "min",
            "wait_for_url_fragment": "/product_details/",
        },

        "select_most_expensive_product": {
            "type": "filter_compare",
            "strict": True,
            "match": [
                "most expensive product", "select the most expensive",
                "highest price product", "highest priced",
                "most expensive",
            ],
            "container_xpath": "//div[contains(@class,"
                               "'product-image-wrapper')]",
            "value_xpath": ".//h2[contains(text(),'Rs.')]",
            "link_xpath": ".//a[contains(@href,'/product_details/')]",
            "extract_pattern": r"\d+",
            "operator": "max",
            "wait_for_url_fragment": "/product_details/",
        },

        "select_product_under_price": {
            "type": "filter_compare",
            "strict": True,
            "match": [
                "product with price less than", "product under",
                "price less than", "under budget", "less than",
            ],
            "container_xpath": "//div[contains(@class,"
                               "'product-image-wrapper')]",
            "value_xpath": ".//h2[contains(text(),'Rs.')]",
            "link_xpath": ".//a[contains(@href,'/product_details/')]",
            "extract_pattern": r"\d+",
            "operator": "lt",
            "wait_for_url_fragment": "/product_details/",
        },

        "select_product_over_price": {
            "type": "filter_compare",
            "strict": True,
            "match": [
                "product with price more than", "product above",
                "price more than", "above threshold", "more than",
            ],
            "container_xpath": "//div[contains(@class,"
                               "'product-image-wrapper')]",
            "value_xpath": ".//h2[contains(text(),'Rs.')]",
            "link_xpath": ".//a[contains(@href,'/product_details/')]",
            "extract_pattern": r"\d+",
            "operator": "gt",
            "wait_for_url_fragment": "/product_details/",
        },
    },
}


# Merge the site layer onto the static base contract.
# SITE_CONFIG is what the rest of the framework imports.
SITE_CONFIG = build_site_config(SITE_OVERRIDES)