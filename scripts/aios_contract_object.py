#!/usr/bin/env python3
"""ContractObject v0 — AIOS contracts as runtime objects.

Per founder directive 2026-05-20:
- Contracts are not markdown documents to accumulate.
- Contracts are *system objects* with state, scope, plan, receipts, evals,
  memory effects, and explicit delegated authority.
- AIOS head is the *delegated* (not blind root) device authority that
  executes within the bounds named in the ContractObject.

Schema is stdlib-only (dataclasses + json). No external deps. Lives in
scripts/ as the minimum-kernel candidate; existing 218 markdown ASCs are
*pattern dataset*, not runtime objects.

Reference: docs/AIOS_MINIMUM_KERNEL_AUDIT.md "Chosen path — C. Hybrid".
NOT a contract about creating contracts. Just code + schema.
"""
from __future__ import annotations

import dataclasses as dc
import hashlib
import json
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


# --- State machine -----------------------------------------------------------

STATES = (
    "proposed",     # written, not approved
    "accepted",     # operator/founder approved scope + plan
    "running",      # at least one step in progress
    "waiting_user", # user checkpoint hit, awaiting input
    "verified",     # all steps done, evals pass
    "closed",       # memory effects applied, ledger entry written
    "blocked",      # stop condition triggered; cannot advance without reframe
)

ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    "proposed":     {"accepted", "blocked"},
    "accepted":     {"running", "blocked"},
    "running":      {"waiting_user", "verified", "blocked"},
    "waiting_user": {"running", "blocked"},
    "verified":     {"closed", "blocked"},
    "closed":       set(),  # terminal
    "blocked":      {"proposed", "accepted"},  # reframe re-enters
}


# --- Scope dataclasses -------------------------------------------------------

@dataclass
class FilesystemScope:
    """Founder-delegated filesystem authority. Empty list = no permission.

    Paths are resolved relative to ContractObject.workspace_root unless
    absolute. Deny-paths take precedence over allow-paths (privacy gate).
    """
    read_paths: list[str] = field(default_factory=list)
    write_paths: list[str] = field(default_factory=list)
    delete_paths: list[str] = field(default_factory=list)
    move_paths: list[str] = field(default_factory=list)
    deny_paths: list[str] = field(default_factory=list)

    def allows_read(self, path: str) -> bool:
        return self._allowed(path, self.read_paths) and not self._matches(path, self.deny_paths)

    def allows_write(self, path: str) -> bool:
        return self._allowed(path, self.write_paths) and not self._matches(path, self.deny_paths)

    def allows_delete(self, path: str) -> bool:
        return self._allowed(path, self.delete_paths) and not self._matches(path, self.deny_paths)

    def allows_move(self, path: str) -> bool:
        return self._allowed(path, self.move_paths) and not self._matches(path, self.deny_paths)

    @staticmethod
    def _allowed(path: str, allow_list: list[str]) -> bool:
        return any(FilesystemScope._matches(path, [a]) for a in allow_list)

    @staticmethod
    def _matches(path: str, patterns: list[str]) -> bool:
        for pat in patterns:
            if path == pat:
                return True
            if pat.endswith("/") and path.startswith(pat):
                return True
            if pat.endswith("**") and path.startswith(pat[:-2]):
                return True
        return False


@dataclass
class ProviderRoute:
    """One provider + how AIOS may invoke it within this contract."""
    provider: str          # 'claude' | 'codex' | 'gemini' | 'ollama_local' | ...
    auth_mode: str         # 'session' | 'api_key' | 'public' | 'none'
    role: str              # 'planner' | 'executor' | 'critic' | 'summarizer' | 'router'
    model: str | None = None
    notes: str = ""


@dataclass
class AuthorityScope:
    """Non-filesystem, non-provider scopes (cross-cutting authority)."""
    network: bool = False
    secrets_paths: list[str] = field(default_factory=list)  # explicit secret-bearing files allowed
    user_checkpoints_required: list[str] = field(default_factory=list)  # step ids requiring human
    expires_at: str | None = None  # ISO ts; None = no expiry, but operator should set


# --- Plan / execution dataclasses --------------------------------------------

@dataclass
class Step:
    id: str
    description: str
    tool: str              # 'web' | 'fs.read' | 'fs.write' | 'provider.claude' | 'local_llm' | ...
    inputs: dict[str, Any] = field(default_factory=dict)
    expects: str = ""      # description of expected outcome
    requires_checkpoint: bool = False


@dataclass
class Receipt:
    step_id: str
    timestamp: str
    success: bool
    artifacts: list[str] = field(default_factory=list)
    summary: str = ""
    error: str | None = None


