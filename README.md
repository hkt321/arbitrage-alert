# Arbitrage Alert

个人使用的 LOF 溢价/折价关注提醒工具。它从公开数据中筛选值得进一步查看的基金，并可通过 Server酱推送到微信。

> 提醒结果不是“可执行套利”信号。溢价/折价使用最新官方净值计算；QDII 等基金的净值日期可能滞后。

## 数据来源

- 标准库小分页加载器：从东方财富公开接口获取 LOF 市场行情，每页固定 20 条并校验完整性
- [AkShare](https://github.com/akfamily/akshare) `fund_purchase_em()`：最新官方净值、净值日期、申购赎回状态、限额和费率
- 两条数据链均不需要 API Key；任一链路返回不完整时，本次检查失败且不推送

## 安装与运行

要求 Python 3.9+。项目唯一的直接依赖是固定版本的 AkShare。

```powershell
python -m pip install -r requirements.txt
python tools\run_check.py
python tools\run_check.py --top 50
python tools\run_check.py --min-premium 1.0 --min-discount -1.5 --min-limit 100
python tools\run_check.py --json
python tools\run_check.py --push-key SCTXXXXXXXXXXXXXXXXX
```

## 参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--top N` | 25 | 按绝对溢价/折价排序后显示前 N 只 |
| `--min-premium X` | 1.5 | 溢价关注阈值（%） |
| `--min-discount X` | -2.0 | 折价关注阈值（%） |
| `--min-limit N` | 20 | 申购限额提示阈值（元） |
| `--json` | - | 输出 JSON |
| `--push-key SENDKEY` | - | 通过 Server酱推送到微信 |

结果只有三种状态：`watch` 表示达到阈值、`normal` 表示未达到阈值、`unknown` 表示缺少可用净值。系统不会输出 `executable`。

## GitHub Actions

工作流在每个工作日北京时间 14:00 运行。需要在仓库 Actions secrets 中配置 `SCT_SENDKEY`；也可以从 Actions 页面手动触发并调整 Top N。

## 目录

```text
tools/run_check.py                         CLI 和 Server酱推送
backend/app/models/lof_snapshot.py         轻量 LOF 快照
backend/app/providers/eastmoney_lof_spot_loader.py  小分页行情加载器
backend/app/providers/akshare_lof_provider.py  AkShare 数据适配
tests/                                     标准库 unittest 测试
```
