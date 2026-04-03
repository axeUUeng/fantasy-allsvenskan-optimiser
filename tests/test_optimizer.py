"""Tests for the optimizer constraint logic in scripts/optimize_team.py"""

import cvxpy as cp
import numpy as np
import pandas as pd

from fantasy_optimizer.config import OptimizationConfig
from scripts.optimize_team import build_optimizer


def _make_pool(n_gk=4, n_def=10, n_mid=10, n_fwd=6, seed=0):
    """Build a synthetic player pool large enough for the optimizer."""
    rng = np.random.default_rng(seed)
    positions = ["GK"] * n_gk + ["DEF"] * n_def + ["MID"] * n_mid + ["FWD"] * n_fwd
    n = len(positions)
    # Spread players across 8 teams so the max-3-per-team constraint is satisfiable
    teams = [i % 8 + 1 for i in range(n)]
    df = pd.DataFrame(
        {
            "player_id": range(1, n + 1),
            "position": positions,
            "team": teams,
            "cost": rng.uniform(4.5, 9.5, n).round(1),
            "expected_points": rng.uniform(2.0, 8.0, n).round(2),
            "market_score": rng.uniform(0, 1, n),
            "upside_score": rng.uniform(0, 1, n),
            "discipline_penalty": rng.uniform(0, 1, n),
        }
    )
    return df


def _solve(pool, current_ids, balance=10.0, max_transfers=15, cfg=None):
    if cfg is None:
        cfg = OptimizationConfig()
    problem, x = build_optimizer(pool, current_ids, balance, max_transfers, cfg)
    problem.solve(solver=cp.HIGHS)
    return problem, x


def test_optimal_team_has_15_players():
    pool = _make_pool()
    current_ids = list(pool["player_id"].iloc[:15])
    problem, x = _solve(pool, current_ids)
    assert problem.status == cp.OPTIMAL
    selected = (x.value > 0.99).sum()
    assert selected == 15


def test_position_counts_satisfied():
    pool = _make_pool()
    current_ids = list(pool["player_id"].iloc[:15])
    _, x = _solve(pool, current_ids)
    pool["selected"] = x.value > 0.99
    selected = pool[pool["selected"]]
    assert (selected["position"] == "GK").sum() == 2
    assert (selected["position"] == "DEF").sum() == 5
    assert (selected["position"] == "MID").sum() == 5
    assert (selected["position"] == "FWD").sum() == 3


def test_max_players_per_team():
    pool = _make_pool()
    current_ids = list(pool["player_id"].iloc[:15])
    cfg = OptimizationConfig(max_players_per_team=3)
    _, x = _solve(pool, current_ids, cfg=cfg)
    pool["selected"] = x.value > 0.99
    selected = pool[pool["selected"]]
    assert selected.groupby("team").size().max() <= 3


def test_budget_constraint_respected():
    pool = _make_pool()
    current_ids = list(pool["player_id"].iloc[:15])
    balance = 0.0
    team_value = pool[pool["player_id"].isin(current_ids)]["cost"].sum()
    budget = team_value + balance
    _, x = _solve(pool, current_ids, balance=balance)
    pool["selected"] = x.value > 0.99
    total_cost = pool[pool["selected"]]["cost"].sum()
    assert total_cost <= budget + 0.01  # small tolerance for floating point


def test_transfer_limit_respected():
    pool = _make_pool()
    # Build a valid starting team with correct position counts
    current_ids = (
        list(pool[pool["position"] == "GK"]["player_id"].iloc[:2])
        + list(pool[pool["position"] == "DEF"]["player_id"].iloc[:5])
        + list(pool[pool["position"] == "MID"]["player_id"].iloc[:5])
        + list(pool[pool["position"] == "FWD"]["player_id"].iloc[:3])
    )
    max_transfers = 3
    _, x = _solve(pool, current_ids, max_transfers=max_transfers)
    pool["selected"] = x.value > 0.99
    changes = (~pool[pool["selected"]]["player_id"].isin(current_ids)).sum()
    assert changes <= max_transfers


def test_transfer_limit_disabled():
    pool = _make_pool()
    current_ids = list(pool["player_id"].iloc[:15])
    cfg = OptimizationConfig(limit_transfers=False)
    problem, x = _solve(pool, current_ids, cfg=cfg)
    assert problem.status == cp.OPTIMAL


def test_tight_budget_still_finds_solution():
    pool = _make_pool()
    # Set all costs to 5.0 so a valid 15-player team costs exactly 75.0
    pool["cost"] = 5.0
    current_ids = list(pool["player_id"].iloc[:15])
    problem, x = _solve(pool, current_ids, balance=0.0)
    assert problem.status == cp.OPTIMAL
