# 实时估值与误差校准方案

调研日期：2026-05-31

## 目标

套利提醒的核心不是“看到溢价率”，而是得到一个可置信的实时估值，并知道这个估值的误差有多大。

最终提醒应基于：

```text
场内价格
- 实时估值
- 交易成本
- 申赎成本
- 盘口滑点
- 估值误差安全垫
= 可执行净套利空间
```

## 总体原则

1. 不同基金类型用不同估值模型。
2. 能用官方 IOPV / PCF 的 ETF，不优先自己从指数成分股重算。
3. LOF / QDII-LOF 没有可靠 IOPV 时，用跟踪指数、汇率、代理资产估值。
4. 每只基金必须持续记录“估值误差”，否则不允许触发高置信提醒。
5. 估值模型输出的不只是 `estimatedNav`，还要输出 `confidence` 和 `errorBufferPct`。

## 估值模型分层

### A. ETF：IOPV / PCF 优先

适用：

- 境内股票 ETF。
- 跨境 ETF。
- 商品 ETF。
- 黄金 ETF。
- 债券 ETF。

优先级：

```text
交易所/行情源 IOPV
  -> 根据 PCF 自算 IOPV 校验
  -> 根据跟踪指数涨跌估算
```

理由：

- 交易所 ETF 招募说明书通常明确，IOPV 根据申购赎回清单和组合证券实时成交数据计算，并在交易时间内发布。
- PCF 比指数成分股更接近 ETF 当日真实申赎篮子，包含现金替代、预估现金部分、最小申赎单位、申赎开关、申赎限额等。

基础公式：

```text
IOPV =
(
  必须现金替代金额
  + 可以现金替代证券数量 * 最新价格
  + 禁止现金替代证券数量 * 最新价格
  + 预估现金部分
) / 最小申购赎回单位对应份额
```

跨境 ETF 需要把境外证券价格按汇率换算为人民币。

### B. 指数 LOF：上一净值 + 指数涨跌

适用：

- 指数型 LOF。
- 场外申购、场内交易的指数基金。
- 没有实时 IOPV 的基金。

第一版估值：

```text
estimatedNavRaw_t = lastOfficialNav * (1 + beta * benchmarkReturn_t + fxReturn_t * fxExposure)
```

其中：

- `lastOfficialNav`：最近披露的基金单位净值。
- `benchmarkReturn_t`：跟踪指数从上一净值估值时点到当前的涨跌幅。
- `beta`：基金对指数的实际跟踪系数，初始为 1，后续用历史误差校准。
- `fxExposure`：QDII 或跨境资产的汇率暴露。

如果基金招募说明书披露跟踪指数和跟踪误差控制目标，则作为模型基础配置。

是否要拆到指数成分股？

- 第一版不必对所有 LOF 拆到公司权重。
- 只有当指数行情不可得、指数停更、指数跨市场、或跟踪误差异常时，才需要成分股级别重算。
- 对 ETF，PCF 通常比指数成分股更重要；对 LOF，指数涨跌通常比旧季报持仓更可靠。

### C. QDII-LOF / QDII-ETF：指数 + 汇率 + 时差代理

适用：

- 原油、黄金、白银。
- 纳指、标普、恒生、港股科技。
- 全球油气、海外债券等。

估值因素：

- 标的指数涨跌。
- 海外市场是否开盘。
- 海外期货或参考 ETF 价格。
- 人民币汇率。
- 最近官方净值披露滞后天数。
- QDII 外汇额度和申购暂停概率。

公式框架：

```text
estimatedNavRaw_t =
  lastOfficialNav
  * (1 + overseasProxyReturn_t)
  * (1 + fxReturn_t * fxExposure)
```

海外市场休市或未开盘时：

```text
overseasProxyReturn_t =
  期货涨跌
  或 同类境外 ETF 盘前/隔夜涨跌
  或 标的指数上一收盘涨跌
```

QDII 估值必须降低置信度，因为净值披露可能 T+1 / T+2，且汇率、假期、外汇额度会造成误差。

### D. 主动基金 / 持仓不透明基金

适用：

- 主动管理 LOF。
- 持仓季度披露、实时性弱的基金。

估值方法：

```text
季度持仓加权估值
  + 行业指数回归
  + 历史 beta 校准
```

这类基金第一版只做观察，不建议作为高置信套利提醒。

## 误差校准

每只基金都维护一张估值误差表。

### 每日收盘误差

