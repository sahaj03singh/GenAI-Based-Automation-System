class EvaluationAgent:
    def __init__(self):
        self.total = 0
        self.passed = 0
        self.failed = 0
        self.repaired = 0

    def record_pass(self):
        self.total += 1
        self.passed += 1

    def record_fail(self):
        self.total += 1
        self.failed += 1

    def record_repair(self):
        self.repaired += 1

    def report(self):
        success_rate = (self.passed / self.total) * 100 if self.total else 0
        repair_rate = (self.repaired / self.failed) * 100 if self.failed else 0

        return {
            "total_tests": self.total,
            "passed": self.passed,
            "failed": self.failed,
            "repair_success_rate": repair_rate,
            "success_rate": success_rate
        }