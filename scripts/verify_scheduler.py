#!/usr/bin/env python3
"""Verify VolatilityHunter Windows Task Scheduler configuration."""

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TASK_NAME = "VolatilityHunter_Daily_Live"
EXPECTED_COMMAND_FRAGMENT = r"scripts\DAILY_ROUTINE\run_trading.bat"
EXPECTED_WORKDIR = str(ROOT)


def run_ps(script: str) -> tuple[int, str, str]:
    completed = subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=60,
    )
    return completed.returncode, completed.stdout.strip(), completed.stderr.strip()


def main() -> int:
    ps = rf"""
$task = Get-ScheduledTask -TaskName '{TASK_NAME}' -TaskPath '\' -ErrorAction Stop
$info = Get-ScheduledTaskInfo -TaskName '{TASK_NAME}' -TaskPath '\'
$trigger = $task.Triggers[0]
$action = $task.Actions[0]
[PSCustomObject]@{{
    TaskName = $task.TaskName
    State = [string]$task.State
    LastRunTime = [string]$info.LastRunTime
    LastTaskResult = [int]$info.LastTaskResult
    NextRunTime = [string]$info.NextRunTime
    TriggerClass = $trigger.CimClass.CimClassName
    DaysOfWeek = [string]$trigger.DaysOfWeek
    At = [string]$trigger.StartBoundary
    Execute = [string]$action.Execute
    Arguments = [string]$action.Arguments
    WorkingDirectory = [string]$action.WorkingDirectory
    WakeToRun = [bool]$task.Settings.WakeToRun
    StartWhenAvailable = [bool]$task.Settings.StartWhenAvailable
    RestartCount = [int]$task.Settings.RestartCount
    RestartInterval = [string]$task.Settings.RestartInterval
    RunLevel = [string]$task.Principal.RunLevel
    LogonType = [string]$task.Principal.LogonType
    UserId = [string]$task.Principal.UserId
}} | ConvertTo-Json -Depth 4
"""
    code, out, err = run_ps(ps)
    if code != 0:
        print(f"[FAIL] Could not query scheduled task: {err or out}")
        return 1

    data = json.loads(out)
    expected_days = {"Monday", "Tuesday", "Wednesday", "Thursday", "Friday"}
    raw_days = str(data.get("DaysOfWeek", ""))
    if raw_days.isdigit():
        mask = int(raw_days)
        day_bits = {
            1: "Sunday",
            2: "Monday",
            4: "Tuesday",
            8: "Wednesday",
            16: "Thursday",
            32: "Friday",
            64: "Saturday",
        }
        actual_days = {name for bit, name in day_bits.items() if mask & bit}
    else:
        actual_days = {part.strip() for part in raw_days.split(",") if part.strip()}

    checks = [
        ("Task is Ready", data.get("State") == "Ready"),
        ("Weekly trigger", data.get("TriggerClass") == "MSFT_TaskWeeklyTrigger"),
        ("Monday-Friday only", actual_days == expected_days),
        ("Command uses cmd.exe", str(data.get("Execute", "")).lower() == "cmd.exe"),
        ("Runs production batch", EXPECTED_COMMAND_FRAGMENT.lower() in str(data.get("Arguments", "")).lower()),
        ("Working directory correct", str(data.get("WorkingDirectory", "")).lower() == EXPECTED_WORKDIR.lower()),
        ("WakeToRun enabled", data.get("WakeToRun") is True),
        ("StartWhenAvailable enabled", data.get("StartWhenAvailable") is True),
        ("RestartCount at least 3", int(data.get("RestartCount", 0)) >= 3),
        ("Highest privileges", data.get("RunLevel") == "Highest"),
        ("Interactive logon for Ghost-Typist", data.get("LogonType") == "Interactive"),
    ]

    print("=== VolatilityHunter Scheduler Verification ===")
    print(json.dumps(data, indent=2))
    failed = False
    for name, ok in checks:
        if ok:
            print(f"[OK] {name}")
        else:
            failed = True
            print(f"[FAIL] {name}")

    if failed:
        print("[FAIL] Scheduler configuration is not production-ready")
        return 1
    print("[OK] Scheduler configuration is production-ready")
    return 0


if __name__ == "__main__":
    sys.exit(main())
