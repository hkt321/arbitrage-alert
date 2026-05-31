import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from app.providers.market_signal_provider import MarketSignalProvider
from app.providers.tdx_quant_provider import TdxQuantProvider


def load_signal_configs() -> dict[str, dict]:
    path = BACKEND / "app" / "config" / "valuation_signals.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    return {item["id"]: item for item in data["signals"]}


def main() -> None:
    provider = TdxQuantProvider()
    provider.connect(__file__)
    try:
        signal_provider = MarketSignalProvider(load_signal_configs(), provider)
        output = [
            signal_provider.get_signal(signal_id).to_dict()
            for signal_id in load_signal_configs()
        ]
        print(json.dumps(output, ensure_ascii=False, indent=2, default=str))
    finally:
        provider.close()


if __name__ == "__main__":
    main()
