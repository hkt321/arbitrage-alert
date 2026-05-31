import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.domain.opportunity_scorer import OpportunityScorer
from app.domain.valuation_engine import ValuationEngine
from app.models.fund import FundProfile
from app.models.market_signal import MarketSignal, ValuationSignalSet
from app.models.quote import QuoteSnapshot
from app.providers.eastmoney_fund_status_provider import EastmoneyFundStatusProvider
from app.providers.market_signal_provider import MarketSignalProvider
from app.providers.tdx_pcf_provider import TdxPcfProvider
from app.providers.tdx_quant_provider import TdxQuantProvider


class DomainTest(unittest.TestCase):
    def test_iopv_etf_can_be_executable_when_controls_pass(self):
        profile = FundProfile.from_dict(
            {
                "code": "510000.SH",
                "name": "测试ETF",
                "assetType": "ETF",
                "valuationModel": "iopv",
                "trackingIndexCode": "TEST",
                "subscriptionStatus": "open",
                "redemptionStatus": "open",
                "purchaseLimitYuan": 1_000_000,
                "feePct": 0.03,
                "slippageBufferPct": 0.02,
                "errorBufferPct": 0.05,
                "confidenceFloor": "high",
            }
        )
        quote = QuoteSnapshot(
            code="510000.SH",
            market_price=1.05,
            prev_close=1,
            open_price=1,
            high_price=1.05,
            low_price=1,
            volume=10_000_000,
            turnover_yuan=100_000_000,
            bid_price1=1.049,
            bid_volume1=100_000,
            ask_price1=1.05,
            ask_volume1=100_000,
            reference_nav=1,
            average_price=1.02,
            change_pct=5,
            raw={},
        )

        valuation = ValuationEngine().value(profile, quote)
        score = OpportunityScorer(min_edge_pct=2).score(profile, quote, valuation)

        self.assertEqual(score.level, "executable")
        self.assertGreater(score.score, 2)
        self.assertEqual(score.execution["purchaseLimitYuan"], 1_000_000)

    def test_low_purchase_limit_blocks_execution(self):
        profile = FundProfile.from_dict(
            {
                "code": "162411.SZ",
                "name": "测试LOF",
                "assetType": "QDII-LOF",
                "valuationModel": "qdii_proxy",
                "trackingIndexCode": "TEST",
                "lastOfficialNav": 1,
                "subscriptionStatus": "limited",
                "redemptionStatus": "open",
                "purchaseLimitYuan": 100,
                "feePct": 0.5,
                "slippageBufferPct": 0.2,
                "errorBufferPct": 1,
                "confidenceFloor": "low",
            }
        )
        quote = QuoteSnapshot(
            code="162411.SZ",
            market_price=1.2,
            prev_close=1.1,
            open_price=1.1,
            high_price=1.2,
            low_price=1.1,
            volume=10_000_000,
            turnover_yuan=100_000_000,
            bid_price1=1.19,
            bid_volume1=100_000,
            ask_price1=1.2,
            ask_volume1=100_000,
            reference_nav=None,
            average_price=1.15,
            change_pct=5,
            raw={},
        )

        valuation = ValuationEngine().value(profile, quote)
        score = OpportunityScorer(min_edge_pct=2, desired_trade_yuan=10_000).score(profile, quote, valuation)

        self.assertEqual(score.level, "watch")
        self.assertIn("申购限额低于计划交易额", score.reasons)

    def test_etf_does_not_require_cash_subscription_limit(self):
        profile = FundProfile.from_dict(
            {
                "code": "510000.SH",
                "name": "测试ETF",
                "assetType": "ETF",
                "valuationModel": "iopv",
                "trackingIndexCode": "TEST",
                "subscriptionStatus": "open",
                "redemptionStatus": "open",
                "purchaseLimitYuan": None,
                "feePct": 0.03,
                "slippageBufferPct": 0.02,
                "errorBufferPct": 0.05,
                "confidenceFloor": "high",
            }
        )
        quote = QuoteSnapshot(
            code="510000.SH",
            market_price=1.05,
            prev_close=1,
            open_price=1,
            high_price=1.05,
            low_price=1,
            volume=10_000_000,
            turnover_yuan=100_000_000,
            bid_price1=1.049,
            bid_volume1=100_000,
            ask_price1=1.05,
            ask_volume1=100_000,
            reference_nav=1,
            average_price=1.02,
            change_pct=5,
            raw={},
        )

        valuation = ValuationEngine().value(profile, quote)
        score = OpportunityScorer(min_edge_pct=2).score(profile, quote, valuation)

        self.assertEqual(score.level, "executable")
        self.assertNotIn("申购限额未知", score.reasons)

    def test_pcf_switch_parser_blocks_creation_only(self):
        creation, redemption = TdxPcfProvider._parse_switch("禁止申购允许赎回")

        self.assertEqual(creation, "closed")
        self.assertEqual(redemption, "open")

    def test_eastmoney_status_parser_maps_limit_and_pause(self):
        row = [
            "162411",
            "华宝标普油气上游股票人民币A",
            "指数型-海外股票",
            "0.8731",
            "05-28",
            "暂停申购",
            "开放赎回",
            "",
            "10.0",
            "10.0",
            "1.0",
            "4",
            "0.15%",
        ]

        status = EastmoneyFundStatusProvider._to_status(row)

        self.assertEqual(status.subscription_status, "closed")
        self.assertEqual(status.redemption_status, "open")
        self.assertEqual(status.latest_nav, 0.8731)
        self.assertEqual(status.purchase_limit_yuan, 10.0)
        self.assertEqual(status.fee_pct, 0.15)

    def test_manual_market_signal_provider(self):
        provider = MarketSignalProvider(
            {
                "OIL_PROXY": {
                    "id": "OIL_PROXY",
                    "name": "Oil proxy",
                    "kind": "benchmark",
                    "source": "manual",
                    "returnPct": 1.25,
                    "currency": "USD",
                    "confidence": "low",
                }
            }
        )

        signal = provider.get_signal("OIL_PROXY")

        self.assertEqual(signal.return_pct, 1.25)
        self.assertEqual(signal.source, "manual")
        self.assertEqual(signal.confidence, "low")

    def test_tdx_quote_change_pct_prefers_price_ratio(self):
        quote = TdxQuantProvider()._to_quote_snapshot(
            "AG2608.SHF",
            {
                "Now": "18323",
                "LastClose": "18206",
                "Open": "18294",
                "Max": "18485",
                "Min": "18060",
                "Volume": "508787",
                "Amount": "13952405.00",
                "Buyp": ["18322"],
                "Buyv": ["5"],
                "Sellp": ["18323"],
                "Sellv": ["3"],
                "Jjjz": "0",
                "Average": "18281",
                "ZAFPre3": "0.00",
            },
        )

        self.assertAlmostEqual(quote.change_pct, 0.6426452817752448)

    def test_valuation_engine_uses_signal_inputs(self):
        profile = FundProfile.from_dict(
            {
                "code": "162411.SZ",
                "name": "测试QDII",
                "assetType": "QDII-LOF",
                "valuationModel": "qdii_proxy",
                "trackingIndexCode": "TEST",
                "lastOfficialNav": 1,
                "benchmarkSignalId": "BENCH",
                "fxSignalId": "FX",
                "beta": 1,
                "fxExposure": 1,
                "subscriptionStatus": "open",
                "redemptionStatus": "open",
                "purchaseLimitYuan": 100_000,
                "feePct": 0.5,
                "slippageBufferPct": 0.2,
                "errorBufferPct": 1,
                "confidenceFloor": "low",
            }
        )
        quote = QuoteSnapshot(
            code="162411.SZ",
            market_price=1.05,
            prev_close=1,
            open_price=1,
            high_price=1.05,
            low_price=1,
            volume=10_000_000,
            turnover_yuan=100_000_000,
            bid_price1=1.04,
            bid_volume1=100_000,
            ask_price1=1.05,
            ask_volume1=100_000,
            reference_nav=None,
            average_price=1.02,
            change_pct=5,
            raw={},
        )
        signals = ValuationSignalSet(
            benchmark=MarketSignal(
                id="BENCH",
                name="Benchmark",
                kind="benchmark",
                return_pct=2,
                source="manual",
            ),
            fx=MarketSignal(
                id="FX",
                name="FX",
                kind="fx",
                return_pct=1,
                source="manual",
            ),
        )

        valuation = ValuationEngine().value(
            profile,
            quote,
            signals,
        )

        self.assertAlmostEqual(valuation.estimated_nav, 1.0302)
        self.assertEqual(valuation.confidence, "low")
        self.assertEqual(valuation.inputs["signals"]["benchmark"]["id"], "BENCH")

    def test_commodity_proxy_uses_benchmark_without_fx(self):
        profile = FundProfile.from_dict(
            {
                "code": "161226.SZ",
                "name": "测试商品LOF",
                "assetType": "COMMODITY-LOF",
                "valuationModel": "commodity_proxy",
                "trackingIndexCode": "SILVER",
                "lastOfficialNav": 2,
                "benchmarkSignalId": "SILVER_PROXY",
                "subscriptionStatus": "open",
                "redemptionStatus": "open",
                "purchaseLimitYuan": 100_000,
                "feePct": 0.1,
                "slippageBufferPct": 0.2,
                "errorBufferPct": 1,
                "confidenceFloor": "medium",
            }
        )
        quote = QuoteSnapshot(
            code="161226.SZ",
            market_price=2.1,
            prev_close=2,
            open_price=2,
            high_price=2.1,
            low_price=2,
            volume=10_000_000,
            turnover_yuan=100_000_000,
            bid_price1=2.09,
            bid_volume1=100_000,
            ask_price1=2.1,
            ask_volume1=100_000,
            reference_nav=None,
            average_price=2.05,
            change_pct=5,
            raw={},
        )
        signals = ValuationSignalSet(
            benchmark=MarketSignal(
                id="SILVER_PROXY",
                name="Silver",
                kind="benchmark",
                return_pct=3,
                source="tdx_candidate_quote",
                confidence="medium",
            )
        )

        valuation = ValuationEngine().value(profile, quote, signals)

        self.assertAlmostEqual(valuation.estimated_nav, 2.06)
        self.assertEqual(valuation.model, "commodity_proxy")
        self.assertEqual(valuation.confidence, "medium")


if __name__ == "__main__":
    unittest.main()
