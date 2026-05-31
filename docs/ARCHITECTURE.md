# 架构设计

## 阶段一：静态 MVP

```text
浏览器页面
  -> 本地模拟数据
  -> 前端计算溢价率、排序、筛选、高亮
```

用途：

- 快速确认页面布局和核心指标。
- 先把交互、字段、提醒阈值打磨好。

前端模块边界：

```text
data     -> 数据源适配，当前是模拟数据
domain   -> 套利判断、机会评分、成本和限额规则
ui       -> 表格、标签、摘要等展示
app      -> 状态、事件、模块编排
```

## 阶段二：真实数据服务

```text
前端 Web
  -> API Server
    -> 行情采集器
    -> 公告/申购限额采集器
    -> ETF PCF 采集器
    -> 数据清洗
    -> 套利规则引擎
    -> SQLite/PostgreSQL
    -> 提醒任务
```

建议技术：

- 前端：React / Vue / 或继续 Vanilla JS。
- 后端：Python FastAPI。
- 任务：APScheduler。
- 数据库：SQLite 起步，PostgreSQL 扩展。
- 部署：本地电脑或轻量云服务器。

后端模块边界：

```text
api             HTTP 接口
collectors      行情、公告、PCF、费用、交易日历采集
adapters        QMT、通达信、网页、第三方 API 适配器
domain          套利规则、成本模型、评分模型
models          统一数据模型
repositories    数据读写
notifications   推送渠道
jobs            定时任务、失败重试、提醒去重
```

当前数据源落地：

```text
TdxQuantProvider
  -> get_market_snapshot
  -> QuoteSnapshot
  -> ValuationEngine
  -> OpportunityScorer
```

通达信仅作为行情源，不作为申购限额、基金公告、ETF PCF 的唯一来源。

## 数据模型

基金行情统一为：

```json
{
  "code": "161226",
  "name": "白银基金",
  "category": "QDII-ETF",
  "fundType": "QDII-LOF",
  "exchange": "SZSE",
  "arbitragePath": "申购后卖出",
  "purchaseChannel": "场外",
  "nav": 3.3541,
  "navChangePct": 1.41,
  "marketPrice": 5.247,
  "priceChangePct": 0,
  "bidPrice": 5.246,
  "askPrice": 5.247,
  "spreadPct": 0.02,
  "premiumPct": 56.43,
  "netPremiumPct": 55.98,
  "turnover": 0,
  "depthYuan": 0,
  "tradeStatus": "停牌",
  "subscriptionStatus": "暂停",
  "redemptionStatus": "开放",
  "purchaseLimitYuan": 0,
  "purchaseLimitScope": "单日单账户",
  "purchaseRemainingYuan": 0,
  "feePct": 0.45,
  "settlementCycle": "T+2确认，T+3可用",
  "navTime": "2026-05-30",
  "quoteTime": "2026-05-31 11:05:00",
  "executionStatus": "不可执行",
  "executionReasons": ["暂停申购", "停牌"],
  "watch": true,
  "updatedAt": "2026-05-31 11:05:00"
}
```

ETF 类品种还需要扩展：

```json
{
  "creationRedemptionUnit": 1000000,
  "creationRedemptionSwitch": "申购和赎回皆允许",
  "creationLimit": 50000000,
  "redemptionLimit": 50000000,
  "netCreationLimit": null,
  "netRedemptionLimit": null,
  "creationLimitPerAccount": 10000000,
  "redemptionLimitPerAccount": 10000000,
  "publishIopv": true,
  "estimatedCashComponent": 1200.15,
  "cashSubstituteRatio": 0.1
}
```

## 数据源候选

- 通达信 / QMT：适合个人本地行情，稳定性较好。
- 公开网页：容易起步，但可能不稳定、限流或结构变化。
- 第三方金融 API：稳定性较好，但可能收费或限制调用频率。

## 风险

- 基金估值、净值和场内价格不是同一时间点，溢价率会有误差。
- QDII 的实时估值可能滞后。
- 限购、暂停申购、暂停赎回、暂停交易等状态会直接影响可操作性。
- 单日申购限额可能按单账户、单渠道、单基金份额类别分别计算，不能只存一个模糊标签。
- 交易佣金、申购费、赎回费、现金替代和滑点会吞掉毛溢价。
- 份额确认、可卖出日、赎回到账日会带来折溢价收敛风险。
- 自动交易要单独做风控和合规评估。
