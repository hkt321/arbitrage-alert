from dataclasses import asdict, dataclass
from typing import Any


@dataclass
class ValuationSnapshot:
    code: str
    model: str
    estimated_nav: float | None
    gross_premium_pct: float | None
    estimated_cost_pct: float
    slippage_buffer_pct: float
    error_buffer_pct: float
    tradable_edge_pct: float | None
    confidence: str
    reasons: list[str]
    inputs: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
