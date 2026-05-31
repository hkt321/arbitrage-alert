import json
import sys
from datetime import datetime, timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from app.providers.tdx_pcf_provider import TdxPcfProvider


def latest_weekday() -> str:
    day = datetime.now()
    while day.weekday() >= 5:
        day -= timedelta(days=1)
    return day.strftime("%Y%m%d")


def main() -> None:
    codes = sys.argv[1:] or ["510300.SH", "513100.SH", "159915.SZ"]
    trade_date = latest_weekday()

    provider = TdxPcfProvider()
    provider.connect(__file__)
    try:
        result = []
        for code in codes:
            snapshot = provider.get_etf_pcf(code, trade_date)
            result.append(snapshot.to_dict() if snapshot else {"code": code, "pcf": None})
        print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    finally:
        provider.close()


if __name__ == "__main__":
    main()
