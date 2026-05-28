import os
import re
import json
from datetime import datetime

from agents.requirement_agent import RequirementAgent
from agents.planner_agent import PlannerAgent
from agents.test_generator_agent import TestGeneratorAgent
from agents.execution_agent import ExecutionAgent
from agents.failure_classifier_agent import FailureClassifierAgent
from agents.debug_agent import DebugAgent
from agents.locator_agent import LocatorAgent
from agents.report_manager import ReportManager

from config import MAX_REPAIR_LOOPS


# ✅ Create run folder
RUN_ID = datetime.now().strftime("%Y%m%d_%H%M%S")
RUN_DIR = f"reports/run_{RUN_ID}"
os.makedirs(RUN_DIR, exist_ok=True)


# 🔥 NEW: Extract test cases (LOSSLESS)
def extract_test_cases(text):
    pattern = r"(TEST CASE.*?)(?=TEST CASE|\Z)"
    matches = re.findall(pattern, text, re.DOTALL)
    return [m.strip() for m in matches]


class Orchestrator:

    def load_prompt(self, file_path):
        with open(file_path, "r") as f:
            return f.read()

    def ensure_memory_files(self):
        os.makedirs("memory", exist_ok=True)

        files = {
            "memory/locator_memory.json": "{}",
            "memory/repair_logs.json": "[]"
        }

        for path, default in files.items():
            if not os.path.exists(path):
                with open(path, "w") as f:
                    f.write(default)

    def extract_failed_xpath(self, error):
        match = re.search(r'"selector":"(.*?)"', error)
        return match.group(1) if match else ""

    def log_repair(self, error, category):
        with open("memory/repair_logs.json", "r") as f:
            logs = json.load(f)

        logs.append({
            "error": error[:200],
            "category": category
        })

        with open("memory/repair_logs.json", "w") as f:
            json.dump(logs, f, indent=4)

    def count_tests(self, code):
        return code.count("def test_")

    def run(self):

        print("🚀 Starting Agentic Test Automation Pipeline...\n")

        self.ensure_memory_files()

        planner_prompt = self.load_prompt("prompts/planner_prompt.txt")
        test_prompt = self.load_prompt("prompts/test_prompt.txt")
        classification_prompt = self.load_prompt("prompts/failure_classification_prompt.txt")
        debug_prompt = self.load_prompt("prompts/debug_prompt.txt")

        report_manager = ReportManager(RUN_DIR)

        # Step 1
        requirements = RequirementAgent().read_user_stories()

        # 🔥 STEP 2 — LOSSLESS EXTRACTION
        raw_test_cases = extract_test_cases(requirements)
        print(f"📊 Extracted {len(raw_test_cases)} test cases")

        planner = PlannerAgent()
        structured_plan = []

        for tc in raw_test_cases:
            result = planner.create_plan(tc, planner_prompt)
            if result:
                structured_plan.extend(result)

        print(f"📊 Final structured test cases: {len(structured_plan)}")

        # Step 3
        generator = TestGeneratorAgent()
        test_code = generator.generate_test_script(structured_plan, test_prompt)

        os.makedirs("tests_generated", exist_ok=True)
        test_file_path = "tests_generated/test_auto.py"

        with open(test_file_path, "w") as f:
            f.write(test_code)

        # Backup
        backup_path = f"{RUN_DIR}/original_test_backup.py"
        with open(backup_path, "w") as f:
            f.write(test_code)

        print("✅ Test script generated.\n")

        # Step 4 — EXECUTION
        executor = ExecutionAgent()

        returncode, stdout, stderr = executor.execute_tests(
            html_report_path=f"{RUN_DIR}/full_report.html"
        )

        print("📄 STDOUT:\n", stdout)
        print("\n❌ STDERR:\n", stderr)

        repair_count = 0

        while returncode != 0 and repair_count < MAX_REPAIR_LOOPS:

            print(f"\n⚠️ Repair attempt {repair_count + 1}")

            classifier = FailureClassifierAgent()
            classification = classifier.classify(stderr, classification_prompt)
            category = classification.get("category", "LOCATOR_NOT_FOUND")

            print("🔍 Category:", category)

            self.log_repair(stderr, category)

            failed_xpath = self.extract_failed_xpath(stderr)

            try:
                html_dom = executor.get_dom()
            except:
                html_dom = "<html></html>"

            with open(test_file_path, "r") as f:
                original_code = f.read()

            original_count = self.count_tests(original_code)

            debugger = DebugAgent()

            fixed_code = debugger.repair_test(
                failing_code=original_code,
                error_log=stderr,
                category=category,
                html_dom=html_dom,
                failed_xpath=failed_xpath,
                prompt_template=debug_prompt
            )

            if not fixed_code:
                print("⚠️ GPT returned empty fix")
                break

            fixed_count = self.count_tests(fixed_code)

            print(f"🔍 Test count before: {original_count}, after fix: {fixed_count}")

            if fixed_count < original_count:
                print("🚫 Rejecting fix: test count reduced")
            else:
                with open(test_file_path, "w") as f:
                    f.write(fixed_code)
                print("✅ Fix accepted")

            print("🔁 Re-running tests...\n")

            returncode, stdout, stderr = executor.execute_tests(
                html_report_path=f"{RUN_DIR}/rerun_{repair_count}.html"
            )

            repair_count += 1

        if returncode == 0:
            print("\n🎉 Tests Passed Successfully.")
        else:
            print("\n❌ Tests Failed After Maximum Repair Attempts.")

        report_manager.generate_summary()

        print(f"\n📊 Reports generated in: {RUN_DIR}")
        print("🏁 Pipeline Complete.")


if __name__ == "__main__":
    orchestrator = Orchestrator()
    orchestrator.run()