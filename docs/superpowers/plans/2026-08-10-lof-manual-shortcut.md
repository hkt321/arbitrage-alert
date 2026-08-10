# “LOF提醒” Manual Shortcut Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 Windows 桌面提供名为“LOF提醒”的快捷方式，双击后可在任意时间提交一次前 15 只 LOF 的 GitHub Actions 更新请求。

**Architecture:** 现有 `tools/trigger_daily_check.py` 继续拥有唯一的 `gh workflow run` 命令，并增加显式 `--force` 手动入口。项目根目录的批处理文件只负责调用该入口和短暂显示结果；桌面 `.lnk` 只指向该批处理文件，不保存凭据或业务逻辑。

**Tech Stack:** Python 3.9+、标准库 `argparse`/`unittest`、Windows CMD、Windows Script Host、GitHub CLI。

## Global Constraints

- 桌面快捷方式名称必须是“LOF提醒”。
- 手动模式允许在任意时间触发；自动任务仍只在工作日 13:00–14:50 内触发。
- 每次只提交一次 `daily-check.yml`，参数固定为 `top=15`、分支固定为 `master`。
- 不新增依赖，不保存或复制 GitHub 凭据及 `SCT_SENDKEY`。
- 成功文案必须表达“请求已提交”，不能声称远端采集或微信推送已经完成。
- 不改变 Windows 自动任务 `ArbitrageAlert-LOF-Weekdays` 的配置。

## File Structure

- Modify: `tools/trigger_daily_check.py` — 保留自动时间门控，并提供 `--force` 手动入口。
- Modify: `tests/test_trigger_daily_check.py` — 验证强制模式和自动模式边界。
- Create: `run_lof_alert.cmd` — Windows 双击入口和五秒结果提示。
- Create: `tests/test_manual_shortcut.py` — 静态验证批处理入口不复制凭据或采集逻辑。
- Modify: `README.md` — 记录自动任务与手动快捷方式的区别。
- External artifact: `%USERPROFILE%\Desktop\LOF提醒.lnk` — 指向版本控制内的批处理文件。

---

### Task 1: Add an explicit manual dispatch mode

**Files:**
- Modify: `tools/trigger_daily_check.py`
- Modify: `tests/test_trigger_daily_check.py`

**Interfaces:**
- Consumes: 现有 `trigger_daily_check(now, find_executable, run_command) -> int`。
- Produces: `trigger_daily_check(force: bool = False, ...) -> int`；命令行参数 `--force`。

- [ ] **Step 1: Write the failing force-mode test**

在 `tests/test_trigger_daily_check.py` 增加周末强制触发测试：

```python
def test_force_mode_triggers_once_outside_automatic_window(self):
    calls = []

    exit_code = trigger_daily_check(
        now=datetime(2026, 8, 9, 18, 0),
        force=True,
        find_executable=lambda _: r"C:\Program Files\GitHub CLI\gh.exe",
        run_command=lambda command: calls.append(command)
        or SimpleNamespace(returncode=0),
    )

    self.assertEqual(exit_code, 0)
    self.assertEqual(len(calls), 1)
    self.assertEqual(calls[0][1:], WORKFLOW_COMMAND)
```

同时从 `tools.trigger_daily_check` 导入 `WORKFLOW_COMMAND`，避免测试复制整条命令。

- [ ] **Step 2: Run the targeted test and confirm RED**

Run: `python -m unittest tests.test_trigger_daily_check.TriggerDailyCheckTests.test_force_mode_triggers_once_outside_automatic_window -v`

Expected: FAIL，因为 `trigger_daily_check()` 尚不接受 `force`。

- [ ] **Step 3: Implement the smallest force flag and CLI parser**

在 `tools/trigger_daily_check.py` 中加入：

```python
import argparse

def trigger_daily_check(
    now: Optional[datetime] = None,
    force: bool = False,
    find_executable: Callable[[str], Optional[str]] = shutil.which,
    run_command: Callable[[list[str]], Any] = subprocess.run,
) -> int:
    now = now or datetime.now()
    if not force and (
        now.weekday() >= 5 or not (WINDOW_START <= now.time() <= WINDOW_END)
    ):
        print(f"跳过：当前时间 {now:%Y-%m-%d %H:%M} 不在工作日 13:00-14:50")
        return 0
```

将入口替换为：

```python
def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    return trigger_daily_check(force=args.force)

if __name__ == "__main__":
    sys.exit(main())
```

强制模式成功时打印 `请求已提交，微信稍后更新。`；自动模式可以继续打印现有触发信息。

- [ ] **Step 4: Run trigger tests and confirm GREEN**

Run: `python -m unittest tests.test_trigger_daily_check -v`

Expected: 全部 PASS；原有窗口外跳过测试仍通过，新增强制测试只调用一次命令。

- [ ] **Step 5: Commit the manual trigger behavior**

```powershell
git add tools/trigger_daily_check.py tests/test_trigger_daily_check.py
git commit -m "Add manual LOF workflow trigger"
```

---

