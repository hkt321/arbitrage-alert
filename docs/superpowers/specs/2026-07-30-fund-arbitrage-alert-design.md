# 基金套利每日快照提醒系统设计

日期：2026-07-30

状态：用户已确认设计，待书面复核

基线：`hkt321/arbitrage-alert` `6c6be9029c566ded5150228cf84157af09ac6f94`

## 1. 目标与产品边界

本项目面向单个用户，在 Windows 电脑上运行。系统每天 14:00 对沪深官方基金目录做一次完整快照，发现 LOF 溢价、折价套利候选，并通过本地网页和 Server酱提供人工复核提醒。

本版的产品名称和能力边界是“每日 14:00 快照提醒”，不是全天实时监控：

- 沪深交易日 14:00 自动执行一次完整扫描。
- 网页支持手动立即刷新。
- 行情数据最大允许年龄为 5 分钟。
- 提醒不等于下单建议，不承诺收益，也不自动交易。
- “可执行候选”只表示数据与规则链满足系统准入条件，用户操作前仍须在券商通道再次确认。

非目标：

- 自动下单、账户持仓读取和组合仓位管理。
- 云端、多用户、移动端或远程访问。
- 首版自动解析所有基金管理人的全部公告。
- 首版自动为所有 QDII、主动基金、债券基金建立高置信盘中估值。
- 首版 ETF 一级市场申赎执行。

## 2. 全量目录、分类与执行范围

### 2.1 全量的定义

