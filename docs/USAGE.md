# LOF 关注提醒使用说明

## 基础用法

```powershell
python -m pip install -r requirements.txt
python tools/run_check.py
python tools/run_check.py --top 30
python tools/run_check.py --json
```

## 自定义阈值

```powershell
python tools/run_check.py --min-premium 3.0 --min-discount -3.0 --min-limit 500
```

- 溢价达到阈值时，输出会同时提示申购状态和限额情况。
- 折价达到阈值时，只参考赎回状态，不使用申购限额判断。
- 达到阈值统一标记为 `watch`，不会被描述为可执行交易。

## 数据口径

溢价率计算公式：

```text
(场内最新价 - 最新官方净值) / 最新官方净值 × 100%
```

输出同时包含 `nav_date` 和 `premium_basis=latest_official_nav`。如果某只基金有行情但没有对应净值资料，它会保留在结果中并标记为 `unknown`。

行情由标准库加载器从东方财富公开接口每页获取 20 条并校验总数；AkShare 负责获取最新官方净值和申赎状态。公开接口不承诺实时性或稳定性。接口返回空表、缺页、缺少必要字段或出现重复代码时，命令会以非零状态退出，且不会发送微信通知。

## 微信推送

```powershell
python tools/run_check.py --top 30 --push-key SCTXXXXXXXXXXXXXXXXX
```

不要把 SendKey 写进代码或提交到 Git。GitHub Actions 使用仓库 secret `SCT_SENDKEY`。
