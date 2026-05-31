from dataclasses import replace

from app.models.fund import FundProfile
from app.models.market_signal import ValuationSignalSet
from app.providers.market_signal_provider import MarketSignalProvider


class ValuationSignalResolver:
    def __init__(self, provider: MarketSignalProvider) -> None:
        self.provider = provider

    def resolve(self, profile: FundProfile) -> tuple[FundProfile, ValuationSignalSet]:
        signals = ValuationSignalSet(
            benchmark=self.provider.get_signal(profile.benchmark_signal_id),
            fx=self.provider.get_signal(profile.fx_signal_id),
        )

        return (
            replace(
                profile,
                proxy_return_pct=signals.benchmark_return_pct,
                fx_return_pct=signals.fx_return_pct,
            ),
            signals,
        )
