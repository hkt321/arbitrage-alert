# Arbitrage Alert

套利机会提醒神器 – CLI 工具，每日监控 LOF / ETF / QDII 等基金的溢价/折价套利机会。

## 数据来源

- 价格、溢价率、份额、盘口：palmmicro.com
- 申购限额、申赎状态：天天基金（东方财富）

## 使用方式

无需安装任何第三方依赖（仅使用 Python 标准库）。

```powershell
# 查看前 20 只最高溢价/折价的基金
python -X utf8 tools\run_check.py --top 20

# 显示更多（前 50 只）
python -X utf8 tools\run_check.py --top 50

# 调整最低溢价阈值（默认 2.0%）
python -X utf8 tools\run_check.py --min-premium 1.5

# 调整最低申购限额（默认 100 元）
python -X utf8 tools\run_check.py --min-limit 1000

# JSON 格式输出
python -X utf8 tools\run_check.py --json

# 组合使用
python -X utf8 tools\run_check.py --top 30 --min-premium 1.0 --min-limit 500
```

## 输出说明

结果分为三档：

| 级别 | 图标 | 含义 |
|------|------|------|
| executable | 🟢 | 可执行套利（溢价达标 + 申购开放 + 限额足够） |
| watch | 🟡 | 观察中（溢价高但申购暂停或限额过低） |
| normal | ⚪ | 正常（溢价未达阈值或无数据） |

## 目录结构

```
arbitrage-alert/
  tools/
    run_check.py                           ← CLI 入口
  backend/app/
    models/                                ← 数据模型
    providers/                             ← 数据源适配器
      palmmicro_lof_provider.py             ← palmmicro 行情
      eastmoney_fund_status_provider.py     ← 天天基金申赎状态
  docs/                                    ← 文档
```

## 最低要求

- Python 3.9+
- 无需安装 pip 包