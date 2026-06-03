from dataclasses import dataclass, field, asdict
from typing import Any


@dataclass
class PalmmicroLofSnapshot:
    """Parsed data from palmmicro.com LOF fund detail page."""

    code: str
    """e.g. 'SZ161128'"""

    name: str
    """Fund name e.g. '标普信息科技LOF'"""

    est_nav: float | None = None
    """Official EST NAV value"""

    est_date: str | None = None
    """EST date e.g. '2026-06-02'"""

    est_premium_pct: float | None = None
    """Premium based on official EST"""

    realtime_nav: float | None = None
    """Realtime EST NAV value"""

    realtime_premium_pct: float | None = None
    """Premium based on realtime EST"""

    # From fundsharetable
    shares_wan: float | None = None
    """场内总份额(万)"""

    shares_delta_wan: float | None = None
    """场内新增份额(万), negative means reduction"""

    volume: int | None = None
    """当日成交量(手)"""

    turnover_pct: float | None = None
    """换手率"""

    # From tradingtable (5-level order book)
    bid_price1: float | None = None
    bid_volume1: int | None = None
    ask_price1: float | None = None
    ask_volume1: int | None = None

    price: float | None = None
    """Current market price from referencetable"""

    price_change_pct: float | None = None
    """Price change %"""

    purchase_limit_yuan: float | None = None
    """申购限额(元) from Eastmoney"""

    subscription_status: str | None = None
    """申购状态: open/closed/limited/unknown"""

    redemption_status: str | None = None
    """赎回状态: open/closed/unknown"""

    fee_pct: float | None = None
    """申购费率%"""

    raw: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)