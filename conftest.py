"""
conftest.py — pytest fixtures + session lifecycle hooks.

Driver creation is delegated to utils.driver_factory.create_driver()
so the same Chrome options are used by:
  - this fixture (legacy — for any tests that still take a `driver`
    parameter)
  - the per-test respawn loop in enigne/test_executor.py
  - the parametrised test runner in tests_generated/test_auto.py

Phase 1 of parallel execution:
  - test_auto.py is parametrised so each test case is its own
    pytest test. Each test calls run_single_test() and stashes
    its result on `request.session._aggregated_results`.
  - The pytest_sessionfinish hook below aggregates all results
    into the final HTML report and console summary, mirroring
    what run_tests() used to print at the end.
"""

import pytest
from utils.driver_factory import create_driver
from utils.report_builder import generate_html_report


# ──────────────────────────────────────────────────────────────────
#  Driver fixture (legacy — most tests now create their own)
# ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope="function")
def driver(request):
    """
    Single Chrome driver for any test that takes a `driver` parameter.
    The new parametrised entry point in test_auto.py does NOT use
    this fixture (it creates its own driver per test) — this is kept
    for backward compatibility with the legacy test_run signature.
    """
    is_headless = request.config.getoption("--headless", default=False)
    driver = create_driver(headless=is_headless)
    yield driver
    try:
        driver.quit()
    except Exception:
        pass


# ──────────────────────────────────────────────────────────────────
#  CLI options
# ──────────────────────────────────────────────────────────────────

def pytest_addoption(parser):
    parser.addoption(
        "--headless",
        action="store_true",
        default=False,
        help="Run Chrome in headless mode",
    )


# ──────────────────────────────────────────────────────────────────
#  Session-level result aggregation
# ──────────────────────────────────────────────────────────────────
#
# The parametrised test in test_auto.py stashes per-test result
# dicts on `session._aggregated_results`. After all tests finish,
# this hook builds the HTML report and prints the final summary.
# Works in both sequential and parallel (xdist) modes — parallel
# workers each populate their own session; xdist aggregates at end.

def pytest_sessionfinish(session, exitstatus):
    """
    Build the final HTML report + print the strict-mode summary.

    Called once per pytest session, after all tests (including
    parallel workers) have finished.
    """
    results = getattr(session, "_aggregated_results", [])

    if not results:
        # Nothing to report — probably a collection error or the
        # legacy test_run path (which builds its own report internally).
        return

    # ── Build HTML report ────────────────────────────────────────
    try:
        generate_html_report(results)
    except Exception as e:
        print(f"[REPORT] ⚠️ HTML report generation failed: {e}")

    # ── Final overall summary ────────────────────────────────────
    total = len(results)
    truly_passed = sum(
        1 for r in results if r["status"] == "PASS"
    )
    passed_w_healing = sum(
        1 for r in results if r["status"] == "PASS_WITH_HEALING"
    )
    failed_tests = sum(
        1 for r in results if r["status"] == "FAIL"
    )

    avg_overall = (
        sum(r["confidence"] for r in results) / total
        if total else 0
    )

    print(f"\n{'=' * 60}")
    print(f"📊 FINAL TEST SUMMARY (STRICT MODE)")
    print(f"{'=' * 60}")
    print(f"✅ Clean Pass:        {truly_passed}/{total}")
    print(f"⚠️  Pass with Healing: {passed_w_healing}/{total}")
    print(f"❌ Failed:            {failed_tests}/{total}")
    print(f"📈 Avg Confidence:    {round(avg_overall, 2)}")
    print(f"{'=' * 60}")