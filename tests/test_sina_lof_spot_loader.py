import unittest
from datetime import datetime
from zoneinfo import ZoneInfo

from backend.app.providers.errors import DataSourceError
from backend.app.providers.sina_lof_spot_loader import SinaLofSpotLoader


SHANGHAI = ZoneInfo("Asia/Shanghai")


class FakeQuotation:
    def __init__(self, rows):
        self.rows = rows

    def real(self, codes, prefix=True):
        return self.rows


def quote(name, now, close, date="2026-08-10", time="10:42:18"):
    return {
        "name": name,
        "open": close,
        "close": close,
        "now": now,
        "high": now,
        "low": close,
        "buy": now,
        "sell": now,
        "turnover": 45_450_902,
        "volume": 39_904_883.753,
        "date": date,
        "time": time,
    }


class SinaLofSpotLoaderTests(unittest.TestCase):
    def test_maps_complete_fresh_watchlist_to_provider_schema(self):
        rows = {
            "sh501018": quote("南方原油LOF", 1.892, 1.88),
            "sz162411": quote("华宝油气", 0.879, 0.87),
        }
        loader = SinaLofSpotLoader(
            codes=["501018", "162411"],
            quotation_factory=lambda: FakeQuotation(rows),
            now=lambda: datetime(2026, 8, 10, 10, 43, tzinfo=SHANGHAI),
        )

        frame = loader.fetch_all()

        self.assertEqual(frame["代码"].tolist(), ["501018", "162411"])
        self.assertEqual(frame["名称"].tolist(), ["南方原油LOF", "华宝油气"])
        self.assertEqual(frame["最新价"].tolist(), [1.892, 0.879])
        self.assertAlmostEqual(frame.loc[0, "涨跌幅"], 0.6382978723)
        self.assertEqual(frame.loc[0, "成交量"], 45_450_902)
        self.assertEqual(frame.loc[0, "成交额"], 39_904_883.753)
        self.assertTrue(frame["换手率"].isna().all())

    def test_rejects_missing_watchlist_code(self):
        loader = SinaLofSpotLoader(
            codes=["501018", "162411"],
            quotation_factory=lambda: FakeQuotation(
                {"sh501018": quote("南方原油LOF", 1.892, 1.88)}
            ),
            now=lambda: datetime(2026, 8, 10, 10, 43, tzinfo=SHANGHAI),
        )

        with self.assertRaisesRegex(DataSourceError, "新浪行情缺少自选代码: 162411"):
            loader.fetch_all()

    def test_rejects_stale_quote(self):
        loader = SinaLofSpotLoader(
            codes=["501018"],
            quotation_factory=lambda: FakeQuotation(
                {"sh501018": quote("南方原油LOF", 1.892, 1.88, time="10:30:00")}
            ),
            now=lambda: datetime(2026, 8, 10, 10, 43, tzinfo=SHANGHAI),
        )

        with self.assertRaisesRegex(DataSourceError, "新浪行情已过期: 501018"):
            loader.fetch_all()

    def test_rejects_non_positive_price(self):
        loader = SinaLofSpotLoader(
            codes=["501018"],
            quotation_factory=lambda: FakeQuotation(
                {"sh501018": quote("南方原油LOF", 0, 1.88)}
            ),
            now=lambda: datetime(2026, 8, 10, 10, 43, tzinfo=SHANGHAI),
        )

        with self.assertRaisesRegex(DataSourceError, "新浪行情价格无效: 501018"):
            loader.fetch_all()

    def test_rejects_duplicate_watchlist_code(self):
        with self.assertRaisesRegex(DataSourceError, "自选池存在重复代码: 501018"):
            SinaLofSpotLoader(
                codes=["501018", "501018"],
                quotation_factory=lambda: FakeQuotation({}),
            )


if __name__ == "__main__":
    unittest.main()
