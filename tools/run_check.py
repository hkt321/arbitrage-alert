#!/usr/bin/env python3
"""
套利机会检查器 – 独立脚本，无需启动后端服务。

使用方式：
    python tools/run_check.py
    python tools/run_check.py --top 20
    python tools/run_check.py --min-limit 20
    python tools/run_check.py --min-premium 1.5
    python tools/run_check.py --min-discount -2.0
    python tools/run_check.py --json                      # JSON 格式输出
    python tools/run_check.py --push-key <SENDKEY>        # 推送结果到微信

数据来源：
    - 溢价/净值/份额/盘口：palmmicro.com
    - 申购限额/申赎状态：天天基金（东方财富）
"""
import argparse
import json
import sys
import os
import urllib.parse
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from app.providers.palmmicro_lof_provider import PalmmicroLofProvider
from app.providers.eastmoney_fund_status_provider import EastmoneyFundStatusProvider


# ------------------------------------------------------------------
# 格式化函数
# ------------------------------------------------------------------

def fmt_pct(val, digits=2):
    if val is None:
        return "-"
    sign = "+" if val > 0 else ""
    return f"{sign}{val:.{digits}f}%"


def fmt_yuan(val):
    if val is None:
        return "-"
    if val >= 1_000_000_000:
        return f"{val/1_000_000_000:.1f}B"
    if val >= 10_000:
        return f"{val/10_000:.0f}万"
    return f"{val:.0f}"


def fmt_wan(val):
    return "-" if val is None else f"{val:.2f}万"


def fmt_wan_delta(val):
    if val is None:
        return "-"
    sign = "+" if val > 0 else ""
    return f"{sign}{val:.2f}万"


# ------------------------------------------------------------------
# 套利级别判定
# ------------------------------------------------------------------

def determine_level(premium_pct, purchase_limit, subscription_status,
                    redemption_status, min_limit, min_premium, min_discount):
    """返回 (level, reasons)"""
    reasons = []
    if premium_pct is None:
        return "unknown", ["无估值数据"]

    # 溢价套利（premium > 0）
    if premium_pct > 0:
        if premium_pct < min_premium:
            return "normal", [f"溢价{fmt_pct(premium_pct)}，未达{min_premium}%阈值"]
        if subscription_status == "closed":
            return "watch", [f"申购暂停", f"溢价{fmt_pct(premium_pct)}"]
        if purchase_limit is not None and purchase_limit < min_limit:
            return "watch", [f"限购{fmt_yuan(purchase_limit)}，低于{fmt_yuan(min_limit)}",
                            f"溢价{fmt_pct(premium_pct)}"]
        if purchase_limit is None or purchase_limit == 0:
            return "watch", ["限额未接入", f"溢价{fmt_pct(premium_pct)}"]
        return "executable", [f"溢价{fmt_pct(premium_pct)}",
                              f"限额{fmt_yuan(purchase_limit)}"]

    # 折价套利（premium < 0）：场内买入 -> 场外赎回
    if premium_pct < 0:
        if premium_pct > min_discount:  # min_discount 为负值，如 -2.0
            return "normal", [f"折价{fmt_pct(premium_pct)}，未达{abs(min_discount)}%阈值"]
        if redemption_status == "closed":
            return "watch", [f"赎回暂停", f"折价{fmt_pct(premium_pct)}"]
        if purchase_limit is not None and purchase_limit < min_limit:
            return "watch", [f"限购{fmt_yuan(purchase_limit)}，低于{fmt_yuan(min_limit)}",
                            f"折价{fmt_pct(premium_pct)}"]
        if purchase_limit is None or purchase_limit == 0:
            return "watch", ["限额未接入", f"折价{fmt_pct(premium_pct)}"]
        return "executable", [f"折价{fmt_pct(premium_pct)}",
                              f"限额{fmt_yuan(purchase_limit)}"]

    return "normal", []


