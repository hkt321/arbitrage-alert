from datetime import datetime
from typing import Any, Callable

from ..models.lof_snapshot import LofSnapshot
from .eastmoney_lof_spot_loader import EastmoneyLofSpotLoader
from .errors import DataSourceError


class AkshareLofProvider:
    SPOT_COLUMNS = {
        "代码",
        "名称",
        "最新价",
        "涨跌幅",
        "成交量",
        "成交额",
        "换手率",
    }
    PURCHASE_COLUMNS = {
        "基金代码",
        "基金简称",
        "最新净值/万份收益",
        "最新净值/万份收益-报告时间",
        "申购状态",
        "赎回状态",
        "日累计限定金额",
        "手续费",
    }

    def __init__(
        self,
        spot_loader: Callable[[], Any] | None = None,
        purchase_loader: Callable[[], Any] | None = None,
    ) -> None:
        self._spot_loader = spot_loader or EastmoneyLofSpotLoader().fetch_all
        if purchase_loader is None:
            import akshare as ak

            purchase_loader = ak.fund_purchase_em
        self._purchase_loader = purchase_loader

    def fetch_all(self) -> list[LofSnapshot]:
        try:
            spot = self._spot_loader()
            purchase = self._purchase_loader()
        except Exception as exc:
            raise DataSourceError(f"AkShare 数据获取失败: {exc}") from exc

        self._validate_table(spot, self.SPOT_COLUMNS, "行情表")
        self._validate_table(purchase, self.PURCHASE_COLUMNS, "申赎表")
        self._reject_duplicate_codes(spot, "代码", "行情表")
        self._reject_duplicate_codes(purchase, "基金代码", "申赎表")

        purchase_by_code = {
            self._normalize_code(row["基金代码"]): row
            for _, row in purchase.iterrows()
        }
        observed_at = datetime.now().astimezone().isoformat(timespec="seconds")
        snapshots = []
        for _, row in spot.iterrows():
            bare_code = self._normalize_code(row["代码"])
            status = purchase_by_code.get(bare_code)
            price = self._number(row.get("最新价"))
            nav = self._number(status.get("最新净值/万份收益")) if status is not None else None
            premium = None
            if price is not None and nav is not None and nav > 0:
                premium = round((price - nav) / nav * 100, 10)
            snapshots.append(
                LofSnapshot(
                    code=self._qualified_code(bare_code),
                    name=str(row.get("名称") or ""),
                    price=price,
                    price_change_pct=self._number(row.get("涨跌幅")),
                    volume=self._number(row.get("成交量")),
                    amount_yuan=self._number(row.get("成交额")),
                    turnover_pct=self._number(row.get("换手率")),
                    latest_nav=nav,
                    nav_date=self._text(status.get("最新净值/万份收益-报告时间")) if status is not None else None,
                    premium_pct=premium,
                    purchase_limit_yuan=self._number(status.get("日累计限定金额")) if status is not None else None,
                    subscription_status=self._map_subscription(status.get("申购状态")) if status is not None else "unknown",
                    redemption_status=self._map_redemption(status.get("赎回状态")) if status is not None else "unknown",
                    fee_pct=self._percentage(status.get("手续费")) if status is not None else None,
                    observed_at=observed_at,
                )
            )
        return snapshots

    @classmethod
    def _validate_table(cls, table: Any, required_columns: set[str], label: str) -> None:
        if table is None or not hasattr(table, "columns"):
            raise DataSourceError(f"{label}不是有效表格")
        missing = sorted(required_columns - set(table.columns))
        if missing:
            raise DataSourceError(f"{label}缺少字段: {', '.join(missing)}")
        if table.empty:
            raise DataSourceError(f"{label}为空")

    @classmethod
    def _reject_duplicate_codes(cls, table: Any, column: str, label: str) -> None:
        normalized = table[column].map(cls._normalize_code)
        duplicates = sorted(set(normalized[normalized.duplicated(keep=False)].tolist()))
        if duplicates:
            raise DataSourceError(f"{label}存在重复代码: {', '.join(duplicates)}")

    @staticmethod
    def _normalize_code(value: Any) -> str:
        return str(value).strip().split(".")[0].zfill(6)

    @staticmethod
    def _qualified_code(code: str) -> str:
        return ("SH" if code[0] in {"5", "6"} else "SZ") + code

    @staticmethod
    def _number(value: Any) -> float | None:
        try:
            if value is None or str(value).strip() in {"", "nan", "None", "--"}:
                return None
            return float(str(value).replace(",", ""))
        except (TypeError, ValueError):
            return None

    @classmethod
    def _percentage(cls, value: Any) -> float | None:
        return cls._number(str(value).replace("%", "")) if value is not None else None

    @staticmethod
    def _text(value: Any) -> str | None:
        if value is None or str(value).strip() in {"", "nan", "None", "--"}:
            return None
        return str(value).strip()

    @staticmethod
    def _map_subscription(value: Any) -> str:
        text = str(value or "")
        if "暂停" in text:
            return "closed"
        if "限" in text:
            return "limited"
        if "开放" in text:
            return "open"
        return "unknown"

    @staticmethod
    def _map_redemption(value: Any) -> str:
        text = str(value or "")
        if "暂停" in text:
            return "closed"
        if "开放" in text:
            return "open"
        return "unknown"
