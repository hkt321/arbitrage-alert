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

## GitHub Actions 自动推送（推荐）

无需开电脑，每天 14:00（北京时间）自动在 GitHub 云服务器运行并推送到微信。

### 配置方式

1. 打开你的 GitHub 仓库 → **Settings** → **Secrets and variables** → **Actions**
2. 点击 **New repository secret**
   - Name: `SCT_SENDKEY`
   - Value: 你的 Server酱 SendKey
   - 点击 **Add secret**
3. 以后每天工作日 14:00 自动运行，你也可以去 **Actions** 标签页手动触发

> ⚠️ 首次 push 后需要完成上述 secrets 配置，否则推送会因缺少 SendKey 失败。

## 本地运行（Windows）

```powershell
cd D:\Code\arbitrage-alert
python -X utf8 tools\run_check.py --top 20
```

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