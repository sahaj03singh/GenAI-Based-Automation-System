"""
test_generator.py — LLM-driven user story to step converter.

Place this file at: llm/test_generator.py

Changes vs the previous version:
1. Per-test-case caching (not whole-file caching) via cache_manager
2. Feedback-enriched prompts when a test case is suspect
3. Single parse_user_stories() — duplicate function removed
4. Tracks LLM cost savings via cache hits
"""

from openai import OpenAI
import json
import re
import os

from utils.step_cleaner import clean_steps, remove_repetition
from utils.cache_manager import (
    compute_semantic_hash,
    should_regenerate,
    get_failure_context,
    record_generation,
)
from configPage.site_config import SITE_CONFIG

GENERATED_STEPS_FILE = "tests_generated/test_steps.json"

if not os.getenv("OPENAI_API_KEY"):
    raise ValueError("❌ OPENAI_API_KEY not set")

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


# ──────────────────────────────────────────────────────────────────
#  GENERIC HELPERS — read from site_config, not hardcoded
# ──────────────────────────────────────────────────────────────────

def _build_intent_keyword_map():
    """
    Build a flat map: keyword -> (action, target) tuples
    by reading SITE_CONFIG.intent_actions.
    Site-specific knowledge stays in site_config.py only.
    """
    intents = SITE_CONFIG.get("intent_actions", {})
    keyword_map = []

    for intent_key, intent_cfg in intents.items():
        intent_type = intent_cfg.get("type", "")

        if intent_type == "form_field":
            default_action = "type"
        elif intent_type in ("js_scroll",):
            default_action = "scroll"
        else:
            default_action = "click"

        match_list = intent_cfg.get("match", [])
        if not match_list:
            continue
        target_phrase = match_list[0]

        for kw in match_list:
            keyword_map.append((kw.lower(), target_phrase, default_action))

    sidebar = SITE_CONFIG.get("sidebar", {})
    for sidebar_key in sidebar.keys():
        keyword_map.append((sidebar_key.lower(), sidebar_key, "click"))

    nav_paths = SITE_CONFIG.get("navigation_paths", {})
    for nav_key in nav_paths.keys():
        keyword_map.append((nav_key.lower(), nav_key, "navigate"))

    keyword_map.sort(key=lambda x: -len(x[0]))
    return keyword_map


def _build_verify_keyword_map():
    """List of verify keywords from site_config.verify_keywords."""
    verify_kws = SITE_CONFIG.get("verify_keywords", {})
    return sorted(
        [k.lower() for k in verify_kws.keys()],
        key=lambda x: -len(x)
    )


_INTENT_KEYWORDS = _build_intent_keyword_map()
_VERIFY_KEYWORDS = _build_verify_keyword_map()


def _extract_number_from_text(text):
    m = re.search(r"\d+(?:\.\d+)?", text)
    return m.group(0) if m else ""


def _looks_like_value_for_target(target_phrase, text):
    """
    Decide whether this step needs a value extracted from text.
    For price/quantity/size/storage etc.
    """
    t = target_phrase.lower()
    if any(x in t for x in [
        "price less than", "price more than", "price greater",
        "price under", "price above", "below", "more than", "less than",
        "quantity", "qty", "set quantity",
    ]):
        return _extract_number_from_text(text)

    if "size" in t:
        m = re.search(
            r"\b(XS|S|M|L|XL|XXL|XXXL|small|medium|large|"
            r"extra small|extra large|\d{1,3})\b",
            text, re.IGNORECASE
        )
        if m:
            return m.group(0)

    if "colour" in t or "color" in t:
        m = re.search(
            r"\b(black|white|red|blue|green|silver|gold|"
            r"yellow|pink|purple|grey|gray|brown|orange)\b",
            text, re.IGNORECASE
        )
        if m:
            return m.group(0)

    if "storage" in t:
        m = re.search(
            r"\b(\d{2,4}\s?(?:GB|TB|MB))\b",
            text, re.IGNORECASE
        )
        if m:
            return m.group(0)

    return ""


# ──────────────────────────────────────────────────────────────────
#  PROMPT BUILDERS — generate prompt dynamically from site_config
# ──────────────────────────────────────────────────────────────────

def _site_has_intent(keyword_substrings):
    intents = SITE_CONFIG.get("intent_actions", {})
    for intent_cfg in intents.values():
        for kw in intent_cfg.get("match", []):
            kw_lower = kw.lower()
            if any(sub in kw_lower for sub in keyword_substrings):
                return True
    return False


