from dataclasses import asdict, dataclass
from typing import Any


@dataclass
class LofSnapshot:
    code: str
    name: str
    price: float | None = None
    price_change_pct: float | None = None
    volume: float | None = None
    amount_yuan: float | None = None
    turnover_pct: float | None = None
    latest_nav: float | None = None
    nav_date: str | None = None
    premium_pct: float | None = None
    purchase_limit_yuan: float | None = None
    subscription_status: str = "unknown"
    redemption_status: str = "unknown"
    fee_pct: float | None = None
    source: str = "akshare_eastmoney"
    premium_basis: str = "latest_official_nav"
    observed_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
