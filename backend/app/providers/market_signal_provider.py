from datetime import datetime
from typing import Any

from app.models.market_signal import MarketSignal
from app.providers.tdx_quant_provider import TdxQuantProvider


class MarketSignalProvider:
    def __init__(
        self,
        signal_configs: dict[str, dict[str, Any]],
        quote_provider: TdxQuantProvider | None = None,
    ) -> None:
        self.signal_configs = signal_configs
        self.quote_provider = quote_provider
        self._cache: dict[str, MarketSignal] = {}

    def get_signal(self, signal_id: str | None) -> MarketSignal | None:
        if not signal_id:
            return None
        if signal_id in self._cache:
            return self._cache[signal_id]

        config = self.signal_configs.get(signal_id)
        if config is None:
            signal = self._missing_signal(signal_id)
        elif config.get("source") == "tdx_quote":
            signal = self._tdx_quote_signal(signal_id, config)
        elif config.get("source") == "tdx_candidate_quote":
            signal = self._tdx_candidate_quote_signal(signal_id, config)
        elif config.get("source") == "manual":
            signal = self._manual_signal(signal_id, config)
        else:
            signal = self._unsupported_signal(signal_id, config)

        self._cache[signal_id] = signal
        return signal

    def _tdx_candidate_quote_signal(self, signal_id: str, config: dict[str, Any]) -> MarketSignal:
        codes = config.get("candidateCodes", [])
        if not isinstance(codes, list) or not codes:
            return self._base_signal(
                signal_id,
                config,
                return_pct=None,
                source="tdx_candidate_quote",
                confidence="none",
                reasons=["候选合约列表为空"],
            )

        if self.quote_provider is None:
            return self._base_signal(
                signal_id,
                config,
                return_pct=None,
                source="tdx_candidate_quote",
                confidence="none",
                reasons=["缺少通达信行情 Provider"],
            )

        quotes = []
        failed: list[str] = []
        for code in codes:
            try:
                quote = self.quote_provider.get_quote(str(code))
                if quote.market_price is not None:
                    quotes.append(quote)
            except Exception:
                failed.append(str(code))

        if not quotes:
            return self._base_signal(
                signal_id,
                config,
                return_pct=None,
                source="tdx_candidate_quote",
                confidence="none",
                reasons=["候选合约均无法获取行情"],
            )

        selected = max(quotes, key=lambda item: item.volume or 0)
        return_pct = self._quote_return_pct(selected)
        reasons = [f"使用成交量最大候选合约 {selected.code}"]
        if failed:
            reasons.append(f"部分候选合约不可用: {', '.join(failed)}")
        if return_pct is None:
            reasons.append("无法从候选合约计算涨跌幅")

        return MarketSignal(
            id=signal_id,
            name=config.get("name", signal_id),
            kind=config.get("kind", "benchmark"),
            return_pct=return_pct,
            source="tdx_candidate_quote",
            price=selected.market_price,
            prev_close=selected.prev_close,
            currency=config.get("currency"),
            confidence=config.get("confidence", "medium") if return_pct is not None else "none",
            reasons=reasons,
            raw={
                "selectedCode": selected.code,
                "candidateCodes": codes,
                "quote": selected.to_dict(),
            },
            quote_time=datetime.now().isoformat(timespec="seconds"),
        )

    def _tdx_quote_signal(self, signal_id: str, config: dict[str, Any]) -> MarketSignal:
        if self.quote_provider is None:
            return self._base_signal(
                signal_id,
                config,
                return_pct=None,
                source="tdx_quote",
                confidence="none",
                reasons=["缺少通达信行情 Provider"],
            )

        code = config.get("code")
        if not code:
            return self._base_signal(
                signal_id,
                config,
                return_pct=None,
                source="tdx_quote",
                confidence="none",
                reasons=["信号缺少通达信代码"],
            )

        try:
            quote = self.quote_provider.get_quote(code)
        except Exception as exc:
            return self._base_signal(
                signal_id,
                config,
                return_pct=None,
                source="tdx_quote",
                confidence="none",
                reasons=[f"通达信行情信号拉取失败: {exc}"],
            )
        return_pct = self._quote_return_pct(quote)

        reasons = []
        confidence = config.get("confidence", "medium")
        if return_pct is None:
            confidence = "none"
            reasons.append("无法从通达信行情计算涨跌幅")

        return MarketSignal(
            id=signal_id,
            name=config.get("name", signal_id),
            kind=config.get("kind", "benchmark"),
            return_pct=return_pct,
            source="tdx_quote",
            price=quote.market_price,
            prev_close=quote.prev_close,
            currency=config.get("currency"),
            confidence=confidence,
            reasons=reasons,
            raw={"code": code, "quote": quote.to_dict()},
            quote_time=datetime.now().isoformat(timespec="seconds"),
        )

    def _manual_signal(self, signal_id: str, config: dict[str, Any]) -> MarketSignal:
        reasons = list(config.get("reasons", []))
        if not reasons:
            reasons.append("使用人工配置行情信号")

        return self._base_signal(
            signal_id,
            config,
            return_pct=self._num(config.get("returnPct")),
            source="manual",
            confidence=config.get("confidence", "low"),
            reasons=reasons,
        )

    def _unsupported_signal(self, signal_id: str, config: dict[str, Any]) -> MarketSignal:
        return self._base_signal(
            signal_id,
            config,
            return_pct=None,
            source=str(config.get("source", "unknown")),
            confidence="none",
            reasons=["暂未支持该行情信号来源"],
        )

    def _missing_signal(self, signal_id: str) -> MarketSignal:
        return MarketSignal(
            id=signal_id,
            name=signal_id,
            kind="unknown",
            return_pct=None,
            source="missing",
            confidence="none",
            reasons=["未配置行情信号"],
        )

    @staticmethod
    def _base_signal(
        signal_id: str,
        config: dict[str, Any],
        return_pct: float | None,
        source: str,
        confidence: str,
        reasons: list[str],
    ) -> MarketSignal:
        return MarketSignal(
            id=signal_id,
            name=config.get("name", signal_id),
            kind=config.get("kind", "benchmark"),
            return_pct=return_pct,
            source=source,
            currency=config.get("currency"),
            confidence=confidence,
            reasons=reasons,
            raw=dict(config),
            quote_time=datetime.now().isoformat(timespec="seconds"),
        )

    @staticmethod
    def _num(value: Any) -> float | None:
        try:
            if value is None or value == "":
                return None
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _quote_return_pct(quote: Any) -> float | None:
        return quote.change_pct
