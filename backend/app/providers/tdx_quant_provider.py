import sys
from pathlib import Path
from typing import Any

from app.models.quote import QuoteSnapshot


class TdxQuantProvider:
    def __init__(self, tdx_root: str = r"D:\TongDaXing") -> None:
        self.tdx_root = Path(tdx_root)
        self.plugin_dir = self.tdx_root / "PYPlugins" / "user"
        self._tq = None

    def connect(self, connection_path: str) -> None:
        if not self.plugin_dir.exists():
            raise RuntimeError(f"TdxQuant plugin directory not found: {self.plugin_dir}")

        sys.path.insert(0, str(self.plugin_dir))
        from tqcenter import tq

        tq.initialize(connection_path)
        self._tq = tq

    def close(self) -> None:
        if self._tq is not None:
            self._tq.close()

    def get_quote(self, code: str) -> QuoteSnapshot:
        if self._tq is None:
            raise RuntimeError("TdxQuantProvider is not connected")

        raw = self._tq.get_market_snapshot(stock_code=code, field_list=[])
        return self._to_quote_snapshot(code, raw)

    def get_quotes(self, codes: list[str]) -> list[QuoteSnapshot]:
        return [self.get_quote(code) for code in codes]

    def _to_quote_snapshot(self, code: str, raw: dict[str, Any]) -> QuoteSnapshot:
        market_price = self._num(raw.get("Now"))
        prev_close = self._num(raw.get("LastClose"))

        return QuoteSnapshot(
            code=code,
            market_price=market_price,
            prev_close=prev_close,
            open_price=self._num(raw.get("Open")),
            high_price=self._num(raw.get("Max")),
            low_price=self._num(raw.get("Min")),
            volume=self._num(raw.get("Volume")),
            turnover_yuan=self._amount_to_yuan(raw.get("Amount")),
            bid_price1=self._list_num(raw.get("Buyp"), 0),
            bid_volume1=self._list_num(raw.get("Buyv"), 0),
            ask_price1=self._list_num(raw.get("Sellp"), 0),
            ask_volume1=self._list_num(raw.get("Sellv"), 0),
            reference_nav=self._zero_as_none(raw.get("Jjjz")),
            average_price=self._num(raw.get("Average")),
            change_pct=self._change_pct(market_price, prev_close, raw.get("ZAFPre3")),
            raw=raw,
        )

    @staticmethod
    def _num(value: Any) -> float | None:
        try:
            if value is None or value == "":
                return None
            return float(value)
        except (TypeError, ValueError):
            return None

    @classmethod
    def _zero_as_none(cls, value: Any) -> float | None:
        number = cls._num(value)
        if number == 0:
            return None
        return number

    @classmethod
    def _list_num(cls, value: Any, index: int) -> float | None:
        if not isinstance(value, list) or len(value) <= index:
            return None
        return cls._num(value[index])

    @classmethod
    def _amount_to_yuan(cls, value: Any) -> float | None:
        amount_wan = cls._num(value)
        if amount_wan is None:
            return None
        return amount_wan * 10000

    @classmethod
    def _change_pct(cls, market_price: float | None, prev_close: float | None, fallback: Any) -> float | None:
        if market_price is not None and prev_close:
            return (market_price / prev_close - 1) * 100
        return cls._num(fallback)
