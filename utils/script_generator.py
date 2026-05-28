import json

def generate_python_tests():
    with open("tests_generated/test_steps.json") as f:
        tests = json.load(f)

    lines = []
    lines.append("from utils.actions import execute_step\n\n")

    for i, test in enumerate(tests):
        func_name = f"test_{i+1}"
        lines.append(f"def {func_name}(driver):\n")

        # 🔥 FIX: remove duplicate steps
        filtered_steps = []
        prev = None

        for step in test["steps"]:
            if step == prev:
                continue
            filtered_steps.append(step)
            prev = step

        for step in filtered_steps:
            step_str = repr(step)
            lines.append(f"    execute_step(driver, {step_str})\n")

        lines.append("\n")

    with open("tests_generated/generated_tests.py", "w") as f:
        f.writelines(lines)

    print("✅ Python test scripts generated!")