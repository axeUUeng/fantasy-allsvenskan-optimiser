"""Tests for scripts/build_forecasts.py — PMF building and simulation forecasts."""

import numpy as np
import pandas as pd

from scripts.build_forecasts import (
    _align_and_mix_pmfs,
    _apply_zero_inflation,
    _empirical_decay_pmf,
    _smooth_discrete_pmf,
    build_points_pmf,
    build_simulation_forecasts,
)

# --- PMF helpers ---


def test_empirical_decay_pmf_sums_to_one():
    pts = np.array([2, 3, 5, 2, 6])
    support, probs = _empirical_decay_pmf(pts)
    assert abs(probs.sum() - 1.0) < 1e-9


def test_empirical_decay_pmf_empty_returns_zero_spike():
    support, probs = _empirical_decay_pmf(np.array([]))
    assert support[0] == 0
    assert abs(probs.sum() - 1.0) < 1e-9


def test_empirical_decay_pmf_non_negative():
    support, probs = _empirical_decay_pmf(np.array([0, 1, 0, 2, 0]))
    assert (probs >= 0).all()


def test_align_and_mix_pmfs_sums_to_one():
    s1, p1 = np.array([0, 1, 2]), np.array([0.5, 0.3, 0.2])
    s2, p2 = np.array([1, 2, 3]), np.array([0.4, 0.4, 0.2])
    grid, mixed = _align_and_mix_pmfs(s1, p1, s2, p2, mix=0.2)
    assert abs(mixed.sum() - 1.0) < 1e-9


def test_apply_zero_inflation_increases_zero_mass():
    grid = np.array([0, 1, 2, 3])
    probs = np.array([0.1, 0.4, 0.3, 0.2])
    _, inflated = _apply_zero_inflation(grid, probs, zero_boost=0.1)
    assert inflated[0] > probs[0]
    assert abs(inflated.sum() - 1.0) < 1e-9


def test_apply_zero_inflation_noop_when_zero():
    grid = np.array([0, 1, 2])
    probs = np.array([0.2, 0.5, 0.3])
    _, out = _apply_zero_inflation(grid, probs, zero_boost=0.0)
    np.testing.assert_array_almost_equal(out, probs)


def test_smooth_discrete_pmf_sums_to_one():
    grid = np.arange(10)
    probs = np.zeros(10)
    probs[5] = 1.0
    _, smoothed = _smooth_discrete_pmf(grid, probs, sigma=1.0)
    assert abs(smoothed.sum() - 1.0) < 1e-9
    assert smoothed[5] < 1.0  # mass spread out


def test_smooth_noop_when_sigma_zero():
    grid = np.arange(5)
    probs = np.array([0.1, 0.2, 0.4, 0.2, 0.1])
    _, out = _smooth_discrete_pmf(grid, probs, sigma=0)
    np.testing.assert_array_equal(out, probs)


# --- build_points_pmf ---


def test_build_points_pmf_returns_valid_distribution():
    pts = np.array([2, 4, 3, 5, 2, 6, 3])
    grid, pmf = build_points_pmf(pts)
    assert abs(pmf.sum() - 1.0) < 1e-9
    assert (pmf >= 0).all()
    assert len(grid) == len(pmf)


def test_build_points_pmf_expected_value_positive():
    pts = np.array([3, 4, 5, 6, 4])
    grid, pmf = build_points_pmf(pts)
    ev = float((grid * pmf).sum())
    assert ev > 0


# --- build_simulation_forecasts ---


def test_simulation_forecasts_returns_one_row_per_player():
    df = pd.DataFrame(
        {
            "element": [1, 1, 1, 2, 2, 2],
            "total_points": [3, 5, 2, 4, 6, 3],
            "round": [1, 2, 3, 1, 2, 3],
            "position": ["MID"] * 6,
        }
    )
    result = build_simulation_forecasts(df)
    assert set(result["player_id"]) == {1, 2}
    assert len(result) == 2


def test_simulation_forecasts_expected_points_positive():
    df = pd.DataFrame(
        {
            "element": [1, 1, 2, 2],
            "total_points": [5, 6, 3, 4],
            "round": [1, 2, 1, 2],
            "position": ["FWD", "FWD", "DEF", "DEF"],
        }
    )
    result = build_simulation_forecasts(df)
    assert (result["expected_points"] > 0).all()


def test_simulation_forecasts_player_with_all_zeros():
    df = pd.DataFrame(
        {
            "element": [1, 1, 1],
            "total_points": [0, 0, 0],
            "round": [1, 2, 3],
            "position": ["GK", "GK", "GK"],
        }
    )
    result = build_simulation_forecasts(df)
    assert len(result) == 1
    # Expected points should be low but not negative
    assert result["expected_points"].iloc[0] >= 0
