"""
test_generator.py — LLM-driven user story to step converter.

Place this file at: llm/test_generator.py

This module is fully site-agnostic. All site-specific knowledge
(login flow shape, checkout flow shape, domain value-extraction
patterns) lives in configPage/site_config.py and is read at runtime
from SITE_CONFIG. A site that doesn't have e-commerce / login /
checkout simply omits those keys and the generator skips them
gracefully.

Changes log:
1. Per-test-case caching via cache_manager (Apr-May 2026)
2. Feedback-enriched prompts on regeneration (May 2026)
3. (Jun 2026) Hardcoded e-commerce assumptions moved to site_config:
   - login flow now reads SITE_CONFIG['login_flow']
   - checkout flow now reads SITE_CONFIG['checkout_flow']
   - value extraction now reads SITE_CONFIG['value_patterns']
4. (Jun 2026) LLM prompt rewritten with strict target-preservation
   rules; temperature lowered to 0 for deterministic output.
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

    Reads SITE_CONFIG['value_patterns'] which is a dict of:
       {
         "pattern_name": {
            "target_substrings": [...],
            "regex": r"..."
         },
         ...
       }

    For each pattern, if the target_phrase contains any of the
    pattern's target_substrings, the pattern's regex is run against
    the text. The first match is returned.

    If value_patterns is empty (e.g. a non-e-commerce site), a
    built-in numeric fallback still works for any target.
    """
    t = target_phrase.lower()
    value_patterns = SITE_CONFIG.get("value_patterns", {})

    for pattern_name, pattern_cfg in value_patterns.items():
        substrings = pattern_cfg.get("target_substrings", [])
        regex_str  = pattern_cfg.get("regex", "")
        if not substrings or not regex_str:
            continue
        if any(sub in t for sub in substrings):
            m = re.search(regex_str, text, re.IGNORECASE)
            if m:
                return m.group(0)

    # No site pattern matched. We don't second-guess by extracting
    # a number — that would surprise users with target phrases that
    # happen to contain digits. Return empty.
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
    """
    Build the LOGIN FLOW section of the LLM prompt.

    Reads SITE_CONFIG['login_flow'] — a list of step dicts. If the
    site doesn't define one (or it's empty), no login section is
    included and the LLM won't synthesise login steps.

    When login_requested is False, an explicit "do not include
    login" instruction is returned regardless of site config.
    """
    if not login_requested:
        return (
            "DO NOT include any login or signup steps in the output. "
            "The user story does not mention login.\n"
            "Start the test directly from: navigate -> homepage\n"
        )

    login_flow = SITE_CONFIG.get("login_flow", [])
    if not login_flow:
        # Site has no login flow defined — nothing to synthesise.
        return ""

    lines = []
    for i, step in enumerate(login_flow, start=1):
        action = step.get("action", "")
        target = step.get("target", "")
        lines.append(f"{i}. {action:8s} -> {target}")

    return (
        "LOGIN FLOW (include these steps in this order, before the "
        "test actions):\n"
        + "\n".join(lines)
        + "\n"
    )


def _build_checkout_section():
    """
    Build the CHECKOUT FLOW section of the LLM prompt.

    Reads SITE_CONFIG['checkout_flow'] — a list of
    {action, target_keywords} descriptors. For each descriptor, we
    look up an intent in intent_actions whose match list contains
    any of the target_keywords, and use that intent's first match
    phrase as the actual target.

    If the site has no checkout_flow, or none of its descriptors
    resolve to a real intent, no checkout section is added.
    """
    checkout_flow = SITE_CONFIG.get("checkout_flow", [])
    if not checkout_flow:
        return ""

    intents       = SITE_CONFIG.get("intent_actions", {})
    verify_kws    = SITE_CONFIG.get("verify_keywords", {})

    sequence = []
    step_letter = ord('A')

    for descriptor in checkout_flow:
        action     = descriptor.get("action", "")
        target_kws = descriptor.get("target_keywords", [])
        target     = None

        if action == "verify":
            # Verify targets come from verify_keywords, not intents.
            for vkey in verify_kws.keys():
                if any(sub in vkey.lower() for sub in target_kws):
                    target = vkey
                    break
        else:
            # Click/type targets come from intent_actions.
            for intent_cfg in intents.values():
                for kw in intent_cfg.get("match", []):
                    if any(sub in kw.lower() for sub in target_kws):
                        target = kw
                        break
                if target:
                    break

        if target:
            sequence.append(
                f"Step {chr(step_letter)}: {action} -> {target}"
            )
            step_letter += 1

    if not sequence:
        # Site declared a checkout flow but none of its descriptors
        # resolved to real intents — skip the section silently.
        return ""

    return (
        "CHECKOUT FLOW (only if the test case mentions checkout / "
        "payment / place order — follow this order strictly, never "
        "skip a step):\n"
        + "\n".join(sequence)
        + "\n"
    )


def _build_action_vocabulary():
    """
    Build a reference list of all action+target combinations the
    site supports, for the LLM prompt. Used as a reference only —
    the LLM is explicitly told NOT to constrain itself to this list.
    """
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
            raw_text = title + "\n" + "\n".join(steps)
            test_cases.append({
                "name":     title,
                "steps":    steps,
                "raw_text": raw_text,
            })

    return test_cases


