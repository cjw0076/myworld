#!/usr/bin/env python3
"""AIOS Substrate Character — strengths/weaknesses + automatic complementation (자가 공진).

Founder (2026-06-09): each CLI/substrate has a CHARACTER; AIOS must amplify each one's
strengths and COMPENSATE its weaknesses — automatically, emergently (self-resonance).
Example: claude completes assigned work well but is weak at thinking BIG (ideation /
vision); when a task needs vision, another agent must cover it on its own.

This is the model + the routing that makes that emerge:
  - a per-substrate profile over dimensions (completion / vision / exploration / rigor /
    speed-cost), SEEDED from real session-miner fingerprints + the founder's stated
    priors, then LEARNED from outcomes (the "self" — profiles move toward what actually
    worked, like aios_stakes calibration).
  - complement(active, dim): if the active substrate is WEAK on a needed dimension,
    return the substrate/organ that is strongest on it — the automatic compensator.
    (GenesisOS is the built-in vision/divergence compensator — claude's weak axis.)
  - resonance_plan(active, needed_dims): the emergent ensemble — primary substrate +
    auto-injected complements for each weak-but-needed dimension. No hand-config: the
    weakness is covered by whoever the data says is strong.

Self-resonance loop: outcomes → update_from_outcome → profiles → complement/route →
outcomes. Weak axes get covered automatically and the coverage self-calibrates.

Schema: aios.substrate_character.v1
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STORE = ROOT / ".aios" / "substrate_profiles.json"
WEAK = 0.55          # below this on a needed dimension → needs a complement
DIMENSIONS = ("completion", "vision", "exploration", "rigor", "speed")

# SEED priors (0..1). Sources: session-miner fingerprints (claude=Read/Glob explore +
# Bash/Edit execute; codex=exec_command grind) + the founder's stated example
# (claude completion-strong / vision-weak). These are PRIORS — update_from_outcome
# refines them from real results, so the labels below are starting points, not claims.
SEED: dict[str, dict[str, float]] = {
    # substrate: completion, vision, exploration, rigor, speed(=cheap/fast)
    "claude":     {"completion": 0.85, "vision": 0.45, "exploration": 0.60, "rigor": 0.80, "speed": 0.40},
    "codex":      {"completion": 0.80, "vision": 0.40, "exploration": 0.45, "rigor": 0.65, "speed": 0.60},
    "gemini":     {"completion": 0.65, "vision": 0.60, "exploration": 0.80, "rigor": 0.60, "speed": 0.60},
    "local":      {"completion": 0.55, "vision": 0.40, "exploration": 0.45, "rigor": 0.50, "speed": 0.95},
    # GenesisOS is an ORGAN, not a chat substrate — the built-in vision/divergence
    # compensator (claude's weak axis). High vision/exploration, ~no completion.
    "genesisos":  {"completion": 0.10, "vision": 0.92, "exploration": 0.85, "rigor": 0.35, "speed": 0.70},
}


def load_profiles(store: Path = STORE) -> dict[str, dict[str, float]]:
    if store.exists():
        try:
            saved = json.loads(store.read_text(encoding="utf-8"))
            # merge: seed defaults, saved values win (learned)
            return {s: {**SEED.get(s, {}), **saved.get(s, {})} for s in set(SEED) | set(saved)}
        except (json.JSONDecodeError, OSError):
            pass
    return {s: dict(d) for s, d in SEED.items()}


def save_profiles(profiles: dict, store: Path = STORE) -> None:
    store.parent.mkdir(parents=True, exist_ok=True)
    store.write_text(json.dumps(profiles, ensure_ascii=False, indent=2), encoding="utf-8")


def strongest(dim: str, *, exclude: set[str] | None = None, profiles=None) -> str | None:
    profiles = profiles or load_profiles()
    cands = {s: p.get(dim, 0.0) for s, p in profiles.items() if s not in (exclude or set())}
    return max(cands, key=cands.get) if cands else None


def complement(active: str, dim: str, *, profiles=None) -> str | None:
    """If `active` is weak on a needed dimension, who covers it? (None if active is
    already strong enough.)"""
    profiles = profiles or load_profiles()
    if profiles.get(active, {}).get(dim, 0.0) >= WEAK:
        return None
    best = strongest(dim, exclude={active}, profiles=profiles)
    # only inject a complement that is actually strong on the dimension
    if best and profiles[best].get(dim, 0.0) >= WEAK:
        return best
    return None


def resonance_plan(active: str, needed_dims: list[str], *, profiles=None) -> dict:
    """The emergent ensemble: primary substrate + auto-injected complements for each
    weak-but-needed dimension. This is the self-resonance — weaknesses covered by
    whoever is strong, with no hand-configuration."""
    profiles = profiles or load_profiles()
    injected = {}
    for dim in needed_dims:
        c = complement(active, dim, profiles=profiles)
        if c:
            injected[dim] = c
    return {
        "schema_version": "aios.substrate_character.v1",
        "primary": active,
        "needed": needed_dims,
        "injected": injected,           # dim → compensating substrate/organ
        "self_sufficient": not injected,
    }


def update_from_outcome(substrate: str, dim: str, success: bool, *, rate: float = 0.1,
                        store: Path = STORE) -> dict:
    """Move a substrate's profile toward what actually worked (the learned 'self' —
    EMA toward 1.0 on success, 0.0 on failure). This is what makes the resonance
    self-calibrating rather than a static table."""
    profiles = load_profiles(store)
    cur = profiles.setdefault(substrate, {}).get(dim, 0.5)
    profiles[substrate][dim] = round(cur + rate * ((1.0 if success else 0.0) - cur), 4)
    save_profiles(profiles, store)
    return profiles[substrate]


# map task signals → needed dimensions (so a turn can declare what it needs)
_SIGNAL_DIM = {
    "vision": "vision", "idea": "vision", "strategy": "vision", "imagine": "vision",
    "big picture": "vision", "what should": "vision", "rethink": "vision",
    "explore": "exploration", "research": "exploration", "find": "exploration",
    "verify": "rigor", "prove": "rigor", "audit": "rigor", "check": "rigor",
    "implement": "completion", "build": "completion", "finish": "completion",
    "fast": "speed", "bulk": "speed", "cheap": "speed",
}


def needed_dimensions(task_text: str) -> list[str]:
    t = task_text.lower()
    return sorted({d for kw, d in _SIGNAL_DIM.items() if kw in t})


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Substrate character + automatic complementation")
    p.add_argument("--active", default="claude")
    p.add_argument("--task", default="")
    p.add_argument("--json", action="store_true")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    dims = needed_dimensions(args.task) or DIMENSIONS[:0]
    plan = resonance_plan(args.active, dims or [])
    if args.json:
        print(json.dumps(plan, ensure_ascii=False, indent=2))
    else:
        print(f"primary={plan['primary']} needs={plan['needed']}")
        for dim, c in plan["injected"].items():
            print(f"  weak on {dim} → auto-inject {c}")
        if plan["self_sufficient"]:
            print("  (self-sufficient — no complement needed)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
