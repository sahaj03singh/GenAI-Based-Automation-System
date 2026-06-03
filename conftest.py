"""
conftest.py — pytest fixtures and configuration.

Driver creation is delegated to utils.driver_factory.create_driver()
so the same Chrome options are used by:
  - this fixture (used for the top-level pytest test function), AND
  - the per-test respawn loop in enigne/test_executor.py

All Chrome-option logic (anti-detection, user-agent, page-load
strategy, timeouts, popup-dismissal wrapper) lives in
utils/driver_factory.py. Edit there if you need to change anything
about how Chrome is launched.
"""

import pytest
from utils.driver_factory import create_driver


@pytest.fixture(scope="function")
def driver(request):
    """
    Creates a single Chrome driver for the top-level pytest test
    function. The executor loop in test_executor.py will close this
    driver immediately and spawn its own fresh driver per test case
    — but pytest still needs *some* driver here to satisfy the
    fixture machinery.
    """
    is_headless = request.config.getoption("--headless", default=False)
    driver = create_driver(headless=is_headless)
    yield driver
    try:
        driver.quit()
    except Exception:
        pass


def pytest_addoption(parser):
    parser.addoption(
        "--headless",
        action="store_true",
        default=False,
        help="Run Chrome in headless mode",
    )