def _is_login_requested(test_case=None):
    """
    Decide whether the LLM prompt should include the login_flow.

    Reads the current TEST CASE's name + step text (not the whole
    userstories.txt file). Previous version read the whole file,
    which meant ANY test mentioning login caused EVERY test to get
    the login flow prepended — major source of false failures.

    Args:
        test_case: dict with 'name' and 'steps' keys. If None,
                   conservatively returns True (preserves old
                   behaviour for any caller that hasn't been
                   updated yet).
    """
    if test_case is None:
        return True

    text_parts = [test_case.get("name", "")]
    text_parts.extend(test_case.get("steps", []))
    text = " ".join(text_parts).lower()

    return any(
        kw in text for kw in [
            "login", "sign in", "sign-in",
            "enter email", "enter password",
            "click login", "signup",
            # NOTE: deliberately NOT including "email" or "password"
            # alone — many forms have email/password fields without
            # being a login (e.g. subscribe, contact, register).
        ]
    )

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

    login_requested = _is_login_requested(None)

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

    Prompt design notes (Jun 2026 rewrite):
      - Temperature is 0 — we want deterministic output, not creativity.
      - The vocabulary list is shown only as a reference for what
        action verbs exist (click / type / verify / scroll / navigate).
      - The LLM is explicitly told NOT to substitute targets. The
        target field must come from the user-story step text, even
        if it doesn't appear in the vocabulary list.
      - Without this discipline, the LLM "helpfully corrects" a step
        like 'Enter subscription email' to 'type -> search bar',
        which silently breaks any test using a custom intent
        (TC26 subscribe, TC27 contact, TC31 invalid password, etc.)
    """
    steps_text      = "\n".join(test_case["steps"])
    login_requested = _is_login_requested(test_case)

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
You convert plain English test steps into a structured JSON array
for browser automation. The output is consumed by a deterministic
matcher — not by a human reader — so accuracy of the `target` field
matters more than natural language.
{feedback_section}
{login_section}
{checkout_section}

============================================================
CRITICAL RULES — read carefully, these are not optional
============================================================

RULE 1: PRESERVE THE TARGET TEXT FROM THE USER STORY.
    Do NOT substitute targets. If the user step says
    'Enter contact name', the JSON target MUST be 'contact name'
    (or similar) — NOT 'search bar', NOT 'email field',
    NOT 'name field'.

    Examples of correct preservation:
      User step: "Enter subscription email"
        → {{"action":"type","target":"subscription email","value":""}}
      User step: "Enter invalid login password"
        → {{"action":"type","target":"invalid login password","value":""}}
      User step: "Verify recommended items section visible"
        → {{"action":"verify","target":"recommended items section visible","value":""}}
      User step: "Click remove cart item"
        → {{"action":"click","target":"remove cart item","value":""}}

    Examples of WRONG substitution (do not do this):
      User step: "Enter contact name"
        ✗ {{"action":"type","target":"search bar"}}  ← WRONG
        ✗ {{"action":"type","target":"name"}}        ← WRONG (too generic)
        ✓ {{"action":"type","target":"contact name"}} ← CORRECT
      User step: "Verify login error visible"
        ✗ {{"action":"verify","target":"search results visible"}}  ← WRONG
        ✓ {{"action":"verify","target":"login error visible"}}      ← CORRECT

RULE 2: PRESERVE THE VERB-TO-ACTION MAPPING.
    "Open" / "Navigate to" / "Go to" → action: "navigate"
    "Click" / "Press" / "Tap" → action: "click"
    "Enter" / "Type" / "Fill in" / "Set" → action: "type"
    "Verify" / "Check" / "Assert" / "Confirm" → action: "verify"
    "Scroll" → action: "scroll"

RULE 3: EXTRACT NUMBERS INTO `value`, NOT TARGET.
    "Select the product with price less than 500"
      → {{"action":"click","target":"product with price less than","value":"500"}}
    "Set quantity to 3"
      → {{"action":"type","target":"quantity","value":"3"}}

RULE 4: ONE USER STEP = EXACTLY ONE JSON STEP.
    Do NOT split one user step into multiple JSON steps.
    Do NOT merge two user steps into one.
    Do NOT add steps the user did not write.
    Do NOT remove steps the user did write.
    If the user gave N steps, return N steps (plus the login
    flow above if applicable).

RULE 5: VOCABULARY LIST IS A REFERENCE, NOT A CONSTRAINT.
    The list below shows what action types exist and gives example
    target phrases. Your job is NOT to match against this list —
    your job is to faithfully translate the user's step text into
    structured form. Custom target phrases not in this list are
    expected and correct.

============================================================

ACTION VOCABULARY REFERENCE (action types only — target text
should come from the user story, even if it doesn't appear here):
{action_vocabulary}

============================================================

Return ONLY a valid JSON array. No explanation, no markdown fence,
no preamble. Start the response with '[' and end with ']'.

Test case steps to convert (one JSON step per line below):
{steps_text}
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=2000,
        temperature=0,   # deterministic; no creativity wanted
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

        regenerate, reason = should_regenerate(name, semantic_hash)

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

        record_generation(name, semantic_hash)
        regen_count += 1

    cost_saved = cache_hits * 0.005
    print("─" * 50)
    print(
        f"📦 Cache summary: {cache_hits} hit(s), {regen_count} regenerated"
    )
    if cache_hits > 0:
        print(f"💰 Estimated cost saved this run: ~£{cost_saved:.3f}")
    print("─" * 50)

    os.makedirs("tests_generated", exist_ok=True)
    with open(GENERATED_STEPS_FILE, "w") as f:
        json.dump(structured_tests, f, indent=2)

    return structured_tests


def load_generated_steps():
    if not os.path.exists(GENERATED_STEPS_FILE):
        return []
    with open(GENERATED_STEPS_FILE, "r") as f:
        return json.load(f)