def _build_login_section(login_requested):
    if not login_requested:
        return (
            "DO NOT include any login or signup steps in the output. "
            "The user story does not mention login.\n"
            "Start the test directly from: navigate -> homepage\n"
        )

    if not _site_has_intent(["login", "sign in", "email", "password"]):
        return ""

    return (
        "LOGIN FLOW (include these steps in this order, "
        "before the test actions):\n"
        "1. navigate -> homepage\n"
        "2. verify  -> homepage loaded\n"
        "3. click   -> login\n"
        "4. type    -> email\n"
        "5. type    -> password\n"
        "6. click   -> login button\n"
        "7. verify  -> logged in\n"
    )


def _build_checkout_section():
    has_checkout = _site_has_intent([
        "proceed to checkout", "place order",
        "pay and confirm", "pay now",
    ])
    if not has_checkout:
        return ""

    sequence = []
    intents = SITE_CONFIG.get("intent_actions", {})

    ordered_step_substrings = [
        ("click",  ["proceed to checkout", "checkout"]),
        ("type",   ["message box", "comment", "order note"]),
        ("click",  ["place order", "confirm order"]),
        ("type",   ["card name", "name on card"]),
        ("type",   ["card number", "credit card"]),
        ("type",   ["cvc", "cvv"]),
        ("type",   ["expiry month", "exp month"]),
        ("type",   ["expiry year", "exp year"]),
        ("click",  ["pay and confirm", "pay now",
                    "submit payment"]),
        ("verify", ["order confirmed"]),
    ]

    step_letter = ord('A')
    for action, subs in ordered_step_substrings:
        target = None
        for intent_cfg in intents.values():
            for kw in intent_cfg.get("match", []):
                if any(sub in kw.lower() for sub in subs):
                    target = kw
                    break
            if target:
                break

        if action == "verify":
            for vkey in SITE_CONFIG.get("verify_keywords", {}).keys():
                if any(sub in vkey.lower() for sub in subs):
                    target = vkey
                    break

        if target:
            sequence.append(
                f"Step {chr(step_letter)}: "
                f"{action} -> {target}"
            )
            step_letter += 1

    if not sequence:
        return ""

    return (
        "CHECKOUT FLOW (only if the test case mentions checkout / "
        "payment / place order — follow this order strictly, "
        "never skip a step):\n"
        + "\n".join(sequence)
        + "\n"
    )


def _build_action_vocabulary():
    intents = SITE_CONFIG.get("intent_actions", {})
    examples = []

    for intent_cfg in intents.values():
        intent_type = intent_cfg.get("type", "")
        match_list  = intent_cfg.get("match", [])
        if not match_list:
            continue

        target = match_list[0]

        if intent_type == "form_field":
            examples.append(f"  type -> {target}")
        elif intent_type in ("js_scroll",):
            examples.append(f"  scroll -> {target}")
        else:
            examples.append(f"  click -> {target}")

    for vkey in SITE_CONFIG.get("verify_keywords", {}).keys():
        examples.append(f"  verify -> {vkey}")

    return "\n".join(examples[:60])


# ──────────────────────────────────────────────────────────────────
#  CORE FUNCTIONS
# ──────────────────────────────────────────────────────────────────

def extract_test_cases(file_path):
    """
    Parse userstories.txt into a list of test cases.
    Each test case gets a 'raw_text' field used for semantic hashing.
    """
    with open(file_path) as f:
        content = f.read()

    test_cases = []
    raw_cases = re.split(r"TEST CASE \d+:", content)[1:]

    for case in raw_cases:
        lines = case.strip().split("\n")
        title = lines[0].strip()
        steps = []

        for line in lines:
            stripped = line.strip()
            if re.match(r"^STEP\s+\d+", stripped, re.IGNORECASE):
                parts = stripped.split(":", 1)
                if len(parts) > 1:
                    steps.append(parts[1].strip())

        if steps:
            # raw_text is title + step lines — input to semantic hash
            raw_text = title + "\n" + "\n".join(steps)
            test_cases.append({
                "name":     title,
                "steps":    steps,
                "raw_text": raw_text,
            })

    return test_cases


def _is_login_requested():
    try:
        with open("userstories.txt") as f:
            story = f.read().lower()
        return any(
            kw in story for kw in [
                "login", "sign in", "sign-in",
                "enter email", "enter password",
                "click login", "signup",
            ]
        )
    except Exception:
        return True