在官方净值披露后，回看当日收盘时刻的估值：

```text
rawErrorPct =
  (estimatedNavClose - officialNav) / officialNav
```

记录：

- `biasPct`：滚动平均误差。
- `maePct`：平均绝对误差。
- `rmsePct`：均方根误差。
- `p90AbsErrorPct`：90 分位绝对误差。
- `p95AbsErrorPct`：95 分位绝对误差。
- `sampleSize`：样本数。
- `lastUpdated`：最近校准日期。

### 偏差修正

```text
estimatedNavCorrected =
  estimatedNavRaw / (1 + rollingBiasPct)
```

或者：

```text
fundReturn = alpha + beta * benchmarkReturn + gamma * fxReturn + residual
```

滚动回归更新：

- `alpha`：管理费、现金拖累、长期偏移。
- `beta`：指数暴露。
- `gamma`：汇率暴露。
- `residual`：无法解释的误差。

### 安全垫

提醒时不看毛溢价，而看：

```text
tradableEdgePct =
  grossPremiumPct
  - estimatedCostPct
  - slippagePct
  - errorBufferPct
```

其中：

```text
errorBufferPct = max(p95AbsErrorPct, minErrorBufferPct)
```

建议初始值：

```text
A 股 ETF：0.10% - 0.30%
普通指数 LOF：0.30% - 0.80%
QDII ETF：0.50% - 1.50%
QDII LOF：1.00% - 3.00%
主动基金：不触发高置信提醒
```

这些值后续由历史误差自动校准。

## 字段设计

### FundProfile

```json
{
  "code": "162411",
  "name": "华宝油气",
  "fundType": "QDII-LOF",
  "exchange": "SZSE",
  "trackingIndexCode": "SPSIOP",
  "trackingIndexName": "标普石油天然气上游股票指数",
  "benchmarkCurrency": "USD",
  "baseCurrency": "CNY",
  "valuationModel": "qdii_proxy",
  "navPublishLagDays": 2,
  "usesIopv": false,
  "usesPcf": false,
  "subscriptionPath": "场内/场外申购",
  "redemptionPath": "场内/场外赎回"
}
```

### ValuationSnapshot

```json
{
  "code": "162411",
  "estimatedNavRaw": 0.8660,
  "estimatedNavCorrected": 0.8625,
  "officialNav": 0.7618,
  "officialNavDate": "2026-05-29",
  "quoteTime": "2026-05-31 11:05:00",
  "model": "qdii_proxy",
  "confidence": "medium",
  "grossPremiumPct": 13.68,
  "estimatedCostPct": 0.55,
  "errorBufferPct": 1.20,
  "tradableEdgePct": 11.93,
  "inputs": {
    "benchmarkReturnPct": 1.80,
    "fxReturnPct": 0.20,
    "beta": 0.98,
    "gamma": 1.00
  }
}
```

### ValuationErrorStat

```json
{
  "code": "162411",
  "model": "qdii_proxy",
  "sampleSize": 60,
  "biasPct": 0.18,
  "maePct": 0.72,
  "rmsePct": 1.05,
  "p90AbsErrorPct": 1.41,
  "p95AbsErrorPct": 1.86,
  "lastUpdated": "2026-05-31"
}
```

## 数据源分工

### 必需数据

| 数据 | 优先来源 | 备用来源 |
| --- | --- | --- |
| 场内价格、成交额、盘口 | QMT / TdxQuant | 公开行情 |
| IOPV | QMT / 交易所行情 | PCF 自算 |
| ETF PCF | 上交所/深交所/基金公司 | 券商终端 |
| 官方净值 | 基金电子披露网站 / 基金公司 | 交易所基金信息 |
| 跟踪指数 | 招募说明书 / 基金产品资料概要 | 第三方基金库 |
| 指数行情 | 指数公司 / 行情源 | 公开行情 |
| 指数成分权重 | 指数公司 | 第三方数据 |
| 汇率 | 中国外汇交易中心 / 行情源 | 银行/第三方 |
| 申购限额/暂停申购 | 基金公告 / 销售平台 | 人工配置校验 |
| 交易日历 | 上交所/深交所/海外交易所 | 第三方日历 |

## 实施步骤

## 已落地的第一版信号层

当前已经把估值输入从基金档案中的手填字段，升级为独立信号配置：

```text
valuation_signals.json
  -> MarketSignalProvider
  -> ValuationSignalResolver
  -> ValuationEngine
```

第一版支持：

