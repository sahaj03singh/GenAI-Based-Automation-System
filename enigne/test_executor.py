"""
test_executor.py — Strict-mode test execution engine.

Place this file at: enigne/test_executor.py

Strict pass criteria:
- PASS              : ALL steps passed cleanly, no healing
- PASS_WITH_HEALING : All steps passed but at least one needed healing
- FAIL              : At least one step failed completely

This matches production CI/CD standards where any step-level
instability indicates fragility worth flagging.

NEW (per-test respawn): Each test case now runs in a fresh Chrome
instance. The driver passed in from the pytest fixture is closed
immediately, and a new driver is created/quit per test case.

Why: gives every test a clean cart, clean login session, clean
cookies, and a freshly-dismissed consent popup. Eliminates the
five state-bleed false positives observed in the 50-test audit
(TC37, TC42, TC46, TC49 and the TC29 register-as-existing-user case).

Cost: each spawn/quit adds ~3–4 seconds. On a 50-test run that's
roughly 2–3 extra minutes — acceptable trade for genuine isolation.

NEW: Records each test outcome to cache_manager for the feedback loop.
Future runs use this data to decide whether to regenerate steps.
"""

from utils.actions import execute_step, reset_session
from utils.reporter import clear_logs
from utils.report_builder import generate_html_report
from utils.cache_manager import record_outcome
from utils.driver_factory import create_driver
from configPage.site_config import SITE_CONFIG

BASE_URL = SITE_CONFIG["base_url"]


def _first_failed_step(step_results):
    """Return (1-indexed step number, short reason) of the first failure."""
    for idx, r in enumerate(step_results, start=1):
        if not r.get("passed") and not r.get("healed"):
            step      = r.get("step", {})
            action    = step.get("action", "")
            target    = step.get("target", "")
            reason    = f"{action} → {target} (conf {r.get('confidence', 0):.2f})"
            return idx, reason
    return None, None


def _quit_quietly(driver):
    """Quit a driver; never raise."""
    try:
        driver.quit()
    except Exception:
        pass


