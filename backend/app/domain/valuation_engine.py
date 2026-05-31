from app.models.fund import FundProfile
from app.models.market_signal import ValuationSignalSet
from app.models.quote import QuoteSnapshot
from app.models.valuation import ValuationSnapshot


class ValuationEngine:
    def value(
        self,
        profile: FundProfile,
        quote: QuoteSnapshot,
        signals: ValuationSignalSet | None = None,
    ) -> ValuationSnapshot:
        if profile.valuation_model == "iopv":
            return self._value_iopv(profile, quote, signals)
        if profile.valuation_model == "index_proxy":
            return self._value_index_proxy(profile, quote, signals)
        if profile.valuation_model == "commodity_proxy":
            return self._value_commodity_proxy(profile, quote, signals)
        if profile.valuation_model == "qdii_proxy":
            return self._value_qdii_proxy(profile, quote, signals)
        return self._unsupported(profile, quote, signals)

    def _value_iopv(
        self,
        profile: FundProfile,
        quote: QuoteSnapshot,
        signals: ValuationSignalSet | None,
    ) -> ValuationSnapshot:
        reasons = []
        estimated_nav = quote.reference_nav
        if estimated_nav is None:
            reasons.append("缺少 IOPV/Jjjz")
        return self._build_snapshot(profile, quote, estimated_nav, "iopv", reasons, signals)

    def _value_index_proxy(
        self,
        profile: FundProfile,
        quote: QuoteSnapshot,
        signals: ValuationSignalSet | None,
    ) -> ValuationSnapshot:
        reasons = []
        if profile.last_official_nav is None:
            reasons.append("缺少最新官方净值")
            estimated_nav = None
        else:
            benchmark_return = signals.benchmark_return_pct if signals is not None else profile.proxy_return_pct
            index_return = benchmark_return * profile.beta
            estimated_nav = profile.last_official_nav * (1 + index_return / 100)
            reasons.append("使用指数代理估值")
        return self._build_snapshot(profile, quote, estimated_nav, "index_proxy", reasons, signals)

    def _value_commodity_proxy(
        self,
        profile: FundProfile,
        quote: QuoteSnapshot,
        signals: ValuationSignalSet | None,
    ) -> ValuationSnapshot:
        reasons = []
        if profile.last_official_nav is None:
            reasons.append("缺少最新官方净值")
            estimated_nav = None
        else:
            benchmark_return = signals.benchmark_return_pct if signals is not None else profile.proxy_return_pct
            proxy_return = benchmark_return * profile.beta
            estimated_nav = profile.last_official_nav * (1 + proxy_return / 100)
            reasons.append("使用商品期货代理估值")
        return self._build_snapshot(profile, quote, estimated_nav, "commodity_proxy", reasons, signals)

    def _value_qdii_proxy(
        self,
        profile: FundProfile,
        quote: QuoteSnapshot,
        signals: ValuationSignalSet | None,
    ) -> ValuationSnapshot:
        reasons = []
        if profile.last_official_nav is None:
            reasons.append("缺少最新官方净值")
            estimated_nav = None
        else:
            benchmark_return = signals.benchmark_return_pct if signals is not None else profile.proxy_return_pct
            base_fx_return = signals.fx_return_pct if signals is not None else profile.fx_return_pct
            proxy_return = benchmark_return * profile.beta
            fx_return = base_fx_return * profile.fx_exposure
            estimated_nav = profile.last_official_nav * (1 + proxy_return / 100) * (1 + fx_return / 100)
            reasons.append("使用 QDII 代理估值")
        return self._build_snapshot(profile, quote, estimated_nav, "qdii_proxy", reasons, signals)

    def _unsupported(
        self,
        profile: FundProfile,
        quote: QuoteSnapshot,
        signals: ValuationSignalSet | None,
    ) -> ValuationSnapshot:
        return self._build_snapshot(profile, quote, None, "unsupported", ["暂未支持该品种估值"], signals)

    def _build_snapshot(
        self,
        profile: FundProfile,
        quote: QuoteSnapshot,
        estimated_nav: float | None,
        model: str,
        reasons: list[str],
        signals: ValuationSignalSet | None,
    ) -> ValuationSnapshot:
        gross_premium_pct = None
        tradable_edge_pct = None

        if quote.market_price is None:
            reasons.append("缺少场内价格")
        if estimated_nav is not None and quote.market_price is not None and estimated_nav > 0:
            gross_premium_pct = (quote.market_price / estimated_nav - 1) * 100
            tradable_edge_pct = (
                gross_premium_pct
                - profile.fee_pct
                - profile.slippage_buffer_pct
                - profile.error_buffer_pct
            )

        if signals is not None:
            reasons.extend(signals.reasons())

        return ValuationSnapshot(
            code=profile.code,
            model=model,
            estimated_nav=estimated_nav,
            gross_premium_pct=gross_premium_pct,
            estimated_cost_pct=profile.fee_pct,
            slippage_buffer_pct=profile.slippage_buffer_pct,
            error_buffer_pct=profile.error_buffer_pct,
            tradable_edge_pct=tradable_edge_pct,
            confidence=self._confidence(profile, model, estimated_nav, signals),
            reasons=reasons,
            inputs={
                "trackingIndexCode": profile.tracking_index_code,
                "lastOfficialNav": profile.last_official_nav,
                "proxyReturnPct": profile.proxy_return_pct,
                "fxReturnPct": profile.fx_return_pct,
                "beta": profile.beta,
                "fxExposure": profile.fx_exposure,
                "benchmarkSignalId": profile.benchmark_signal_id,
                "fxSignalId": profile.fx_signal_id,
                "signals": signals.to_dict() if signals is not None else None,
            },
        )

    @staticmethod
    def _confidence(
        profile: FundProfile,
        model: str,
        estimated_nav: float | None,
        signals: ValuationSignalSet | None,
    ) -> str:
        if estimated_nav is None or model == "unsupported":
            return "none"

        confidence = profile.confidence_floor
        if signals is not None and model in ("index_proxy", "commodity_proxy", "qdii_proxy"):
            signal_confidences = [
                signal.confidence
                for signal in (signals.benchmark, signals.fx)
                if signal is not None
            ]
            if "none" in signal_confidences:
                return "none"
            if "low" in signal_confidences:
                confidence = "low"
            elif "medium" in signal_confidences and confidence == "high":
                confidence = "medium"

        if confidence == "high":
            return "high"
        if confidence == "medium":
            return "medium"
        return "low"
