from dataclasses import asdict, dataclass
from typing import Any


@dataclass
class FundStatus:
    code: str
    name: str
    fund_type: str
    latest_nav: float | None
    nav_date: str | None
    subscription_status: str
    redemption_status: str
    next_open_date: str | None
    min_purchase_yuan: float | None
    purchase_limit_yuan: float | None
    fee_pct: float | None
    raw_subscription_status: str
    raw_redemption_status: str
    raw: list[Any]
    source: str = "eastmoney_fund_status"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
