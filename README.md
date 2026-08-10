# Arbitrage Alert

个人使用的 LOF 溢价/折价关注提醒工具。它从公开数据中筛选值得进一步查看的基金，并可通过 Server酱推送到微信。

> 提醒结果不是“可执行套利”信号。溢价/折价使用最新官方净值计算；QDII 等基金的净值日期可能滞后。

## 数据来源

- [easyquotation](https://github.com/shidenggui/easyquotation) 新浪适配器：批量获取 `config/lof_watchlist.json` 中的 LOF 场内行情
- [AkShare](https://github.com/akfamily/akshare) `fund_purchase_em()`：最新官方净值、净值日期、申购赎回状态、限额和费率
- 两条数据链均不需要 API Key；自选代码缺失、价格无效、行情超过 5 分钟或任一链路返回不完整时，本次检查失败且不推送

## 安装与运行

要求 Python 3.9+。项目直接依赖固定版本的 AkShare 和 easyquotation。

```powershell
python -m pip install -r requirements.txt
python tools\run_check.py
python tools\run_check.py --top 50
python tools\run_check.py --min-premium 1.0 --min-discount -1.5 --min-limit 100
python tools\run_check.py --json
python tools\run_check.py --push-key SCTXXXXXXXXXXXXXXXXX
```

编辑 `config/lof_watchlist.json` 可以增删自选 LOF。初始自选池为上一版最近一次成功运行的前 15 只；代码使用六位数字格式，例如 `501018`、`161129`。系统只检查这份自选池，不再自动扫描全市场目录。

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

工作流在每个工作日北京时间 13:17 运行，避开 GitHub Actions 整点调度高峰。计划任务如果在 14:50 后才启动会跳过推送；手动触发不受该窗口限制。需要在仓库 Actions secrets 中配置 `SCT_SENDKEY`；也可以从 Actions 页面手动触发并调整 Top N。

## 目录

```text
tools/run_check.py                         CLI 和 Server酱推送
backend/app/models/lof_snapshot.py         轻量 LOF 快照
backend/app/providers/sina_lof_spot_loader.py  新浪自选池行情加载器
backend/app/providers/akshare_lof_provider.py  AkShare 数据适配
config/lof_watchlist.json                   LOF 自选池
tests/                                     标准库 unittest 测试
```
