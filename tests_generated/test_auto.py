"""
tests_generated/test_auto.py — pytest entry point.

Phase 1 refactor: each test case is now a separately-collected
pytest test (via @pytest.mark.parametrize). This unlocks parallel
execution via pytest-xdist (`pytest -n 4 ...`).

Before this refactor, the entire suite was one `test_run` function
that looped over 49 cases internally — invisible to pytest's
collector and impossible to parallelise.

How it works:
  1. At module load (BEFORE any tests run), userstories.txt is
     parsed and steps are generated/regenerated as needed. This
     happens ONCE per pytest invocation, so all workers see the
     same generated_tests.py / test_steps.json.
  2. ALL_TESTS is populated with the full list of test cases.
  3. The parametrised function `test_case_runs` is collected as
     49 separate tests by pytest.
  4. Each test calls `run_single_test()` which spawns its own
     Chrome and returns a result dict.
  5. Result dicts are stashed on the pytest session for the
     report-builder hook in conftest.py to aggregate at the end.
"""

import os
import sys

sys.path.insert(
    0,
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)

import pytest

from llm.test_generator import parse_user_stories, load_generated_steps
from utils.script_generator import generate_python_tests
from enigne.test_executor import run_single_test


# ──────────────────────────────────────────────────────────────────
#  Generate steps ONCE at module load (not per-test)
# ──────────────────────────────────────────────────────────────────
# This runs when pytest collects this module — exactly once, before
# any test runs and before parallel workers fan out.
# Each parallel worker imports this module separately, but the
# parse_user_stories() call is idempotent (cache hits when nothing
# has changed) so workers don't all hammer the LLM.

parse_user_stories("userstories.txt")
generate_python_tests()
ALL_TESTS = load_generated_steps()


# ──────────────────────────────────────────────────────────────────
#  Parametrised test function — one pytest test per test case
# ──────────────────────────────────────────────────────────────────

def _test_id(test_case):
    """Use the test case name as the pytest test ID."""
    return test_case.get("name", "unknown")


@pytest.mark.parametrize(
    "test_case",
    ALL_TESTS,
    ids=[_test_id(t) for t in ALL_TESTS],
)
def test_case_runs(test_case, request):
    """
    Run a single test case in a fresh Chrome instance.

    The result dict is stashed on the pytest session so the
    pytest_sessionfinish hook in conftest.py can aggregate
    everything into the final HTML report and console summary.

    The assertion at the end is what tells pytest whether the
    test passed or failed. The result dict captures the detail
    even when the test fails (for the report).
    """
    result = run_single_test(test_case)

    # Stash result on the session — picked up by sessionfinish hook
    if not hasattr(request.session, "_aggregated_results"):
        request.session._aggregated_results = []
    request.session._aggregated_results.append(result)

    # Tell pytest pass/fail based on the result
    if result["status"] == "FAIL":
        pytest.fail(
            f"{test_case['name']} failed: "
            f"{result['details']['steps_failed']} step(s) failed "
            f"(confidence: {result['confidence']:.2f})"
        )