- `tdx_quote`：用通达信快照计算指数/代理标的涨跌幅。
- `tdx_candidate_quote`：配置一组通达信候选合约，拉取快照后自动选择成交量最大的合约，并用 `Now / LastClose - 1` 计算涨跌幅。
- `manual`：暂时无法自动采集的海外代理资产或汇率，用人工配置占位，并强制写入低置信度原因。

已验证信号：

```text
HS300_TDX      沪深300指数，来源通达信
SPSIOP_PROXY   国内原油期货代理，来源通达信候选合约，低置信度
SILVER_PROXY   沪银期货代理，来源通达信候选合约
USDCNY         美元兑人民币，暂用 manual
```

注意：`manual` 信号只能用于保持链路完整，不能作为高置信提醒依据。国内原油期货对华宝油气也只是低置信代理，因为它不能完整代表海外油气上游股票指数；后续要优先替换为真实海外油气指数/ETF、商品期货和汇率源。

### M2-1：基金档案

为每只基金建立 `FundProfile`：

- 基金类型。
- 交易所。
- 跟踪指数。
- 估值模型。
- 净值披露滞后。
- 是否有 IOPV。
- 是否有 PCF。
- 申购/赎回路径。

先用 20 到 50 只重点基金人工校准，后续再自动化抓取。

### M2-2：估值引擎

实现三个模型：

```text
iopv_model       ETF 用 IOPV / PCF
index_model      指数 LOF 用上一净值 + 指数涨跌
qdii_proxy_model QDII 用海外代理资产 + 汇率
```

所有模型输出同一个 `ValuationSnapshot`。

### M2-3：误差回放

每天官方净值出来后：

1. 找到当日收盘时刻估值。
2. 对比官方净值。
3. 记录误差。
4. 更新滚动 bias / MAE / RMSE / P95。
5. 自动调整下一日的 `errorBufferPct`。

### M2-4：提醒规则升级

旧规则：

```text
溢价率 > 阈值
```

新规则：

```text
tradableEdgePct > 阈值
且 估值置信度不低
且 申购/赎回路径开放
且 额度满足计划交易额
且 盘口满足计划交易额
```

### M2-5：异常监控

估值引擎必须监控：

- IOPV 停止更新。
- 指数行情停止更新。
- 汇率停止更新。
- 官方净值缺失。
- 估值误差突然放大。
- 基金公告出现暂停申购、大额限购、溢价风险提示。

## 关键判断

### 是否必须知道基金追踪哪个指数？

必须。尤其是 LOF、QDII、指数基金。没有跟踪指数，就无法建立可信估值模型。

### 是否必须知道指数成分股和权重？

不是所有基金第一版都必须。

- ETF：优先 PCF，不优先指数成分股。
- 普通指数 LOF：第一版用指数涨跌，成分股作为增强和校验。
- QDII：第一版用海外指数/期货/ETF 代理，成分股级别以后再做。
- 主动基金：成分股通常滞后，只能做低置信估值。

### 如何“追踪消除误差”？

不是手工猜，而是让系统每天做误差闭环：

```text
估值 -> 等官方净值 -> 计算误差 -> 更新 bias/beta/errorBuffer -> 次日修正估值
```

当某只基金样本足够多后，可以从固定参数升级为滚动回归模型。

## 参考资料

- 上交所 ETF 申购赎回清单页面：https://www.sse.com.cn/disclosure/fund/etflist/
- 深交所基金信息页面：https://www.szse.cn/disclosure/fund/index.html
- 上交所 ETF 招募说明书 IOPV 计算示例：https://www.sse.com.cn/disclosure/fund/announcement/c/new/2025-12-08/510560_20251208_IBSF.pdf
- 深交所 ETF 技术文档，含 IOPV 与 PCF 字段：https://www.szse.cn/marketServices/technicalservice/history/P020180328468147239406.pdf
- 上交所 ETF 申购赎回清单字段技术文档：https://www.sse.com.cn/services/tradingtech/development/c/10791074/files/fd7d24ee9c5946f4a571d6049e5d70f2.pdf
- 证监会《公开募集证券投资基金信息披露管理办法》：https://www.csrc.gov.cn/csrc/c106256/c1653985/content.shtml
- 证监会基金信息披露网站上线说明：https://www.csrc.gov.cn/csrc/c100028/c1002707/content.shtml
- 深交所 LOF 申赎规则说明：https://investor.sse.org.cn/knowledge/fund/trade/t20210113_584216.html
