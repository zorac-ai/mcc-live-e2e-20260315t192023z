from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def run_cli(db_path: Path, *args: str) -> object:
    result = subprocess.run(
        [sys.executable, "-m", "issue_tracker", "--db", str(db_path), *args],
        cwd=REPO_ROOT,
        check=True,
        text=True,
        capture_output=True,
    )
    return json.loads(result.stdout)


class CliTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "issues.json"

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def run_json(self, *args: str) -> object:
        return run_cli(self.db_path, *args)

    def test_create_and_list_open_issues(self) -> None:
        created = self.run_json("add", "Ship the CLI")
        self.assertEqual(created["id"], 1)
        self.assertEqual(created["status"], "open")

        issues = self.run_json("list")
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0]["title"], "Ship the CLI")

    def test_list_includes_created_issue(self) -> None:
        created = self.run_json("add", "Document the commands")
        issues = self.run_json("list")
        self.assertEqual(issues[0]["id"], created["id"])
        self.assertEqual(issues[0]["title"], "Document the commands")

    def test_close_issue_and_filter_closed(self) -> None:
        self.run_json("add", "Close me")
        closed = self.run_json("close", "1")
        self.assertEqual(closed["status"], "closed")
        self.assertIsNotNone(closed["closed_at"])

        issues = self.run_json("list", "--status", "closed")
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0]["id"], 1)

    def test_list_open_status_filter(self) -> None:
        self.run_json("add", "Open issue")
        self.run_json("add", "Issue to close")
        self.run_json("close", "2")

        open_issues = self.run_json("list", "--status", "open")
        self.assertEqual(len(open_issues), 1)
        self.assertEqual(open_issues[0]["id"], 1)
        self.assertEqual(open_issues[0]["status"], "open")

    def test_list_all_without_filter(self) -> None:
        self.run_json("add", "Open one")
        self.run_json("add", "Close me")
        self.run_json("close", "2")

        all_issues = self.run_json("list")
        self.assertEqual(len(all_issues), 2)
        statuses = {i["id"]: i["status"] for i in all_issues}
        self.assertEqual(statuses[1], "open")
        self.assertEqual(statuses[2], "closed")

    def test_missing_issue_returns_non_zero(self) -> None:
        result = subprocess.run(
            [sys.executable, "-m", "issue_tracker", "--db", str(self.db_path), "close", "999"],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("issue 999 not found", result.stderr)


if __name__ == "__main__":
    unittest.main()
