import json
import sys
from pathlib import Path


sys.path.insert(0, str(Path(r"D:\TongDaXing\PYPlugins\user")))
from tqcenter import tq


def main():
    tq.initialize(__file__)

    result = {
        "lists": {},
        "snapshots": {},
    }

    for market in ["", "5", "0", "1"]:
        for list_type in [0, 1, 5, 31, 32, 33, 34, 35, 36, 91]:
            key = f"market={market or 'default'},list_type={list_type}"
            try:
                values = tq.get_stock_list(market or None, list_type=list_type)
                result["lists"][key] = {
                    "count": len(values),
                    "sample": values[:3],
                }
            except Exception as exc:
                result["lists"][key] = {"error": str(exc)}

    for code in [
        "600519.SH",
        "000001.SZ",
        "510300.SH",
        "513100.SH",
        "162411.SZ",
        "161226.SZ",
        "113044.SH",
        "127027.SZ",
        "123107.SZ",
    ]:
        try:
            result["snapshots"][code] = tq.get_market_snapshot(code, field_list=[])
        except Exception as exc:
            result["snapshots"][code] = {"error": str(exc)}

    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    tq.close()


if __name__ == "__main__":
    main()
