import json
import re
from dataclasses import replace
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from app.models.fund import FundProfile
from app.models.fund_status import FundStatus


class EastmoneyFundStatusProvider:
    API_URL = "https://fund.eastmoney.com/Data/Fund_JJJZ_Data.aspx"

    def __init__(self, page_size: int = 200, timeout: int = 15) -> None:
        self.page_size = page_size
        self.timeout = timeout
        self._page_cache: dict[int, dict[str, Any]] = {}
        self._status_cache: dict[str, FundStatus | None] = {}

    def get_status(self, code: str) -> FundStatus | None:
        normalized = self._normalize_code(code)
        if normalized in self._status_cache:
            return self._status_cache[normalized]

        first = self._fetch_page(1)
        pages = int(first.get("pages", 1))

        left, right = 1, pages
        while left <= right:
            mid = (left + right) // 2
            page = self._fetch_page(mid)
            rows = page.get("datas", [])
            if not rows:
                break

            first_code = rows[0][0]
            last_code = rows[-1][0]

            if normalized < first_code:
                right = mid - 1
                continue
            if normalized > last_code:
                left = mid + 1
                continue

            for row in rows:
                if row[0] == normalized:
                    status = self._to_status(row)
                    self._status_cache[normalized] = status
                    return status
            self._status_cache[normalized] = None
            return None

        self._status_cache[normalized] = None
        return None

    def apply_to_profile(self, profile: FundProfile) -> FundProfile:
        status = self.get_status(profile.code)
        if status is None:
            return profile

        return replace(
            profile,
            subscription_status=status.subscription_status,
            redemption_status=status.redemption_status,
            purchase_limit_yuan=status.purchase_limit_yuan,
            fee_pct=status.fee_pct if status.fee_pct is not None else profile.fee_pct,
            last_official_nav=status.latest_nav if status.latest_nav is not None else profile.last_official_nav,
        )

    def _fetch_page(self, page_index: int) -> dict[str, Any]:
        if page_index in self._page_cache:
            return self._page_cache[page_index]

        params = {
            "t": "8",
            "page": f"{page_index},{self.page_size}",
            "js": "reData",
            "sort": "fcode,asc",
        }
        request = Request(
            self.API_URL + "?" + urlencode(params),
            headers={"User-Agent": "Mozilla/5.0"},
        )
        with urlopen(request, timeout=self.timeout) as response:
            text = response.read().decode("utf-8", errors="replace")

        parsed = self._parse_response(text)
        self._page_cache[page_index] = parsed
        return parsed

    @classmethod
    def _parse_response(cls, text: str) -> dict[str, Any]:
        datas_match = re.search(r"datas:(\[.*?\]),record:", text, flags=re.S)
        if not datas_match:
            return {"datas": [], "record": 0, "pages": 0, "curpage": 0}

        datas = json.loads(datas_match.group(1))
        return {
            "datas": datas,
            "record": cls._match_int(text, r'record:"(\d+)"'),
            "pages": cls._match_int(text, r'pages:"(\d+)"'),
            "curpage": cls._match_int(text, r'curpage:"(\d+)"'),
        }

    @staticmethod
    def _match_int(text: str, pattern: str) -> int:
        match = re.search(pattern, text)
        return int(match.group(1)) if match else 0

    @classmethod
    def _to_status(cls, row: list[Any]) -> FundStatus:
        return FundStatus(
            code=row[0],
            name=row[1],
            fund_type=row[2],
            latest_nav=cls._num(row[3]),
            nav_date=row[4] or None,
            subscription_status=cls._map_subscription(row[5], row[11]),
            redemption_status=cls._map_redemption(row[6]),
            next_open_date=row[7] or None,
            min_purchase_yuan=cls._num(row[8]),
            purchase_limit_yuan=cls._limit(row[9]),
            fee_pct=cls._pct(row[12]),
            raw_subscription_status=row[5],
            raw_redemption_status=row[6],
            raw=row,
        )

    @staticmethod
    def _normalize_code(code: str) -> str:
        return code.split(".")[0]

    @staticmethod
    def _num(value: Any) -> float | None:
        try:
            if value is None or value == "":
                return None
            return float(value)
        except (TypeError, ValueError):
            return None

    @classmethod
    def _limit(cls, value: Any) -> float | None:
        number = cls._num(value)
        if number is None:
            return None
        if number >= 80_000_000_000:
            return None
        return number

    @classmethod
    def _pct(cls, value: Any) -> float | None:
        if value is None:
            return None
        text = str(value).replace("%", "")
        return cls._num(text)

    @staticmethod
    def _map_subscription(status: str, buy_code: Any) -> str:
        if "暂停" in status or str(buy_code) in {"4", "5", "6", "7", "10"}:
            return "closed"
        if "限" in status:
            return "limited"
        if "开放" in status:
            return "open"
        return "unknown"

    @staticmethod
    def _map_redemption(status: str) -> str:
        if "暂停" in status:
            return "closed"
        if "开放" in status:
            return "open"
        return "unknown"
