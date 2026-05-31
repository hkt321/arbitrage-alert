from dataclasses import asdict, dataclass
from typing import Any


@dataclass
class OpportunityScore:
    code: str
    name: str
    level: str
    score: float
    reasons: list[str]
    execution: dict[str, Any]
    quote: dict[str, Any]
    valuation: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