基金全集以[上交所基金目录](https://www.sse.com.cn/assortment/fund/)和[深交所基金目录](https://www.szse.cn/market/fund/list/stockFundList/index.html)为准。行情源不得反向定义基金池。

每个官方基金代码必须有唯一记录，并落入以下状态之一：

- `executable_candidate`：满足方向、估值、规则、费率、行情、容量和净边际门槛。
- `watch`：数据完整但未达到净边际，或存在尚未满足的可操作条件。
- `data_insufficient`：缺少或冲突的关键数据，不允许推断为“无机会”。
- `not_applicable`：产品机制不适用于本版 LOF 双向套利。

系统不得使用 `top N` 截断。每次扫描输出：

- 官方目录总数。
- 已分类数。
- 长桥有效行情数。
- 公共降级行情数。
- 有效估值数。
- 规则已核验数。
- 各状态数量。
- 官方目录与各数据源的覆盖差集。

### 2.2 首版可执行范围

允许进入 `executable_candidate` 的品种仅包括：

1. 国内被动股票指数 LOF，且官方跟踪标的、最新净值、申赎规则、费率和方向性行情全部有效。
2. QDII-LOF 核验白名单。白名单初始为空；每只基金必须人工记录跟踪标的或代理资产、汇率、净值时点、境内外交易日历、估值误差垫、持有期风险垫、证据来源和有效期。

其他品种处理：

- 主动股票/混合、债券、FOF、商品、货币类 LOF：全量展示，首版只能 `watch` 或 `data_insufficient`。
- ETF：全量监控理论偏离，首版不进入一级申赎可执行状态。仅在取得 5 分钟内、带源时间的交易所或其他已核准可信 IOPV/盘中参考净值时计算
  `etf_deviation = P_last / IOPV - 1`；缺少可信 IOPV 时为 `data_insufficient`。公共 IOPV 最多支持 `watch`。
- 封闭式基金、公募 REITs：`not_applicable`。
- QDII-LOF 非白名单：全量展示，但不得进入 `executable_candidate`。

## 3. 数据来源与可信度裁决

### 3.1 行情

优先级：

1. 长桥 OpenAPI：场内最新价、成交时间、交易状态、成交额；折价候选还需要卖方盘口。
2. Eastmoney 与 Tencent 两个彼此独立的公共行情适配器：仅在长桥缺失、过期或失败时用于降级观察。
3. Palmmicro：只作为对照数据，不再决定基金目录、执行状态或主估值。

长桥行情有效条件：

- 代码和交易所映射正确。
- 交易状态允许交易。
- 源时间距扫描基准时间不超过 5 分钟。
- 价格为正且字段完整。

公共双源有效条件：

- 两源代码和交易所一致。
- 两源源时间均不超过 5 分钟。
- 设两源价格为 `p1`、`p2`，中间价为 `mid`，最小价位为 `tick`；必须满足
  `abs(p1 - p2) / mid <= max(0.002, 2 × tick / mid)`。
- 冲突时不得平均，直接降为 `data_insufficient`。
- 即使双源一致，也只允许 `watch`，不得用于 `executable_candidate`。

### 3.2 净值与估值

净值优先级：

1. 基金管理人正式披露的份额净值及估值日期。
2. 交易所披露的 LOF 净值。
3. 其他来源只能交叉核验，不能单独支持可执行状态。

国内被动股票指数 LOF 的首版估值：

```text
estimated_nav =
  latest_official_nav
  × (1 + benchmark_return_since_nav_time)
```

估值必须记录：

- 官方净值及其估值日期。
- 跟踪指数、指数行情来源和基准时点。
- 原始估算净值。
- 基金类别误差垫。
- 置信度和阻断原因。

所有盘中估值信号（跟踪指数、代理资产、期货、ETF、汇率）都必须经过来源准入：

- `trusted`：基金级配置明确允许的长桥行情，或对应指数公司、交易所、外汇官方来源，并具有可验证的源时间。
- `public_degraded`：Eastmoney、Tencent 或其他未核准公共源，只能支持 `watch`。
- `manual_value`：人工填写的行情数值不能支持 `executable_candidate`；人工只能核验信号映射和官方规则。

除官方净值外，任何参与可执行估值的盘中信号都必须满足 5 分钟时效门。基金级配置未明确 provider、代码和基准时点时，实施者不得自行选择近似信号。

QDII 白名单使用基金级显式配置：

```text
estimated_nav =
  latest_official_nav
  × overseas_proxy_factor
  × fx_factor
```

代理指数、ETF、期货和汇率信号优先使用长桥或对应指数/外汇官方来源。公共降级信号只能支持观察。每个白名单配置必须明确实际 provider、证券代码、币种和基准时点；不得由实施者临时选择相似资产。若海外市场时区、节假日、代理资产、汇率或净值滞后无法对齐，则降为 `data_insufficient`。

### 3.3 申赎状态、限额和费率

可信度优先级：

1. 基金管理人最新生效公告。
2. 交易所公告或业务状态。
3. 最新招募说明书、产品资料概要和费率公告。
4. 用户在网页中基于基金管理人、交易所或实际券商通道完成的人工核验。
5. 公共聚合网站只能生成 `watch`，不能支持 `executable_candidate`。

人工核验必须保存：

- 基金、份额类别和场内/场外渠道。
- `can_subscribe`、`can_redeem`。
- 单笔、单日、单账户和全渠道限额。
- 申购、赎回费率及金额/持有期档位。
- 申购确认、份额可卖、买入后最早可赎回等基金与渠道级周期规则。
- 证据来源 URL 或文件标识。
- 核验时间和有效期。

当日已使用申购/赎回额度是独立的可选用户声明，不属于规则核验的必填证据。未填写时按 0 处理，每个沪深交易日自动重置，并在容量旁持续显示假设警告。

人工记录到期、来源冲突、字段无法解析或适用渠道不明时，自动失效并降级。

人工核验不是允许用户凭印象覆盖规则。公共聚合页面本身不能作为人工核验的唯一证据。

## 4. 毛边际、净边际与容量

### 4.1 必填配置

系统不内置会产生真实提醒的投资参数默认值。正式启用前，用户必须填写：

- 全局单机会资金上限。
- 最低净边际阈值。
- 券商买卖佣金和最低收费。
- 各基金类别的估值误差垫。
- 各基金类别的持有期风险垫。
- 溢价路径固定流动性/滑点垫。

支持基金级覆盖配置。任一关键值缺失时可展示理论数据，但不得生成可执行提醒。

### 4.2 毛边际

设：

- `P_last`：5 分钟内最新场内成交价。
- `V_est`：对齐当前估值时点的估算净值。

```text
premium_gross = P_last / V_est - 1
discount_gross = V_est / P_last - 1
```

毛边际只表达原始折溢价，不扣费用或风险垫。

费用不得压成单个 `fee_pct`。领域层使用以下金额函数处理费率档位、最低佣金和持有期：

- `subscription_units(amount_cny, nav, fee_schedule)`
- `sell_proceeds(units, price, commission_schedule)`
- `buy_units(amount_cny, orderbook, commission_schedule)`
- `redemption_proceeds(units, nav, holding_days, fee_schedule)`

券商佣金按配置执行 `max(成交金额 × 佣金率, 最低收费)`；明确免收时才可为 0。基金申购费按申购金额档位计算，赎回费按持有期和份额类别计算。任何适用档位不明确时阻断可执行状态。

### 4.3 溢价净边际与容量

溢价路径：场内申购，确认并可卖后在二级市场卖出。

对候选金额 `amount`：

```text
adverse_nav = V_est × (1 + valuation_error_buffer)
adverse_sell_price = P_last × (1 - sell_slippage_buffer)
units = subscription_units(amount, adverse_nav, subscription_fee_schedule)
proceeds = sell_proceeds(units, adverse_sell_price, sell_commission_schedule)
premium_net(amount) = proceeds / amount - 1 - holding_period_risk_buffer
```

容量：

```text
premium_capacity_cny =
  floor_to_allowed_increment(
    min(
      global_manual_cap,
      fund_override_cap,
      official_subscription_limit - manual_used_subscription_amount,
      max_amount_meeting_net_threshold
    )
  )
```

按用户确认，当前买盘不直接限制溢价申购容量；界面必须显示“未来卖出流动性未保证”，并在净边际中扣固定流动性/滑点垫。

`floor_to_allowed_increment` 使用官方申购最低金额和递增单位；字段缺失时不得自行假设，降为 `data_insufficient`。

### 4.4 折价净边际与容量

折价路径：二级市场买入，随后赎回。

对卖方盘口按价格从低到高累计，计算目标金额对应的加权买入价 `P_ask(amount)`：

`expected_holding_days` 不是固定默认值。系统根据扫描交易日、沪深交易日历，以及已核验的基金/渠道确认与最早可赎回规则，计算预计赎回申请日，再按费率文件规定的自然日或交易日口径计算持有期。周期规则或计日口径未知时，折价路径为 `data_insufficient`。

```text
adverse_nav = V_est × (1 - valuation_error_buffer)
units, actual_cost = buy_units(
  amount,
  orderbook,
  buy_commission_schedule
)
proceeds = redemption_proceeds(
  units,
  adverse_nav,
  expected_holding_days,
  redemption_fee_schedule
)
discount_net(amount) =
  proceeds / actual_cost - 1 - holding_period_risk_buffer
```

从小到大累计盘口，选择净边际仍不低于全局阈值的最大金额：

```text
discount_capacity_cny =
  floor_to_trade_lot(
    min(
      global_manual_cap,
      fund_override_cap,
      official_redemption_limit - manual_used_redemption_amount,
      max_orderbook_amount_meeting_net_threshold
    )
  )
```

折价候选缺少有效卖方盘口时只能 `watch`。

`floor_to_trade_lot` 使用交易所或证券元数据中的交易单位，并逐档模拟整数交易单位；交易单位未知时降级。申赎限额保留原始单位，计算时按不利净值转换为份额或人民币，不允许直接混用。

不存在基金级覆盖上限时忽略 `fund_override_cap`；官方明确“不限额”时将对应限额视为无穷大。未知、无法解析或已过期的限额不是“不限额”，必须降级。全局资金上限缺失时不计算可执行容量。

### 4.5 展示规则

看板分列显示：

- 毛边际。
- 净边际。
- 最大估算容量人民币金额。
- 容量的首个约束原因。

容量是约束下的最大估算金额，不是建议仓位。路径被阻断时显示 `0 元` 和阻断原因；不得用破折号隐藏原因。未录入当日已用额度时按 0 处理，并显示“假设今日尚未使用额度”。

## 5. 机会状态与通知状态机

机会键为 `(exchange, fund_code, direction)`。

进入 `executable_candidate` 必须同时满足：

- 品种在首版可执行范围。
- 行情、估值、申赎、限额、费率全部通过来源与时效门。
- 容量大于 0。
- 净边际达到用户配置阈值。
- 扫描通过全局质量门。

Server酱规则：

- 每次连续机会首次进入候选时推送一次。
- 持续候选不重复推送。
- 连续 3 次合格退出后，事件重新武装。
- 合格退出要求：全局质量门通过、该基金关键数据完整，并且至少一个可执行谓词为假。申赎关闭、容量为 0、品种退出白名单等都可形成合格退出。
- 仅当唯一退出原因是净边际不足时，使用 `最低净边际阈值 - 0.20 个百分点` 的滞回线，减少阈值附近抖动。
- 该基金为 `data_insufficient`、全局质量门失败或扫描失败时，不计入连续退出次数。
- 因执行级行情源丢失而由长桥降到公共观察行情时，视为不可评估，不计入连续退出次数。
- 任意两次状态推进扫描至少间隔 5 分钟；该规则同时适用于手动和计划扫描。
- 手动刷新发现新候选时同样发送提醒。
- 14:00 计划任务发送一次每日回执，包含候选数、覆盖率和异常数。
- 运行异常按错误指纹 60 分钟去重；恢复后发送一次恢复通知。

Server酱采用 `at-least-once` 投递：本地 outbox 和确定性事件 ID 防止重复建事件，但若请求已送达而响应丢失，重试可能产生极少量重复。消息正文显示短事件 ID，便于识别重复；不采用可能静默漏报的发送前即标记成功策略。

## 6. 架构与数据流

唯一主流程：

```text
官方基金目录
  -> Longbridge 批量行情
  -> 公共源降级核对
  -> 净值/估值/申赎/费率补全
  -> 纯函数机会判断
  -> SQLite 原子提交
  -> Server酱事件
  -> 本地网页读取最后一个 completed run
```

模块边界：

- `models`：统一领域模型和快照类型。
- `providers`：基金目录、长桥行情、公共行情、净值、申赎规则和估值信号适配器。
- `domain`：无网络、无数据库副作用的估值、费率、容量和机会纯函数。
- `services`：`ScanService` 负责一次扫描的阶段编排、质量门和单实例锁。
- `repositories`：SQLite 事务、查询和状态持久化。
- `notifications`：Server酱消息构建、去重和发送。
- `api/ui`：FastAPI、Jinja 和轻量 JavaScript 本地看板。
- `tools`：计划任务与诊断命令行入口，复用 `ScanService`。

当前仓库可选择性复用：

- Eastmoney 状态解析思路，但其结果只能用于观察，且需补来源时间与失败状态。
- Server酱消息构建与发送适配层。
- 现有 CLI/JSON 输出方式。
- `VALUATION_ENGINE.md` 中按基金类型输出置信度和误差垫的原则。

不得原样复用：

- Palmmicro 作为全量目录或主数据源。
- 现有单体 `run_check.py` 的扫描编排。
- 现有 `determine_level()` 可执行判断。
- 折价路径使用申购限额的旧逻辑。
- 把源特定 DTO 直接作为统一领域模型。

## 7. 本地接口与主要类型

主要领域类型：

- `Instrument`：官方身份、交易所、产品类别、执行范围。
- `QuoteSnapshot`：价格、盘口、交易状态、源时间、抓取时间、来源。
- `FundRuleSnapshot`：申赎开关、渠道、限额、费率、证据和有效期。
- `SettlementRule`：确认周期、份额可用/可卖/可赎回日期规则和持有期计日口径。
- `ValuationSnapshot`：估算净值、模型、输入、误差垫、置信度和净值日期。
- `Opportunity`：方向、状态、毛边际、净边际、容量、约束和原因码。
- `ScanRun`：运行阶段、覆盖统计、质量门、错误和完成时间。
- `ManualVerification`：人工核验字段、来源、核验时间和有效期。
- `AlertEpisode`：进入、退出计数、重新武装和通知记录。
- `NotificationOutbox`：确定性事件 ID、发送状态、尝试次数和最后错误。

本地 API：

- `GET /`：看板。
- `GET /api/scans/latest`：最后一个完整扫描。
- `POST /api/scans`：手动触发扫描并返回 `run_id`；已有扫描运行时返回 `409`。
- `GET /api/scans/{run_id}`：扫描状态和结果。
- `GET /api/coverage`：全量覆盖与差集。
- `GET /api/source-health`：数据源健康和数据年龄。
- `GET /api/settings`、`PUT /api/settings`：非秘密运行参数。
- `POST /api/manual-verifications`：保存官方或人工核验记录。

API 和页面不得返回密钥。长桥凭据与 Server酱 SendKey 使用 Windows 用户级环境变量，日志只记录变量是否存在，不记录值。

## 8. SQLite 与一致性

SQLite 至少保存：

- 官方基金目录及身份历史。
- 扫描批次和阶段状态。
- 行情、规则、估值快照。
- 机会结果。
- 来源健康与覆盖差集。
- 人工核验。
- 通知事件和去重状态。

规则：

- 每次扫描有唯一 `run_id`。
- 计划扫描使用确定性 `trigger_id = scheduled:交易日`；同一交易日重复启动返回已有运行或结果，不创建第二次计划扫描。
- 中间结果写入当前运行，但看板只读取 `completed` 批次。
- 完成时用单个事务提交机会、覆盖统计和通知 outbox。
- 每条通知使用确定性 `event_id`，并有数据库唯一约束：机会进入事件按 episode，日报按交易日，异常按错误指纹和冷却窗口。
- 通知在事务提交后发送；进程中断或任务重试只重试同一 outbox 项，不重新生成消息。
- 首版不自动删除历史扫描；提供只读存储统计，避免未经确认清理数据。

## 9. Windows 运行方式

安装脚本创建固定虚拟环境和两个任务计划：

1. 用户登录时启动 FastAPI 本地网页，仅绑定 `127.0.0.1`。
2. 周一至周五 14:00 调用计划扫描入口；入口再按沪深交易所交易日历判断，非交易日只记录跳过，不发送机会回执。

运行规则：

- 启用单实例锁，避免计划任务和网页刷新并发。
- 14:00 计划入口若遇到活动扫描，不丢弃任务：等待当前扫描释放锁后执行确定性计划触发，最晚不得超过 14:30。
- 若活动扫描本身已使用同一 `scheduled:交易日` 触发 ID，则计划入口直接复用其状态。
- 任务允许唤醒电脑。
- 错过 14:00 后只允许在 14:30 前补跑；更晚时记录 `missed`，不使用收盘数据伪装 14:00 机会。
- 进程失败后由任务计划程序按 1 分钟间隔重启，最多 3 次。
- 日志滚动保存，网页显示最近成功扫描、最近失败、下次任务和源健康。
- GitHub Actions 不再作为主调度；现有工作流可保留但默认禁用机会推送，避免双重通知。

## 10. 失败与降级

全局质量门：

- 官方目录 100% 有分类结果。
- `display_quote_coverage` 不低于 95%；该指标包含有效长桥行情和通过双源一致性检查的公共观察行情。
- `trusted_execution_quote_coverage` 单独统计，仅包含可支持执行评估的长桥或其他已核准行情。
- 相比最近成功扫描，`trusted_execution_quote_coverage` 下降不超过 5 个百分点；初次运行只建立基线，不启用执行提醒。

未通过时：

- 运行记录为 `failed` 或 `degraded`。
- 不生成新的 `executable_candidate` 通知。
- 不推进连续退出计数。
- 保留上次成功看板，并显示本次失败横幅。
- 14:00 任务发送异常通知，不把失败解释为“无机会”。

当日官方目录同步失败时，可以用最近成功目录维持看板浏览，但本轮不得通过全局质量门，也不得发送新的机会提醒。系统不得把旧目录标为当日已核验。

单基金缺失时：

- 只降级该基金。
- 保存具体缺失字段、来源错误和时间。
- 不允许用 `0`、空字符串或旧值伪装有效输入。

## 11. 测试与验收

### 11.1 自动测试

- 两个方向的毛/净边际、费率档位、误差垫和风险垫。
- 溢价容量、折价盘口累计、金额/份额取整和约束原因。
- 缺字段、旧数据、停牌、限流、空响应和源冲突。
- 官方目录唯一性、新增、退市、更名、重复份额和覆盖差集。
- 扫描原子提交、单实例锁和失败后保留最后成功结果。
- 首次通知、持续去重、3 次退出、5 分钟手动扫描间隔和异常去重。
- FastAPI 主要接口和本机绑定。
- 模拟长桥与 Server酱的端到端扫描。

### 11.2 五个交易日影子验证

初装默认：

- `shadow_mode = true`
- `alerts_enabled = false`
- QDII 可执行白名单为空

影子模式仍发送标有“影子验证”的每日成功或失败回执，但不发送可执行机会措辞。

连续 5 个交易日验证：

- 官方目录分类覆盖每天为 100%。
- 每次合格扫描 `display_quote_coverage` 不低于 95%，并单独核对 `trusted_execution_quote_coverage`。
- 系统结果与用户 14:00 人工查看逐只核对。
- 没有把公共聚合状态、公共降级行情或未核验 QDII 标成可执行。
- 每个毛边际、净边际、容量及原因均可从保存输入复算。
- Server酱在正常响应链路中没有重复机会消息，且每日有成功或失败回执；对响应丢失故障只验证事件 ID 可识别和 outbox 可重试，不宣称外部 exactly-once。

出现以下任一情况，修复后重新开始连续 5 日：

- 错误的 `executable_candidate`。
- 官方目录漏项或错误分类。
- 关键公式无法复算。
- 通知状态丢失或重复。
- 读取半成品扫描。

达标后仍不自动启用。用户在设置页手动关闭影子模式并启用提醒。

## 12. 实施停止线

在以下基础能力通过测试前，不实现正式可执行提醒：

- 官方目录全量入库与覆盖差集。
- 长桥批量行情覆盖探测。
- 数据源时间戳与质量门。
- SQLite 完整扫描事务。
- 本地看板读取最后完成批次。

若长桥对用户重点 LOF 无有效行情，或折价候选无法获得可用卖方盘口，应停止扩展 UI，先重新评估行情提供方；不得以公共单源或旧数据绕过。

## 13. 依据

- [项目仓库](https://github.com/hkt321/arbitrage-alert)
- [上交所基金目录](https://www.sse.com.cn/assortment/fund/)
- [深交所基金目录](https://www.szse.cn/market/fund/list/stockFundList/index.html)
- [上交所 LOF 业务规则](https://www.sse.com.cn/lawandrules/sselawsrules2025/fund/trading/c/c_20250519_10779392.shtml)
- [Longbridge OpenAPI](https://open.longbridge.com/zh-CN/docs)
- [Longbridge 实时报价接口](https://open.longbridge.com/zh-CN/docs/quote/pull/quote)
- [证监会公开募集证券投资基金销售费用管理规定](https://www.csrc.gov.cn/csrc/c101954/c7606091/content.shtml)
