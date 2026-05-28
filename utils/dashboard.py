import json
import os

def generate_dashboard(results):
    os.makedirs("reports", exist_ok=True)

    total_tests = len(results)
    passed = len([r for r in results if r["passed"]])

    avg_accuracy = sum(r["accuracy"] for r in results) / total_tests

    report = f"""
    <html>
    <body>
        <h1>AI Test Dashboard</h1>
        <p>Total Tests: {total_tests}</p>
        <p>Passed: {passed}</p>
        <p>Average Accuracy: {avg_accuracy:.2f}%</p>
    </body>
    </html>
    """

    with open("reports/dashboard.html", "w") as f:
        f.write(report)