@dataclass
class Eval:
    name: str
    check: str             # human-readable check; runtime hook resolves
    required: bool = True
    result: str | None = None  # 'pass' | 'fail' | None when unrun


@dataclass
class MemoryEffect:
    """What this contract proposes to *write* to memoryOS at closeout.

    Always draft-first (never auto-accept). Operator/peer reviews.
    """
    target: str            # 'memoryOS.draft' | 'ledger' | 'self_observation'
    op: str                # 'draft' | 'append' | 'link'
    content_ref: str       # path or memoryos id reference
    note: str = ""


# --- ContractObject ----------------------------------------------------------

@dataclass
class ContractObject:
    contract_id: str
    goal: str
    state: str = "proposed"
    workspace_root: str = ""

    authority_scope: AuthorityScope = field(default_factory=AuthorityScope)
    filesystem_scope: FilesystemScope = field(default_factory=FilesystemScope)
    provider_routes: list[ProviderRoute] = field(default_factory=list)

    memory_inputs: list[str] = field(default_factory=list)   # memoryos memory_ids
    capability_route: dict[str, Any] = field(default_factory=dict)
    genesis_challenge: dict[str, Any] | None = None

    steps: list[Step] = field(default_factory=list)
    actions: list[dict[str, Any]] = field(default_factory=list)  # planned-vs-actual
    receipts: list[Receipt] = field(default_factory=list)
    evals: list[Eval] = field(default_factory=list)
    user_checkpoints: list[str] = field(default_factory=list)  # step ids hit
    memory_effects: list[MemoryEffect] = field(default_factory=list)
    next_state: str | None = None

    created_at: str = field(default_factory=lambda: _now())
    updated_at: str = field(default_factory=lambda: _now())

    # ----- validation -----

    def validate(self) -> list[str]:
        errors: list[str] = []
        if self.state not in STATES:
            errors.append(f"state '{self.state}' not in {STATES}")
        if not self.goal.strip():
            errors.append("goal is empty")
        step_ids = {s.id for s in self.steps}
        for r in self.receipts:
            if r.step_id not in step_ids:
                errors.append(f"receipt references unknown step_id '{r.step_id}'")
        if self.authority_scope.network is False:
            for s in self.steps:
                if s.tool == "web" and not self._network_allowed_by_provider(s):
                    errors.append(f"step '{s.id}' uses web but authority_scope.network=False")
        return errors

    def _network_allowed_by_provider(self, step: Step) -> bool:
        # web step might still be allowed if delegated to a provider whose
        # auth_mode permits network on its own substrate; default: deny.
        return False

    # ----- transitions -----

    def can_transition(self, to: str) -> bool:
        return to in ALLOWED_TRANSITIONS.get(self.state, set())

    def transition(self, to: str, *, reason: str = "") -> None:
        if not self.can_transition(to):
            raise ValueError(
                f"transition {self.state} → {to} not allowed; allowed: {sorted(ALLOWED_TRANSITIONS.get(self.state, set()))}"
            )
        self.actions.append({
            "kind": "state_transition",
            "from": self.state,
            "to": to,
            "reason": reason,
            "at": _now(),
        })
        self.state = to
        self.updated_at = _now()

    # ----- step authority enforcement -----

    def authorize_step(self, step: Step) -> list[str]:
        """Return list of authority errors; empty = allowed."""
        errors: list[str] = []
        tool = step.tool
        inputs = step.inputs or {}
        if tool == "fs.read":
            p = inputs.get("path", "")
            if not self.filesystem_scope.allows_read(p):
                errors.append(f"step '{step.id}': fs.read on '{p}' not in scope")
        elif tool == "fs.write":
            p = inputs.get("path", "")
            if not self.filesystem_scope.allows_write(p):
                errors.append(f"step '{step.id}': fs.write on '{p}' not in scope")
        elif tool == "fs.delete":
            p = inputs.get("path", "")
            if not self.filesystem_scope.allows_delete(p):
                errors.append(f"step '{step.id}': fs.delete on '{p}' not in scope")
        elif tool == "fs.move":
            for p in (inputs.get("src", ""), inputs.get("dst", "")):
                if p and not self.filesystem_scope.allows_move(p):
                    errors.append(f"step '{step.id}': fs.move touches '{p}' not in scope")
        elif tool.startswith("provider."):
            provider = tool.split(".", 1)[1]
            if not any(r.provider == provider for r in self.provider_routes):
                errors.append(f"step '{step.id}': provider '{provider}' not in provider_routes")
        elif tool == "web" and not self.authority_scope.network:
            errors.append(f"step '{step.id}': web requested but network=False")
        return errors

    def record_receipt(self, receipt: Receipt) -> None:
        if receipt.step_id not in {s.id for s in self.steps}:
            raise ValueError(f"receipt step_id '{receipt.step_id}' not in plan")
        self.receipts.append(receipt)
        self.updated_at = _now()

    # ----- serialization -----

    def to_dict(self) -> dict[str, Any]:
        return dc.asdict(self)

    def to_json(self, *, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ContractObject":
        return cls(
            contract_id=data["contract_id"],
            goal=data["goal"],
            state=data.get("state", "proposed"),
            workspace_root=data.get("workspace_root", ""),
            authority_scope=_load_dc(AuthorityScope, data.get("authority_scope", {})),
            filesystem_scope=_load_dc(FilesystemScope, data.get("filesystem_scope", {})),
            provider_routes=[_load_dc(ProviderRoute, r) for r in data.get("provider_routes", [])],
            memory_inputs=list(data.get("memory_inputs", [])),
            capability_route=dict(data.get("capability_route", {})),
            genesis_challenge=data.get("genesis_challenge"),
            steps=[_load_dc(Step, s) for s in data.get("steps", [])],
            actions=list(data.get("actions", [])),
            receipts=[_load_dc(Receipt, r) for r in data.get("receipts", [])],
            evals=[_load_dc(Eval, e) for e in data.get("evals", [])],
            user_checkpoints=list(data.get("user_checkpoints", [])),
            memory_effects=[_load_dc(MemoryEffect, m) for m in data.get("memory_effects", [])],
            next_state=data.get("next_state"),
            created_at=data.get("created_at") or _now(),
            updated_at=data.get("updated_at") or _now(),
        )


# --- helpers -----------------------------------------------------------------

def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _load_dc(cls, data: dict[str, Any]):
    """Load a dataclass from a dict, ignoring unknown keys."""
    if not isinstance(data, dict):
        return cls()
    field_names = {f.name for f in dc.fields(cls)}
    return cls(**{k: v for k, v in data.items() if k in field_names})


def new_contract_id(prefix: str = "co") -> str:
    return f"{prefix}-" + uuid.uuid4().hex[:12]


# --- CLI ---------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    import argparse
    p = argparse.ArgumentParser(description="ContractObject v0 — validate/inspect/advance")
    sub = p.add_subparsers(dest="cmd", required=True)

    new_p = sub.add_parser("new", help="emit a skeleton ContractObject JSON")
    new_p.add_argument("--goal", required=True)
    new_p.add_argument("--id", default=None)
    new_p.add_argument("--workspace-root", default="")

    val_p = sub.add_parser("validate", help="validate an existing ContractObject JSON")
    val_p.add_argument("path", type=Path)

    show_p = sub.add_parser("show", help="pretty-print state + receipts of a ContractObject")
    show_p.add_argument("path", type=Path)

    trans_p = sub.add_parser("transition", help="advance state if allowed")
    trans_p.add_argument("path", type=Path)
    trans_p.add_argument("--to", required=True)
    trans_p.add_argument("--reason", default="")
    trans_p.add_argument("--write", action="store_true",
                         help="write back to file (default prints to stdout)")

    args = p.parse_args(argv)

    if args.cmd == "new":
        co = ContractObject(
            contract_id=args.id or new_contract_id(),
            goal=args.goal,
            workspace_root=args.workspace_root,
        )
        print(co.to_json())
        return 0

    if args.cmd == "validate":
        data = json.loads(args.path.read_text(encoding="utf-8"))
        co = ContractObject.from_dict(data)
        errors = co.validate()
        if errors:
            for e in errors:
                print(f"ERROR: {e}")
            return 1
        print("ok")
        return 0

    if args.cmd == "show":
        data = json.loads(args.path.read_text(encoding="utf-8"))
        co = ContractObject.from_dict(data)
        print(f"{co.contract_id}  state={co.state}  goal={co.goal[:80]}")
        print(f"  filesystem: read={len(co.filesystem_scope.read_paths)} "
              f"write={len(co.filesystem_scope.write_paths)} "
              f"deny={len(co.filesystem_scope.deny_paths)}")
        print(f"  providers: {[r.provider for r in co.provider_routes]}")
        print(f"  steps: {len(co.steps)}, receipts: {len(co.receipts)}, evals: {len(co.evals)}")
        return 0

    if args.cmd == "transition":
        data = json.loads(args.path.read_text(encoding="utf-8"))
        co = ContractObject.from_dict(data)
        co.transition(args.to, reason=args.reason)
        if args.write:
            args.path.write_text(co.to_json(), encoding="utf-8")
            print(f"wrote {args.path}  state={co.state}")
        else:
            print(co.to_json())
        return 0

    return 2


if __name__ == "__main__":
    import sys
    sys.exit(main())
