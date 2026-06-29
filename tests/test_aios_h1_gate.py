"""
Automated assertions for the H1 gate experiment (scripts/aios_h1_gate.py).

Tests verify the mechanistic claims on the synthetic AIOS-shaped graph;
they do NOT assert anything about real memory (that is a factual probe, not a spec).
"""

import sys
from pathlib import Path

import pytest
import torch

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "universe" / "descentnet"))
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from api import SheafCover, project_edge_field, coboundary  # noqa: E402
from aios_h1_gate import (  # noqa: E402
    ATOM_ERROR,
    CORRUPT_ERROR,
    DTYPE,
    IDX_ATOM_IN,
    IDX_ATOM_OUT,
    IDX_CORRUPTED,
    IDX_LIAR_IN,
    IDX_LIAR_OUT,
    LIAR_OFFSET,
    TRIANGLE_A_EDGES,
    TRIANGLE_B_EDGES,
    TRIANGLE_C_EDGES,
    BRIDGE_EDGES,
    N_NODES,
    TRUE_VALS,
    _sub_threshold_demo,
    build_corrupted_measurements,
    build_cover,
    build_true_measurements,
    compute_h1,
    cycle_sums,
    least_squares_solve,
    threshold_detector,
)


# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def setup():
    cover     = build_cover()
    true_m    = build_true_measurements()
    corrupt_m = build_corrupted_measurements()
    h1        = compute_h1(cover, corrupt_m)
    obs_abs   = h1["obstruction"][0, :, 0].abs()
    ls        = least_squares_solve(cover, corrupt_m)
    return {
        "cover":     cover,
        "true_m":    true_m,
        "corrupt_m": corrupt_m,
        "h1":        h1,
        "obs_abs":   obs_abs,
        "ls":        ls,
    }


# ---------------------------------------------------------------------------
# 1. Cycle holonomy is correctly injected
# ---------------------------------------------------------------------------

def test_cycle_A_holonomy_equals_corrupt_error(setup):
    holonomy = cycle_sums(setup["corrupt_m"])
    assert abs(holonomy["cycle_A_holonomy"] - CORRUPT_ERROR) < 1e-10, (
        f"Cycle-A holonomy should equal CORRUPT_ERROR={CORRUPT_ERROR}, "
        f"got {holonomy['cycle_A_holonomy']}"
    )


def test_cycle_B_holonomy_is_zero(setup):
    """Coherent liar produces zero cycle holonomy (it is a gauge shift)."""
    holonomy = cycle_sums(setup["corrupt_m"])
    assert abs(holonomy["cycle_B_holonomy (liar)"]) < 1e-10, (
        f"Liar cycle holonomy should be 0, got {holonomy['cycle_B_holonomy (liar)']}"
    )


def test_cycle_C_holonomy_equals_2x_atom_error(setup):
    """Incoherent atom injects errors in the same direction -> holonomy = 2*ATOM_ERROR."""
    holonomy = cycle_sums(setup["corrupt_m"])
    expected = 2 * ATOM_ERROR
    assert abs(holonomy["cycle_C_holonomy (atom)"] - expected) < 1e-10, (
        f"Atom cycle holonomy should be {expected}, got {holonomy['cycle_C_holonomy (atom)']}"
    )


# ---------------------------------------------------------------------------
# 2. H1 obstruction concentrates on the correct triangle
# ---------------------------------------------------------------------------

def test_triangle_A_obstruction_nonzero(setup):
    obs_A = float(setup["obs_abs"][TRIANGLE_A_EDGES].mean())
    assert obs_A > 1e-6, f"Triangle A should have non-zero obstruction, got {obs_A}"


def test_triangle_B_liar_obstruction_near_zero(setup):
    """Coherent liar (gauge) -> H1 obstruction on Triangle B is exactly 0."""
    obs_B = float(setup["obs_abs"][TRIANGLE_B_EDGES].mean())
    assert obs_B < 1e-10, (
        f"Liar triangle obstruction should be ~0, got {obs_B}"
    )


def test_triangle_C_atom_obstruction_nonzero(setup):
    obs_C = float(setup["obs_abs"][TRIANGLE_C_EDGES].mean())
    assert obs_C > 1e-6, f"Atom triangle should have non-zero obstruction, got {obs_C}"


def test_bridge_edges_obstruction_near_zero(setup):
    obs_bridge = float(setup["obs_abs"][BRIDGE_EDGES].mean())
    assert obs_bridge < 1e-10, (
        f"Bridge edges (no cycles) should have ~0 obstruction, got {obs_bridge}"
    )


# ---------------------------------------------------------------------------
# 3. Liar vs Atom discrimination: atom/liar ratio >> 10
# ---------------------------------------------------------------------------

