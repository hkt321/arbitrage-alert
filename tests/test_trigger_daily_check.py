import unittest
from datetime import datetime
from types import SimpleNamespace

from tools.trigger_daily_check import trigger_daily_check


class TriggerDailyCheckTests(unittest.TestCase):
    def test_triggers_master_workflow_once_during_weekday_window(self):
        calls = []

        def run_command(command):
            calls.append(command)
            return SimpleNamespace(returncode=0)

        exit_code = trigger_daily_check(
            now=datetime(2026, 8, 10, 13, 17),
            find_executable=lambda _: r"C:\Program Files\GitHub CLI\gh.exe",
            run_command=run_command,
        )

        self.assertEqual(exit_code, 0)
        self.assertEqual(
            calls,
            [
                [
                    r"C:\Program Files\GitHub CLI\gh.exe",
                    "workflow",
                    "run",
                    "daily-check.yml",
                    "--repo",
                    "hkt321/arbitrage-alert",
                    "--ref",
                    "master",
                    "-f",
                    "top=15",
                ]
            ],
        )

    def test_skips_outside_weekday_trading_window(self):
        for instant in [
            datetime(2026, 8, 10, 14, 51),
            datetime(2026, 8, 9, 13, 17),
        ]:
            with self.subTest(instant=instant):
                calls = []
                exit_code = trigger_daily_check(
                    now=instant,
                    find_executable=lambda _: r"C:\Program Files\GitHub CLI\gh.exe",
                    run_command=lambda command: calls.append(command),
                )

                self.assertEqual(exit_code, 0)
                self.assertEqual(calls, [])

    def test_returns_nonzero_when_gh_is_unavailable(self):
        exit_code = trigger_daily_check(
            now=datetime(2026, 8, 10, 13, 17),
            find_executable=lambda _: None,
            run_command=lambda command: None,
        )

        self.assertEqual(exit_code, 1)


if __name__ == "__main__":
    unittest.main()
