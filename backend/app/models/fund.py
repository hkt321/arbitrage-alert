from dataclasses import dataclass
from typing import Any


@dataclass
class FundProfile:
    code: str
    name: str
    asset_type: str
    valuation_model: str
    tracking_index_code: str | None
    subscription_status: str
    redemption_status: str
    purchase_limit_yuan: float | None
    fee_pct: float
    slippage_buffer_pct: float
    error_buffer_pct: float
    confidence_floor: str
    last_official_nav: float | None = None
    proxy_return_pct: float = 0
    fx_return_pct: float = 0
    beta: float = 1
    fx_exposure: float = 1
    benchmark_signal_id: str | None = None
    fx_signal_id: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "FundProfile":
        return cls(
            code=data["code"],
            name=data["name"],
            asset_type=data["assetType"],
            valuation_model=data["valuationModel"],
            tracking_index_code=data.get("trackingIndexCode"),
            subscription_status=data.get("subscriptionStatus", "unknown"),
            redemption_status=data.get("redemptionStatus", "unknown"),
            purchase_limit_yuan=data.get("purchaseLimitYuan"),
            fee_pct=float(data.get("feePct", 0)),
            slippage_buffer_pct=float(data.get("slippageBufferPct", 0)),
            error_buffer_pct=float(data.get("errorBufferPct", 0)),
            confidence_floor=data.get("confidenceFloor", "low"),
            last_official_nav=data.get("lastOfficialNav"),
            proxy_return_pct=float(data.get("proxyReturnPct", 0)),
            fx_return_pct=float(data.get("fxReturnPct", 0)),
            beta=float(data.get("beta", 1)),
            fx_exposure=float(data.get("fxExposure", 1)),
            benchmark_signal_id=data.get("benchmarkSignalId"),
            fx_signal_id=data.get("fxSignalId"),
        )
