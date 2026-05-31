import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from app.providers.eastmoney_fund_status_provider import EastmoneyFundStatusProvider


def main() -> None:
    codes = sys.argv[1:] or ["162411.SZ", "161226.SZ", "513100.SH", "510300.SH"]
    provider = EastmoneyFundStatusProvider()
    result = []

    for code in codes:
        status = provider.get_status(code)
        result.append(status.to_dict() if status else {"code": code, "status": None})

    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
