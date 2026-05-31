import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from app.providers.tdx_quant_provider import TdxQuantProvider


def load_watchlist() -> list[dict]:
    path = BACKEND / "app" / "config" / "watchlist.json"
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    provider = TdxQuantProvider()
    provider.connect(__file__)

    try:
        watchlist = load_watchlist()
        quotes = provider.get_quotes([item["code"] for item in watchlist])
        output = [quote.to_dict() for quote in quotes]
        print(json.dumps(output, ensure_ascii=False, indent=2, default=str))
    finally:
        provider.close()


if __name__ == "__main__":
    main()
