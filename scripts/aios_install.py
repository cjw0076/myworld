#!/usr/bin/env python3
"""Reversible user-space installer for the AIOS control plane."""

from __future__ import annotations

import argparse
import json
import os
import shlex
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "aios.install.v1"
MANAGED_MARKER = "# AIOS_INSTALLER_MANAGED v=asc-0080"
ROOT_MARKER = Path("scripts") / "aios_runtime.py"
SERVICE_NAME = "aios.service"
DEFAULT_PORT = 8765
DEFAULT_WS_PORT = 8766


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def is_aios_root(path: Path) -> bool:
    return (path / ROOT_MARKER).exists() and (path / "bin" / "aios").exists()


def resolve_root(value: str) -> Path:
    root = Path(value).expanduser().resolve()
    if not is_aios_root(root):
        raise SystemExit(f"not an AIOS root: {root}")
    return root


def env_path(name: str, fallback: Path, env: dict[str, str] | None = None) -> Path:
    source = env if env is not None else os.environ
    raw = source.get(name)
    return Path(raw).expanduser().resolve() if raw else fallback.expanduser().resolve()


@dataclass(frozen=True)
class InstallPlan:
    root: Path
    home: Path
    config_home: Path
    bin_dir: Path
    launcher_path: Path
    service_path: Path
    desktop_path: Path
    enable_now: bool
    desktop: bool
    port: int
    ws_port: int


def build_plan(args: argparse.Namespace) -> InstallPlan:
    root = resolve_root(args.root)
    home = Path(args.home).expanduser().resolve() if args.home else env_path("HOME", Path.home())
    config_home = (
        Path(args.xdg_config_home).expanduser().resolve()
        if args.xdg_config_home
        else env_path("XDG_CONFIG_HOME", home / ".config")
    )
    bin_dir = Path(args.bin_dir).expanduser().resolve() if args.bin_dir else home / ".local" / "bin"
    return InstallPlan(
        root=root,
        home=home,
        config_home=config_home,
        bin_dir=bin_dir,
        launcher_path=bin_dir / "aios",
        service_path=config_home / "systemd" / "user" / SERVICE_NAME,
        desktop_path=config_home / "autostart" / "aios-control.desktop",
        enable_now=bool(getattr(args, "enable_now", False)),
        desktop=not bool(getattr(args, "no_desktop", False)),
        port=int(getattr(args, "port", DEFAULT_PORT)),
        ws_port=int(getattr(args, "ws_port", DEFAULT_WS_PORT)),
    )


def managed_header(root: Path) -> str:
    return f"{MANAGED_MARKER}\n# AIOS_ROOT={root.as_posix()}\n"


def is_managed(path: Path) -> bool:
    if not path.exists() or not path.is_file():
        return False
    try:
        head = path.read_text(encoding="utf-8", errors="replace")[:500]
    except OSError:
        return False
    return MANAGED_MARKER in head


def file_state(path: Path) -> dict[str, Any]:
    return {
        "path": path.as_posix(),
        "exists": path.exists(),
        "managed_by_aios_install": is_managed(path),
    }


def render_launcher(plan: InstallPlan) -> str:
    root_q = shlex.quote(plan.root.as_posix())
    bin_q = shlex.quote((plan.root / "bin" / "aios").as_posix())
    return f"""#!/usr/bin/env bash
set -euo pipefail
{managed_header(plan.root).rstrip()}

export AIOS_HOME={root_q}
exec {bin_q} --root "$AIOS_HOME" "$@"
"""


def render_service(plan: InstallPlan) -> str:
    root = plan.root.as_posix()
    root_q = shlex.quote(root)
    py_q = shlex.quote(sys.executable)
    local_log = shlex.quote((plan.root / ".aios" / "logs" / "aios_local_app.up.log").as_posix())
    exec_start = (
        f"cd {root_q} && "
        f"{py_q} scripts/aios_local_app.py --root {root_q} up --port {plan.port} --ws-port {plan.ws_port} --json >{local_log} 2>&1; "
        f"exec {py_q} scripts/aios_round_controller.py run --root {root_q} --interval 30 --execute-children"
    )
    exec_stop = (
        f"cd {root_q} && "
        f"{py_q} scripts/aios_round_controller.py stop --root {root_q} >/dev/null 2>&1 || true; "
        f"{py_q} scripts/aios_local_app.py --root {root_q} stop --json >/dev/null 2>&1 || true"
    )
    return f"""{managed_header(plan.root)}[Unit]
Description=AIOS Control Plane
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory={root}
Environment=AIOS_HOME={root}
ExecStart=/usr/bin/env bash -lc {shlex.quote(exec_start)}
ExecStop=/usr/bin/env bash -lc {shlex.quote(exec_stop)}
Restart=always
RestartSec=10

[Install]
WantedBy=default.target
"""


