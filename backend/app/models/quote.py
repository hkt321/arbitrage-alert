from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any


@dataclass
class QuoteSnapshot:
    code: str
    market_price: float | None
    prev_close: float | None
    open_price: float | None
    high_price: float | None
    low_price: float | None
    volume: float | None
    turnover_yuan: float | None
    bid_price1: float | None
    bid_volume1: float | None
    ask_price1: float | None
    ask_volume1: float | None
    reference_nav: float | None
    average_price: float | None
    change_pct: float | None
    raw: dict[str, Any]
    source: str = "tdx_quant"
    quote_time: str = ""

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["quote_time"] = self.quote_time or datetime.now().isoformat(timespec="seconds")
        return data
