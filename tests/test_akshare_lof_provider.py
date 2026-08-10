import unittest
from unittest.mock import patch

import pandas as pd

from backend.app.providers.akshare_lof_provider import AkshareLofProvider, DataSourceError


class AkshareLofProviderTests(unittest.TestCase):
    def test_default_provider_uses_sina_watchlist_quote_loader(self):
        spot = pd.DataFrame(
            [
                {
                    "代码": "501010",
                    "名称": "默认行情源",
                    "最新价": 1.2,
                    "涨跌幅": 2.0,
                    "成交量": 100,
                    "成交额": 12000,
                    "换手率": 0.5,
                }
            ]
        )
        purchase = pd.DataFrame(
            [
                {
                    "基金代码": "501010",
                    "基金简称": "默认行情源",
                    "最新净值/万份收益": 1.0,
                    "最新净值/万份收益-报告时间": "2026-08-08",
                    "申购状态": "开放申购",
                    "赎回状态": "开放赎回",
                    "日累计限定金额": 1000,
                    "手续费": 0.1,
                }
            ]
        )

        with patch(
            "backend.app.providers.akshare_lof_provider.SinaLofSpotLoader"
        ) as loader_type, patch("akshare.fund_purchase_em", return_value=purchase):
            loader_type.return_value.fetch_all.return_value = spot
            snapshot = AkshareLofProvider().fetch_all()[0]

        self.assertEqual(snapshot.code, "SH501010")
        self.assertEqual(snapshot.price, 1.2)
        self.assertEqual(snapshot.latest_nav, 1.0)
        self.assertEqual(snapshot.nav_date, "2026-08-08")
        self.assertEqual(snapshot.premium_pct, 20.0)

    def test_merges_market_and_official_nav_by_code(self):
        spot_calls = 0
        purchase_calls = 0

        def load_spot():
            nonlocal spot_calls
            spot_calls += 1
            return pd.DataFrame(
                [
                    {
                        "代码": "501001",
                        "名称": "测试沪市LOF",
                        "最新价": 1.2,
                        "涨跌幅": 2.5,
                        "成交量": 1200,
                        "成交额": 144000,
                        "换手率": 1.8,
                    },
                    {
                        "代码": "161001",
                        "名称": "测试深市LOF",
                        "最新价": 0.9,
                        "涨跌幅": -1.0,
                        "成交量": 800,
                        "成交额": 72000,
                        "换手率": 0.7,
                    },
                ]
            )

        def load_purchase():
            nonlocal purchase_calls
            purchase_calls += 1
            return pd.DataFrame(
                [
                    {
                        "基金代码": "161001",
                        "基金简称": "测试深市LOF",
                        "最新净值/万份收益": 1.0,
                        "最新净值/万份收益-报告时间": "2026-08-07",
                        "申购状态": "开放申购",
                        "赎回状态": "开放赎回",
                        "日累计限定金额": 1000,
                        "手续费": "0.12%",
                    },
                    {
                        "基金代码": "501001",
                        "基金简称": "测试沪市LOF",
                        "最新净值/万份收益": 1.0,
                        "最新净值/万份收益-报告时间": "2026-08-08",
                        "申购状态": "限制大额申购",
                        "赎回状态": "暂停赎回",
                        "日累计限定金额": 500,
                        "手续费": "0.15%",
                    },
                ]
            )

        snapshots = AkshareLofProvider(load_spot, load_purchase).fetch_all()

        self.assertEqual(spot_calls, 1)
        self.assertEqual(purchase_calls, 1)
        self.assertEqual([item.code for item in snapshots], ["SH501001", "SZ161001"])
        self.assertEqual(snapshots[0].premium_pct, 20.0)
        self.assertEqual(snapshots[0].nav_date, "2026-08-08")
        self.assertEqual(snapshots[0].subscription_status, "limited")
        self.assertEqual(snapshots[0].redemption_status, "closed")
        self.assertEqual(snapshots[0].premium_basis, "latest_official_nav")
        self.assertEqual(snapshots[1].premium_pct, -10.0)
        self.assertEqual(snapshots[1].subscription_status, "open")
        self.assertEqual(snapshots[1].redemption_status, "open")

    def test_keeps_spot_row_as_unknown_when_purchase_data_is_missing(self):
        spot = pd.DataFrame(
            [
                {
                    "代码": "501002",
                    "名称": "缺少净值资料",
                    "最新价": 1.05,
                    "涨跌幅": 0.5,
                    "成交量": 100,
                    "成交额": 10500,
                    "换手率": 0.1,
                }
            ]
        )
        purchase = pd.DataFrame(
            [
                {
                    "基金代码": "161999",
                    "基金简称": "其他基金",
                    "最新净值/万份收益": 1.0,
                    "最新净值/万份收益-报告时间": "2026-08-08",
                    "申购状态": "开放申购",
                    "赎回状态": "开放赎回",
                    "日累计限定金额": 1000,
                    "手续费": "0.1%",
                }
            ]
        )

        snapshot = AkshareLofProvider(lambda: spot, lambda: purchase).fetch_all()[0]

        self.assertIsNone(snapshot.latest_nav)
        self.assertIsNone(snapshot.premium_pct)
        self.assertEqual(snapshot.subscription_status, "unknown")
        self.assertEqual(snapshot.redemption_status, "unknown")

    def test_rejects_empty_market_table(self):
        spot = pd.DataFrame(
            columns=["代码", "名称", "最新价", "涨跌幅", "成交量", "成交额", "换手率"]
        )
        purchase = pd.DataFrame(
            columns=[
                "基金代码",
                "基金简称",
                "最新净值/万份收益",
                "最新净值/万份收益-报告时间",
                "申购状态",
                "赎回状态",
                "日累计限定金额",
                "手续费",
            ]
        )

        with self.assertRaisesRegex(DataSourceError, "行情表为空"):
            AkshareLofProvider(lambda: spot, lambda: purchase).fetch_all()

    def test_rejects_empty_purchase_table(self):
        spot = pd.DataFrame(
            [
                {
                    "代码": "501003",
                    "名称": "行情正常",
                    "最新价": 1.0,
                    "涨跌幅": 0.0,
                    "成交量": 1,
                    "成交额": 1,
                    "换手率": 0.0,
                }
            ]
        )
        purchase = pd.DataFrame(
            columns=[
                "基金代码",
                "基金简称",
                "最新净值/万份收益",
                "最新净值/万份收益-报告时间",
                "申购状态",
                "赎回状态",
                "日累计限定金额",
                "手续费",
            ]
        )

        with self.assertRaisesRegex(DataSourceError, "申赎表为空"):
            AkshareLofProvider(lambda: spot, lambda: purchase).fetch_all()

    def test_rejects_missing_required_columns(self):
        spot = pd.DataFrame([{"代码": "501003", "名称": "字段缺失"}])
        purchase = pd.DataFrame([{"基金代码": "501003"}])

        with self.assertRaisesRegex(DataSourceError, "行情表缺少字段"):
            AkshareLofProvider(lambda: spot, lambda: purchase).fetch_all()

    def test_rejects_duplicate_codes(self):
        spot_row = {
            "代码": "501004",
            "名称": "重复代码",
            "最新价": 1.0,
            "涨跌幅": 0.0,
            "成交量": 1,
            "成交额": 1,
            "换手率": 0.0,
        }
        spot = pd.DataFrame([spot_row, spot_row])
        purchase = pd.DataFrame(
            [
                {
                    "基金代码": "501004",
                    "基金简称": "重复代码",
                    "最新净值/万份收益": 1.0,
                    "最新净值/万份收益-报告时间": "2026-08-08",
                    "申购状态": "开放申购",
                    "赎回状态": "开放赎回",
                    "日累计限定金额": 1000,
                    "手续费": "0.1%",
                }
            ]
        )

        with self.assertRaisesRegex(DataSourceError, "行情表存在重复代码: 501004"):
            AkshareLofProvider(lambda: spot, lambda: purchase).fetch_all()

    def test_wraps_loader_failure_as_data_source_error(self):
        def fail_spot():
            raise RuntimeError("network down")

        with self.assertRaisesRegex(DataSourceError, "AkShare 数据获取失败: network down"):
            AkshareLofProvider(fail_spot, lambda: pd.DataFrame()).fetch_all()


if __name__ == "__main__":
    unittest.main()