def render_desktop(plan: InstallPlan) -> str:
    url = f"http://127.0.0.1:{plan.port}/"
    root_q = shlex.quote(plan.root.as_posix())
    launcher_q = shlex.quote(plan.launcher_path.as_posix())
    command = f"AIOS_HOME={root_q} {launcher_q} status --json >/dev/null 2>&1 || true; xdg-open {shlex.quote(url)} >/dev/null 2>&1 || true"
    return f"""{managed_header(plan.root)}[Desktop Entry]
Type=Application
Name=AIOS Control Center
Comment=Open the local AIOS control application
Exec=/usr/bin/env bash -lc {shlex.quote(command)}
Terminal=false
X-GNOME-Autostart-enabled=true
"""


def write_managed(path: Path, body: str, *, force: bool = False, mode: int | None = None) -> dict[str, Any]:
    if path.exists() and not is_managed(path) and not force:
        return {
            "path": path.as_posix(),
            "status": "blocked",
            "stop_condition": "unmanaged_target_exists",
        }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    if mode is not None:
        path.chmod(mode)
    return {"path": path.as_posix(), "status": "written"}


def remove_managed(path: Path, *, force: bool = False) -> dict[str, Any]:
    if not path.exists():
        return {"path": path.as_posix(), "status": "missing"}
    if not is_managed(path) and not force:
        return {
            "path": path.as_posix(),
            "status": "skipped",
            "stop_condition": "unmanaged_target_exists",
        }
    path.unlink()
    return {"path": path.as_posix(), "status": "removed"}


def systemctl_available() -> bool:
    return bool(shutil.which("systemctl")) and os.environ.get("AIOS_INSTALL_SKIP_SYSTEMCTL") != "1"


def run_systemctl(args: list[str]) -> dict[str, Any]:
    if not systemctl_available():
        return {"command": ["systemctl", "--user", *args], "status": "skipped", "reason": "systemctl_unavailable"}
    completed = subprocess.run(["systemctl", "--user", *args], text=True, capture_output=True, check=False, timeout=20)
    return {
        "command": ["systemctl", "--user", *args],
        "status": "passed" if completed.returncode == 0 else "failed",
        "returncode": completed.returncode,
        "stdout": completed.stdout.strip(),
        "stderr": completed.stderr.strip()[-1000:],
    }


def service_state() -> dict[str, Any]:
    if not systemctl_available():
        return {"available": False, "reason": "systemctl_unavailable"}
    enabled = run_systemctl(["is-enabled", SERVICE_NAME])
    active = run_systemctl(["is-active", SERVICE_NAME])
    return {
        "available": True,
        "enabled": enabled.get("stdout") or "unknown",
        "active": active.get("stdout") or "unknown",
        "enabled_check": enabled,
        "active_check": active,
    }


def local_app_status(root: Path) -> dict[str, Any]:
    command = [sys.executable, (root / "scripts" / "aios_local_app.py").as_posix(), "--root", root.as_posix(), "status", "--json"]
    try:
        completed = subprocess.run(command, text=True, capture_output=True, check=False, timeout=20)
    except subprocess.TimeoutExpired:
        return {"status": "timeout", "command": command}
    parsed: Any = None
    if completed.stdout.strip():
        try:
            parsed = json.loads(completed.stdout)
        except json.JSONDecodeError:
            parsed = None
    return {
        "returncode": completed.returncode,
        "parsed": parsed,
        "stderr_tail": completed.stderr[-500:],
    }


def plan_payload(plan: InstallPlan) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": now_iso(),
        "status": "planned",
        "root": plan.root.as_posix(),
        "home": plan.home.as_posix(),
        "targets": {
            "launcher": file_state(plan.launcher_path),
            "service": file_state(plan.service_path),
            "desktop": file_state(plan.desktop_path),
        },
        "would_write": [
            plan.launcher_path.as_posix(),
            plan.service_path.as_posix(),
            *([plan.desktop_path.as_posix()] if plan.desktop else []),
        ],
        "enable_now": plan.enable_now,
        "desktop_entry": plan.desktop,
        "port": plan.port,
        "ws_port": plan.ws_port,
        "service_model": {
            "type": "systemd_user_service",
            "keeps_alive": "scripts/aios_round_controller.py run --execute-children",
            "preflight": "scripts/aios_local_app.py up --json",
            "restart": "always",
        },
    }