def run_tests(driver):
    """
    Run all generated test cases in strict mode, each in a fresh
    Chrome instance.

    The `driver` argument is the one created by the pytest fixture
    in conftest.py. We close it immediately and spawn a new one
    per test case, so each test starts from a guaranteed clean
    browser state (no cookies, no cart, no login session).
    """
    from llm.test_generator import load_generated_steps

    all_tests   = load_generated_steps()
    all_results = []

    if not all_tests:
        print("⚠️ No test cases found in tests_generated/test_steps.json")
        print("   Did you run llm/test_generator.parse_user_stories()?")
        return []

    # The fixture-supplied driver is not used. Close it so we don't
    # have an idle Chrome sitting around eating memory.
    print("🔒 Closing pytest-fixture driver — per-test respawn enabled")
    _quit_quietly(driver)

    for test_index, test in enumerate(all_tests, start=1):
        print(f"\n{'=' * 50}")
        print(f"🚀 Running ({test_index}/{len(all_tests)}): {test['name']}")
        print("=" * 50)

        # ── Spawn a fresh Chrome for this test ───────────────────
        try:
            test_driver = create_driver()
        except Exception as e:
            print(f"❌ Could not start Chrome for this test: {e}")
            # Record as a fail and move on to the next test.
            all_results.append({
                "name":       test["name"],
                "passed":     False,
                "status":     "FAIL",
                "confidence": 0.0,
                "details": {
                    "steps_passed": 0,
                    "steps_failed": 1,
                    "steps_healed": 0,
                    "total_steps":  1,
                },
                "screenshots": [],
                "step_logs": [{
                    "log":        f"[FAIL] driver_create → {e}",
                    "status":     "FAIL",
                    "action":     "driver_create",
                    "target":     "",
                    "confidence": 0.0,
                    "screenshot": None,
                }],
            })
            continue

        # ── Reset framework state for this test ──────────────────
        reset_session()
        clear_logs()

        # Initial navigation — popup wrapper inside the driver handles consent.
        test_driver.get(BASE_URL)

        step_results = []
        screenshots  = []
        step_logs    = []

        # ── Execute each step ────────────────────────────────────
        try:
            for step in test["steps"]:
                result = execute_step(test_driver, step)
                result.setdefault("confidence", 0.0)
                result.setdefault("passed",     False)
                result.setdefault("step",       step)

                step_results.append(result)

                if result.get("healed"):
                    status = "HEALED"
                elif result["passed"]:
                    status = "PASS"
                elif result["confidence"] > 0.4:
                    status = "WARN"
                else:
                    status = "FAIL"

                action     = step.get("action", "")
                target     = step.get("target", "")
                confidence = result["confidence"]
                screenshot = result.get("screenshot")

                step_logs.append({
                    "log": (
                        f"[{status}] {action} → {target} "
                        f"(conf: {round(confidence, 2)})"
                    ),
                    "status":     status,
                    "action":     action,
                    "target":     target,
                    "confidence": confidence,
                    "screenshot": screenshot,
                })

                if screenshot:
                    screenshots.append(screenshot)
        finally:
            # Always close this test's browser before moving on,
            # even if execution raised partway through.
            _quit_quietly(test_driver)

        # ── Per-test summary ─────────────────────────────────────
        total    = len(step_results)
        passed   = sum(1 for r in step_results if r["passed"])
        healed   = sum(1 for r in step_results if r.get("healed"))
        failed   = sum(
            1 for r in step_results
            if not r["passed"] and not r.get("healed")
        )
        avg_conf = (
            sum(r["confidence"] for r in step_results) / total
            if total > 0 else 0
        )

        test_passed = (failed == 0 and healed == 0)

        if failed > 0:
            test_status = "FAIL"
        elif healed > 0:
            test_status = "PASS_WITH_HEALING"
        else:
            test_status = "PASS"

        # ── Record outcome to cache for feedback loop ────────────
        failed_step, failure_reason = (
            _first_failed_step(step_results) if test_status == "FAIL"
            else (None, None)
        )
        try:
            record_outcome(
                test_name      = test["name"],
                outcome        = test_status,
                confidence     = round(avg_conf, 3),
                failed_step    = failed_step,
                failure_reason = failure_reason,
            )
        except Exception as e:
            print(f"[CACHE] ⚠️ outcome recording failed: {e}")

        all_results.append({
            "name":        test["name"],
            "passed":      test_passed,
            "status":      test_status,
            "confidence":  round(avg_conf, 2),
            "details": {
                "steps_passed": passed,
                "steps_failed": failed,
                "steps_healed": healed,
                "total_steps":  total,
            },
            "screenshots": screenshots,
            "step_logs":   step_logs,
        })

        # ── Verbose console summary per test ─────────────────────
        if test_status == "PASS":
            status_icon = "✅ PASSED"
        elif test_status == "PASS_WITH_HEALING":
            status_icon = (
                f"⚠️  PASSED WITH HEALING ({healed} healed steps)"
            )
        else:
            status_icon = f"❌ FAILED ({failed} failed steps)"

        print(
            f"\n{status_icon} — "
            f"{passed}/{total} steps passed, "
            f"{healed} healed, {failed} failed "
            f"(avg confidence: {round(avg_conf * 100)}%)"
        )

    # ── Build HTML report ────────────────────────────────────────
    generate_html_report(all_results)

    # ── Final overall summary ────────────────────────────────────
    total_tests       = len(all_results)
    truly_passed      = sum(
        1 for r in all_results if r["status"] == "PASS"
    )
    passed_w_healing  = sum(
        1 for r in all_results
        if r["status"] == "PASS_WITH_HEALING"
    )
    failed_tests      = sum(
        1 for r in all_results if r["status"] == "FAIL"
    )

    avg_overall = (
        sum(r["confidence"] for r in all_results) / total_tests
        if total_tests else 0
    )

    print(f"\n{'=' * 60}")
    print(f"📊 FINAL TEST SUMMARY (STRICT MODE)")
    print(f"{'=' * 60}")
    print(f"✅ Clean Pass:        {truly_passed}/{total_tests}")
    print(f"⚠️  Pass with Healing: {passed_w_healing}/{total_tests}")
    print(f"❌ Failed:            {failed_tests}/{total_tests}")
    print(f"📈 Avg Confidence:    {round(avg_overall, 2)}")
    print(f"{'=' * 60}")

    return all_results