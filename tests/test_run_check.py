import io
import json
import unittest
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime, timezone
from unittest.mock import patch

from backend.app.models.lof_snapshot import LofSnapshot
from tools.run_check import (
    DataSourceError,
    build_push_content,
    build_results,
    determine_level,
    main,
    run,
)


class ReminderLevelTests(unittest.TestCase):
    def test_open_high_premium_is_watch_not_executable(self):
        level, reasons = determine_level(
            premium_pct=3.0,
            purchase_limit=1000,
            subscription_status="open",
            redemption_status="open",
            min_limit=20,
            min_premium=1.5,
            min_discount=-2.0,
        )

        self.assertEqual(level, "watch")
        self.assertIn("基于最新官方净值", reasons)

    def test_discount_does_not_use_purchase_limit(self):
        level, reasons = determine_level(
            premium_pct=-3.0,
            purchase_limit=1,
            subscription_status="closed",
            redemption_status="open",
            min_limit=20,
            min_premium=1.5,
            min_discount=-2.0,
        )

        self.assertEqual(level, "watch")
        self.assertFalse(any("限购" in reason for reason in reasons))


class PushContentTests(unittest.TestCase):
    def test_summary_heading_reports_displayed_and_total_counts(self):
        results = [
            {
                "code": f"SH50100{index}",
                "name": f"测试基金{index}",
                "latest_nav": 1.0,
                "nav_date": "2026-08-08",
                "premium_pct": float(index),
                "level": "watch",
                "reasons": ["基于最新官方净值"],
            }
            for index in range(1, 6)
        ]

        content = build_push_content(
            results,
            instant=datetime(2026, 8, 10, 3, 11, tzinfo=timezone.utc),
        )

        self.assertIn("### 汇总（前5，本次共5只）", content)
        self.assertNotIn("### 汇总（前15）", content)

    def test_push_content_converts_utc_instant_to_beijing_time(self):
        content = build_push_content(
            [
                {
                    "code": "SH501001",
                    "name": "测试基金",
                    "latest_nav": 1.0,
                    "nav_date": "2026-08-08",
                    "premium_pct": 20.0,
                    "level": "watch",
                    "reasons": ["基于最新官方净值"],
                }
            ],
            instant=datetime(2026, 8, 10, 3, 11, tzinfo=timezone.utc),
        )

        self.assertIn("2026-08-10 11:11", content)

    def test_push_identifies_watch_only_official_nav_basis(self):
        content = build_push_content(
            [
                {
                    "code": "SH501001",
                    "name": "测试基金",
                    "price": 1.2,
                    "latest_nav": 1.0,
                    "nav_date": "2026-08-08",
                    "premium_pct": 20.0,
                    "level": "watch",
                    "reasons": ["基于最新官方净值", "溢价+20.00%"],
                    "purchase_limit_yuan": 1000,
                    "subscription_status": "open",
                    "redemption_status": "open",
                }
            ]
        )

        self.assertIn("关注提醒", content)
        self.assertIn("最新官方净值", content)
        self.assertIn("2026-08-08", content)
        self.assertNotIn("可执行", content)


class RunTests(unittest.TestCase):
    def test_build_results_sorts_then_limits_and_uses_lightweight_schema(self):
        snapshots = [
            LofSnapshot(code="SH501001", name="低溢价", price=1.01, latest_nav=1.0, nav_date="2026-08-08", premium_pct=1.0),
            LofSnapshot(code="SZ161001", name="高折价", price=0.8, latest_nav=1.0, nav_date="2026-08-08", premium_pct=-20.0, redemption_status="open"),
            LofSnapshot(code="SH501002", name="高溢价", price=1.1, latest_nav=1.0, nav_date="2026-08-08", premium_pct=10.0, subscription_status="open", purchase_limit_yuan=1000),
        ]

        results = build_results(snapshots, 2, 20, 1.5, -2.0)

        self.assertEqual([item["code"] for item in results], ["SZ161001", "SH501002"])
        self.assertEqual({item["level"] for item in results}, {"watch"})
        self.assertEqual(results[0]["premium_basis"], "latest_official_nav")
        self.assertNotIn("shares_wan", results[0])
        self.assertNotIn("shares_delta_wan", results[0])

    def test_run_emits_json_from_injected_provider(self):
        class Provider:
            def fetch_all(self):
                return [
                    LofSnapshot(
                        code="SH501001",
                        name="测试基金",
                        price=1.2,
                        latest_nav=1.0,
                        nav_date="2026-08-08",
                        premium_pct=20.0,
                        subscription_status="open",
                        redemption_status="open",
                        purchase_limit_yuan=1000,
                    )
                ]

        output = io.StringIO()
        with redirect_stdout(output):
            results = run(25, 20, 1.5, -2.0, True, None, provider=Provider())

        payload = json.loads(output.getvalue())
        self.assertEqual(payload, results)
        self.assertEqual(payload[0]["level"], "watch")

    def test_main_returns_nonzero_and_does_not_push_when_source_fails(self):
        class FailingProvider:
            def fetch_all(self):
                raise DataSourceError("数据源不可用")

        pushed = []
        stderr = io.StringIO()
        with patch("tools.run_check.AkshareLofProvider", return_value=FailingProvider()), patch(
            "tools.run_check.push_to_wechat", side_effect=lambda *args: pushed.append(args)
        ), redirect_stderr(stderr):
            exit_code = main(["--json", "--push-key", "dummy"])

        self.assertEqual(exit_code, 1)
        self.assertEqual(pushed, [])
        self.assertIn("数据源错误", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