def command_plan(args: argparse.Namespace) -> int:
    print(json.dumps(plan_payload(build_plan(args)), ensure_ascii=False, indent=2, sort_keys=True))
    return 0


def command_status(args: argparse.Namespace) -> int:
    plan = build_plan(args)
    payload = plan_payload(plan)
    payload["status"] = "installed" if plan.launcher_path.exists() and plan.service_path.exists() else "partial_or_missing"
    payload["systemd_user_service"] = service_state()
    payload["local_app"] = local_app_status(plan.root)
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


def command_install(args: argparse.Namespace) -> int:
    plan = build_plan(args)
    writes = [
        write_managed(plan.launcher_path, render_launcher(plan), force=args.force, mode=0o755),
        write_managed(plan.service_path, render_service(plan), force=args.force),
    ]
    if plan.desktop:
        writes.append(write_managed(plan.desktop_path, render_desktop(plan), force=args.force))
    blocked = [item for item in writes if item.get("status") == "blocked"]
    systemd: list[dict[str, Any]] = []
    if not blocked and plan.enable_now:
        systemd.append(run_systemctl(["daemon-reload"]))
        systemd.append(run_systemctl(["enable", "--now", SERVICE_NAME]))
    payload = {
        **plan_payload(plan),
        "status": "blocked" if blocked else "installed",
        "writes": writes,
        "systemd": systemd,
        "next": (
            "resolve_unmanaged_targets_or_use_force"
            if blocked
            else "systemctl --user enable --now aios.service" if not plan.enable_now else "aios status --json"
        ),
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    return 1 if blocked else 0


def command_uninstall(args: argparse.Namespace) -> int:
    plan = build_plan(args)
    systemd: list[dict[str, Any]] = []
    if args.disable_now:
        systemd.append(run_systemctl(["disable", "--now", SERVICE_NAME]))
    removals = [
        remove_managed(plan.launcher_path, force=args.force),
        remove_managed(plan.service_path, force=args.force),
        remove_managed(plan.desktop_path, force=args.force),
    ]
    payload = {
        **plan_payload(plan),
        "status": "uninstalled",
        "systemd": systemd,
        "removals": removals,
        "state_preserved": [".aios/", "child repositories", "provider credentials"],
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


def add_common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--root", default=argparse.SUPPRESS, help="AIOS control-plane root")
    parser.add_argument("--home", help="home directory override for tests or sandboxed installs")
    parser.add_argument("--xdg-config-home", help="XDG config directory override")
    parser.add_argument("--bin-dir", help="launcher directory override; defaults to ~/.local/bin")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="control app HTTP port")
    parser.add_argument("--ws-port", type=int, default=DEFAULT_WS_PORT, help="control app WebSocket port")
    parser.add_argument("--no-desktop", action="store_true", help="do not create the GUI autostart desktop entry")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".", help="AIOS control-plane root")
    sub = parser.add_subparsers(dest="cmd", required=True)

    plan = sub.add_parser("plan", help="show exact user-space files that would be written")
    add_common(plan)
    plan.add_argument("--json", action="store_true")
    plan.set_defaults(func=command_plan)

    install = sub.add_parser("install", help="write reversible user-space launcher/service files")
    add_common(install)
    install.add_argument("--json", action="store_true")
    install.add_argument("--force", action="store_true", help="overwrite unmanaged target files")
    install.add_argument("--enable-now", action="store_true", help="run systemctl --user enable --now aios.service after writing files")
    install.set_defaults(func=command_install)

    status = sub.add_parser("status", help="report install targets, systemd state, and local app status")
    add_common(status)
    status.add_argument("--json", action="store_true")
    status.set_defaults(func=command_status)

    uninstall = sub.add_parser("uninstall", help="remove only files created by this installer")
    add_common(uninstall)
    uninstall.add_argument("--json", action="store_true")
    uninstall.add_argument("--force", action="store_true", help="remove targets even if the marker is missing")
    uninstall.add_argument("--disable-now", action="store_true", help="run systemctl --user disable --now aios.service before removing files")
    uninstall.set_defaults(func=command_uninstall)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
