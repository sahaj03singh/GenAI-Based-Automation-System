import subprocess
import os
import time


class ExecutionAgent:

    def execute_tests(self, html_report_path="reports/report.html"):
        """
        Executes pytest and generates HTML report at given path
        """

        print("🚀 Starting test execution...\n")

        # Ensure folders exist
        os.makedirs("reports", exist_ok=True)
        os.makedirs("screenshots", exist_ok=True)

        # ✅ Ensure dynamic report folder exists
        report_dir = os.path.dirname(html_report_path)
        if report_dir:
            os.makedirs(report_dir, exist_ok=True)

        command = [
            "pytest",
            "tests_generated/test_auto.py",
            f"--html={html_report_path}",
            "--self-contained-html",
            "-s",   # print logs
            "-v"    # verbose test names
        ]

        start_time = time.time()

        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        stdout, stderr = process.communicate()

        end_time = time.time()

        print("✅ Execution completed in {:.2f} seconds\n".format(end_time - start_time))

        # ✅ Print logs (important for orchestrator parsing)
        print("📄 STDOUT:\n")
        print(stdout)

        print("\n❌ STDERR:\n")
        print(stderr)

        # ✅ Report validation
        if os.path.exists(html_report_path):
            print(f"\n📊 HTML Report generated at: {html_report_path}")
        else:
            print("\n⚠️ Report not generated. Check pytest-html installation.")

        return process.returncode, stdout, stderr

    def get_dom(self):
        """
        Future: Replace with real browser DOM capture
        """
        return "<html>DOM capture not implemented</html>"