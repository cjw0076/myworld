from __future__ import annotations

from typing import Any


NON_BLOCKING_MONITOR_SEVERITIES = {"info"}


def monitor_blocks_goal(monitor: dict[str, Any]) -> bool:
    health = monitor.get("health")
    if health in {None, "clear"}:
        return False
    if health == "watch" and monitor_has_only_non_blocking_findings(monitor):
        return False
    return True


def monitor_has_only_non_blocking_findings(monitor: dict[str, Any]) -> bool:
    findings = monitor.get("findings") or []
    if not isinstance(findings, list) or not findings:
        return False
    for finding in findings:
        if not isinstance(finding, dict):
            return False
        if finding.get("severity") not in NON_BLOCKING_MONITOR_SEVERITIES:
            return False
    return True
