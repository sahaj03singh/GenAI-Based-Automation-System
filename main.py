import subprocess
import sys
import os
from llm.test_generator import parse_user_stories
from utils.script_generator import generate_python_tests


def run_pipeline(input_file="userstories.txt"):
    print("\n" + "=" * 50)
    print("STEP 1: Parsing manual test cases")
    print("=" * 50)

    if not os.path.exists(input_file):
        print(f"❌ Input file not found: {input_file}")
        sys.exit(1)

    parse_user_stories(input_file)

    print("\n" + "=" * 50)
    print("STEP 2: Generating Python test scripts")
    print("=" * 50)
    generate_python_tests()

    print("\n" + "=" * 50)
    print("STEP 3: Running tests with pytest")
    print("=" * 50)
    result = subprocess.run(
        [
            sys.executable, "-m", "pytest",
            "tests_generated/generated_tests.py",
            "-v", "--tb=short", "--no-header",
            f"--html=reports/report_latest.html",
            "--self-contained-html"
        ],
        capture_output=False
    )

    print("\n" + "=" * 50)
    print("Pipeline complete")
    print("=" * 50)
    return result.returncode


if __name__ == "__main__":
    input_file = sys.argv[1] if len(sys.argv) > 1 else "userstories.txt"
    sys.exit(run_pipeline(input_file))
