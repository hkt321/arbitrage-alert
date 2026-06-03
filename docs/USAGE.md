# 套利机会检查器使用说明

## 基础用法

```powershell
# 查看前 25 只高溢价/折价基金（默认）
python -X utf8 tools/run_check.py

# 查看前 N 只
python -X utf8 tools/run_check.py --top 10
python -X utf8 tools/run_check.py --top 30
```

## 过滤条件

```powershell
# 设置最低溢价阈值（默认 2.0%）
python -X utf8 tools/run_check.py --min-premium 3.0

# 设置最低申购限额（默认 100 元，低于此值不展示为可执行）
python -X utf8 tools/run_check.py --min-limit 500

# 同时设置
python -X utf8 tools/run_check.py --top 15 --min-premium 3.0 --min-limit 1000
```

## JSON 输出

```powershell
# 导出 JSON 供其他工具处理
python -X utf8 tools/run_check.py --json

# 保存到文件
python -X utf8 tools/run_check.py --json > opportunity.json
```

## 输出解读

### 机会级别

| 级别 | 图标 | 含义 |
|------|------|------|
| 可执行 | 🟢 绿色 | 溢价≥阈值 + 申购开放 + 额度足够 |
| 观察 | 🟡 黄色 | 溢价高但申购暂停/限额过低 |
| 普通 | ⚪ 灰色 | 溢价未达阈值或无数据 |

### 汇总表字段

| 字段 | 说明 |
|------|------|
| 代码 | SH=上交所 SZ=深交所 |
| 名称 | 基金名称 |
| 溢价 | 实时估值溢价/折价百分比 |
| 限购 | 单日申购限额（元） |
| 份额 | 场内总份额（万份） |
| 新增 | 当日新增份额（万份），负值为减少 |
| 结论 | 机会级别 |

### 套利方向

- **📈 溢价套利**：场内价格 > 估值，场外申购 → T+N天后场内卖出
- **📉 折价套利**：场内价格 < 估值，场内买入 → 场外赎回

## 注意事项

1. 数据从 `palmmicro.com` 抓取，有 ~0.5 秒/次的请求间隔避免被限流
2. 申购限额数据来自天天基金，盘中可能滞后
3. 折价品种目前全部标记为"观察"，因为折价套利需要确认赎回通道正常
4. QDII 基金溢价率含估值误差，实际可交易空间可能更小
5. 建议每天下午 2 点左右运行一次