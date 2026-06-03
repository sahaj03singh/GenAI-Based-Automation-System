

SITE_CONFIG = {

    "base_url": "https://www.amazon.co.uk",

    # ── Navigation paths ──────────────────────────────────────────
    "navigation_paths": {
        "homepage": "/",
        "home":     "/",
        "login":    "/ap/signin",
        "logout":   "/gp/sign-out.html",
        "cart":     "/gp/cart/view.html",
        "basket":   "/gp/cart/view.html",
    },

    "page_ready_signals": {
        "homepage": ("id",    "nav-search-bar-form"),
        "home":     ("id",    "nav-search-bar-form"),
        "login":    ("id",    "ap_email"),
        "cart":     ("xpath",
                     "//h1[contains(.,'Basket') or contains(.,'Cart')]"),
        "basket":   ("xpath",
                     "//h1[contains(.,'Basket') or contains(.,'Cart')]"),
    },

    "page_url_fragments": {
        "search_results": "/s?",
        "product_detail": "/dp/",
        "cart":           "/gp/cart",
        "basket":         "/gp/cart",
        "login":          "/ap/signin",
        "home":           "amazon.co.uk",
    },

    "ui_action_keywords": [
        "button", "filter", "sort", "add to basket",
        "add to cart", "basket", "buy now", "submit",
        "sign in", "sign out", "proceed", "search",
        "price low", "rating", "select", "type",
        "click", "view product", "first product",
        "minimum customer rating",
    ],

    "navigation_session_flags": {
        "logged_in":          ["home", "homepage"],
        "on_homepage_page":   ["homepage", "home"],
    },
    "navigation_reset_flags": {
        "logged_in":          ["login", "logout"],
        "on_homepage_page":   [],
    },
    "pre_navigate_for": {
        "homepage": ["search bar", "search input"],
    },

    # ── Verify keywords ───────────────────────────────────────────
    "verify_keywords": {
        "homepage loaded": [
            "amazon.co.uk", "deliver to", "today's deals",
            "your amazon", "basket"
        ],
        "home page": [
            "amazon.co.uk", "deliver to", "today's deals", "basket"
        ],
        "logged in": [
            "sign out", "account & lists", "hello,"
        ],
        "search results visible": [
            "results", "results for", "sort by", "sponsored"
        ],
        "search results": [
            "results", "results for", "sort by", "sponsored"
        ],
        "product detail page": [
            "add to basket", "buy now", "in stock",
            "out of 5 stars", "add to cart"
        ],
        "product page": [
            "add to basket", "buy now", "in stock",
            "out of 5 stars"
        ],
        # ── Expanded keyword set for Amazon's varied confirmation UI ──
        "added to basket": [
            "added to basket",
            "added to cart",
            "added to your basket",
            "added to your cart",
            "go to basket",
            "go to cart",
            "subtotal",
            "1 item added",
            "items added",
            "view basket",
            "view cart",
            "proceed to checkout",
            "cart subtotal",
            "basket subtotal",
        ],
        "added to cart": [
            "added to basket",
            "added to cart",
            "added to your basket",
            "go to basket",
            "go to cart",
            "subtotal",
            "1 item added",
            "items added",
            "view basket",
            "view cart",
            "proceed to checkout",
        ],
        "cart contains item": [
            "subtotal", "proceed to checkout"
        ],
        "basket contains item": [
            "subtotal", "proceed to checkout"
        ],
        "sort applied": [
            "price: low to high", "price: high to low"
        ],
    },

    "waitable_verifications": [
        "logged in", "added to basket", "added to cart",
        "search results visible", "search results",
        "product detail page", "sort applied",
    ],

    "count_verifications": {},
    "modal_buttons":       {},
    "sidebar":             {},

    # ── Intent actions ────────────────────────────────────────────
    "intent_actions": {

        # ── Search input ───────────────────────────────────────
        "search_input": {
            "type": "form_field",
            "match": [
                "search bar", "search box", "search field",
                "search input", "search for",
                "type in search bar"
            ],
            "field_hints": [
                "twotabsearchtextbox", "search",
                "field-keywords", "k"
            ],
            "field_type": "text",
            "data_key":   "search",
        },

        # ── Search submit button ───────────────────────────────
        "search_submit": {
            "type": "click_strategies",
            "match": [
                "search button", "search submit",
                "click search", "go button"
            ],
            "strategies": [
                ("id",    "nav-search-submit-button"),
                ("xpath", "//input[@id='nav-search-submit-button']"),
                ("xpath",
                 "//div[@id='nav-search']//input[@type='submit']"),
            ],
            "wait_for_url_fragment": "/s?",
        },

        # ── Sort dropdown — Price: Low to High ─────────────────
        "sort_by_price_low_high": {
            "type": "select_option",
            "match": [
                "sort by price low to high",
                "sort by price: low to high",
                "sort by lowest price",
                "sort low to high",
                "sort by price",
                "price low to high",
                "low to high",
            ],
            "select_id":    "s-result-sort-select",
            "option_text":  "Price: Low to High",
            "option_value": "price-asc-rank",
            "wait_for_url_fragment": "s=price-asc-rank",
            "fallback_strategies": [
                ("xpath", "//a[contains(@href,'price-asc-rank')]"),
                ("xpath",
                 "//span[contains(text(),'Price: Low to High')]"),
            ],
        },

        # ── Sort dropdown — Price: High to Low ─────────────────
        "sort_by_price_high_low": {
            "type": "select_option",
            "match": [
                "sort by price high to low",
                "sort by price: high to low",
                "sort by highest price",
                "sort high to low",
                "price high to low",
                "high to low",
            ],
            "select_id":    "s-result-sort-select",
            "option_text":  "Price: High to Low",
            "option_value": "price-desc-rank",
            "wait_for_url_fragment": "s=price-desc-rank",
            "fallback_strategies": [
                ("xpath", "//a[contains(@href,'price-desc-rank')]"),
                ("xpath",
                 "//span[contains(text(),'Price: High to Low')]"),
            ],
        },

        # ── Product selection with rating filter ────────────────
        # Tries 4.5 → 4.4 → 4.3 → any 4+ → first product → /dp/ href
        # Resilient to Amazon DOM A/B variants
        "view_product": {
            "type": "click_first_match",
            "match": [
                "view product", "click product",
                "select product", "product with",
                "minimum customer rating",
                "select the product with minimum",
                "product with minimum customer rating of 4.3",
                "first product", "first result",
            ],
            "pre_wait": 3,
            "scroll_before_click": True,
            "strategies": [
                # ── Variant 1: Standard layout with rating ──────
                # 4.5+ stars
                ("xpath",
                 "(//div[@data-component-type='s-search-result']"
                 "[.//span[contains(@class,'a-icon-alt') and "
                 "starts-with(.,'4.5')]]//h2//a)[1]"),
                # 4.4+ stars
                ("xpath",
                 "(//div[@data-component-type='s-search-result']"
                 "[.//span[contains(@class,'a-icon-alt') and "
                 "starts-with(.,'4.4')]]//h2//a)[1]"),
                # 4.3+ stars
                ("xpath",
                 "(//div[@data-component-type='s-search-result']"
                 "[.//span[contains(@class,'a-icon-alt') and "
                 "starts-with(.,'4.3')]]//h2//a)[1]"),
                # Any 4+ stars
                ("xpath",
                 "(//div[@data-component-type='s-search-result']"
                 "[.//span[contains(@class,'a-icon-alt') and "
                 "starts-with(.,'4.')]]//h2//a)[1]"),

                # ── Variant 2: Standard layout, any product ─────
                ("xpath",
                 "(//div[@data-component-type='s-search-result']"
                 "[not(.//span[contains(text(),'Sponsored')])]"
                 "//h2//a)[1]"),
                ("xpath",
                 "(//div[@data-component-type='s-search-result']"
                 "//h2//a)[1]"),

                # ── Variant 3: data-asin layout (A/B variant) ───
                ("xpath",
                 "(//div[@data-asin and string-length(@data-asin) > 5]"
                 "//h2//a)[1]"),
                ("xpath",
                 "(//div[@data-asin and string-length(@data-asin) > 5]"
                 "//a[contains(@class,'s-line-clamp')])[1]"),

                # ── Variant 4: Direct /dp/ href (most resilient) ──
                # Even if Amazon restructures DOM entirely, product
                # pages always have /dp/ in href
                ("xpath",
                 "(//a[contains(@href,'/dp/') "
                 "and not(contains(@href,'sspa'))])[1]"),
                ("xpath",
                 "(//a[contains(@href,'/gp/product/')])[1]"),

                # ── Variant 5: Last resort — image-anchored link ──
                ("xpath",
                 "(//a[contains(@class,'s-product-image-link')])[1]"),
            ],
            "wait_for_url_fragment": "/dp/",
        },

        # ── Add to basket (strict, scoped to main buy-box only) ──
        # IMPORTANT: scoped to #addToCart_feature_div / #desktop_buybox
        # to avoid clicking add-to-basket on recommendation cards
 "add_to_basket": {
    "type": "click_strategies",
    "strict": True,
    "match": [
        "add to basket", "add to cart",
        "add to bag", "add this to basket"
    ],
    "pre_wait": 2,
    "scroll_before_click": True,
    "wait_after": 3,
    "strategies": [
        # Scope to main product's buy-box
        ("xpath",
         "//div[@id='addToCart_feature_div']"
         "//input[@id='add-to-cart-button']"),
        ("xpath",
         "//div[@id='desktop_buybox']"
         "//input[@id='add-to-cart-button']"),
        ("id", "add-to-cart-button"),
        # Span variant
        ("xpath",
         "//span[@id='submit.add-to-cart']//input"),
    ],
    "after": "increment_count",
    "count_key": "cart_count",
    # JS fallback — submits the form directly if all clicks fail
    "js_fallback": (
        "var btn = document.getElementById('add-to-cart-button');"
        "if (btn) { btn.click(); return 'clicked'; }"
        "var form = document.getElementById('addToCart');"
        "if (form) { form.submit(); return 'form_submitted'; }"
        "return 'not_found';"
    ),
},
        # ── Buy now (alternative path) ──────────────────────────
        "buy_now": {
            "type": "click_strategies",
            "strict": True,
            "match": ["buy now", "buy it now"],
            "scroll_before_click": True,
            "strategies": [
                ("xpath",
                 "//div[@id='buyNow_feature_div']"
                 "//input[@id='buy-now-button']"),
                ("id", "buy-now-button"),
                ("xpath", "//input[@id='buy-now-button']"),
            ],
        },

        # ── View basket / cart ──────────────────────────────────
        "view_basket": {
            "type": "click_strategies",
            "match": [
                "view basket", "view cart", "go to basket",
                "go to cart", "see basket", "see cart",
                "open basket", "open cart"
            ],
            "strategies": [
                ("id",    "nav-cart"),
                ("id",    "hlb-view-cart-announce"),
                ("xpath", "//a[@id='nav-cart']"),
                ("xpath", "//a[contains(@href,'/gp/cart/view')]"),
            ],
            "wait_for_url_fragment": "/gp/cart",
        },

        # ── Proceed to checkout ─────────────────────────────────
        "proceed_to_checkout": {
            "type": "click_strategies",
            "strict": True,
            "match": [
                "proceed to checkout", "checkout",
                "go to checkout"
            ],
            "scroll_before_click": True,
            "strategies": [
                ("xpath",
                 "//input[@name='proceedToRetailCheckout']"),
                ("id", "sc-buy-box-ptc-button"),
                ("xpath",
                 "//*[@data-feature-id='proceed-to-checkout-action']"),
                ("xpath",
                 "//*[contains(@aria-label,'Proceed to checkout')]"),
            ],
            "wait_for_url_change": True,
        },
    },

    "order_success_keywords": [
        "order placed", "order confirmed", "thank you",
        "your order has been placed",
    ],

    "product_detail_url_fragment": "/dp/",
}