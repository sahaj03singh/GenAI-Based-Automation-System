from agents.llm_client import call_gpt
from config import PLANNER_MODEL, TEMPERATURE_PLANNER
import json


class TestGeneratorAgent:

    def generate_test_script(self, structured_plan, prompt_template):

        base_prompt = prompt_template.replace(
            "{{PLAN}}",
            json.dumps(structured_plan, indent=2)
        )

        # 🔥 Force imports + setup automatically
        framework_injection = (
    "import pytest\n"
    "from selenium import webdriver\n"
    "from selenium.webdriver.common.by import By\n"
    "from selenium.webdriver.support.ui import WebDriverWait\n"
    "from selenium.webdriver.support import expected_conditions as EC\n\n"
)

        final_prompt = framework_injection + base_prompt

        return call_gpt(
            prompt=final_prompt,
            system_role=(
    "You are a senior Selenium automation engineer.\n"
    "Generate pytest-based automation code.\n\n"

    "STRICT RULES:\n"

    # 🔥 Locator discipline
    "- NEVER hardcode XPath directly\n"
    "- ALWAYS use LocatorAgent for locators\n"
    "- If locator exists:\n"
    "    locator = locator_agent.get_locator('element_name')\n"
    "- If NOT exists:\n"
    "    locator_agent.save_locator('element_name', 'xpath', 'xpath_here')\n"
    "    locator = locator_agent.get_locator('element_name')\n"
    "- Use locators like:\n"
    "    driver.find_element(locator['by'], locator['value'])\n"

    # 🔥 Test structure
    "- Each test case must be a separate pytest function\n"
    "- Each test must be independent\n"

    # 🔥 State reset (VERY IMPORTANT - fixes your failures)
    "- ALWAYS reset state before test starts\n"
    "- Use driver.delete_all_cookies() at beginning of each test\n"
    "- Start each test by opening https://www.saucedemo.com\n"

    # 🔥 Logging & screenshots
    "- Capture screenshot after each important step\n"
    "- Use driver.save_screenshot('screenshots/<testname>_step_X.png')\n"
    "- Add print logs for each step\n"

    # 🔥 Stability
    "- Use explicit waits (WebDriverWait)\n"
    "- Use robust XPath only when saving locator (prefer contains())\n"
    "- Avoid strict assertions like == for dynamic values\n"
    "- Prefer >= or presence checks instead\n"

    # 🔥 Output control
    "- Do NOT return explanation\n"
    "- Return ONLY Python code\n"
),
            model_name=PLANNER_MODEL,
            temperature=TEMPERATURE_PLANNER
        )