def test_atom_to_liar_ratio_greater_than_10(setup):
    liar_avg = float(setup["obs_abs"][TRIANGLE_B_EDGES].mean())
    atom_avg = float(setup["obs_abs"][TRIANGLE_C_EDGES].mean())
    if liar_avg < 1e-12:
        # liar is exactly zero -> ratio is infinite (the strong case)
        assert atom_avg > 1e-6, "Atom should have non-zero obstruction"
    else:
        ratio = atom_avg / liar_avg
        assert ratio > 10.0, (
            f"Atom/Liar obstruction ratio should exceed 10; got {ratio:.2f}"
        )


# ---------------------------------------------------------------------------
# 4. H1 obstruction within Triangle A is distributed equally (bad edge NOT uniquely pinpointed)
# ---------------------------------------------------------------------------

def test_all_cycle_A_edges_share_obstruction(setup):
    """
    H1 distributes holonomy uniformly across all k edges in the cycle.
    The corrupted edge is NOT the unique argmax within Triangle A.
    """
    obs_A_vals = [float(setup["obs_abs"][i]) for i in TRIANGLE_A_EDGES]
    max_v = max(obs_A_vals)
    min_v = min(obs_A_vals)
    spread = max_v - min_v
    assert spread < 1e-10, (
        f"All cycle-A edges should have equal obstruction; spread = {spread:.2e}, "
        f"values = {obs_A_vals}"
    )


def test_corrupted_edge_is_not_unique_argmax_globally(setup):
    """
    The bad edge shares its obstruction with the rest of Triangle A,
    so it is NOT the unique global argmax.
    """
    obs_abs = setup["obs_abs"]
    max_val = float(obs_abs.max())
    corrupted_val = float(obs_abs[IDX_CORRUPTED])
    # Corrupted edge has max obstruction, but so do its cycle partners
    n_at_max = int((obs_abs >= max_val - 1e-10).sum())
    assert n_at_max > 1, (
        f"Expected multiple edges at argmax (holonomy distributes), got {n_at_max}"
    )


# ---------------------------------------------------------------------------
# 5. H1 == LS edge residual (numerically identical)
# ---------------------------------------------------------------------------

def test_h1_obstruction_equals_ls_residual(setup):
    """
    Both compute (I - BB^+) applied to the same residual vector.
    Numerically they must be identical.
    """
    h1_flat = setup["h1"]["obstruction"][0, :, 0]
    ls_flat = setup["ls"]["ls_residual"]
    max_diff = float((h1_flat - ls_flat).abs().max())
    assert max_diff < 1e-9, (
        f"H1 obstruction and LS edge residual should be identical; "
        f"max diff = {max_diff:.2e}"
    )


# ---------------------------------------------------------------------------
# 6. Sub-threshold holonomy demo: H1 detects, threshold misses
# ---------------------------------------------------------------------------

def test_subthreshold_holonomy_h1_detects(setup):
    cover = setup["cover"]
    result = _sub_threshold_demo(cover)
    assert result["h1_detects_holonomy"], (
        "H1 should detect cycle-A holonomy even when individual edge errors are sub-threshold"
    )


def test_subthreshold_threshold_misses(setup):
    cover = setup["cover"]
    result = _sub_threshold_demo(cover)
    assert not result["threshold_flags_any_A_edge"], (
        "Per-edge threshold should NOT flag sub-threshold errors (0.04 < 0.08)"
    )


# ---------------------------------------------------------------------------
# 7. Obstruction magnitude is correct for Triangle A
# ---------------------------------------------------------------------------

def test_triangle_A_obstruction_magnitude(setup):
    """
    Cycle A holonomy = CORRUPT_ERROR = 0.30.
    With 3 edges in the cycle, H1 per-edge obstruction = 0.30/3 = 0.10.
    """
    expected = CORRUPT_ERROR / 3
    obs_A = float(setup["obs_abs"][TRIANGLE_A_EDGES].mean())
    assert abs(obs_A - expected) < 1e-8, (
        f"Expected triangle-A obstruction = {expected:.6f}, got {obs_A:.8f}"
    )


def test_triangle_C_obstruction_magnitude(setup):
    """
    Cycle C holonomy = 2 * ATOM_ERROR = 0.20.
    With 3 edges, H1 per-edge obstruction = 0.20/3 ≈ 0.0667.
    """
    expected = 2 * ATOM_ERROR / 3
    obs_C = float(setup["obs_abs"][TRIANGLE_C_EDGES].mean())
    assert abs(obs_C - expected) < 1e-8, (
        f"Expected triangle-C obstruction = {expected:.8f}, got {obs_C:.8f}"
    )