def get_premium(snapshot):
    p = snapshot.realtime_premium_pct
    return p if p is not None else snapshot.est_premium_pct


# ------------------------------------------------------------------
# 视觉宽度（CJK 字符算 2 个宽度）
# ------------------------------------------------------------------

def visual_len(text: str) -> int:
    count = 0
    for ch in text:
        if '\u4e00' <= ch <= '\u9fff' or '\u3000' <= ch <= '\u303f' or '\uff00' <= ch <= '\uffef':
            count += 2
        else:
            count += 1
    return count


def pad_visual(text: str, width: int) -> str:
    return text + ' ' * max(0, width - visual_len(text))


# ------------------------------------------------------------------
# Server酱 微信推送
# ------------------------------------------------------------------

def push_to_wechat(sendkey, title, content):
    """通过 Server酱 推送消息到微信"""
    import urllib.request
    data = urllib.parse.urlencode({"title": title, "desp": content}).encode("utf-8")
    url = f"https://sctapi.ftqq.com/{sendkey}.send"
    req = urllib.request.Request(url, data=data, method="POST")
    resp = urllib.request.urlopen(req, timeout=15)
    result = json.loads(resp.read().decode("utf-8"))
    if result.get("code") == 0:
        print(f"  ✅ 微信推送成功: {result.get('data', {}).get('pushid', '')}")
    else:
        print(f"  ⚠️ 微信推送失败: {result.get('message', '未知错误')}")


