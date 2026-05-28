from agents.llm_client import call_gpt
from config import REPAIR_MODEL, TEMPERATURE_REPAIR

class DebugAgent:

    def repair_test(
        self,
        failing_code,
        error_log,
        category,
        html_dom,
        failed_xpath,
        prompt_template
    ):

        category_instruction = {
            "LOCATOR_NOT_FOUND": "Fix the XPath using DOM context.",
            "TIMING_ISSUE": "Add explicit waits (WebDriverWait).",
            "ASSERTION_FAILURE": "Fix assertion logic.",
            "ELEMENT_NOT_INTERACTABLE": "Ensure element is clickable/visible.",
            "NAVIGATION_ERROR": "Fix navigation flow.",
            "UNKNOWN": "Analyze and fix the issue."
        }

        # 🔥 Build enriched prompt
        prompt = prompt_template
        prompt = prompt.replace("{{CODE}}", failing_code)
        prompt = prompt.replace("{{ERROR}}", error_log)
        prompt = prompt.replace("{{DOM}}", html_dom[:3000])  # limit size
        prompt = prompt.replace("{{FAILED_XPATH}}", failed_xpath)
        prompt = prompt.replace(
            "{{CATEGORY_INSTRUCTION}}",
            category_instruction.get(category, "")
        )

        response = call_gpt(
            prompt=prompt,
            system_role="You are a senior QA automation engineer fixing Selenium tests intelligently using DOM context.",
            model_name=REPAIR_MODEL,
            temperature=TEMPERATURE_REPAIR
        )

        # 🔥 Extract clean code (basic cleaning)
        cleaned_code = self._clean_response(response)

        return cleaned_code

    def _clean_response(self, response):
        # Remove markdown if GPT returns ```python blocks
        if "```" in response:
            response = response.split("```")[-2]
        return response.strip()