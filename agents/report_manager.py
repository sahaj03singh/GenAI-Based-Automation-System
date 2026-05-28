import json
import os

class ReportManager:

    def __init__(self, run_dir):
        self.run_dir = run_dir
        self.summary = []

    def add_result(self, test_name, status, rerun=False):
        self.summary.append({
            "test_name": test_name,
            "status": status,
            "rerun": rerun
        })

    def generate_summary(self):
        total = len(self.summary)
        passed = len([t for t in self.summary if t["status"] == "PASSED"])
        failed = len([t for t in self.summary if t["status"] == "FAILED"])
        rerun = len([t for t in self.summary if t["rerun"]])

        html = f"""
        <html>
        <head><title>Test Summary</title></head>
        <body>
            <h1>Test Run Summary</h1>
            <p>Total: {total}</p>
            <p>Passed: {passed}</p>
            <p>Failed: {failed}</p>
            <p>Rerun: {rerun}</p>

            <table border="1">
                <tr>
                    <th>Test Name</th>
                    <th>Status</th>
                    <th>Rerun</th>
                </tr>
        """

        for t in self.summary:
            html += f"""
                <tr>
                    <td>{t['test_name']}</td>
                    <td>{t['status']}</td>
                    <td>{t['rerun']}</td>
                </tr>
            """

        html += "</table></body></html>"

        with open(f"{self.run_dir}/summary.html", "w") as f:
            f.write(html)