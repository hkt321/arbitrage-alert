# Arbitrage Alert

套利机会提醒神器 – CLI 工具，每日监控 LOF / ETF / QDII 等基金的溢价/折价套利机会，支持推送到微信。

## 数据来源

- 价格、溢价率、份额、盘口：palmmicro.com
- 申购限额、申赎状态：天天基金（东方财富）

## 使用方式

```powershell
# 查看前 25 只（默认）
python -X utf8 tools\run_check.py

# 显示前 50 只
python -X utf8 tools\run_check.py --top 50

# 自定义阈值
python -X utf8 tools\run_check.py --min-premium 1.0 --min-discount -1.5 --min-limit 100

# 推送到微信（需要 Server酱 SendKey）
python -X utf8 tools\run_check.py --push-key SCTXXXXXXXXXXXXXXXXX

# 组合使用（推荐用于定时任务）
python -X utf8 tools\run_check.py --top 30 --min-premium 1.5 --min-discount -2.0 --min-limit 20 --push-key SCTXXXXXXXXXXXXXXXXX

# JSON 格式输出
python -X utf8 tools\run_check.py --json
```

## 参数说明

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--top N` | 25 | 检查前 N 只高溢价/折价基金 |
| `--min-premium X` | 1.5 | 最低溢价阈值（%） |
| `--min-discount X` | -2.0 | 最低折价阈值（%，负值表示折价） |
| `--min-limit N` | 20 | 最低申购限额（元） |
| `--json` | - | 输出 JSON 格式 |
| `--push-key SENDKEY` | - | Server酱 SendKey，推送结果到微信 |

## 输出说明

结果分为三档：

| 级别 | 图标 | 含义 |
|------|------|------|
| executable | 🟢 | **可执行套利**（溢价/折价达标 + 申赎开放 + 限额足够） |
| watch | 🟡 | **观察中**（溢价/折价高但申赎暂停或限额过低） |
| normal | ⚪ | **正常**（溢价/折价未达阈值） |

## 定时推送（Windows 任务计划程序）

每天 14:00 自动运行并推送微信：

1. 按下 `Win + R`，输入 `taskschd.msc` 回车
2. 右侧点击 **创建任务**
3. **常规** 标签：名称填 "套利机会检查"
4. **触发器** 标签 → 新建 → 每天 14:00 开始
5. **操作** 标签 → 新建：
   - 程序或脚本：`python`
   - 添加参数：`-X utf8 D:\Code\arbitrage-alert\tools\run_check.py --push-key SCT358832TbljKzAG4ZHQyEqyXzqQgxTDa`
6. 确定保存即可

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