# ai-generated: 90% - runs the Lab 2 own-service pytest suite and prints the grader protocol
import sys

import pytest


class ResultSummary:
    passed = 0
    failed = 0

    def pytest_terminal_summary(self, terminalreporter):
        stats = terminalreporter.stats
        self.passed = len(stats.get("passed", []))
        self.failed = sum(len(stats.get(key, [])) for key in ("failed", "error"))


def main():
    summary = ResultSummary()
    result = pytest.main(["-q", "tests/test_dora_api.py"], plugins=[summary])
    print(f"ITSMLAB-TESTS: passed={summary.passed} failed={summary.failed}")
    return int(result)


if __name__ == "__main__":
    sys.exit(main())
