import os
import sys

sys.path.insert(
    0,
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)

from llm.test_generator import parse_user_stories
from utils.script_generator import generate_python_tests
from enigne.test_executor import run_tests
from utils.report_builder import generate_html_report


def test_run(driver):
    # Step 1: Generate test steps from userstories.txt
    parse_user_stories("userstories.txt")

    # Step 2: Generate Python test scripts
    generate_python_tests()

    # Step 3: Execute tests
    results = run_tests(driver)

    # Step 4: Generate HTML report
    generate_html_report(results)

    # Step 5: Print summary
    total = len(results)
    if total == 0:
        print("⚠️ No test cases ran")
        return

    truly_passed     = sum(
        1 for r in results if r.get("status") == "PASS"
    )
    passed_w_healing = sum(
        1 for r in results
        if r.get("status") == "PASS_WITH_HEALING"
    )
    failed           = sum(
        1 for r in results if r.get("status") == "FAIL"
    )
    avg_confidence   = (
        sum(r["confidence"] for r in results) / total
    )

    print("\n📊 FINAL TEST SUMMARY")
    print(f"✅ Clean Pass:        {truly_passed}/{total}")
    print(f"⚠️  Pass with Healing: {passed_w_healing}/{total}")
    print(f"❌ Failed:            {failed}/{total}")
    print(f"📈 Avg Confidence:    {avg_confidence:.2f}")

    if avg_confidence < 0.65:
        print("⚠️ WARNING: Average confidence below 0.65")
    if (truly_passed + passed_w_healing) / total < 0.7:
        print("⚠️ WARNING: Pass rate (incl. healing) below 70%")

    # Hard fail ONLY if framework appears broken
    assert avg_confidence > 0.3, (
        "❌ Framework appears broken — confidence near zero"
    )