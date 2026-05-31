from app.models.fund import FundProfile
from app.models.opportunity import OpportunityScore
from app.models.quote import QuoteSnapshot
from app.models.valuation import ValuationSnapshot


class OpportunityScorer:
    def __init__(
        self,
        min_edge_pct: float = 2.0,
        min_turnover_yuan: float = 50_000_000,
        desired_trade_yuan: float = 10_000,
    ) -> None:
        self.min_edge_pct = min_edge_pct
        self.min_turnover_yuan = min_turnover_yuan
        self.desired_trade_yuan = desired_trade_yuan

    def score(
        self,
        profile: FundProfile,
        quote: QuoteSnapshot,
        valuation: ValuationSnapshot,
    ) -> OpportunityScore:
        reasons = list(valuation.reasons)

        if valuation.tradable_edge_pct is None:
            reasons.append("缺少可交易边际")
            return self._build(profile, quote, valuation, "unavailable", 0, reasons)

        if valuation.tradable_edge_pct < self.min_edge_pct:
            reasons.append("可交易边际不足")

        if quote.turnover_yuan is None or quote.turnover_yuan < self.min_turnover_yuan:
            reasons.append("成交额不足")

        if not self._has_enough_top_quote(quote):
            reasons.append("买一卖一深度不足")

        if profile.subscription_status != "open":
            reasons.append(f"申购状态: {profile.subscription_status}")

        if profile.redemption_status not in ("open", "not_applicable"):
            reasons.append(f"赎回状态: {profile.redemption_status}")

        if self._requires_cash_subscription_limit(profile):
            if profile.purchase_limit_yuan is None:
                reasons.append("申购限额未知")
            elif profile.purchase_limit_yuan < self.desired_trade_yuan:
                reasons.append("申购限额低于计划交易额")

        if valuation.confidence in ("none", "low"):
            reasons.append(f"估值置信度: {valuation.confidence}")

        blocking = [
            "成交额不足",
            "买一卖一深度不足",
            "申购限额未知",
            "申购限额低于计划交易额",
            "估值置信度: none",
            "估值置信度: low",
        ]
        has_blocking = any(reason in reasons for reason in blocking) or profile.subscription_status != "open"

        if valuation.tradable_edge_pct >= self.min_edge_pct and not has_blocking:
            return self._build(profile, quote, valuation, "executable", valuation.tradable_edge_pct, reasons)

        if valuation.gross_premium_pct is not None and valuation.gross_premium_pct > 0:
            return self._build(profile, quote, valuation, "watch", max(valuation.tradable_edge_pct, 0), reasons)

        return self._build(profile, quote, valuation, "normal", 0, reasons)

    def _has_enough_top_quote(self, quote: QuoteSnapshot) -> bool:
        if quote.ask_price1 is None or quote.ask_volume1 is None:
            return False
        ask_value = quote.ask_price1 * quote.ask_volume1 * 100
        return ask_value >= self.desired_trade_yuan

    @staticmethod
    def _requires_cash_subscription_limit(profile: FundProfile) -> bool:
        return "LOF" in profile.asset_type

    def _build(
        self,
        profile: FundProfile,
        quote: QuoteSnapshot,
        valuation: ValuationSnapshot,
        level: str,
        score: float,
        reasons: list[str],
    ) -> OpportunityScore:
        return OpportunityScore(
            code=profile.code,
            name=profile.name,
            level=level,
            score=round(score, 4),
            reasons=list(dict.fromkeys(reasons)),
            execution=self._build_execution(profile, quote, level),
            quote=quote.to_dict(),
            valuation=valuation.to_dict(),
        )

    def _build_execution(
        self,
        profile: FundProfile,
        quote: QuoteSnapshot,
        level: str,
    ) -> dict[str, float | str | list[str] | None]:
        basis = []
        suggested_subscription_yuan = None

        if level == "executable":
            suggested_subscription_yuan = self.desired_trade_yuan
            basis.append(f"计划交易额 {self.desired_trade_yuan:.0f} 元")

            if self._requires_cash_subscription_limit(profile):
                if profile.purchase_limit_yuan is not None:
                    suggested_subscription_yuan = min(
                        suggested_subscription_yuan,
                        profile.purchase_limit_yuan,
                    )
                    basis.append(f"单日申购限额 {profile.purchase_limit_yuan:.0f} 元")
                else:
                    suggested_subscription_yuan = None
                    basis.append("现金申购限额未知")
            else:
                basis.append("ETF 最小申购单位暂未接入，金额仅作看板参考")

            if suggested_subscription_yuan is not None and quote.ask_price1 and quote.ask_volume1:
                ask_depth_yuan = quote.ask_price1 * quote.ask_volume1 * 100
                basis.append(f"卖一深度约 {ask_depth_yuan:.0f} 元")

        return {
            "suggestedSubscriptionYuan": suggested_subscription_yuan,
            "desiredTradeYuan": self.desired_trade_yuan,
            "purchaseLimitYuan": profile.purchase_limit_yuan,
            "basis": basis,
        }
