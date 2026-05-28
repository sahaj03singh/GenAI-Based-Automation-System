import re

TEST_DATA = {
    "email":        "your_amazon_email@example.com",
    "password":     "your_amazon_password",
    "search":       "portable monitor 2k 16 inch",
    "search_bar":   "portable monitor 2k 16 inch",
    "card_name":    "Test User",
    "card_number":  "4111111111111111",
    "cvc":          "123",
    "expiry_month": "12",
    "expiry_year":  "2030",
    "quantity":     "1",
}

FIELD_PATTERNS = {
    r"email|username":              "email",
    r"password":                    "password",
    r"search":                      "search",
    r"card.?name|name.?on.?card":   "card_name",
    r"card.?number|credit.?card":   "card_number",
    r"cvc|cvv":                     "cvc",
    r"expiry.?month|exp.?month":    "expiry_month",
    r"expiry.?year|exp.?year":      "expiry_year",
    r"quantity|qty":                "quantity",
}


def resolve_test_data(field_description, step_value=""):
    if step_value and str(step_value).strip():
        return str(step_value).strip()
    desc = field_description.lower().strip()
    if desc in TEST_DATA:
        return TEST_DATA[desc]
    for pattern, key in FIELD_PATTERNS.items():
        if re.search(pattern, desc):
            return TEST_DATA.get(key, "")
    return ""