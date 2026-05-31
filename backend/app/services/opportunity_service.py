import json
from dataclasses import replace
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from app.domain.opportunity_scorer import OpportunityScorer
from app.domain.valuation_engine import ValuationEngine
from app.domain.valuation_signal_resolver import ValuationSignalResolver
from app.models.fund import FundProfile
from app.providers.eastmoney_fund_status_provider import EastmoneyFundStatusProvider
from app.providers.market_signal_provider import MarketSignalProvider
from app.providers.tdx_pcf_provider import TdxPcfProvider
from app.providers.tdx_quant_provider import TdxQuantProvider


class OpportunityService:
    def __init__(self, backend_root: Path | None = None) -> None:
        self.backend_root = backend_root or Path(__file__).resolve().parents[2]

    def score_watchlist(self, connection_path: str) -> list[dict[str, Any]]:
        quote_provider = TdxQuantProvider()
        pcf_provider = TdxPcfProvider()
        status_provider = EastmoneyFundStatusProvider()
        signal_provider = MarketSignalProvider(self.load_signal_configs(), quote_provider)
        signal_resolver = ValuationSignalResolver(signal_provider)
        valuation_engine = ValuationEngine()
        scorer = OpportunityScorer()
        trade_date = self.latest_weekday()

        quote_provider.connect(connection_path)
        pcf_provider.connect(connection_path)
        try:
            results = []
            for profile in self.load_profiles():
                profile = self.apply_fund_status(profile, status_provider)
                profile = self.apply_pcf(profile, pcf_provider, trade_date)
                profile, signals = signal_resolver.resolve(profile)
                quote = quote_provider.get_quote(profile.code)
                valuation = valuation_engine.value(profile, quote, signals)
                results.append(scorer.score(profile, quote, valuation).to_dict())

            results.sort(key=lambda item: item["score"], reverse=True)
            return results
        finally:
            quote_provider.close()
            pcf_provider.close()

    def fetch_valuation_signals(self, connection_path: str) -> list[dict[str, Any]]:
        quote_provider = TdxQuantProvider()
        quote_provider.connect(connection_path)
        try:
            signal_provider = MarketSignalProvider(self.load_signal_configs(), quote_provider)
            return [
                signal_provider.get_signal(signal_id).to_dict()
                for signal_id in self.load_signal_configs()
            ]
        finally:
            quote_provider.close()

    def load_profiles(self) -> list[FundProfile]:
        data = json.loads(self._config_path("fund_profiles.json").read_text(encoding="utf-8"))
        return [FundProfile.from_dict(item) for item in data]

    def load_signal_configs(self) -> dict[str, dict[str, Any]]:
        data = json.loads(self._config_path("valuation_signals.json").read_text(encoding="utf-8"))
        return {item["id"]: item for item in data["signals"]}

    def _config_path(self, name: str) -> Path:
        return self.backend_root / "app" / "config" / name

    @staticmethod
    def latest_weekday() -> str:
        day = datetime.now()
        while day.weekday() >= 5:
            day -= timedelta(days=1)
        return day.strftime("%Y%m%d")

    @staticmethod
    def apply_pcf(profile: FundProfile, pcf_provider: TdxPcfProvider, trade_date: str) -> FundProfile:
        if "ETF" not in profile.asset_type:
            return profile

        pcf = pcf_provider.get_etf_pcf(profile.code, trade_date)
        if pcf is None:
            return profile

        return replace(
            profile,
            subscription_status=pcf.creation_status,
            redemption_status=pcf.redemption_status,
        )

    @staticmethod
    def apply_fund_status(profile: FundProfile, status_provider: EastmoneyFundStatusProvider) -> FundProfile:
        if "ETF" in profile.asset_type:
            return profile
        return status_provider.apply_to_profile(profile)
