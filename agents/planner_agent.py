import json
from agents.llm_client import call_gpt
from config import PLANNER_MODEL, TEMPERATURE_PLANNER
from agents.dom_extractor import get_dom, clean_dom


class PlannerAgent:

    def create_plan(self, requirements, prompt_template=None):

        dom = get_dom()
        cleaned_dom = clean_dom(dom)

        print("\n🔍 DOM LENGTH:", len(cleaned_dom))

        prompt = f"""
You are a test planning agent.

Here is the ACTUAL DOM:

{cleaned_dom}

IMPORTANT:
- Input contains ONLY ONE test case
- You MUST return EXACTLY ONE test case
- DO NOT merge or skip

STRICT RULES:
- Return ONLY valid JSON
- Output must be a JSON list with EXACTLY ONE item

FORMAT:
[
  {{
    "test_name": "Test Case Name",
    "steps": [
      "Step 1 ...",
      "Step 2 ..."
    ]
  }}
]

User Story:
{requirements}
"""

        response = call_gpt(
            prompt=prompt,
            system_role="Return only JSON.",
            model_name=PLANNER_MODEL,
            temperature=0.2
        )

        print("\n🧠 RAW PLANNER RESPONSE:\n", response)

        try:
            data = json.loads(response)
            if isinstance(data, list):
                return data
            return []
        except:
            return []