# Arbitrage Alert

套利机会提醒神器，第一阶段目标是做成一个个人可用的网页看板：

- 监控 LOF / ETF / QDII 等基金的场内价格、估值或净值、溢价率、成交额和交易状态。
- 支持按溢价率、成交额、价格涨跌幅排序。
- 支持申购限额、申赎状态、成本、资金占用周期、自选池和提醒规则。
- 先做提醒，不做自动下单。

## MVP 范围

第一版只解决一个问题：在交易时间内快速发现值得关注的高溢价或高折价机会。

包含：

- 一个网页版监控看板。
- 模拟数据源和统一数据结构。
- 溢价率、成交额、单日申购限额、申赎状态、状态标签、高亮规则。
- 基础筛选和排序。
- 本地浏览器提醒逻辑的前端占位。

暂不包含：

- 自动交易。
- 真实资金账户接入。
- 复杂用户系统。
- 多人协作权限。

## 目录

```text
arbitrage-alert/
  backend/
    app/
      config/
      models/
      providers/
    tools/
  docs/
    MODULES.md
    DATA_SOURCE_RESEARCH.md
    VALUATION_ENGINE.md
    TDX_INTEGRATION.md
    PRD.md
    ARCHITECTURE.md
    ROADMAP.md
    TASKS.md
  web/
    index.html
    src/
      app.js
      data/
      domain/
      ui/
      styles.css
  tools/
    tdx_probe.py
```

## 设计原则

- 数据源、套利规则、页面渲染、提醒渠道分层。
- 统一内部数据模型，外部行情和公告都先通过适配器清洗。
- 新增品种、新增数据源、新增提醒渠道时，优先新增模块，不重写核心流程。
- MVP 也保留清晰边界，避免后续接真实行情时推倒重来。

## 本地预览

第一版是纯静态页面，直接打开：

```text
web/index.html
```

后续接入真实行情后，再升级为前后端服务。
