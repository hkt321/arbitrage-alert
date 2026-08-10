import unittest
from pathlib import Path


class WorkflowTriggerPolicyTests(unittest.TestCase):
    def test_github_workflow_is_dispatch_only(self):
        workflow = (
            Path(__file__).parents[1] / ".github" / "workflows" / "daily-check.yml"
        ).read_text(encoding="utf-8")

        self.assertIn("workflow_dispatch:", workflow)
        self.assertNotIn("schedule:", workflow)
        self.assertNotIn("cron:", workflow)
        self.assertNotIn("schedule_gate", workflow)


if __name__ == "__main__":
    unittest.main()
