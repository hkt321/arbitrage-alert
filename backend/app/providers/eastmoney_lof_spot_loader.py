import json
import math
from typing import Any, Callable
from urllib.parse import urlencode
from urllib.request import ProxyHandler, Request, build_opener

import pandas as pd

from .errors import DataSourceError


class EastmoneyLofSpotLoader:
    URL = "https://88.push2.eastmoney.com/api/qt/clist/get"
    MARKETS = "b:MK0404,b:MK0405,b:MK0406,b:MK0407"
    FIELDS = "f2,f3,f5,f6,f8,f12,f14"
    OUTPUT_COLUMNS = ["代码", "名称", "最新价", "涨跌幅", "成交量", "成交额", "换手率"]
    FIELD_MAP = {
        "f12": "代码",
        "f14": "名称",
        "f2": "最新价",
        "f3": "涨跌幅",
        "f5": "成交量",
        "f6": "成交额",
        "f8": "换手率",
    }

    def __init__(
        self,
        page_size: int = 20,
        timeout: int = 15,
        open_url: Callable[..., Any] | None = None,
    ) -> None:
        if page_size <= 0:
            raise ValueError("page_size must be positive")
        self.page_size = page_size
        self.timeout = timeout
        self._open_url = open_url or build_opener(ProxyHandler({})).open

    def fetch_all(self) -> pd.DataFrame:
        first = self._fetch_page(1)
        total, first_rows = self._parse_page(first, 1)
        if total <= 0:
            raise DataSourceError("Eastmoney 行情总数必须大于 0")

        page_count = math.ceil(total / self.page_size)
        rows = self._validate_page_size(first_rows, 1, total)

        for page in range(2, page_count + 1):
            page_total, page_rows = self._parse_page(self._fetch_page(page), page)
            if page_total != total:
                raise DataSourceError(
                    f"Eastmoney 行情总数不符: 第 1 页 {total}, 第 {page} 页 {page_total}"
                )
            rows.extend(self._validate_page_size(page_rows, page, total))

        if len(rows) != total:
            raise DataSourceError(f"Eastmoney 行情总数不符: 声明 {total}, 实际 {len(rows)}")

        normalized_codes = [str(row.get("f12") or "").strip().zfill(6) for row in rows]
        duplicates = sorted({code for code in normalized_codes if normalized_codes.count(code) > 1})
        if duplicates:
            raise DataSourceError(f"Eastmoney 行情存在重复代码: {', '.join(duplicates)}")

        records = []
        for row, code in zip(rows, normalized_codes):
            records.append(
                {
                    "代码": code,
                    "名称": str(row.get("f14") or "").strip(),
                    "最新价": row.get("f2"),
                    "涨跌幅": row.get("f3"),
                    "成交量": row.get("f5"),
                    "成交额": row.get("f6"),
                    "换手率": row.get("f8"),
                }
            )
        frame = pd.DataFrame(records, columns=self.OUTPUT_COLUMNS)
        for column in ["最新价", "涨跌幅", "成交量", "成交额", "换手率"]:
            frame[column] = pd.to_numeric(frame[column], errors="coerce")
        return frame

    def _fetch_page(self, page: int) -> dict[str, Any]:
        params = {
            "pn": str(page),
            "pz": str(self.page_size),
            "po": "1",
            "np": "1",
            "ut": "bd1d9ddb04089700cf9c27f6f7426281",
            "fltt": "2",
            "invt": "2",
            "fid": "f3",
            "fs": self.MARKETS,
            "fields": self.FIELDS,
        }
        request = Request(
            self.URL + "?" + urlencode(params),
            headers={"User-Agent": "Mozilla/5.0"},
        )
        try:
            with self._open_url(request, timeout=self.timeout) as response:
                status = getattr(response, "status", None)
                if status is None and hasattr(response, "getcode"):
                    status = response.getcode()
                if status != 200:
                    raise DataSourceError(f"Eastmoney 行情 HTTP {status}")
                return json.loads(response.read().decode("utf-8"))
        except DataSourceError:
            raise
        except Exception as exc:
            raise DataSourceError(
                f"Eastmoney 行情第 {page} 页请求失败: {type(exc).__name__}"
            ) from exc

    @staticmethod
    def _parse_page(payload: dict[str, Any], page: int) -> tuple[int, list[dict[str, Any]]]:
        data = payload.get("data") if isinstance(payload, dict) else None
        if not isinstance(data, dict):
            raise DataSourceError(f"Eastmoney 行情第 {page} 页结构无效")
        total = data.get("total")
        rows = data.get("diff")
        if not isinstance(total, int) or not isinstance(rows, list):
            raise DataSourceError(f"Eastmoney 行情第 {page} 页结构无效")
        if not all(isinstance(row, dict) for row in rows):
            raise DataSourceError(f"Eastmoney 行情第 {page} 页结构无效")
        return total, rows

    def _validate_page_size(
        self, rows: list[dict[str, Any]], page: int, total: int
    ) -> list[dict[str, Any]]:
        expected = min(self.page_size, total - (page - 1) * self.page_size)
        if len(rows) != expected:
            raise DataSourceError(
                f"Eastmoney 行情第 {page} 页记录数不符: 应为 {expected}, 实为 {len(rows)}"
            )
        return rows
