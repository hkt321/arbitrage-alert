import json
from datetime import datetime
from pathlib import Path
from typing import Any, Callable
from zoneinfo import ZoneInfo

import pandas as pd

from .errors import DataSourceError


SHANGHAI = ZoneInfo("Asia/Shanghai")
DEFAULT_WATCHLIST = Path(__file__).resolve().parents[3] / "config" / "lof_watchlist.json"


class _HttpsSina:
    """Build easyquotation's Sina parser with bounded, proxy-free HTTPS I/O."""

    def __new__(cls, timeout: int):
        from easyquotation.sina import Sina

        class BoundedSina(Sina):
            @property
            def stock_api(self) -> str:
                return "https://hq.sinajs.cn/list="

            def get_stocks_by_range(self, params):
                response = self._session.get(
                    self.stock_api + params,
                    headers=self._get_headers(),
                    timeout=timeout,
                )
                response.raise_for_status()
                return response.text

            def _fetch_stock_data(self, stock_list):
                return [self.get_stocks_by_range(item) for item in stock_list]

        quotation = BoundedSina()
        quotation._session.trust_env = False
        return quotation


class SinaLofSpotLoader:
    OUTPUT_COLUMNS = ["代码", "名称", "最新价", "涨跌幅", "成交量", "成交额", "换手率"]

    def __init__(
        self,
        codes: list[str] | None = None,
        watchlist_path: str | Path = DEFAULT_WATCHLIST,
        timeout: int = 35,
        max_quote_age_seconds: int = 300,
        quotation_factory: Callable[[], Any] | None = None,
        now: Callable[[], datetime] | None = None,
    ) -> None:
        self.watchlist_path = Path(watchlist_path)
        self.timeout = timeout
        self.max_quote_age_seconds = max_quote_age_seconds
        self._quotation_factory = quotation_factory or (lambda: _HttpsSina(timeout))
        self._now = now or (lambda: datetime.now(SHANGHAI))
        self.codes = self._validate_codes(codes) if codes is not None else self._load_codes()

    def fetch_all(self) -> pd.DataFrame:
        try:
            raw = self._quotation_factory().real(self.codes, prefix=True)
        except Exception as exc:
            raise DataSourceError(f"新浪行情获取失败: {type(exc).__name__}") from exc

        if not isinstance(raw, dict):
            raise DataSourceError("新浪行情结构无效")

        expected = {self._prefixed(code): code for code in self.codes}
        missing = [code for key, code in expected.items() if key not in raw]
        if missing:
            raise DataSourceError(f"新浪行情缺少自选代码: {', '.join(missing)}")
        unexpected = sorted(set(raw) - set(expected))
        if unexpected:
            raise DataSourceError(f"新浪行情返回意外代码: {', '.join(unexpected)}")

        observed_at = self._now()
        if observed_at.tzinfo is None:
            observed_at = observed_at.replace(tzinfo=SHANGHAI)
        else:
            observed_at = observed_at.astimezone(SHANGHAI)

        records = []
        for code in self.codes:
            row = raw[self._prefixed(code)]
            if not isinstance(row, dict):
                raise DataSourceError(f"新浪行情结构无效: {code}")
            price = self._number(row.get("now"))
            if price is None or price <= 0:
                raise DataSourceError(f"新浪行情价格无效: {code}")
            quote_at = self._quote_time(row, code)
            age_seconds = (observed_at - quote_at).total_seconds()
            if age_seconds < -60 or age_seconds > self.max_quote_age_seconds:
                raise DataSourceError(f"新浪行情已过期: {code}")

            close = self._number(row.get("close"))
            change_pct = None
            if close is not None and close > 0:
                change_pct = (price - close) / close * 100
            records.append(
                {
                    "代码": code,
                    "名称": str(row.get("name") or "").strip(),
                    "最新价": price,
                    "涨跌幅": change_pct,
                    "成交量": self._number(row.get("turnover")),
                    "成交额": self._number(row.get("volume")),
                    "换手率": None,
                }
            )

        return pd.DataFrame(records, columns=self.OUTPUT_COLUMNS)

    def _load_codes(self) -> list[str]:
        try:
            payload = json.loads(self.watchlist_path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise DataSourceError(f"自选池读取失败: {self.watchlist_path}") from exc
        codes = payload.get("codes") if isinstance(payload, dict) else None
        return self._validate_codes(codes)

    @staticmethod
    def _validate_codes(codes: Any) -> list[str]:
        if not isinstance(codes, list) or not codes:
            raise DataSourceError("自选池代码不能为空")
        normalized = [str(code).strip() for code in codes]
        invalid = [code for code in normalized if len(code) != 6 or not code.isdigit()]
        if invalid:
            raise DataSourceError(f"自选池代码无效: {', '.join(invalid)}")
        duplicates = sorted({code for code in normalized if normalized.count(code) > 1})
        if duplicates:
            raise DataSourceError(f"自选池存在重复代码: {', '.join(duplicates)}")
        return normalized

    @staticmethod
    def _prefixed(code: str) -> str:
        return ("sh" if code[0] in {"5", "6"} else "sz") + code

    @staticmethod
    def _number(value: Any) -> float | None:
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _quote_time(row: dict[str, Any], code: str) -> datetime:
        try:
            return datetime.strptime(
                f"{row['date']} {row['time']}", "%Y-%m-%d %H:%M:%S"
            ).replace(tzinfo=SHANGHAI)
        except (KeyError, TypeError, ValueError) as exc:
            raise DataSourceError(f"新浪行情时间无效: {code}") from exc
