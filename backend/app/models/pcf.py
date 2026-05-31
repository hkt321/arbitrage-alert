from dataclasses import asdict, dataclass
from typing import Any


@dataclass
class PcfSnapshot:
    code: str
    fund_name: str | None
    trade_date: str | None
    creation_redemption_unit: float | None
    creation_status: str
    redemption_status: str
    cash_substitute_ratio_pct: float | None
    estimated_cash_component: float | None
    cash_difference: float | None
    raw_shfe: float | None
    raw_jzrfe: float | None
    component_count: int | None
    raw: dict[str, Any]
    source: str = "tdx_pcf"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
