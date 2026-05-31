# 模块化设计

项目第一原则：新增功能时优先新增模块或适配器，避免改动核心套利判断和页面编排。

## 当前前端模块

```text
web/src/
  app.js                  # 页面状态、事件绑定、模块编排
  data/
    mockFunds.js          # 模拟行情数据，后续替换为 API 数据适配器
  domain/
    execution.js          # 可执行套利判断规则
    formatters.js         # 金额、百分比、状态格式化
  ui/
    table.js              # 表格渲染和执行结论摘要
```

## 未来后端模块

```text
  backend/
  app/
    api/                  # FastAPI 接口，当前提供 health / valuation-signals / opportunities
    config/               # 阈值、品种池、账户与渠道配置
    models/               # 统一数据模型
    providers/            # 行情源统一接口，当前含 TdxQuantProvider
    services/             # 编排服务，当前含 OpportunityService
    api/                  # HTTP 接口
    collectors/           # 行情、公告、PCF、费用等采集器
    adapters/             # QMT、通达信、网页、第三方 API 适配器
    domain/               # 套利规则、估值引擎、成本模型、机会评分
    repositories/         # SQLite/PostgreSQL 读写
    notifications/        # 浏览器、企业微信、Telegram、邮件
    jobs/                 # 定时刷新、提醒去重、清理任务
  tools/
    fetch_tdx_quotes.py   # 拉取通达信快照并转换为统一字段
    fetch_tdx_pcf.py      # 下载并解析通达信 ETF PCF 摘要
    fetch_fund_status.py  # 拉取天天基金净值、申购状态和限额
    fetch_valuation_signals.py # 拉取估值用指数/代理资产/汇率信号
    score_watchlist.py    # 拉行情、估值、评分，输出机会列表
```

## 估值信号层

新增估值信号层，位置：

```text
backend/app/config/valuation_signals.json
backend/app/models/market_signal.py
backend/app/providers/market_signal_provider.py
backend/app/domain/valuation_signal_resolver.py
```

职责：

- `MarketSignalProvider` 只负责把通达信、通达信候选合约、人工配置、未来外部行情源转换为统一 `MarketSignal`。
- `ValuationSignalResolver` 只负责按基金档案里的 `benchmarkSignalId` / `fxSignalId` 找到信号，并生成估值输入。
- `ValuationEngine` 只消费统一后的信号，不直接关心行情来自通达信、网页还是 QMT。
- 海外代理资产和汇率暂时允许 `manual` 占位，但必须在 `reasons` 中明确标低置信度，避免误判为真实高质量估值。
- 期货主力合约列表当前不能稳定从通达信列表接口获取，因此用 `candidateCodes` 配置候选合约，并自动选择成交量最大的可用合约。

## 扩展规则

### 新增数据源

只新增 `collector` 或 `adapter`，输出统一基金行情模型。前端和套利规则不直接依赖某个网站、券商或接口字段。

### 新增品种

新增品种类型时，先定义字段差异和套利路径，再加对应规则。例如：

- LOF：场内价格、场外申购、份额确认、可卖出日。
- ETF：PCF、最小申赎单位、现金替代、IOPV、篮子股票。
- QDII：净值滞后、海外市场日历、外汇额度、跨境节假日。
- 可转债：转股价值、溢价率、强赎风险、剩余规模、评级。

### 新增提醒渠道

新增 `notification provider`，接收统一提醒事件：

```json
{
  "type": "arbitrage_opportunity",
  "code": "163208",
  "name": "全球油气能源",
  "level": "executable",
  "message": "净溢价 17.82%，额度和流动性满足",
  "createdAt": "2026-05-31 12:10:00"
}
```

### 新增规则

规则应该是纯函数，输入统一数据和用户阈值，输出执行结论、原因和评分。不要在规则里请求网络、读写数据库或操作页面。

### 新增估值模型

新增 `valuation model`，输入基金档案、行情快照、净值、指数、汇率和 PCF，输出统一估值快照。估值模型必须给出误差安全垫和置信度，不允许只输出一个估值数。

## 第一阶段边界

- 可以先用静态数据，但字段必须贴近真实数据。
- 可以先用浏览器页面，但领域规则必须独立出来。
- 可以先只做基金，但模型要允许后续增加其他套利品种。
- 可以先只做提醒，但不要把自动交易逻辑混进提醒模块。
