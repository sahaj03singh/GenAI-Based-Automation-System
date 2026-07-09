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

═══════════════════════════════════════════════════════════════
2026-07-03 UPDATE — Phase 1+2 additions for verify-strictness fix
═══════════════════════════════════════════════════════════════
After the verify-strictness fix in utils/actions.py (loose fallback
removed), many tests failed because their verify targets weren't
registered. Added:
  - ~23 new verify_keywords entries for legitimate page elements
  - contact form field intents (name/email/subject/message/submit)
  - cart_quantity form_field intent
Entries added are marked with # [2026-07-03] tags.
═══════════════════════════════════════════════════════════════
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

        # ═══════════════════════════════════════════════════════════
        # [2026-07-03] Phase 1 additions — verify_keywords for
        # tests that were previously matching via loose fallback.
        # Each keyword list is text that actually appears on the
        # target page (verified against automationexercise.com).
        # ═══════════════════════════════════════════════════════════

        # ── Contact / Contact-us page ──
        "contact page loaded": [
            "get in touch", "feedback for us", "your message here",
        ],
        "contact us page loaded": [
            "get in touch", "feedback for us", "your message here",
        ],
        "contact form visible": [
            "get in touch", "your name", "your email", "your message",
        ],
        "message sent": [
            "success! your details have been submitted successfully",
            "your details have been submitted",
        ],

        # ── Checkout page ──
        "checkout page": [
            "address details", "review your order", "place order",
        ],
        "checkout address details visible": [
            "address details", "delivery address", "billing address",
        ],
        "review your order section visible": [
            "review your order", "total amount",
        ],

        # ── Navigation destinations ──
        "test cases page": [
            "test cases", "register user", "login user",
            "logout user",
        ],
        "api testing page": [
            "apis list for practice", "api name",
        ],
        "video tutorials page": [
            "automation practice", "video tutorials",
        ],

        # ── Account / Register ──
        "account information page": [
            "enter account information", "date of birth",
            "sign up for our newsletter", "receive special offers",
        ],

        # ── Section-presence checks ──
        "featured items section visible": [
            "features items",
        ],
        "recommended items section visible": [
            "recommended items",
        ],
        "reviews section visible": [
            "write your review",
        ],
        "write your review section visible": [
            "write your review", "add review here",
        ],
        "subscription section visible": [
            "subscription", "get the most recent updates",
        ],
        "subscribe email field present": [
            "susbscribe_email", "your email address",
            # note: site has typo "susbscribe_email" as the ID — kept
        ],

        # ── Product detail fields ──
        "product has price displayed": [
            "rs.",
        ],
        "product has availability shown": [
            "availability:", "in stock",
        ],
        "product has brand listed": [
            "brand:",
        ],

        # ── Subscription success ──
        "subscription success": [
            "you have been successfully subscribed",
        ],
        "subscription success message": [
            "you have been successfully subscribed",
        ],

        # ── Review submitted ──
        "review submitted": [
            "thank you for your review", "review has been submitted",
            "review has been posted",
        ],

        # ── Logout state ──
        # When logged out, the "Signup / Login" link is visible.
        # (When logged in, it's replaced by "Logout".)
        "logged out": [
            "signup / login",
        ],

        # NOTE — targets deliberately NOT added (site cannot produce them):
        #   "no results message" — empty/nonsense search returns all products
        #   "error message" (quantity 0/negative) — site accepts silently
        #   "email format error" / "required field error" — HTML5 browser
        #     validation tooltips, not in page source
        # Tests using these targets will genuinely fail — that's honest.
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

        # ──────────────────────────────────────────────────────────
        #  SPECIFIC CATEGORY INTENTS
        # ──────────────────────────────────────────────────────────
        # Added 2026-06-04 to fix the locator-caching false-positive
        # bug identified in the screenshot audit (Phase 2). Before
        # this, every category test (Women/Men/Kids) resolved to the
        # same generic `category_link` intent below, which picked the
        # first sidebar item on page — always WOMEN. The score-based
        # `_resolve_intent` in actions.py picks the intent whose
        # longest matched keyword is in the description, so these
        # specific intents win over the generic `category_link`.
        "category_women": {
            "type": "click_strategies",
            "match": ["women category"],
            "pre_wait": 1,
            "scroll_before_click": True,
            "strategies": [
                ("xpath", "//a[@href='#Women']"),
                ("xpath", "//a[normalize-space()='Women']"),
            ],
        },
        "category_men": {
            "type": "click_strategies",
            "match": ["men category"],
            "pre_wait": 1,
            "scroll_before_click": True,
            "strategies": [
                ("xpath", "//a[@href='#Men']"),
                ("xpath", "//a[normalize-space()='Men']"),
            ],
        },
        "category_kids": {
            "type": "click_strategies",
            "match": ["kids category"],
            "pre_wait": 1,
            "scroll_before_click": True,
            "strategies": [
                ("xpath", "//a[@href='#Kids']"),
                ("xpath", "//a[normalize-space()='Kids']"),
            ],
        },

        # ──────────────────────────────────────────────────────────
        #  SPECIFIC SUBCATEGORY INTENTS
        # ──────────────────────────────────────────────────────────
        # Same fix pattern as category. Clicking these requires the
        # parent category to be expanded first (category_women etc.).
        # The XPath targets the link inside /category_products/ URL.
        "subcategory_dress": {
            "type": "click_strategies",
            "match": ["dress subcategory"],
            "pre_wait": 1,
            "strategies": [
                ("xpath", "//a[contains(@href,'/category_products/') "
                          "and normalize-space()='Dress']"),
                ("xpath", "//a[normalize-space()='Dress']"),
            ],
        },
        "subcategory_tops": {
            "type": "click_strategies",
            "match": ["tops subcategory"],
            "pre_wait": 1,
            "strategies": [
                ("xpath", "//a[contains(@href,'/category_products/') "
                          "and normalize-space()='Tops']"),
                ("xpath", "//a[normalize-space()='Tops']"),
            ],
        },
        "subcategory_saree": {
            "type": "click_strategies",
            "match": ["saree subcategory"],
            "pre_wait": 1,
            "strategies": [
                ("xpath", "//a[contains(@href,'/category_products/') "
                          "and normalize-space()='Saree']"),
                ("xpath", "//a[normalize-space()='Saree']"),
            ],
        },
        "subcategory_tshirts": {
            "type": "click_strategies",
            "match": ["tshirts subcategory"],
            "pre_wait": 1,
            "strategies": [
                ("xpath", "//a[contains(@href,'/category_products/') "
                          "and normalize-space()='Tshirts']"),
                ("xpath", "//a[normalize-space()='Tshirts']"),
            ],
        },
        "subcategory_jeans": {
            "type": "click_strategies",
            "match": ["jeans subcategory"],
            "pre_wait": 1,
            "strategies": [
                ("xpath", "//a[contains(@href,'/category_products/') "
                          "and normalize-space()='Jeans']"),
                ("xpath", "//a[normalize-space()='Jeans']"),
            ],
        },

        # ── category_link (GENERIC FALLBACK) ─────────────────────
        # Kept as fallback for any unanticipated category/subcategory
        # not covered by the specific intents above. Score-based
        # resolver only picks this when no longer keyword matched.
        # Draft markers resolved:
        #   👉 FIX type            → click_first_match
        #   👉 FIX match           → restored from PREVIOUS working config
        #                            (NOT adding "category" — that broke
        #                            "Click products tab" routing earlier)
        #   ⚠️ PROPOSED button[type=button] (matched 2) → discarded
        "category_link": {
            "type": "click_first_match",
            "match": [
                "category link",
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

        # ──────────────────────────────────────────────────────────
        #  SPECIFIC BRAND INTENTS
        # ──────────────────────────────────────────────────────────
        # Added 2026-06-04 for the same locator-caching fix. Before
        # this, every brand test (Madame/H&M/Biba) hit the generic
        # `brand_link` intent and clicked POLO (first brand in
        # sidebar). These specific intents target each brand by its
        # /brand_products/<Name> URL fragment.
        "brand_polo": {
            "type": "click_strategies",
            "match": ["polo brand"],
            "pre_wait": 1,
            "scroll_before_click": True,
            "strategies": [
                ("xpath", "//a[contains(@href,'/brand_products/Polo')]"),
                ("xpath", "//a[normalize-space()='Polo']"),
            ],
        },
        "brand_madame": {
            "type": "click_strategies",
            "match": ["madame brand"],
            "pre_wait": 1,
            "scroll_before_click": True,
            "strategies": [
                ("xpath", "//a[contains(@href,'/brand_products/Madame')]"),
                ("xpath", "//a[normalize-space()='Madame']"),
            ],
        },
        "brand_hm": {
            "type": "click_strategies",
            "match": ["h&m brand"],
            "pre_wait": 1,
            "scroll_before_click": True,
            "strategies": [
                ("xpath", "//a[contains(@href,'/brand_products/H&M')]"),
                ("xpath", "//a[normalize-space()='H&M']"),
            ],
        },
        "brand_biba": {
            "type": "click_strategies",
            "match": ["biba brand"],
            "pre_wait": 1,
            "scroll_before_click": True,
            "strategies": [
                ("xpath", "//a[contains(@href,'/brand_products/Biba')]"),
                ("xpath", "//a[normalize-space()='Biba']"),
            ],
        },

        # ── brand_link (GENERIC FALLBACK) ────────────────────────
        # Kept as fallback for any unanticipated brand not covered
        # by the specific intents above.
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

        # ═══════════════════════════════════════════════════════════
        # [2026-07-03] Phase 2 additions — action-level intents
        # ═══════════════════════════════════════════════════════════

        # ── contact_name / email / subject / message form fields ──
        # For the "Contact Us Form Submission" test. The site's
        # contact form has these named fields directly (id/name).
        "contact_name": {
            "type": "form_field",
            "match": [
                "contact name", "contact us name",
            ],
            "field_hints": ["name"],
            "field_type": "text",
            "data_key": "contact_name",
        },
        "contact_email": {
            "type": "form_field",
            "match": [
                "contact email", "contact us email",
            ],
            "field_hints": ["email"],
            "field_type": "email",
            "data_key": "contact_email",
        },
        "contact_subject": {
            "type": "form_field",
            "match": [
                "contact subject", "contact us subject", "subject field",
            ],
            "field_hints": ["subject"],
            "field_type": "text",
            "data_key": "contact_subject",
        },
        "contact_message": {
            "type": "form_field",
            "match": [
                "contact message", "contact us message", "your message",
                "message body",
            ],
            "field_hints": ["message"],
            "field_type": "text",
            "data_key": "contact_message",
        },
        "submit_contact_button": {
            "type": "click_strategies",
            "match": [
                "submit contact button", "submit contact form",
                "send message", "submit message",
            ],
            "strategies": [
                ("css", "input[name='submit']"),
                ("xpath", "//input[@type='submit' and @value='Submit']"),
                ("xpath", "//form[contains(@action,'contact')]"
                          "//input[@type='submit']"),
            ],
        },

        # ── cart_quantity form_field ──
        # For the "Update Quantity In Cart Page" test. The cart page
        # has a quantity input inside each cart row.
        "cart_quantity": {
            "type": "form_field",
            "match": [
                "cart quantity", "update cart quantity",
                "quantity in cart", "quantity field cart",
            ],
            "field_hints": ["quantity"],
            "field_type": "text",
            "data_key": "cart_quantity",
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