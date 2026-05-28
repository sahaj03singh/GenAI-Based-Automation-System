import json
from agents.llm_client import call_gpt
from config import CLASSIFIER_MODEL, TEMPERATURE_CLASSIFIER


class FailureClassifierAgent:

    def clean_response(self, response):
        """
        Clean GPT response (remove markdown, extra text)
        """
        if not response:
            return ""

        # Remove markdown ```json ``` blocks
        if "```" in response:
            parts = response.split("```")
            for part in parts:
                if "{" in part:
                    response = part
                    break

        return response.strip()

    def classify(self, error_log, prompt_template):

        # Prepare prompt
        prompt = prompt_template.replace("{{ERROR}}", error_log)

        # Call GPT
        response = call_gpt(
            prompt=prompt,
            system_role="You are an expert in classifying Selenium errors. Always return JSON only.",
            model_name=CLASSIFIER_MODEL,
            temperature=TEMPERATURE_CLASSIFIER
        )

        print("\n🧠 GPT RAW RESPONSE:", response)

        # Clean response
        cleaned = self.clean_response(response)

        # Try parsing JSON
        try:
            result = json.loads(cleaned)

            # Safety check
            if "category" not in result:
                raise ValueError("Missing category key")

            return result

        except Exception as e:
            print("⚠️ JSON parsing failed:", e)
            print("⚠️ Falling back to UNKNOWN category")

            return {"category": "LOCATOR_NOT_FOUND"}