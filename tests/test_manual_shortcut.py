import unittest
from pathlib import Path


class ManualShortcutTests(unittest.TestCase):
    def test_launcher_reuses_force_trigger_without_secrets(self):
        launcher = (Path(__file__).parents[1] / "run_lof_alert.cmd").read_text(
            encoding="utf-8"
        )

        self.assertIn(r"D:\anaconda\python.exe", launcher)
        self.assertIn(r"tools\trigger_daily_check.py", launcher)
        self.assertIn("--force", launcher)
        self.assertIn("timeout /t 5", launcher.lower())
        self.assertNotIn("SCT_SENDKEY", launcher)
        self.assertNotIn("run_check.py", launcher)


if __name__ == "__main__":
    unittest.main()
