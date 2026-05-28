
import os
import time
from datetime import datetime

# ── In-memory log store for current test case ────────────────────
_step_logs = []


def clear_logs():
    """Call this before each test case to reset the log buffer."""
    global _step_logs
    _step_logs = []


def get_logs():
    """Return all logs collected since last clear_logs() call."""
    return list(_step_logs)


def log_step(description, status, screenshot_path=None):
    """
    Log a single test step.

    Parameters:
        description:     Human-readable step description
                         e.g. "Clicked on 'login button'"
        status:          "PASS", "FAIL", "WARN", "HEALED"
        screenshot_path: Path to screenshot file (optional)
    """
    entry = {
        "description":   description,
        "status":        status,
        "screenshot":    screenshot_path,
        "timestamp":     datetime.now().strftime("%H:%M:%S"),
    }
    _step_logs.append(entry)

    icon = {
        "PASS":   "✅",
        "FAIL":   "❌",
        "WARN":   "⚠️",
        "HEALED": "🩹",
    }.get(status, "—")

    print(f"{icon} [{status}] {description}")


def take_screenshot(driver, step_description):
    """
    Take a screenshot of the current browser state and save it.

    Returns the file path so it can be embedded in the HTML report.
    Returns None if screenshot fails.

    Parameters:
        driver:           Selenium WebDriver instance
        step_description: Used to build the filename
    """
    if driver is None:
        return None

    try:
        # Build a safe filename from the step description
        safe_name = (
            step_description
            .lower()
            .replace(" ", "_")
            .replace("/", "_")
            .replace("\\", "_")
            .replace(":", "_")
            .replace("'", "")
            .replace('"', "")
            [:60]   # cap length
        )
        timestamp  = datetime.now().strftime("%H%M%S_%f")[:10]
        filename   = f"{safe_name}_{timestamp}.png"

        # Save to reports/screenshots/
        screenshots_dir = os.path.join("reports", "screenshots")
        os.makedirs(screenshots_dir, exist_ok=True)

        filepath = os.path.join(screenshots_dir, filename)
        driver.save_screenshot(filepath)
        return filepath

    except Exception as e:
        print(f"[SCREENSHOT] Failed: {e}")
        return None