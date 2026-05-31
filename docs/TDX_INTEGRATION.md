# 通达信 TdxQuant 接入记录

## 当前安装状态

- 通达信安装目录：`D:\TongDaXing`
- 客户端进程：`D:\TongDaXing\TdxW.exe`
- TdxQuant 插件目录：`D:\TongDaXing\PYPlugins`
- 用户插件目录：`D:\TongDaXing\PYPlugins\user`
- `tqcenter.py` 已存在，版本注释为 `1.0.8 / 2026-05-15`
- 官方样例脚本：`D:\TongDaXing\PYPlugins\user\tdxdata_test.py`

## 已确认能力

从本地 `tqcenter.py` 和样例脚本看，当前版本至少提供：

- `get_market_snapshot`：市场快照。
- `get_market_data`：K 线行情。
- `get_stock_list`：品种列表。
- `get_kzz_info`：可转债基础数据。
- `download_file`：下载文件，样例里提到 ETF 申赎清单。
- `get_trading_dates` / `get_trading_calendar`：交易日历。
- `get_trackzs_etf_info`：按跟踪指数获取 ETF 信息。
- `subscribe_hq`：订阅行情更新，样例注释显示最多 100 条。

## 本机验证结果

验证时间：2026-05-31

已通过：

- `tq.initialize(__file__)` 可以从项目目录直接初始化成功。
- 不需要把脚本放进 `D:\TongDaXing\PYPlugins\user` 也能连接。
- `get_market_snapshot` 可以获取 A 股、ETF、LOF、可转债快照。
- `get_market_snapshot` 可以获取已知代码的国内期货快照，例如沪银 `AG2608.SHF`、原油 `SC2607.INE`。
- `get_market_data` 可以获取 ETF、LOF 的日线 K 线。
- 普通 L1 行情下，`Buyp` / `Sellp` 返回数组，但第 2 到第 5 档多数为 0；第一版只能稳定使用买一卖一，完整五档需要后续确认 Level-2。

已验证样例：

```text
600519.SH  A 股快照可用
000001.SZ  A 股快照可用
510300.SH  ETF 快照可用，Jjjz 有值
513100.SH  ETF 快照可用，Jjjz 有值
162411.SZ  LOF 快照可用，Jjjz 为 0
161226.SZ  LOF 快照可用，Jjjz 为 0
127027.SZ  可转债快照可用
123107.SZ  可转债快照可用
```

关键字段初步映射：

| 通达信字段 | 项目字段 | 备注 |
| --- | --- | --- |
| `Now` | `marketPrice` | 场内最新价 |
| `LastClose` | `prevClose` | 昨收 |
| `Open` | `open` | 开盘价 |
| `Max` | `high` | 最高价 |
| `Min` | `low` | 最低价 |
| `Volume` | `volume` | 成交量，单位需二次确认，通常按手理解 |
| `Amount` | `turnover` | 样例说明为万元，项目内统一转换为元/亿元 |
| `Buyp[0]` | `bidPrice1` | 买一价 |
| `Buyv[0]` | `bidVolume1` | 买一量 |
| `Sellp[0]` | `askPrice1` | 卖一价 |
| `Sellv[0]` | `askVolume1` | 卖一量 |
| `Jjjz` | `referenceNav` / `iopv` | ETF 有值，LOF 样例为 0，不能直接当通用估值 |
| `Average` | `averagePrice` | 均价 |
| `ZAFPre3` | `changePct` | 涨跌幅字段候选，口径不稳定，项目内优先用 `Now / LastClose - 1` 重算 |

当前限制：

- `get_stock_list` 默认可以取 A 股列表，但 `list_type=31/32/33/34/35/36/91` 在当前环境返回 0 或 `server return none`。
- `list_type=92/101` 以及按期货前缀 `get_stock_list_in_sector(..., block_type=2)` 在当前环境返回 0。
- 因此第一版不能依赖通达信自动给 ETF/LOF/可转债品种池；需要自己维护重点基金清单，或从交易所/公开源补全。
- 期货代理信号也先维护候选合约列表，并在程序里自动选择成交量最大的可用合约。
- 当前没有确认 Level-2 权限，先按买一卖一设计滑点模型。
- `Jjjz` 对 ETF 有用，但对 LOF/QDII-LOF 不可用，需要估值引擎自己算。

样例脚本中 `get_stock_list` 的关键 `list_type`：

```text
31 ETF 基金
32 可转债
33 LOF 基金
34 所有可交易基金
35 所有沪深基金
36 T+0 基金
91 ETF 追踪的指数
```

