import json
import sys
from pathlib import Path
from typing import Any

from app.models.pcf import PcfSnapshot


class TdxPcfProvider:
    def __init__(self, tdx_root: str = r"D:\TongDaXing") -> None:
        self.tdx_root = Path(tdx_root)
        self.plugin_dir = self.tdx_root / "PYPlugins" / "user"
        self.data_dir = self.tdx_root / "PYPlugins" / "data"
        self._tq = None

    def connect(self, connection_path: str) -> None:
        if not self.plugin_dir.exists():
            raise RuntimeError(f"TdxQuant plugin directory not found: {self.plugin_dir}")

        sys.path.insert(0, str(self.plugin_dir))
        from tqcenter import tq

        tq.initialize(connection_path)
        self._tq = tq

    def close(self) -> None:
        if self._tq is not None:
            self._tq.close()

    def get_etf_pcf(self, code: str, trade_date: str) -> PcfSnapshot | None:
        if self._tq is None:
            raise RuntimeError("TdxPcfProvider is not connected")

        self._tq.download_file(stock_code=code, down_time=trade_date, down_type=2)
        path = self._pcf_path(code, trade_date)
        if not path.exists():
            return None

        payload = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(payload, dict) and payload.get("ErrorCode"):
            return None
        if not isinstance(payload, list) or not payload:
            return None

        return self._to_snapshot(code, payload[0])

    def _pcf_path(self, code: str, trade_date: str) -> Path:
        numeric_code = code.split(".")[0].lower()
        return self.data_dir / f"etfpcf{numeric_code}_{trade_date}.json"

    def _to_snapshot(self, code: str, raw: dict[str, Any]) -> PcfSnapshot:
        creation_status, redemption_status = self._parse_switch(str(raw.get("sgshqk", "")))
        unit = self._num(raw.get("sgfe"))

        return PcfSnapshot(
            code=code,
            fund_name=raw.get("jjjc"),
            trade_date=raw.get("jzrq"),
            creation_redemption_unit=unit,
            creation_status=creation_status,
            redemption_status=redemption_status,
            cash_substitute_ratio_pct=self._num(raw.get("xjtdbl")),
            estimated_cash_component=self._num(raw.get("ygxj")),
            cash_difference=self._num(raw.get("xjce")),
            raw_shfe=self._num(raw.get("shfe")),
            raw_jzrfe=self._num(raw.get("jzrfe")),
            component_count=self._int(raw.get("cfgs")),
            raw=raw,
        )

    @staticmethod
    def _parse_switch(text: str) -> tuple[str, str]:
        if "皆允许" in text or "申购和赎回皆允许" in text:
            return "open", "open"
        if "禁止申购允许赎回" in text:
            return "closed", "open"
        if "允许申购禁止赎回" in text:
            return "open", "closed"
        if "禁止申购" in text and "禁止赎回" in text:
            return "closed", "closed"
        return "unknown", "unknown"

    @staticmethod
    def _num(value: Any) -> float | None:
        try:
            if value is None or value == "":
                return None
            return float(value)
        except (TypeError, ValueError):
            return None

    @classmethod
    def _int(cls, value: Any) -> int | None:
        number = cls._num(value)
        return int(number) if number is not None else None
