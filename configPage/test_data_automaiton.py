FIELD_PATTERNS = {
    "email":        ["email", "e-mail", "username", "user name", "user id"],
    "password":     ["password", "pass", "secret", "pwd"],
    "card_name":    ["card name", "name on card", "cardholder", "card holder"],
    "card_number":  ["card number", "credit card", "card no", "card num"],
    "cvc":          ["cvc", "cvv", "security code", "card code"],
    "expiry_month": ["expiry month", "exp month"],
    "expiry_year":  ["expiry year", "exp year"],
    "expiry":       ["expiry", "expiration"],
    "name":         ["full name", "your name", "billing name"],
    "address":      ["address", "street", "billing address"],
    "search":       ["search", "keyword", "query"],
    "comment":      ["comment", "message", "order note", "message box"],
    "quantity":     ["quantity", "qty", "amount", "how many"],
}

TEST_DATA = {
    "email":        "demotest1502@test.com",
    "password":     "test@123",
    "card_name":    "Test User",
    "card_number":  "4111111111111111",
    "cvc":          "123",
    "expiry_month": "12",
    "expiry_year":  "2030",
    "expiry":       "12/2030",
    "name":         "Test User",
    "address":      "123 Test Street",
    "search":       "tshirt",
    "comment":      "Automated test order - please ignore",
    "quantity":     "2",
}


def resolve_test_data(description, value=""):
    if value:
        return value

    desc = description.lower().strip()

    if desc in TEST_DATA:
        return TEST_DATA[desc]

    for field, patterns in FIELD_PATTERNS.items():
        if any(p in desc for p in patterns):
            return TEST_DATA.get(field, "test123")

    return "test123"