## 待验证字段

第一轮探测脚本：

```text
tools/tdx_probe.py
tools/tdx_min_probe.py
```

要验证：

1. ETF、LOF、可转债列表是否能正常取到。当前未通过，需要另找品种池来源。
2. `get_market_snapshot` 是否返回最新价、成交额、买一卖一、五档盘口、IOPV/基金净值相关字段。已部分通过。
3. `get_market_data` 是否能返回 ETF、LOF、可转债 K 线。ETF/LOF 已通过，可转债需继续用有效代码验证。
4. `download_file(..., down_type=2)` 下载 ETF 申赎清单是否可用。
5. 订阅更新是否能用于 10 秒到 60 秒级提醒。

## 当前依赖

本机 Python 是 `3.14.5`，但还没有安装 `pandas` / `numpy`。TdxQuant 的 `tqcenter.py` 会直接 import 它们，所以需要先装依赖。

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements-tdx.txt
.\.venv\Scripts\python tools\tdx_probe.py
```

如果从项目目录直接运行 `tq.initialize(__file__)` 失败，再改为把探测脚本放到 `D:\TongDaXing\PYPlugins\user` 目录中运行。

## 下一步验证

1. 建立项目自有重点品种池。
2. 用 `get_market_snapshot` 批量拉取品种池行情。
3. 实现 `TdxQuantProvider`，把通达信字段转换为项目统一 `QuoteSnapshot`。已完成第一版。
4. 验证 `download_file(..., down_type=2)` 是否可拿 ETF PCF。
5. 验证 `subscribe_hq` 是否适合盘中实时刷新；若不稳定，第一版先用 10 秒到 30 秒轮询。

## 第一版评分链路

已实现：

```text
fund_profiles.json
  -> TdxQuantProvider 拉行情
  -> ValuationEngine 算估值和可交易边际
  -> OpportunityScorer 输出 executable / watch / normal / unavailable
```

运行：

```powershell
.\.venv\Scripts\python backend\tools\score_watchlist.py
```

当前配置仍有人工占位：

- 跟踪指数当日涨跌。
- 汇率涨跌。
- 估值误差安全垫。

这些字段后续要逐步改为自动采集和回放校准。

LOF / QDII-LOF 的最新官方净值、申购状态、赎回状态、日累计限额、申购费率已接入 `EastmoneyFundStatusProvider` 作为第一版公开数据源。

注意：ETF 的 `PCF 申赎状态 / 最小申赎单位` 和 LOF/QDII-LOF 的 `现金申购日限额` 不是同一种约束。评分器当前只对含 `LOF` 的品种检查现金申购限额；ETF 先使用通达信 PCF 判断申购/赎回是否开放，后续再单独建 ETF 一级市场权限、最小篮子规模、现金替代比例和 AP 通道成本模型。

## ETF PCF 验证

已验证通达信 `download_file(stock_code, down_time, down_type=2)` 可以下载 ETF 申赎清单摘要，文件保存到：

```text
D:\TongDaXing\PYPlugins\data\etfpcf{code}_{date}.json
```

样例：

```text
510300.SH -> etfpcf510300_20260529.json
513100.SH -> etfpcf513100_20260529.json
159915.SZ -> etfpcf159915_20260529.json
```

当前可稳定使用字段：

| 字段 | 含义 | 用途 |
| --- | --- | --- |
| `jjjc` | 基金简称 | 展示 |
| `jzrq` | 净值日期/清单日期 | 校验时效 |
| `sgfe` | 最小申赎单位 | 估算 ETF 一级市场门槛，不能当作现金申购日限额 |
| `cfgs` | 成分数量 | 校验 PCF 完整性 |
| `xjtdbl` | 现金替代比例 | 成本/风险 |
| `ygxj` | 预估现金部分 | 成本/校验 |
| `xjce` | 现金差额 | 成本/校验 |
| `sgshqk` | 申购赎回允许情况 | 直接阻断可执行机会 |

谨慎字段：

```text
shfe
jzrfe
```

这两个字段暂不参与估值，因为当前样例无法直接和 IOPV/单位净值对齐。

已实现：

```text
TdxPcfProvider
  -> 下载 PCF 摘要
  -> 解析申购/赎回状态
  -> score_watchlist.py 中覆盖 ETF 的申赎状态
```

运行：

```powershell
.\.venv\Scripts\python backend\tools\fetch_tdx_pcf.py
```