def normalize_steps(raw_steps):
    """
    Convert raw step text or LLM-output dicts into structured
    {action, target, value} dicts.
    """
    normalized = []

    for step in raw_steps:
        if isinstance(step, str):
            text = step.lower().strip()
            matched = False

            for keyword, target_phrase, default_action in _INTENT_KEYWORDS:
                if keyword in text:
                    value = _looks_like_value_for_target(
                        target_phrase, text
                    )
                    normalized.append({
                        "action": default_action,
                        "target": target_phrase,
                        "value":  value,
                    })
                    matched = True
                    break

            if not matched:
                for vkw in _VERIFY_KEYWORDS:
                    if vkw in text:
                        normalized.append({
                            "action": "verify",
                            "target": vkw,
                            "value":  "",
                        })
                        matched = True
                        break

            if not matched:
                normalized.append({
                    "action": "verify",
                    "target": text[:60],
                    "value":  "",
                })
            continue

        # Dict input from LLM
        action = step.get("action", "").lower()
        target = step.get("target", "").lower()
        value  = step.get("value", "")

        if action not in ["click", "type", "verify",
                          "navigate", "scroll"]:
            action = "verify"

        if action == "click" and target == "search":
            target = "search button"

        if action == "type" and target in [
            "cart", "checkout", "add to cart"
        ]:
            action = "click"

        normalized.append({
            "action": action,
            "target": target,
            "value":  value,
        })

    return normalized


def validate_and_fix_flow(steps):
    LOGIN_TARGETS = set()
    intents = SITE_CONFIG.get("intent_actions", {})
    for intent_cfg in intents.values():
        for kw in intent_cfg.get("match", []):
            kw_lower = kw.lower()
            if any(s in kw_lower for s in [
                "login", "sign in", "email",
                "password", "signup",
            ]):
                LOGIN_TARGETS.add(kw_lower)

    REQUIRED_BEFORE_PAYMENT = []
    standard_checkout = [
        ("click", ["proceed to checkout"]),
        ("type",  ["message box", "comment"]),
        ("click", ["place order"]),
    ]
    for action, subs in standard_checkout:
        for intent_cfg in intents.values():
            for kw in intent_cfg.get("match", []):
                if any(s in kw.lower() for s in subs):
                    REQUIRED_BEFORE_PAYMENT.append({
                        "action": action,
                        "target": kw,
                        "value":  "",
                    })
                    break
            else:
                continue
            break

    PAYMENT_TRIGGERS = set()
    for intent_cfg in intents.values():
        for kw in intent_cfg.get("match", []):
            kw_lower = kw.lower()
            if any(s in kw_lower for s in [
                "card name", "card number", "cvc", "cvv",
                "expiry", "pay and confirm", "pay now",
                "confirm payment",
            ]):
                PAYMENT_TRIGGERS.add(kw_lower)

    login_requested = _is_login_requested()

    fixed = []
    targets_seen = set()

    for step in steps:
        target = step.get("target", "").lower().strip()

        if not login_requested and target in LOGIN_TARGETS:
            print(f"[FLOW FIX] Removing unwanted login step: '{target}'")
            continue

        if target in PAYMENT_TRIGGERS and REQUIRED_BEFORE_PAYMENT:
            checkout_target = REQUIRED_BEFORE_PAYMENT[0]["target"]
            if checkout_target not in targets_seen:
                print(
                    f"[FLOW FIX] Inserting missing checkout steps "
                    f"before '{target}'"
                )
                for required_step in REQUIRED_BEFORE_PAYMENT:
                    if required_step["target"] not in targets_seen:
                        fixed.append(required_step.copy())
                        targets_seen.add(required_step["target"])

        fixed.append(step)
        targets_seen.add(target)

    return fixed


