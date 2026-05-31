import json
import sys
from dataclasses import replace
from datetime import datetime, timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from app.domain.opportunity_scorer import OpportunityScorer
from app.domain.valuation_engine import ValuationEngine
from app.domain.valuation_signal_resolver import ValuationSignalResolver
from app.models.fund import FundProfile
from app.providers.eastmoney_fund_status_provider import EastmoneyFundStatusProvider
from app.providers.market_signal_provider import MarketSignalProvider
from app.providers.tdx_pcf_provider import TdxPcfProvider
from app.providers.tdx_quant_provider import TdxQuantProvider


def load_profiles() -> list[FundProfile]:
    path = BACKEND / "app" / "config" / "fund_profiles.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    return [FundProfile.from_dict(item) for item in data]


def load_signal_configs() -> dict[str, dict]:
    path = BACKEND / "app" / "config" / "valuation_signals.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    return {item["id"]: item for item in data["signals"]}


def latest_weekday() -> str:
    day = datetime.now()
    while day.weekday() >= 5:
        day -= timedelta(days=1)
    return day.strftime("%Y%m%d")


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


def apply_fund_status(profile: FundProfile, status_provider: EastmoneyFundStatusProvider) -> FundProfile:
    if "ETF" in profile.asset_type:
        return profile
    return status_provider.apply_to_profile(profile)


def main() -> None:
    profiles = load_profiles()
    provider = TdxQuantProvider()
    pcf_provider = TdxPcfProvider()
    status_provider = EastmoneyFundStatusProvider()
    signal_provider = MarketSignalProvider(load_signal_configs(), provider)
    signal_resolver = ValuationSignalResolver(signal_provider)
    valuation_engine = ValuationEngine()
    scorer = OpportunityScorer()
    trade_date = latest_weekday()

    provider.connect(__file__)
    pcf_provider.connect(__file__)
    try:
        results = []
        for profile in profiles:
            profile = apply_fund_status(profile, status_provider)
            profile = apply_pcf(profile, pcf_provider, trade_date)
            profile, signals = signal_resolver.resolve(profile)
            quote = provider.get_quote(profile.code)
            valuation = valuation_engine.value(profile, quote, signals)
            results.append(scorer.score(profile, quote, valuation).to_dict())

        results.sort(key=lambda item: item["score"], reverse=True)
        print(json.dumps(results, ensure_ascii=False, indent=2, default=str))
    finally:
        provider.close()
        pcf_provider.close()


if __name__ == "__main__":
    main()