def build_push_content(results):
    """构建推送给微信的文本内容"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    executables = [r for r in results if r["level"] == "executable"]
    watches = [r for r in results if r["level"] == "watch"]

    lines = [f"## 套利机会检查 – {now}", ""]

    if not executables and not watches:
        lines.append("今日无套利机会。")
        lines.append("")
        lines.append("| 代码 | 名称 | 溢价 |")
        lines.append("|------|------|------|")
        for r in results[:5]:
            lines.append(f"| {r['code']} | {r['name']} | {fmt_pct(r['premium_pct'])} |")
        return "\n".join(lines)

    if executables:
        lines.append(f"### 🟢 可执行机会 ({len(executables)})")
        lines.append("")
        for r in sorted(executables, key=lambda x: abs(x["premium_pct"] or 0), reverse=True):
            direction = "📈溢价" if (r["premium_pct"] or 0) > 0 else "📉折价"
            lines.append(f"- **{r['name']}** ({r['code']}) {direction} {fmt_pct(r['premium_pct'])} | 限购 {fmt_yuan(r['purchase_limit_yuan'])}")
        lines.append("")

    if watches:
        lines.append(f"### 🟡 观察机会 ({len(watches)})")
        lines.append("")
        for r in sorted(watches, key=lambda x: abs(x["premium_pct"] or 0), reverse=True):
            direction = "📈溢价" if (r["premium_pct"] or 0) > 0 else "📉折价"
            lines.append(f"- {r['name']} ({r['code']}) {direction} {fmt_pct(r['premium_pct'])} | {'  ⚠️ '.join(r['reasons'])}")
        lines.append("")

    # 简要汇总表
    rows = results[:15]
    lines.append("### 📊 溢价/折价汇总（前15）")
    lines.append("")
    lines.append("| 代码 | 名称 | 溢价 | 限购 | 结论 |")
    lines.append("|------|------|------|------|------|")
    for r in rows:
        icon = "🟢" if r["level"] == "executable" else ("🟡" if r["level"] == "watch" else "⚪")
        lines.append(f"| {r['code']} | {r['name']} | {fmt_pct(r['premium_pct'])} | {fmt_yuan(r['purchase_limit_yuan'])} | {icon}{r['level']} |")

    summary = "\n".join(lines)
    # Server酱 desp 限制 64KB，足够
    return summary


# ------------------------------------------------------------------
# 核心运行逻辑
# ------------------------------------------------------------------

def run(top_n, min_limit, min_premium, min_discount, output_json, push_key):
    palmmicro = PalmmicroLofProvider(request_delay=0.5)
    status_provider = EastmoneyFundStatusProvider()

    funds = palmmicro.fetch_all_funds()

    def abs_prem(f):
        p = get_premium(f)
        return abs(p) if p is not None else 0

    funds.sort(key=abs_prem, reverse=True)
    top_candidates = funds[:top_n]
    enriched = []

    for fund in top_candidates:
        detail = palmmicro.fetch_detail(fund.code)
        if detail:
            if detail.price is not None:
                fund.price = detail.price
                fund.price_change_pct = detail.price_change_pct
            if detail.shares_wan is not None:
                fund.shares_wan = detail.shares_wan
                fund.shares_delta_wan = detail.shares_delta_wan
                fund.volume = detail.volume
                fund.turnover_pct = detail.turnover_pct
            if detail.bid_price1 is not None:
                fund.bid_price1 = detail.bid_price1
                fund.bid_volume1 = detail.bid_volume1
                fund.ask_price1 = detail.ask_price1
                fund.ask_volume1 = detail.ask_volume1

        # Normalize code: "SH501225" -> "501225", "SZ161128" -> "161128"
        status_code = fund.code[2:] if fund.code.startswith(("SH", "SZ")) else fund.code
        status = status_provider.get_status(status_code)
        if status:
            fund.purchase_limit_yuan = status.purchase_limit_yuan
            fund.subscription_status = status.subscription_status
            fund.redemption_status = status.redemption_status
            fund.fee_pct = status.fee_pct

        enriched.append(fund)

    results = []
    for fund in enriched:
        prem = get_premium(fund)
        level, reasons = determine_level(
            prem, fund.purchase_limit_yuan, fund.subscription_status,
            fund.redemption_status, min_limit, min_premium, min_discount,
        )
        results.append({
            "code": fund.code,
            "name": fund.name,
            "price": fund.price,
            "price_change_pct": fund.price_change_pct,
            "premium_pct": prem,
            "level": level,
            "reasons": reasons,
            "shares_wan": fund.shares_wan,
            "shares_delta_wan": fund.shares_delta_wan,
            "volume": fund.volume,
            "turnover_pct": fund.turnover_pct,
            "purchase_limit_yuan": fund.purchase_limit_yuan,
            "subscription_status": fund.subscription_status,
            "redemption_status": fund.redemption_status,
            "fee_pct": fund.fee_pct,
        })

    results.sort(key=lambda r: abs(r["premium_pct"]) if r["premium_pct"] else 0,
                 reverse=True)

    if output_json:
        print(json.dumps(results, ensure_ascii=False, indent=2, default=str))
        if push_key:
            content = build_push_content(results)
            title = f"套利机会 {datetime.now().strftime('%m-%d')}"
            push_to_wechat(push_key, title, content)
        return

    # ---- 终端输出 ----
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    print(f"\n{'=' * 70}")
    print(f"  套利机会检查 – {now}")
    print(f"  过滤条件: 溢价 ≥{min_premium}% | 折价 ≤{min_discount}% | 最低限购 {fmt_yuan(min_limit)}")
    print(f"{'=' * 70}\n")

    executables = [r for r in results if r["level"] == "executable"]
    watches = [r for r in results if r["level"] == "watch"]
    normals = [r for r in results if r["level"] in ("normal", "unknown")]

    if executables:
        print(f"🟢 可执行机会 ({len(executables)})")
        print("-" * 70)
        for r in sorted(executables, key=lambda x: abs(x["premium_pct"] or 0),
                        reverse=True):
            _print_fund(r)
        print()

    if watches:
        print(f"🟡 观察机会 ({len(watches)})")
        print("-" * 70)
        for r in sorted(watches, key=lambda x: abs(x["premium_pct"] or 0),
                        reverse=True):
            _print_fund(r)
        print()

    print(f"\n📊 溢价/折价汇总（前 {len(results)} 只）")
    print("-" * 70)
    hdr = f"  {'代码':>10} | {pad_visual('名称', 16)} | {'溢价':>8} | {'限购':>10} | {'份额':>10} | {'新增':>10} | {'结论'}"
    print(hdr)
    print("-" * 70)
    for r in results:
        prem_str = fmt_pct(r["premium_pct"])
        limit_str = fmt_yuan(r["purchase_limit_yuan"])
        shares_str = fmt_wan(r["shares_wan"])
        delta_str = fmt_wan_delta(r["shares_delta_wan"])
        lvl = r["level"]
        icon = "🟢" if lvl == "executable" else ("🟡" if lvl == "watch" else "⚪")
        name_padded = pad_visual(r['name'], 16)
        print(f"  {r['code']:>10} | {name_padded} | {prem_str:>8} | "
              f"{limit_str:>10} | {shares_str:>10} | {delta_str:>10} | {icon}{lvl}")

    print(f"\n{'=' * 70}")
    print(f"  提示: --json 获取完整数据 | --top N 控制数量 | "
          f"--min-limit N 设置最低限购 | --push-key SENDKEY 推送微信")
    print(f"{'=' * 70}")

    # 微信推送
    if push_key:
        content = build_push_content(results)
        title = f"套利机会 {datetime.now().strftime('%m-%d')}"
        push_to_wechat(push_key, title, content)


def _print_fund(r):
    prem = r["premium_pct"]
    prem_str = fmt_pct(prem)
    price_str = f"{r['price']:.3f}" if r["price"] else "-"
    change_str = fmt_pct(r["price_change_pct"])
    limit_str = fmt_yuan(r["purchase_limit_yuan"])
    sub_status = r["subscription_status"] or "-"
    title = f"{r['name']} ({r['code']})"
    direction = ("📈 溢价套利" if (prem or 0) > 0
                 else "📉 折价套利" if (prem or 0) < 0 else "")
    print(f"\n  {direction} {title}")
    print(f"    价格: {price_str} ({change_str}) | 估值溢价: {prem_str}")
    if r["shares_wan"] is not None:
        print(f"    份额: {fmt_wan(r['shares_wan'])} | "
              f"新增: {fmt_wan_delta(r['shares_delta_wan'])} | "
              f"成交: {r['volume'] or '-'} | 换手: {r['turnover_pct'] or '-'}")
    if r["purchase_limit_yuan"] is not None or r["subscription_status"]:
        print(f"    限购: {limit_str} | 申购: {sub_status}")
    if r["reasons"]:
        print(f"    {' ⚠️ '.join(r['reasons'])}")


# ------------------------------------------------------------------
# 入口
# ------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="套利机会检查器")
    parser.add_argument("--top", type=int, default=25,
                        help="检查前N只高溢价/折价基金 (默认25)")
    parser.add_argument("--min-limit", type=float, default=20,
                        help="最低申购限额 (默认20元)")
    parser.add_argument("--min-premium", type=float, default=1.5,
                        help="最低溢价阈值%% (默认1.5)")
    parser.add_argument("--min-discount", type=float, default=-2.0,
                        help="最低折价阈值%% (默认-2.0，即折价超过2%%才提醒)")
    parser.add_argument("--json", action="store_true",
                        help="输出JSON格式")
    parser.add_argument("--push-key", type=str, default=None,
                        help="Server酱 SendKey，用于推送结果到微信")
    args = parser.parse_args()
    try:
        run(top_n=args.top, min_limit=args.min_limit,
            min_premium=args.min_premium, min_discount=args.min_discount,
            output_json=args.json, push_key=args.push_key)
    except KeyboardInterrupt:
        print("\n已中断")
        sys.exit(1)


if __name__ == "__main__":
    main()