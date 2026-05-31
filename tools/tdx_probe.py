import json
import sys
from pathlib import Path


TDX_USER_PLUGIN_DIR = Path(r"D:\TongDaXing\PYPlugins\user")


def load_tq():
    if not TDX_USER_PLUGIN_DIR.exists():
        raise RuntimeError(f"通达信 TQ 插件目录不存在: {TDX_USER_PLUGIN_DIR}")

    sys.path.insert(0, str(TDX_USER_PLUGIN_DIR))
    from tqcenter import tq

    tq.initialize(__file__)
    return tq


def compact(value, limit=5):
    if isinstance(value, dict):
        result = {}
        for key, item in list(value.items())[:limit]:
            result[str(key)] = compact(item, limit=limit)
        return result
    if isinstance(value, list):
        return [compact(item, limit=limit) for item in value[:limit]]
    if hasattr(value, "head"):
        return compact(value.head(limit).to_dict(), limit=limit)
    return value


def probe_stock_lists(tq):
    list_types = {
        "etf": 31,
        "convertible_bond": 32,
        "lof": 33,
        "tradable_funds": 34,
        "sh_sz_funds": 35,
        "t0_funds": 36,
        "etf_tracking_index": 91,
    }

    output = {}
    for name, list_type in list_types.items():
        probes = []
        selected = []
        try:
            for market in ["5", "0", "1"]:
                values = tq.get_stock_list(market, list_type=list_type)
                probes.append({"market": market, "count": len(values), "sample": values[:3]})
                if values and not selected:
                    selected = values
            output[name] = {
                "count": len(selected),
                "sample": selected[:5],
                "probes": probes,
            }
        except Exception as exc:
            output[name] = {"error": str(exc)}
    return output


def probe_snapshots(tq):
    codes = [
        "510300.SH",  # 沪深300ETF
        "513100.SH",  # 纳指ETF
        "162411.SZ",  # 华宝油气
        "161226.SZ",  # 白银基金
        "128036.SZ",  # 可转债样例
        "110059.SH",  # 可转债样例
    ]

    output = {}
    for code in codes:
        try:
            snapshot = tq.get_market_snapshot(stock_code=code, field_list=[])
            output[code] = compact(snapshot, limit=20)
        except Exception as exc:
            output[code] = {"error": str(exc)}
    return output


def probe_kline(tq):
    codes = ["510300.SH", "162411.SZ", "128036.SZ", "110059.SH"]
    output = {}
    for code in codes:
        try:
            data = tq.get_market_data(
                stock_list=[code],
                period="1d",
                count=3,
                dividend_type="none",
                fill_data=True,
            )
            output[code] = compact(data, limit=3)
        except Exception as exc:
            output[code] = {"error": str(exc)}
    return output


def main():
    tq = load_tq()
    result = {
        "stock_lists": probe_stock_lists(tq),
        "snapshots": probe_snapshots(tq),
        "kline": probe_kline(tq),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    tq.close()


if __name__ == "__main__":
    main()
