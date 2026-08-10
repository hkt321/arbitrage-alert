import json
import unittest
from urllib.parse import parse_qs, urlparse

from backend.app.providers.eastmoney_lof_spot_loader import EastmoneyLofSpotLoader
from backend.app.providers.errors import DataSourceError


def quote(code, name, price=1.0):
    return {
        "f12": code,
        "f14": name,
        "f2": price,
        "f3": 1.2,
        "f5": 100,
        "f6": 10000,
        "f8": 0.5,
    }


def payload(total, rows):
    return {"data": {"total": total, "diff": rows}}


class FakeResponse:
    def __init__(self, body, status=200):
        self.status = status
        self._body = json.dumps(body).encode("utf-8")

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False


class FakeOpenUrl:
    def __init__(self, pages):
        self.pages = pages
        self.requested_pages = []

    def __call__(self, request, timeout):
        page = int(parse_qs(urlparse(request.full_url).query)["pn"][0])
        self.requested_pages.append(page)
        result = self.pages[page]
        if isinstance(result, FakeResponse):
            return result
        return FakeResponse(result)


class EastmoneyLofSpotLoaderTests(unittest.TestCase):
    def test_fetches_all_pages_and_maps_minimal_columns(self):
        open_url = FakeOpenUrl(
            {
                1: payload(3, [quote("501001", "沪市一", 1.2), quote("161001", "深市一", 0.9)]),
                2: payload(3, [quote("501002", "沪市二", 1.1)]),
            }
        )

        frame = EastmoneyLofSpotLoader(page_size=2, open_url=open_url).fetch_all()

        self.assertEqual(open_url.requested_pages, [1, 2])
        self.assertEqual(frame["代码"].tolist(), ["501001", "161001", "501002"])
        self.assertEqual(frame.loc[0, "最新价"], 1.2)
        self.assertEqual(
            frame.columns.tolist(),
            ["代码", "名称", "最新价", "涨跌幅", "成交量", "成交额", "换手率"],
        )

    def test_rejects_incomplete_page(self):
        open_url = FakeOpenUrl(
            {
                1: payload(3, [quote("501001", "沪市一"), quote("161001", "深市一")]),
                2: payload(3, []),
            }
        )

        with self.assertRaisesRegex(DataSourceError, "第 2 页记录数不符"):
            EastmoneyLofSpotLoader(page_size=2, open_url=open_url).fetch_all()

    def test_rejects_duplicate_code(self):
        open_url = FakeOpenUrl(
            {
                1: payload(3, [quote("501001", "沪市一"), quote("161001", "深市一")]),
                2: payload(3, [quote("501001", "沪市一重复")]),
            }
        )

        with self.assertRaisesRegex(DataSourceError, "行情存在重复代码: 501001"):
            EastmoneyLofSpotLoader(page_size=2, open_url=open_url).fetch_all()

    def test_rejects_total_change_between_pages(self):
        open_url = FakeOpenUrl(
            {
                1: payload(3, [quote("501001", "沪市一"), quote("161001", "深市一")]),
                2: payload(4, [quote("501002", "沪市二")]),
            }
        )

        with self.assertRaisesRegex(DataSourceError, "行情总数不符"):
            EastmoneyLofSpotLoader(page_size=2, open_url=open_url).fetch_all()

    def test_rejects_http_error(self):
        open_url = FakeOpenUrl({1: FakeResponse({}, status=500)})

        with self.assertRaisesRegex(DataSourceError, "Eastmoney 行情 HTTP 500"):
            EastmoneyLofSpotLoader(page_size=2, open_url=open_url).fetch_all()


if __name__ == "__main__":
    unittest.main()