### Task 2: Add the Windows double-click entry

**Files:**
- Create: `run_lof_alert.cmd`
- Create: `tests/test_manual_shortcut.py`
- Modify: `README.md`

**Interfaces:**
- Consumes: `D:\anaconda\python.exe tools\trigger_daily_check.py --force`。
- Produces: 一个可由桌面 `.lnk` 调用的批处理入口，返回 Python 原始退出码。

- [ ] **Step 1: Write the failing launcher policy test**

创建 `tests/test_manual_shortcut.py`：

```python
import unittest
from pathlib import Path

class ManualShortcutTests(unittest.TestCase):
    def test_launcher_reuses_force_trigger_without_secrets(self):
        launcher = (Path(__file__).parents[1] / "run_lof_alert.cmd").read_text(
            encoding="utf-8"
        )
        self.assertIn(r'D:\anaconda\python.exe', launcher)
        self.assertIn(r'tools\trigger_daily_check.py', launcher)
        self.assertIn("--force", launcher)
        self.assertIn("timeout /t 5", launcher.lower())
        self.assertNotIn("SCT_SENDKEY", launcher)
        self.assertNotIn("run_check.py", launcher)
```

- [ ] **Step 2: Run the launcher test and confirm RED**

Run: `python -m unittest tests.test_manual_shortcut -v`

Expected: ERROR，`run_lof_alert.cmd` 尚不存在。

- [ ] **Step 3: Create the minimal launcher**

创建 UTF-8 的 `run_lof_alert.cmd`：

```bat
@echo off
chcp 65001 >nul
"D:\anaconda\python.exe" "%~dp0tools\trigger_daily_check.py" --force
set "LOF_EXIT=%ERRORLEVEL%"
echo.
if not "%LOF_EXIT%"=="0" echo LOF提醒提交失败，请检查上方错误。
timeout /t 5 /nobreak >nul
exit /b %LOF_EXIT%
```

Python 成功时已经输出 `请求已提交，微信稍后更新。`，批处理不重复宣称成功。

- [ ] **Step 4: Document the manual shortcut**

在 README 的 GitHub Actions 章节补充：桌面“LOF提醒”可在任意时间手动提交一次更新；它与自动任务共用远端工作流，成功提示仅代表请求已提交。

- [ ] **Step 5: Run launcher and full tests**

Run: `python -m unittest tests.test_manual_shortcut tests.test_trigger_daily_check -v`

Expected: PASS。

Run: `python -m unittest discover -s tests -v`

Expected: 全部 PASS。

- [ ] **Step 6: Commit the launcher**

```powershell
git add run_lof_alert.cmd tests/test_manual_shortcut.py README.md
git commit -m "Add LOF desktop launcher"
```

---

### Task 3: Publish, install, and perform one real acceptance run

**Files:**
- Create externally: `%USERPROFILE%\Desktop\LOF提醒.lnk`
- No repository code changes expected.

**Interfaces:**
- Consumes: absolute target `D:\Project\arbitrage-alert\run_lof_alert.cmd`。
- Produces: desktop shortcut `LOF提醒.lnk`。

- [ ] **Step 1: Verify before publishing**

Run:

```powershell
python -m unittest discover -s tests -v
python -m compileall -q backend tools tests
git diff --check
git status --short
```

Expected: tests PASS、compileall exit 0、diff check exit 0、工作区干净。

- [ ] **Step 2: Push and merge the implementation branch**

Push `codex/manual-shortcut`，创建 PR 到 `master`，确认可合并后合并。不要改变或重新注册 `ArbitrageAlert-LOF-Weekdays`。

- [ ] **Step 3: Create the desktop shortcut**

使用 Windows Script Host：

```powershell
$desktopPath = [Environment]::GetFolderPath('Desktop')
$shortcutPath = Join-Path $desktopPath 'LOF提醒.lnk'
$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = 'D:\Project\arbitrage-alert\run_lof_alert.cmd'
$shortcut.WorkingDirectory = 'D:\Project\arbitrage-alert'
$shortcut.IconLocation = "$env:SystemRoot\System32\shell32.dll,167"
$shortcut.Description = '立即提交一次前15只LOF关注提醒'
$shortcut.Save()
```

- [ ] **Step 4: Inspect the installed shortcut without running it**

重新打开 `.lnk` 并核对名称、目标、工作目录、图标和说明；确认自动任务的下一运行时间与设置未变化。

- [ ] **Step 5: Execute exactly one real acceptance run**

记录执行前最新的 `daily-check.yml` run id，然后启动桌面快捷方式一次。轮询 GitHub Actions，确认只新增一个 `workflow_dispatch` run；等待其完成并确认结论为 `success`。不要在验收期间再次点击或手动 dispatch。

- [ ] **Step 6: Report the exact state**

报告快捷方式配置 `PASS`、GitHub run URL/结论、是否收到一次微信提醒。若 GitHub 已成功但微信送达无法从代码侧确认，将微信送达标为“待用户确认”，不得把它写成 PASS。
