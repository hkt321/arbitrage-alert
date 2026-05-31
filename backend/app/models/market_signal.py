from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class MarketSignal:
    id: str
    name: str
    kind: str
    return_pct: float | None
    source: str
    price: float | None = None
    prev_close: float | None = None
    currency: str | None = None
    confidence: str = "low"
    reasons: list[str] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)
    quote_time: str = ""

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["quote_time"] = self.quote_time or datetime.now().isoformat(timespec="seconds")
        return data


@dataclass
class ValuationSignalSet:
    benchmark: MarketSignal | None = None
    fx: MarketSignal | None = None

    @property
    def benchmark_return_pct(self) -> float:
        if self.benchmark is None or self.benchmark.return_pct is None:
            return 0
        return self.benchmark.return_pct

    @property
    def fx_return_pct(self) -> float:
        if self.fx is None or self.fx.return_pct is None:
            return 0
        return self.fx.return_pct

    def reasons(self) -> list[str]:
        output: list[str] = []
        for signal in (self.benchmark, self.fx):
            if signal is None:
                continue
            output.extend(signal.reasons)
        return output

    def to_dict(self) -> dict[str, Any]:
        return {
            "benchmark": self.benchmark.to_dict() if self.benchmark else None,
            "fx": self.fx.to_dict() if self.fx else None,
        }
