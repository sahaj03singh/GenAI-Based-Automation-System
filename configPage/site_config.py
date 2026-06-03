"""
site_config.py — automationexercise.com (PRODUCTION)

Generated from site_config_DRAFT.py (108 markers, addressed below).
Drop in at: configPage/site_config.py

MARKER-BY-MARKER RESOLUTION
───────────────────────────
🗑️ DELETE   16 lines — all cookie-consent (fc-*); removed entirely
⚠️ CHECK   10 lines — flagged wrong picks, documented as DISCARDED below
👉 FIX     ~82 lines — each addressed inline with [MANUAL] explanations

PROVENANCE TAGS
───────────────
[BOOTSTRAP-VERIFIED]   the draft marked this ✅ — promoted as-is
[BOOTSTRAP-DISCARDED]  draft ⚠️ CHECK or wrong-page pick — documented, not used
[BOOTSTRAP-MERGED]     two role-separated bootstrap intents combined
[MANUAL]               supplied by hand (intent semantics or DOM tweaks)

Match phrases are kept identical to the previous working production
config; introducing new ones risks re-routing existing steps (a bug we
hit once and reverted from).
"""

from configPage.base_config import build_site_config


SITE_OVERRIDES = {

    # [BOOTSTRAP-VERIFIED] base_url loaded cleanly during the run.
    "base_url": "https://www.automationexercise.com",

    # ── Navigation paths ──────────────────────────────────────────
    # [BOOTSTRAP-VERIFIED] all five paths loaded.
    # [MANUAL] aliases home/basket added — the engine looks these up.
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
    # [MANUAL] resolves 5 × 👉 FIX from the draft. The bootstrapper
    # could not auto-detect these (its heuristic is honestly weak here).
    # Each one is a single stable element confirming the page loaded.
    "page_ready_signals": {
        "homepage": ("id",  "search_product"),
        "home":     ("id",  "search_product"),
        "products": ("css", ".features_items"),
        "product":  ("id",  "search_product"),
        "login":    ("css", "input[data-qa='login-email']"),
        "cart":     ("id",  "cart_info"),
        "basket":   ("id",  "cart_info"),
    },

    # ── URL fragments for verify-page-detection ───────────────────
    # [MANUAL] URL substrings, not DOM selectors — pure site knowledge.
    "page_url_fragments": {
        "products":       "/products",
        "product_detail": "/product_details/",
        "cart":           "/view_cart",
        "basket":         "/view_cart",
        "login":          "/login",
        "home":           "automationexercise.com",
    },

    # ── Verify keywords ───────────────────────────────────────────
    # [MANUAL] resolves the 5 × ⚠️ PROPOSED entries from the draft.
    # The draft's auto-sampled keywords were the same generic nav text
    # ("home"/"products"/"cart") for every page, which can't
    # distinguish page-states. These are the actual page-unique
    # phrases for each named state used in test steps.
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
        "login page loaded": [
            "login to your account", "new user signup",
            "email address", "password",
        ],
    },

    # ──────────────────────────────────────────────────────────────
    # INTENT ACTIONS
    # ──────────────────────────────────────────────────────────────
    "intent_actions": {

        # ── search_input ─────────────────────────────────────────
        # Draft markers resolved:
        #   👉 FIX type            → form_field
        #   👉 FIX match           → restored from previous working config
        #   👉 FIX data_key        → "search" (key in test_data.py)
        #   3 × 👉 FIX no-resolve  → removed (those selectors don't exist here)
        "search_input": {
            "type": "form_field",
            "match": [
                "search bar", "search box", "search field",
                "search input", "search for", "type in search bar",
            ],
            # [BOOTSTRAP-VERIFIED] ✅ id=search_product matched 1.
            #                       ✅ name=search and placeholder also ✅.
            "field_hints": ["search_product", "search"],
            "field_type": "text",
            "data_key": "search",
        },

        # ── search_submit ────────────────────────────────────────
        # Draft markers resolved:
        #   👉 FIX type            → click_strategies
        #   👉 FIX match           → restored
        #   ⚠️ PROPOSED button[type=button] (matched 2) → discarded (generic)
        #   3 × 👉 FIX no-resolve  → removed
        "search_submit": {
            "type": "click_strategies",
            "match": [
                "search button", "search submit",
                "click search", "go button",
            ],
            "strategies": [
                # [BOOTSTRAP-VERIFIED] ✅ matched 1 — search-form-scoped.
                ("css", "form.searchform button[type='submit']"),
                # [BOOTSTRAP-VERIFIED] ✅ matched 1 — generic submit.
                ("css", "button[type='submit']"),
                # [BOOTSTRAP-DISCARDED] earlier draft offered
                # ("id", "subscribe") here — the newsletter button.
                # Same-page semantic confusion; not used.
            ],
            "wait_for_url_fragment": "/products",
        },

        # ── view_product ─────────────────────────────────────────
        # Draft markers resolved:
        #   👉 FIX type            → click_first_match (many product cards)
        #   👉 FIX match           → restored
        #   ⚠️ PROPOSED button[type=button] (matched 2) → discarded
        #   3 × 👉 FIX no-resolve  → removed
        "view_product": {
            "type": "click_first_match",
            "match": [
                "view product", "click product", "select product",
                "first product", "first result",
            ],
            "pre_wait": 1,
            "scroll_before_click": True,
            "strategies": [
                # [MANUAL] /product_details/ is tighter than the draft's
                # generic /product — avoids matching /products itself.
                ("css", "a[href*='/product_details/']"),
                # [BOOTSTRAP-VERIFIED] ✅ matched 1.
                ("css", "a[href*='/product']"),
            ],
            "wait_for_url_fragment": "/product_details/",
        },

        # ── add_to_basket [BOOTSTRAP-MERGED] ──────────────────────
        # Draft markers resolved:
        #   👉 FIX type            → click_strategies
        #   👉 FIX match           → restored
        #   👉 FIX strict          → True (wrong add-to-cart is bad)
        #   2 × ⚠️ CHECK search_product/submit_search → DISCARDED
        #   ⚠️ PROPOSED xpath matched 25 → kept as backup (covers listing
        #                                   page when product cards have
        #                                   "Add to cart" text)
        #   2 × 👉 FIX no-resolve  → removed
        # [BOOTSTRAP-MERGED] also includes detail-page selectors from the
        # draft's separate product_detail_add_to_cart intent (which had
        # button.cart ✅).
        "add_to_basket": {
            "type": "click_strategies",
            "strict": True,
            "match": [
                "add to cart", "add to basket", "add this to cart",
            ],
            "pre_wait": 1,
            "scroll_before_click": True,
            "wait_after": 2,
            "strategies": [
                # ── Detail page (from product_detail_add_to_cart) ──
                # [BOOTSTRAP-VERIFIED] all four ✅ on /product_details/1.
                ("css", "button.cart"),
                ("css", "button.btn.cart"),
                ("css", "button[type='button'].btn.cart"),
                ("xpath", "//button[contains(@class,'cart') and "
                          "(contains(.,'Add to cart') or "
                          "contains(.,'Add to Cart'))]"),
                # [BOOTSTRAP-DISCARDED] detail page also surfaced
                # id=quantity/name/email/review as ✅ — those are the
                # review form, NOT add-to-cart. Same-page confusion.
                #
                # ── Listing page (the per-card add-to-cart links) ──
                # [BOOTSTRAP-VERIFIED] from the draft's add_to_basket
                # intent — these are the right listing-page selectors.
                ("css", "a.add-to-cart"),
                ("xpath", "//a[contains(@class,'add-to-cart')]"),
            ],
            "after": "increment_count",
            "count_key": "cart_count",
        },

        # ── view_basket ──────────────────────────────────────────
        # Draft markers resolved:
        #   👉 FIX type            → click_strategies
        #   👉 FIX match           → restored
        #   ⚠️ PROPOSED [aria-label*='art'] (matched 7) → discarded (loose)
        #   ⚠️ PROPOSED button[type=button] (matched 2) → discarded
        #   1 × 👉 FIX no-resolve  → removed
        "view_basket": {
            "type": "click_strategies",
            "match": [
                "view cart", "view basket", "go to cart",
                "go to basket", "see cart", "open cart",
                "view cart modal",
            ],
            "strategies": [
                # [BOOTSTRAP-VERIFIED] ✅ matched 1.
                ("css", "a[href='/view_cart']"),
                ("xpath", "//a[@href='/view_cart']"),
                # [MANUAL] post-add modal "View Cart" sits inside <u>.
                # Bootstrapper static crawl never sees it (modal only
                # appears after an add-to-cart click).
                ("xpath", "//u[text()='View Cart']/parent::a"),
            ],
            "wait_for_url_fragment": "/view_cart",
        },

        # ── category_link ────────────────────────────────────────
        # Draft markers resolved:
        #   👉 FIX type            → click_first_match
        #   👉 FIX match           → restored from PREVIOUS working config
        #                            (NOT adding "category" — that broke
        #                            "Click products tab" routing earlier)
        #   ⚠️ PROPOSED button[type=button] (matched 2) → discarded
        "category_link": {
            "type": "click_first_match",
            "match": [
                "women category", "men category", "kids category",
                "category link",
                "dress subcategory", "tops subcategory",
                "tshirts subcategory", "jeans subcategory",
                "saree subcategory",
            ],
            "pre_wait": 1,
            "scroll_before_click": True,
            "strategies": [
                # [BOOTSTRAP-VERIFIED] both ✅ matched 1.
                ("css", ".category-products a"),
                ("css", "#accordian a"),
                ("css", "a[href*='/category_products/']"),
            ],
        },

        # ── brand_link ───────────────────────────────────────────
        # Draft markers resolved:
        #   👉 FIX type            → click_first_match
        #   👉 FIX match           → restored
        #   2 × ⚠️ CHECK search_product/submit_search → DISCARDED
        #   3 × ⚠️ PROPOSED brand selectors (matched 8) → KEPT — matched 8
        #     is correct for a listing of brands; click_first_match handles
        #     selection by URL keyword in the step.
        "brand_link": {
            "type": "click_first_match",
            "match": [
                "polo brand", "madame brand", "h&m brand", "biba brand",
                "brand link",
            ],
            "pre_wait": 1,
            "scroll_before_click": True,
            "strategies": [
                ("css", "a[href*='/brand_products/']"),
                ("css", ".brands_products a"),
                ("css", ".brands-name a"),
            ],
        },

        # ── login_email ──────────────────────────────────────────
        # Draft markers resolved:
        #   👉 FIX type            → form_field
        #   👉 FIX match           → keywords matching test step wording
        #   👉 FIX data_key        → "email"
        #   2 × ⚠️ CHECK subscribe → DISCARDED (newsletter, not login)
        #   5 × ✅ signup-* / login-password / login-button → not used
        #     here; each belongs in its own intent (DOM extractor
        #     surfaces them all on this page; semantics decides).
        #   4 × 🗑️ DELETE fc-*    → removed
        "login_email": {
            "type": "form_field",
            "match": [
                "login email", "enter login email",
                "login email field",
                # NOTE: deliberately NOT including bare "email" or
                # "email address" — those phrases also appear in
                # subscribe/contact/signup test steps and would
                # mis-route. Use phrases that explicitly say "login".
            ],
            # [BOOTSTRAP-VERIFIED] ✅ via the DOM extractor + form context
            # which correctly picked login-email over signup-email.
            "field_hints": ["login-email", "email"],
            "field_type": "email",
            "data_key": "email",
        },

        # ── login_password ───────────────────────────────────────
        # Draft markers resolved similarly to login_email above.
        "login_password": {
            "type": "form_field",
            "match": [
                "login password", "enter login password",
                "password field",
            ],
            "field_hints": ["login-password", "password"],
            "field_type": "password",
            "data_key": "password",
        },
        "invalid_login_password": {
            "type": "form_field",
            "match": [
                "invalid login password", "enter invalid login password",
                "wrong login password", "enter wrong login password",
            ],
            "field_hints": ["login-password", "password"],
            "field_type": "password",
            "data_key": "invalid_password",
        },

        # ── login_button ─────────────────────────────────────────
        # Draft markers resolved:
        #   👉 FIX type            → click_strategies
        #   👉 FIX strict          → True
        #   2 × ⚠️ CHECK subscribe → DISCARDED
        #   4 × 🗑️ DELETE fc-*    → removed
        "login_button": {
            "type": "click_strategies",
            "strict": True,
            "match": [
                "login button", "click login", "submit login",
                "click login button",
            ],
            "strategies": [
                # [BOOTSTRAP-VERIFIED] all three ✅ matched 1.
                ("css", "button[data-qa='login-button']"),
                ("xpath", "//form[contains(@action,'login')]"
                          "//button[@type='submit']"),
                ("xpath", "//button[contains(translate(.,"
                          "'LOGIN','login'),'login')]"),
            ],
            "wait_for_url_fragment": "/",
        },

        # ── filter_compare intents (4 × identical structure) ─────
        # Draft markers resolved for each:
        #   👉 FIX strict          → True (recommended in the draft itself)
        #   👉 FIX match           → restored
        #   👉 FIX wait_for_url_fragment → "/product_details/" (the draft
        #     default "/product" matches /products and is too loose).
        # [BOOTSTRAP-VERIFIED] pattern: container matched 34 items;
        # value resolved in 100%, link in 100%.

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

    # ── Login flow template (used by test_generator) ─────────────
    # When a user story references login, these steps are
    # synthesised in order before the actual test actions.
    # Site-specific: a site without login simply omits this key.
    "login_flow": [
        {"action": "navigate", "target": "homepage",       "value": ""},
        {"action": "verify",   "target": "homepage loaded", "value": ""},
        {"action": "click",    "target": "login",           "value": ""},
        {"action": "type",     "target": "email",           "value": ""},
        {"action": "type",     "target": "password",        "value": ""},
        {"action": "click",    "target": "login button",    "value": ""},
        {"action": "verify",   "target": "logged in",       "value": ""},
    ],

    # ── Checkout flow template (used by test_generator) ──────────
    # The generator looks up an intent in intent_actions whose match
    # list contains any of `target_keywords`, and uses that intent's
    # first match phrase as the JSON target. This lets the same
    # template work whether the site says "proceed to checkout" or
    # "go to checkout" or "checkout now".
    "checkout_flow": [
        {"action": "click",  "target_keywords": ["proceed to checkout", "checkout"]},
        {"action": "type",   "target_keywords": ["message box", "comment", "order note"]},
        {"action": "click",  "target_keywords": ["place order", "confirm order"]},
        {"action": "type",   "target_keywords": ["card name", "name on card"]},
        {"action": "type",   "target_keywords": ["card number", "credit card"]},
        {"action": "type",   "target_keywords": ["cvc", "cvv"]},
        {"action": "type",   "target_keywords": ["expiry month", "exp month"]},
        {"action": "type",   "target_keywords": ["expiry year", "exp year"]},
        {"action": "click",  "target_keywords": ["pay and confirm", "pay now", "submit payment"]},
        {"action": "verify", "target_keywords": ["order confirmed"]},
    ],

    # ── Value extraction patterns (used by test_generator) ───────
    # When a step's target matches `target_substrings`, the regex
    # is run against the step text to pull out a value (e.g. a
    # quantity number or a size letter).
    # A non-e-commerce site would define its own patterns here.
    "value_patterns": {
        "price_threshold": {
            "target_substrings": [
                "price less than", "price more than", "price greater",
                "price under", "price above", "below", "more than", "less than",
            ],
            "regex": r"\d+(?:\.\d+)?",
        },
        "quantity": {
            "target_substrings": ["quantity", "qty", "set quantity"],
            "regex": r"\d+(?:\.\d+)?",
        },
        "size": {
            "target_substrings": ["size"],
            "regex": r"\b(XS|S|M|L|XL|XXL|XXXL|small|medium|large|extra small|extra large|\d{1,3})\b",
        },
        "colour": {
            "target_substrings": ["colour", "color"],
            "regex": r"\b(black|white|red|blue|green|silver|gold|yellow|pink|purple|grey|gray|brown|orange)\b",
        },
        "storage": {
            "target_substrings": ["storage"],
            "regex": r"\b(\d{2,4}\s?(?:GB|TB|MB))\b",
        },
    },
}
# Merge the site overrides onto the static base contract.
SITE_CONFIG = build_site_config(SITE_OVERRIDES)