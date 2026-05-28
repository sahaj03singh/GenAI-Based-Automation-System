SITE_CONFIG = {

    # ── Base URL ──────────────────────────────────────────────────
    "base_url": "https://www.automationexercise.com",

    # ── Navigation paths ──────────────────────────────────────────
    "navigation_paths": {
        "home":     "/",
        "login":    "/login",
        "signup":   "/login",
        "signin":   "/login",
        "logout":   "/logout",
        "products": "/products",
        "cart":     "/view_cart",
    },

    # ── Page ready signals ────────────────────────────────────────
    "page_ready_signals": {
        "login":    ("name",  "email"),
        "signup":   ("name",  "email"),
        "signin":   ("name",  "email"),
        "logout":   ("name",  "email"),
        "products": ("id",    "search_product"),
        "cart":     ("xpath",
                     "//table[@id='cart_info_table'] | "
                     "//p[contains(.,'empty')]"),
        "home":     ("tag",   "body"),
        "payment":  ("tag",   "body"),
        "checkout": ("tag",   "body"),
    },

    # ── URL fragments to identify pages ──────────────────────────
    "page_url_fragments": {
        "login":          "/login",
        "products":       "/products",
        "cart":           "/view_cart",
        "product detail": "/product_details/",
        "payment":        "/payment",
        "checkout":       "/checkout",
        "home":           "/",
    },

    # ── UI action keywords ────────────────────────────────────────
    "ui_action_keywords": [
        "button", "tab", "modal", "link", "submit",
        "add to cart", "view cart", "proceed", "place order",
        "pay", "continue shopping", "view product", "remove",
        "sign up button", "register button", "category",
        "subcategory", "brand", "cheapest", "most expensive",
        "price less than", "price more than",
    ],

    # ── Navigation session flags ──────────────────────────────────
    "navigation_session_flags": {
        "on_products_page": ["products"],
        "logged_in":        ["home", "products", "cart"],
    },

    "navigation_reset_flags": {
        "logged_in": ["logout", "login", "signup"],
    },

    "pre_navigate_for": {
        "products": [
            "search bar", "search box",
            "search field", "search input",
        ],
    },

    # ── Verify keywords ───────────────────────────────────────────
    "verify_keywords": {
        "logged in":         ["logout", "log out", "sign out"],
        "order confirmed":   ["congratulations", "order placed",
                              "order confirmed",
                              "thank you for your order"],
        "searched products": ["searched products"],
        "search results":    ["searched products", "search results"],
        "search results visible": ["searched products"],
        "searched products visible": ["searched products"],
        "brand products":    ["brand products", "polo"],
        "brand page":        ["brand products"],
        "category products": ["category", "women", "men", "kids"],
        "category page":     ["category", "women", "men", "kids"],
        "products page":     ["all products", "products"],
        "address details":   ["address details", "delivery address",
                              "checkout"],
        "order summary":     ["order summary", "cart_info",
                              "checkout"],
        "delivery address":  ["delivery address"],
        "billing address":   ["billing address"],
        "congratulations":   ["congratulations"],
        "product detail page": ["/product_details/", "add to cart",
                                "quantity", "availability"],
        "cart contains item":  ["/view_cart", "cart_info_table",
                                "shopping cart"],
        "homepage loaded":     ["automationexercise", "automation exercise",
                                "features items", "category"],
    },

    "waitable_verifications": [
        "logged in",
        "order confirmed",
        "congratulations",
        "product detail page",
        "cart contains item",
    ],

    # ── Session count verifications ───────────────────────────────
    "count_verifications": {
        "cart is empty":         {"session_var": "cart_count",
                                  "operator": "eq",  "value": 0},
        "cart has one product":  {"session_var": "cart_count",
                                  "operator": "eq",  "value": 1},
        "both products in cart": {"session_var": "cart_count",
                                  "operator": "gte", "value": 2},
        "product in cart":       {"session_var": "cart_count",
                                  "operator": "gt",  "value": 0},
        "product still in cart": {"session_var": "cart_count",
                                  "operator": "gt",  "value": 0},
        "cart has product":      {"session_var": "cart_count",
                                  "operator": "gt",  "value": 0},
    },

    # ── Modal button locators ─────────────────────────────────────
    "modal_buttons": {
        "modal_locator": (
            "xpath",
            "//div[@id='cartModal'] | "
            "//div[contains(@class,'modal') "
            "and contains(@style,'display: block')]"
        ),
        "view_cart": (
            "xpath",
            "//u[contains(text(),'View Cart')]/.. | "
            "//a[contains(text(),'View Cart')]"
        ),
        "continue": (
            "xpath",
            "//button[contains(text(),'Continue Shopping')]"
        ),
    },

    # ── Sidebar (left navigation panel) ───────────────────────────
    "sidebar": {
        "women category":      (
            "xpath",
            "//div[@id='accordian']//a[contains(.,'Women')]"
        ),
        "men category":        (
            "xpath",
            "//div[@id='accordian']//a[contains(.,'Men')]"
        ),
        "kids category":       (
            "xpath",
            "//div[@id='accordian']//a[contains(.,'Kids')]"
        ),
        "dress subcategory":   (
            "xpath",
            "//div[@id='Women']//a[contains(text(),'Dress')]"
        ),
        "tops subcategory":    (
            "xpath",
            "//div[@id='Women']//a[contains(text(),'Tops')]"
        ),
        "saree subcategory":   (
            "xpath",
            "//div[@id='Women']//a[contains(text(),'Saree')]"
        ),
        "tshirts subcategory": (
            "xpath",
            "//div[@id='Men']//a[contains(text(),'Tshirts')]"
        ),
        "jeans subcategory":   (
            "xpath",
            "//div[@id='Men']//a[contains(text(),'Jeans')]"
        ),
        "polo brand":          (
            "xpath",
            "//a[contains(@href,'brand_products/Polo')]"
        ),
        "h&m brand":           (
            "xpath",
            "//a[contains(@href,'brand_products/H&M')]"
        ),
        "madame brand":        (
            "xpath",
            "//a[contains(@href,'brand_products/Madame')]"
        ),
        "mast & harbour brand": (
            "xpath",
            "//a[contains(@href,'brand_products/Mast')]"
        ),
        "babyhug brand":       (
            "xpath",
            "//a[contains(@href,'brand_products/Babyhug')]"
        ),
        "allen solly brand":   (
            "xpath",
            "//a[contains(@href,'brand_products/Allen')]"
        ),
        "kookie kids brand":   (
            "xpath",
            "//a[contains(@href,'brand_products/Kookie')]"
        ),
        "biba brand":          (
            "xpath",
            "//a[contains(@href,'brand_products/Biba')]"
        ),
    },

    # ── Intent actions ────────────────────────────────────────────
    "intent_actions": {

        # ── Login ─────────────────────────────────────────────────
        "login_email": {
            "type":        "form_field",
            "match":       ["email", "e-mail", "username",
                            "user name", "user id"],
            "field_hints": ["email", "username", "user"],
            "data_key":    "email",
        },

        "login_password": {
            "type":        "form_field",
            "match":       ["password", "pass", "pwd", "secret"],
            "field_hints": ["password", "pass"],
            "data_key":    "password",
        },

        "login_submit": {
            "type":  "click_strategies",
            "match": ["login button", "sign in button",
                      "submit login"],
            "strategies": [
                ("xpath",
                 "//div[contains(@class,'login-form')]"
                 "//button[contains(translate(.,"
                 "'ABCDEFGHIJKLMNOPQRSTUVWXYZ',"
                 "'abcdefghijklmnopqrstuvwxyz'),'login')]"),
                ("xpath",
                 "//h2[contains(text(),'Login')]"
                 "/following::button[contains(translate(.,"
                 "'ABCDEFGHIJKLMNOPQRSTUVWXYZ',"
                 "'abcdefghijklmnopqrstuvwxyz'),'login')][1]"),
                ("xpath",
                 "//button[contains(translate(.,"
                 "'ABCDEFGHIJKLMNOPQRSTUVWXYZ',"
                 "'abcdefghijklmnopqrstuvwxyz'),'login')]"),
                ("xpath",
                 "//button[contains(translate(.,"
                 "'ABCDEFGHIJKLMNOPQRSTUVWXYZ',"
                 "'abcdefghijklmnopqrstuvwxyz'),'sign in')]"),
                ("xpath", "//input[@type='submit']"),
                ("xpath", "//button[@type='submit']"),
            ],
            "after": "confirm_login",
        },

        # ── Search ────────────────────────────────────────────────
        "search_input": {
            "type":         "form_field",
            "match":        ["search bar", "search box",
                             "search field", "search input"],
            "field_hints":  ["search_product", "search", "q"],
            "field_type":   "search",
            "data_key":     "search",
            "pre_navigate": "products",
        },

        "search_submit": {
            "type":  "click_strategies",
            "match": ["search button", "search submit",
                      "find button"],
            "strategies": [
                ("id",    "submit_search"),
                ("xpath",
                 "//button[@type='submit' and "
                 "ancestor::form[contains(@action,'search')]]"),
                ("xpath",
                 "//button[contains(translate(.,"
                 "'ABCDEFGHIJKLMNOPQRSTUVWXYZ',"
                 "'abcdefghijklmnopqrstuvwxyz'),'search')]"),
            ],
        },

        # ── Products tab ──────────────────────────────────────────
        "products_tab": {
            "type":  "click_strategies",
            "match": ["products tab", "click products",
                      "go to products", "products page"],
            "strategies": [
                ("xpath", "//a[@href='/products']"),
                ("xpath",
                 "//a[contains(translate(.,"
                 "'ABCDEFGHIJKLMNOPQRSTUVWXYZ',"
                 "'abcdefghijklmnopqrstuvwxyz'),'products')]"),
            ],
        },

        # ── Cart tab ──────────────────────────────────────────────
        "cart_tab": {
            "type":  "click_strategies",
            "match": ["cart tab", "go to cart",
                      "navigate to cart"],
            "strategies": [
                ("xpath", "//a[@href='/view_cart']"),
                ("xpath", "//a[contains(@href,'view_cart')]"),
            ],
        },

        # ── Product browsing ──────────────────────────────────────
        "view_product": {
            "type":  "click_first_match",
            "match": ["view product", "view item",
                      "product detail", "view product for",
                      "click first product", "first product"],
            "strategies": [
                ("xpath",
                 "(//a[contains(@href,'/product_details/')])[1]"),
                ("xpath",
                 "(//a[contains(translate(.,"
                 "'ABCDEFGHIJKLMNOPQRSTUVWXYZ',"
                 "'abcdefghijklmnopqrstuvwxyz'),"
                 "'view product')])[1]"),
            ],
            "wait_for_url_fragment": "/product_details/",
        },

        # ── Price filter intents (filter_compare) ─────────────────
        # These read visible prices and compare in Python
        "select_cheapest_product": {
            "type":  "filter_compare",
            "match": ["cheapest product", "lowest priced",
                      "minimum price product", "cheapest item",
                      "lowest price"],
            "container_xpath":
                "//div[@class='product-image-wrapper']",
            "value_xpath":
                ".//h2",
            "link_xpath":
                ".//a[contains(@href,'/product_details/')] | "
                ".//a[contains(translate(.,"
                "'ABCDEFGHIJKLMNOPQRSTUVWXYZ',"
                "'abcdefghijklmnopqrstuvwxyz'),'view product')]",
            "extract_pattern":       r"\d+(?:\.\d+)?",
            "operator":              "min",
            "wait_for_url_fragment": "/product_details/",
        },

        "select_most_expensive_product": {
            "type":  "filter_compare",
            "match": ["most expensive product", "highest priced",
                      "maximum price product", "costliest"],
            "container_xpath":
                "//div[@class='product-image-wrapper']",
            "value_xpath":
                ".//h2",
            "link_xpath":
                ".//a[contains(@href,'/product_details/')] | "
                ".//a[contains(translate(.,"
                "'ABCDEFGHIJKLMNOPQRSTUVWXYZ',"
                "'abcdefghijklmnopqrstuvwxyz'),'view product')]",
            "extract_pattern":       r"\d+(?:\.\d+)?",
            "operator":              "max",
            "wait_for_url_fragment": "/product_details/",
        },

        "select_product_under_price": {
            "type":  "filter_compare",
            "match": ["product with price less than",
                      "product less than", "product under",
                      "price less than", "price under",
                      "product below", "cheaper than",
                      "within budget"],
            "container_xpath":
                "//div[@class='product-image-wrapper']",
            "value_xpath":
                ".//h2",
            "link_xpath":
                ".//a[contains(@href,'/product_details/')] | "
                ".//a[contains(translate(.,"
                "'ABCDEFGHIJKLMNOPQRSTUVWXYZ',"
                "'abcdefghijklmnopqrstuvwxyz'),'view product')]",
            "extract_pattern":       r"\d+(?:\.\d+)?",
            "operator":              "lt",
            "wait_for_url_fragment": "/product_details/",
        },

        "select_product_above_price": {
            "type":  "filter_compare",
            "match": ["product with price more than",
                      "price more than", "price greater than",
                      "product above", "more expensive than"],
            "container_xpath":
                "//div[@class='product-image-wrapper']",
            "value_xpath":
                ".//h2",
            "link_xpath":
                ".//a[contains(@href,'/product_details/')] | "
                ".//a[contains(translate(.,"
                "'ABCDEFGHIJKLMNOPQRSTUVWXYZ',"
                "'abcdefghijklmnopqrstuvwxyz'),'view product')]",
            "extract_pattern":       r"\d+(?:\.\d+)?",
            "operator":              "gt",
            "wait_for_url_fragment": "/product_details/",
        },

        # ── Variant selection (click_option_with_value) ───────────
        # Generic — site-specific aliases live in value_aliases
        "select_size": {
            "type":  "click_option_with_value",
            "match": ["select size", "click size", "choose size",
                      "size option", "size m", "size l", "size s",
                      "size xl", "size xxl", "size xs"],
            "value_aliases": {
                "extra small": "XS",
                "small":       "S",
                "medium":      "M",
                "large":       "L",
                "extra large": "XL",
                "double xl":   "XXL",
                "triple xl":   "XXXL",
            },
            "extract_pattern":
                r"\b(XS|S|M|L|XL|XXL|XXXL|\d{1,3})\b",
            "option_xpaths": [
                "//button[normalize-space()='{value}']",
                "//a[normalize-space()='{value}']",
                "//label[normalize-space()='{value}']",
                "//*[@data-size='{value}']",
                "//input[@value='{value}' "
                "and (@type='radio' or @type='checkbox')]",
                "//div[contains(@class,'swatch')]"
                "[normalize-space()='{value}']",
                "//li[contains(@class,'size')]"
                "//*[normalize-space()='{value}']",
            ],
        },

        "select_colour": {
            "type":  "click_option_with_value",
            "match": ["select colour", "click colour",
                      "choose colour", "select color",
                      "click color", "choose color",
                      "colour option", "color option"],
            "extract_pattern":
                r"\b(black|white|red|blue|green|silver|gold|"
                r"yellow|pink|purple|grey|gray|brown|orange)\b",
            "option_xpaths": [
                "//button[normalize-space()='{value}']",
                "//*[@title='{value}']",
                "//*[@aria-label='{value}']",
                "//*[@data-color='{value}']",
                "//*[@data-colour='{value}']",
                "//img[@alt='{value}']",
                "//div[contains(@class,'color')]"
                "[normalize-space()='{value}']",
                "//div[contains(@class,'colour')]"
                "[normalize-space()='{value}']",
            ],
        },

        "select_storage": {
            "type":  "click_option_with_value",
            "match": ["select storage", "storage option",
                      "click storage"],
            "extract_pattern":
                r"\b(\d{2,4}\s?(?:GB|TB|MB))\b",
            "option_xpaths": [
                "//button[normalize-space()='{value}']",
                "//button[contains(normalize-space(),'{value}')]",
                "//a[normalize-space()='{value}']",
                "//*[@data-storage='{value}']",
                "//label[normalize-space()='{value}']",
            ],
        },

        # ── Quantity ──────────────────────────────────────────────
        "quantity_input": {
            "type":        "form_field",
            "match":       ["quantity", "qty", "how many",
                            "amount", "set quantity",
                            "quantity to"],
            "field_hints": ["quantity", "qty"],
            "field_type":  "number",
            "data_key":    "quantity",
        },

        # ── Add to cart ───────────────────────────────────────────
        "add_to_cart": {
            "type":  "listing_item_action",
            "match": ["add to cart", "add to bag",
                      "add item", "add product"],
            "detail_page_url_fragment": "/product_details/",
            "detail_page_strategies": [
                ("xpath", "//button[contains(@class,'cart')]"),
                ("xpath",
                 "//button[contains(translate(.,"
                 "'ABCDEFGHIJKLMNOPQRSTUVWXYZ',"
                 "'abcdefghijklmnopqrstuvwxyz'),'add to cart')]"),
                ("xpath",
                 "//button[contains(translate(.,"
                 "'ABCDEFGHIJKLMNOPQRSTUVWXYZ',"
                 "'abcdefghijklmnopqrstuvwxyz'),'add to bag')]"),
            ],
            "item_wrapper": (
                "xpath", "//div[@class='product-image-wrapper']"
            ),
            "item_action_strategies": [
                ("css",   "a.add-to-cart"),
                ("xpath", ".//a[contains(@href,'add_to_cart')]"),
                ("xpath", ".//a[@data-product-id]"),
                ("xpath",
                 ".//a[contains(translate(.,"
                 "'ABCDEFGHIJKLMNOPQRSTUVWXYZ',"
                 "'abcdefghijklmnopqrstuvwxyz'),'add')]"),
            ],
            "count_key": "cart_count",
        },

        # ── Cart modal ────────────────────────────────────────────
        "continue_shopping": {
            "type":   "modal_dismiss",
            "match":  ["continue shopping", "keep shopping"],
            "choice": "continue",
        },

        "view_cart_modal": {
            "type":   "modal_dismiss",
            "match":  ["view cart", "go to cart",
                       "view cart modal", "view cart in modal"],
            "choice": "view_cart",
            "fallback_strategies": [
                ("xpath", "//a[contains(@href,'view_cart')]"),
                ("xpath",
                 "//a[contains(translate(.,"
                 "'ABCDEFGHIJKLMNOPQRSTUVWXYZ',"
                 "'abcdefghijklmnopqrstuvwxyz'),'cart')]"),
            ],
        },

        # ── Cart management ───────────────────────────────────────
        "remove_from_cart": {
            "type":  "click_strategies",
            "match": ["remove product", "remove item",
                      "delete product", "remove first product",
                      "remove product from cart"],
            "strategies": [
                ("xpath", "//a[@class='cart_quantity_delete']"),
                ("xpath",
                 "//a[contains(@class,'delete') "
                 "or contains(@class,'remove')]"),
                ("xpath",
                 "//button[contains(@class,'delete') "
                 "or contains(@class,'remove')]"),
                ("xpath",
                 "//i[contains(@class,'delete') "
                 "or contains(@class,'remove')]/.."),
            ],
            "after":     "decrement_count",
            "count_key": "cart_count",
        },

        # ── Checkout flow ─────────────────────────────────────────
        "proceed_checkout": {
            "type":                "click_strategies",
            "match":               ["proceed to checkout",
                                    "go to checkout", "checkout"],
            "pre_wait":            3,
            "scroll_before_click": True,
            "clear_modals":        True,
            "checkout_fallback":   True,
            "strategies": [
                ("xpath",
                 "//a[normalize-space(text())='Proceed To Checkout']"),
                ("xpath",
                 "//a[normalize-space(text())='Proceed to Checkout']"),
                ("xpath",
                 "//a[contains(text(),'Proceed To Checkout')]"),
                ("xpath",
                 "//a[contains(text(),'Proceed to Checkout')]"),
                ("xpath",
                 "//a[contains(@href,'/checkout')]"),
                ("xpath",
                 "//div[@class='cart-buttons']//a"),
                ("xpath",
                 "//div[contains(@class,'col-sm-6')]"
                 "//a[contains(@href,'checkout')]"),
                ("xpath",
                 "//a[contains(@class,'checkout') "
                 "and not(contains(@href,'login'))]"),
            ],
            "wait_for_url_change": True,
        },

        "order_comment": {
            "type":        "form_field",
            "match":       ["comment", "message", "order note",
                            "message box", "order comment",
                            "comment box"],
            "field_hints": ["message", "comment", "note",
                            "order_note"],
            "field_type":  "textarea",
            "data_key":    "comment",
        },

        "place_order": {
            "type":                "click_strategies",
            "match":               ["place order", "confirm order"],
            "scroll_before_click": True,
            "clear_modals":        True,
            "strategies": [
                ("xpath",
                 "//a[contains(text(),'Place Order')]"),
                ("xpath",
                 "//button[contains(text(),'Place Order')]"),
                ("xpath", "//a[@href='/payment']"),
                ("xpath",
                 "//a[contains(translate(.,"
                 "'ABCDEFGHIJKLMNOPQRSTUVWXYZ',"
                 "'abcdefghijklmnopqrstuvwxyz'),'place order')]"),
            ],
            "wait_for_url_change": True,
        },

        # ── Payment ───────────────────────────────────────────────
        "card_name": {
            "type":        "form_field",
            "match":       ["card name", "name on card",
                            "cardholder", "card holder"],
            "field_hints": ["name_on_card", "card_name",
                            "cardholder", "name", "holder"],
            "data_key":    "card_name",
        },

        "card_number": {
            "type":        "form_field",
            "match":       ["card number", "credit card",
                            "card no", "card num"],
            "field_hints": ["card_number", "cardnumber",
                            "card", "number", "cc_number",
                            "credit"],
            "data_key":    "card_number",
        },

        "cvc": {
            "type":        "form_field",
            "match":       ["cvc", "cvv", "security code",
                            "card code"],
            "field_hints": ["cvc", "cvv", "security",
                            "cvc_number", "cvv2", "cv2"],
            "data_key":    "cvc",
        },

        "expiry_month": {
            "type":        "form_field",
            "match":       ["expiry month", "exp month",
                            "expiration month"],
            "field_hints": ["expiry_month", "exp_month",
                            "expiry", "exp", "month"],
            "data_key":    "expiry_month",
        },

        "expiry_year": {
            "type":        "form_field",
            "match":       ["expiry year", "exp year",
                            "expiration year"],
            "field_hints": ["expiry_year", "exp_year",
                            "year"],
            "data_key":    "expiry_year",
        },

        "pay_confirm": {
            "type":  "click_strategies",
            "match": [
                "pay and confirm",
                "pay and confirm order",
                "pay now",
                "confirm payment",
                "submit payment",
            ],
            "strategies": [
                ("id",    "pay-button"),
                ("xpath", "//button[@id='pay-button']"),
                ("xpath",
                 "//button[contains(translate(.,"
                 "'ABCDEFGHIJKLMNOPQRSTUVWXYZ',"
                 "'abcdefghijklmnopqrstuvwxyz'),'pay')]"),
                ("xpath",
                 "//input[@type='submit' and contains("
                 "translate(@value,'ABCDEFGHIJKLMNOPQRSTUVWXYZ',"
                 "'abcdefghijklmnopqrstuvwxyz'),'pay')]"),
            ],
        },

        # ── Scroll / Recommended ──────────────────────────────────
        "scroll_to_recommended": {
            "type":          "js_scroll",
            "match":         ["scroll", "recommended items",
                              "scroll to recommended"],
            "scroll_action": "bottom",
            "wait_after":    1.5,
        },

        "add_recommended": {
            "type":  "listing_item_action",
            "match": ["recommended product", "add recommended",
                      "add to cart for recommended"],
            "item_wrapper": (
                "xpath",
                "//div[@class='recommended_items']"
                "//div[@class='product-image-wrapper'] | "
                "//div[contains(@class,'recommended')]"
                "//div[contains(@class,'product')]"
            ),
            "item_action_strategies": [
                ("css",   "a.add-to-cart"),
                ("xpath", ".//a[contains(@href,'add_to_cart')]"),
                ("xpath",
                 ".//a[contains(translate(.,"
                 "'ABCDEFGHIJKLMNOPQRSTUVWXYZ',"
                 "'abcdefghijklmnopqrstuvwxyz'),'add')]"),
            ],
            "count_key": "cart_count",
        },
    },

    # ── Order success keywords ────────────────────────────────────
    "order_success_keywords": [
        "congratulations",
        "order placed",
        "order confirmed",
        "thank you for your order",
        "order successful",
    ],

    "products_page_loaded": ["all products", "women", "category",
                             "brand products", "filter"],

    # ── Product detail URL fragment ───────────────────────────────
    "product_detail_url_fragment": "/product_details/",
}