def convert_steps_with_llm(test_case, failure_context: str = ""):
    """
    Build the LLM prompt from site_config and any failure feedback,
    send it, and normalise the response.

    Args:
        test_case: dict with 'name' and 'steps' keys
        failure_context: optional string with previous failure details,
                        embedded into the prompt to inform regeneration.
    """
    steps_text      = "\n".join(test_case["steps"])
    login_requested = _is_login_requested()

    login_section      = _build_login_section(login_requested)
    checkout_section   = _build_checkout_section()
    action_vocabulary  = _build_action_vocabulary()

    # Feedback section — only included if there's prior failure data
    feedback_section = ""
    if failure_context:
        feedback_section = (
            "\n=== FEEDBACK FROM PREVIOUS RUNS ===\n"
            f"{failure_context}\n"
            "=== END FEEDBACK ===\n"
        )

    prompt = f"""
You are a test automation engineer converting plain English test
steps into a structured JSON array for browser automation.
{feedback_section}
{login_section}
{checkout_section}
SUPPORTED ACTIONS AND TARGETS (use phrases close to these):
{action_vocabulary}

GENERAL RULES:
- Convert ONLY what the test case steps describe
- DO NOT add steps that are not in the test case
- DO NOT hallucinate steps like "non-deal price" or
  "apply filter" if not in the test case
- Only use these actions: click, type, verify, navigate, scroll
- For numerical constraints (price, quantity), put the number in
  the "value" field, e.g.
    {{"action": "click",
     "target": "product with price less than",
     "value": "500"}}
- For size/colour/storage selection, put the variant in "value":
    {{"action": "click", "target": "select size", "value": "M"}}

Return ONLY a valid JSON array. No explanation, no markdown:
[
  {{"action": "navigate", "target": "homepage", "value": ""}},
  ...
]

Test case steps to convert:
{steps_text}
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=2000,
    )

    content = response.choices[0].message.content
    content = content.replace("```json", "").replace("```", "").strip()

    try:
        raw = json.loads(content)
        if not isinstance(raw, list):
            print(f"⚠️ LLM returned non-list: {type(raw)}")
            raw = []
    except json.JSONDecodeError as e:
        print(f"⚠️ JSON parse failed: {e}\nRaw: {content[:300]}")
        raw = []

    steps = normalize_steps(raw)
    steps = clean_steps(steps)
    steps = remove_repetition(steps)
    steps = validate_and_fix_flow(steps)

    return steps


# ──────────────────────────────────────────────────────────────────
#  PARSE — single source of truth, with per-test-case caching
# ──────────────────────────────────────────────────────────────────

def parse_user_stories(file_path):
    """
    Convert userstories.txt into structured test steps.

    Per-test-case caching:
    - Each test case is hashed semantically. If the hash is unchanged
      AND the cached entry is healthy, the cached steps are reused.
    - Otherwise the LLM is called to regenerate just that test case.
    - Failed/suspect test cases are regenerated with feedback context.

    The output JSON file always reflects the FULL test suite — cached
    test cases are merged with newly-generated ones.
    """
    test_cases = extract_test_cases(file_path)

    # Load existing cached steps if available
    existing = {}
    if os.path.exists(GENERATED_STEPS_FILE):
        try:
            with open(GENERATED_STEPS_FILE, "r") as f:
                for entry in json.load(f):
                    existing[entry["name"]] = entry.get("steps", [])
        except Exception as e:
            print(f"⚠️ Could not read existing steps: {e}")

    structured_tests = []
    cache_hits = 0
    regen_count = 0

    print(f"\n{'─' * 50}")
    print(f"Cache decisions ({len(test_cases)} test case(s))")
    print("─" * 50)

    for case in test_cases:
        name = case["name"]
        semantic_hash = compute_semantic_hash(case["raw_text"])

        # Decide whether to regenerate
        regenerate, reason = should_regenerate(name, semantic_hash)

        # Even if the cache says HIT, we need the steps to exist
        if not regenerate and name not in existing:
            regenerate = True
            reason = "MISS (cache marked HIT but JSON entry missing)"

        if not regenerate:
            print(f"  [{name}] {reason}")
            structured_tests.append({
                "name":  name,
                "steps": existing[name],
            })
            cache_hits += 1
            continue

        # Regenerate via LLM
        print(f"  [{name}] {reason} — regenerating")
        failure_context = get_failure_context(name)
        if failure_context:
            print(f"    [feedback] {len(failure_context.splitlines())} "
                  f"lines of failure context included in prompt")

        steps = convert_steps_with_llm(case, failure_context=failure_context)
        print(f"    ✅ {len(steps)} steps generated")

        structured_tests.append({
            "name":  name,
            "steps": steps,
        })

        # Record in cache
        record_generation(name, semantic_hash)
        regen_count += 1

    # ── Cost-savings summary (rough) ──────────────────────────────
    # Each LLM call is ~1500 tokens at ~£0.005/test case for gpt-4o-mini.
    cost_saved = cache_hits * 0.005
    print("─" * 50)
    print(
        f"📦 Cache summary: {cache_hits} hit(s), {regen_count} regenerated"
    )
    if cache_hits > 0:
        print(f"💰 Estimated cost saved this run: ~£{cost_saved:.3f}")
    print("─" * 50)

    # Write merged result
    os.makedirs("tests_generated", exist_ok=True)
    with open(GENERATED_STEPS_FILE, "w") as f:
        json.dump(structured_tests, f, indent=2)

    return structured_tests


def load_generated_steps():
    if not os.path.exists(GENERATED_STEPS_FILE):
        return []
    with open(GENERATED_STEPS_FILE, "r") as f:
        return json.load(f)