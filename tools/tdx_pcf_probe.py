import json
import sys
from pathlib import Path


TDX_ROOT = Path(r"D:\TongDaXing")
TDX_USER_PLUGIN_DIR = TDX_ROOT / "PYPlugins" / "user"
TDX_DATA_DIR = TDX_ROOT / "PYPlugins" / "data"

sys.path.insert(0, str(TDX_USER_PLUGIN_DIR))
from tqcenter import tq


def file_state() -> dict[str, dict]:
    if not TDX_DATA_DIR.exists():
        return {}
    result = {}
    for path in TDX_DATA_DIR.rglob("*"):
        if path.is_file():
            result[str(path)] = {
                "size": path.stat().st_size,
                "mtime": path.stat().st_mtime,
            }
    return result


def diff_files(before: dict[str, dict], after: dict[str, dict]) -> dict[str, dict]:
    changed = {}
    for path, info in after.items():
        if path not in before or before[path] != info:
            changed[path] = info
    return changed


def main() -> None:
    tq.initialize(__file__)
    before = file_state()

    attempts = []
    for code in ["510300.SH", "513100.SH", "159915.SZ"]:
        for day in ["20260529", "20260531"]:
            try:
                result = tq.download_file(stock_code=code, down_time=day, down_type=2)
                attempts.append({"code": code, "day": day, "result": result})
            except Exception as exc:
                attempts.append({"code": code, "day": day, "error": str(exc)})

    after = file_state()
    print(
        json.dumps(
            {
                "attempts": attempts,
                "changedFiles": diff_files(before, after),
            },
            ensure_ascii=False,
            indent=2,
            default=str,
        )
    )
    tq.close()


if __name__ == "__main__":
    main()
