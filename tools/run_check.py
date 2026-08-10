#!/usr/bin/env python3
"""LOF 溢价/折价关注提醒。

自选池行情通过 easyquotation 的新浪适配器获取；最新官方净值和申赎信息通过 AkShare 获取。
结果只用于筛选值得关注的基金，不构成可交易套利信号。
"""

import argparse
import json
import os
import sys
import urllib.parse
from datetime import datetime, timezone
from typing import Any
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from app.providers.akshare_lof_provider import AkshareLofProvider, DataSourceError


SHANGHAI = ZoneInfo("Asia/Shanghai")


def beijing_now(instant: datetime | None = None) -> datetime:
    instant = instant or datetime.now(timezone.utc)
    if instant.tzinfo is None:
        instant = instant.replace(tzinfo=timezone.utc)
    return instant.astimezone(SHANGHAI)


def fmt_pct(value: float | None, digits: int = 2) -> str:
    if value is None:
        return "-"
    sign = "+" if value > 0 else ""
    return f"{sign}{value:.{digits}f}%"


def fmt_yuan(value: float | None) -> str:
    if value is None:
        return "-"
    if value >= 1_000_000_000:
        return f"{value / 1_000_000_000:.1f}B"
    if value >= 10_000:
        return f"{value / 10_000:.0f}万"
    return f"{value:.0f}"


def determine_level(
    premium_pct: float | None,
    purchase_limit: float | None,
    subscription_status: str,
    redemption_status: str,
    min_limit: float,
    min_premium: float,
    min_discount: float,
) -> tuple[str, list[str]]:
    """Return a watch-only level and human-readable reasons."""
    if premium_pct is None:
        return "unknown", ["无最新官方净值数据"]

    if premium_pct > 0:
        if premium_pct < min_premium:
            return "normal", [f"溢价{fmt_pct(premium_pct)}，未达{min_premium}%阈值"]
        if subscription_status == "closed":
            return "watch", ["申购暂停", f"溢价{fmt_pct(premium_pct)}", "基于最新官方净值"]
        if purchase_limit is not None and purchase_limit < min_limit:
            return "watch", [
                f"限购{fmt_yuan(purchase_limit)}，低于{fmt_yuan(min_limit)}",
                f"溢价{fmt_pct(premium_pct)}",
                "基于最新官方净值",
            ]
        if purchase_limit is None or purchase_limit == 0:
            return "watch", ["限额未知或不限额", f"溢价{fmt_pct(premium_pct)}", "基于最新官方净值"]
        return "watch", [
            f"溢价{fmt_pct(premium_pct)}",
            f"限额{fmt_yuan(purchase_limit)}",
            "基于最新官方净值",
        ]

    if premium_pct < 0:
        if premium_pct > min_discount:
            return "normal", [f"折价{fmt_pct(premium_pct)}，未达{abs(min_discount)}%阈值"]
        if redemption_status == "closed":
            return "watch", ["赎回暂停", f"折价{fmt_pct(premium_pct)}", "基于最新官方净值"]
        return "watch", [f"折价{fmt_pct(premium_pct)}", "基于最新官方净值"]

    return "normal", []


def build_results(
    snapshots: list[Any],
    top_n: int,
    min_limit: float,
    min_premium: float,
    min_discount: float,
) -> list[dict[str, Any]]:
    ordered = sorted(
        snapshots,
        key=lambda item: abs(item.premium_pct) if item.premium_pct is not None else -1,
        reverse=True,
    )[:top_n]
    results: list[dict[str, Any]] = []
    for snapshot in ordered:
        level, reasons = determine_level(
            snapshot.premium_pct,
            snapshot.purchase_limit_yuan,
            snapshot.subscription_status,
            snapshot.redemption_status,
            min_limit,
            min_premium,
            min_discount,
        )
        item = snapshot.to_dict()
        item["level"] = level
        item["reasons"] = reasons
        results.append(item)
    return results


def push_to_wechat(sendkey: str, title: str, content: str) -> None:
    """Push through Server酱; push failures do not change data processing."""
    import urllib.request

    try:
        data = urllib.parse.urlencode({"title": title, "desp": content}).encode("utf-8")
        request = urllib.request.Request(
            f"https://sctapi.ftqq.com/{sendkey}.send",
            data=data,
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=15) as response:
            result = json.loads(response.read().decode("utf-8"))
        if result.get("code") == 0:
            print(f"  微信推送成功 {result.get('data', {}).get('pushid', '')}")
        else:
            print(f"  微信推送失败: {result.get('message', '未知错误')}")
    except Exception as exc:
        print(f"  微信推送异常: {exc}")


