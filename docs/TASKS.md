# 任务清单

## 当前 Sprint：MVP 原型

- [x] 建项目目录。
- [x] 写 PRD。
- [x] 写架构文档。
- [x] 写路线图。
- [x] 完成静态看板页面。
- [x] 支持排序。
- [x] 支持分类筛选。
- [x] 支持自选筛选。
- [x] 支持阈值高亮。
- [x] 补充套利字段检查清单。
- [x] 补充单日申购限额和申赎状态。
- [x] 区分可执行机会与观察机会。
- [x] 拆分前端模块。
- [x] 补充模块化设计文档。

## 下一 Sprint：真实行情

- [x] 初步调研 QMT / 通达信本地行情方案。
- [x] 设计实时估值与误差校准方案。
- [x] 将第一数据源暂定为 TdxQuant。
- [x] 安装支持 TQ 策略功能的通达信终端。
- [x] 定位 `tqcenter.py` 和样例脚本。
- [x] 验证 `tqcenter.py` 和 `tq.initialize(__file__)` 可用。
- [x] 初步验证 ETF、LOF、可转债实时快照和买一卖一字段。
- [ ] 验证 ETF/LOF/可转债品种列表来源。
- [ ] 验证基金净值、指数行情、指数成分股字段。
- [x] 实现 `TdxQuantProvider` 字段转换。
- [x] 建立第一版重点基金档案配置。
- [x] 实现第一版估值引擎。
- [x] 实现第一版机会评分器。
- [x] 增加领域规则单元测试。
- [x] 验证 ETF PCF 下载能力。
- [x] 实现 `TdxPcfProvider` 并接入 ETF 申赎状态。
- [x] 实现 `EastmoneyFundStatusProvider` 并接入 LOF/QDII-LOF 净值、申购状态和限额。
- [x] 区分 ETF PCF 申赎约束和 LOF 现金申购日限额。
- [ ] 确认通达信 TdxQuant 版本、授权和费用。
- [x] 建立第一批重点基金档案。
- [ ] 确认重点基金追踪指数、净值披露滞后和估值模型。
- [x] 实现估值引擎 `iopv_model` / `index_model` / `qdii_proxy_model` 第一版。
- [x] 建立估值信号层，支持指数、代理资产、汇率输入。
- [x] 实现 `MarketSignalProvider` 和 `ValuationSignalResolver`。
- [x] 将评分链路从手填 `proxyReturnPct/fxReturnPct` 升级为信号配置驱动。
- [x] 接入通达信候选期货合约信号，自动选择成交量最大的沪银/原油代理合约。
- [x] 将通达信涨跌幅统一为 `Now / LastClose - 1` 计算，规避原始字段口径不稳定。
- [ ] 实现估值误差回放与滚动校准。
- [ ] 向券商确认 QMT / miniQMT 开通门槛和 Level-2 费用。
- [ ] 向通达信确认 TdxQuant 可用版本、授权和费用。
- [x] 确认第一版申购限额和申赎状态的数据来源。
- [x] 确认 ETF 申购赎回清单 PCF 的第一版采集方式。
- [ ] 确认费用和确认/到账周期的数据来源。
- [ ] 实现行情采集器。
- [x] 实现 FastAPI 后端。
- [x] 抽取 `OpportunityService`，让 CLI/API/后续任务复用同一评分链路。
- [x] 前端改为请求 API。
- [x] FastAPI 托管前端页面，打开根路径即可查看真实机会看板。
- [ ] 添加缓存和错误提示。

## 提醒 Sprint

- [ ] 设计提醒规则。
- [ ] 实现浏览器通知。
- [ ] 实现企业微信或 Telegram 推送。
- [ ] 实现提醒冷却时间。
- [ ] 实现提醒日志。
