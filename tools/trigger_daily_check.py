#!/usr/bin/env python3
"""Trigger the GitHub LOF workflow from Windows Task Scheduler."""

import shutil
import subprocess
import sys
from datetime import datetime, time
from typing import Any, Callable, Optional


WORKFLOW_COMMAND = [
    "workflow",
    "run",
    "daily-check.yml",
    "--repo",
    "hkt321/arbitrage-alert",
    "--ref",
    "master",
    "-f",
    "top=15",
]
WINDOW_START = time(13, 0)
WINDOW_END = time(14, 50)


def trigger_daily_check(
    now: Optional[datetime] = None,
    find_executable: Callable[[str], Optional[str]] = shutil.which,
    run_command: Callable[[list[str]], Any] = subprocess.run,
) -> int:
    now = now or datetime.now()
    if now.weekday() >= 5 or not (WINDOW_START <= now.time() <= WINDOW_END):
        print(f"跳过：当前时间 {now:%Y-%m-%d %H:%M} 不在工作日 13:00-14:50")
        return 0

    gh_executable = find_executable("gh")
    if not gh_executable:
        print("触发失败：找不到 gh.exe", file=sys.stderr)
        return 1

    command = [gh_executable, *WORKFLOW_COMMAND]
    result = run_command(command)
    if result.returncode != 0:
        print(f"触发失败：gh 返回 {result.returncode}", file=sys.stderr)
    else:
        print(f"已触发：{now:%Y-%m-%d %H:%M} 前15 LOF 工作流")
    return int(result.returncode)


if __name__ == "__main__":
    sys.exit(trigger_daily_check())