def build_push_content(
    results: list[dict[str, Any]], instant: datetime | None = None
) -> str:
    now = beijing_now(instant).strftime("%Y-%m-%d %H:%M")
    watches = [item for item in results if item["level"] == "watch"]
    lines = [
        f"## LOF 关注提醒 – {now}",
        "",
        "> 溢价/折价基于最新官方净值及其净值日期，不代表可立即交易的套利空间。",
        "",
    ]

    if not watches:
        lines.extend(
            [
                "今日没有达到阈值的关注项。",
                "",
                "| 代码 | 名称 | 溢价/折价 | 净值日期 |",
                "|------|------|-----------|----------|",
            ]
        )
        for item in results[:5]:
            lines.append(
                f"| {item['code']} | {item['name']} | {fmt_pct(item['premium_pct'])} | {item.get('nav_date') or '-'} |"
            )
        return "\n".join(lines)

    lines.extend([f"### 达到阈值的关注项 ({len(watches)})", ""])
    for item in watches:
        direction = "溢价" if (item["premium_pct"] or 0) > 0 else "折价"
        lines.append(
            f"- **{item['name']}** ({item['code']}) {direction} {fmt_pct(item['premium_pct'])}"
            f" | 最新官方净值 {item.get('latest_nav') or '-'} ({item.get('nav_date') or '日期未知'})"
            f" | {'；'.join(item['reasons'])}"
        )

    displayed_count = min(15, len(results))
    lines.extend(
        [
            "",
            f"### 汇总（前{displayed_count}，本次共{len(results)}只）",
            "",
            "| 代码 | 名称 | 溢价/折价 | 净值日期 | 结论 |",
            "|------|------|-----------|----------|------|",
        ]
    )
    for item in results[:displayed_count]:
        lines.append(
            f"| {item['code']} | {item['name']} | {fmt_pct(item['premium_pct'])}"
            f" | {item.get('nav_date') or '-'} | {item['level']} |"
        )
    return "\n".join(lines)


def _print_terminal(
    results: list[dict[str, Any]],
    min_limit: float,
    min_premium: float,
    min_discount: float,
) -> None:
    now = beijing_now().strftime("%Y-%m-%d %H:%M")
    print(f"\n{'=' * 88}")
    print(f"LOF 关注提醒 – {now}")
    print(
        f"阈值: 溢价 ≥ {min_premium}% | 折价 ≤ {min_discount}% | "
        f"提示限额 {fmt_yuan(min_limit)}"
    )
    print("口径: 溢价/折价基于最新官方净值及其净值日期，仅供关注。")
    print(f"{'=' * 88}")
    print("代码       名称                 价格      净值      净值日期       溢价/折价    结论")
    print("-" * 88)
    for item in results:
        price = f"{item['price']:.4f}" if item["price"] is not None else "-"
        nav = f"{item['latest_nav']:.4f}" if item["latest_nav"] is not None else "-"
        print(
            f"{item['code']:<10} {item['name'][:18]:<18} {price:>8} {nav:>9} "
            f"{(item['nav_date'] or '-'):>12} {fmt_pct(item['premium_pct']):>10} {item['level']}"
        )


def run(
    top_n: int,
    min_limit: float,
    min_premium: float,
    min_discount: float,
    output_json: bool,
    push_key: str | None,
    provider: Any | None = None,
    push_func: Any | None = None,
) -> list[dict[str, Any]]:
    provider = provider or AkshareLofProvider()
    results = build_results(
        provider.fetch_all(),
        top_n,
        min_limit,
        min_premium,
        min_discount,
    )

    if output_json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        _print_terminal(results, min_limit, min_premium, min_discount)

    if push_key:
        push_func = push_func or push_to_wechat
        push_func(
            push_key,
            f"LOF 关注提醒 {beijing_now().strftime('%m-%d')}",
            build_push_content(results),
        )
    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="LOF 溢价/折价关注提醒")
    parser.add_argument("--top", type=int, default=25, help="显示绝对溢价/折价最高的前 N 只基金")
    parser.add_argument("--min-limit", type=float, default=20, help="申购限额提示阈值，单位元")
    parser.add_argument("--min-premium", type=float, default=1.5, help="溢价关注阈值，单位百分比")
    parser.add_argument("--min-discount", type=float, default=-2.0, help="折价关注阈值，单位百分比")
    parser.add_argument("--json", action="store_true", help="输出 JSON")
    parser.add_argument("--push-key", type=str, default=None, help="Server酱 SendKey")
    args = parser.parse_args(argv)

    try:
        run(
            args.top,
            args.min_limit,
            args.min_premium,
            args.min_discount,
            args.json,
            args.push_key,
        )
    except DataSourceError as exc:
        print(f"数据源错误: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("已中断", file=sys.stderr)
        return 130
    return 0


if __name__ == "__main__":
    sys.exit(main())
