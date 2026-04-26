"""Tests for calculator.py pure functions."""

import numpy as np
import pytest

from calculator import compute_1rm, compute_1rm_grid, compute_unweighted_reps


class TestCompute1RM:
    def test_single_rep_equals_added_weight(self):
        assert compute_1rm(64, 20, 1) == pytest.approx(20.0)

    def test_single_rep_various_weights(self):
        for aw in [0, 10, 30, 50]:
            assert compute_1rm(80, aw, 1) == pytest.approx(aw)

    def test_known_value(self):
        # (64 + 20) * (1 + 0.0333 * 4) - 64 = 84 * 1.1332 - 64
        expected = (64 + 20) * (1 + 0.0333 * 4) - 64
        assert compute_1rm(64, 20, 5) == pytest.approx(expected)

    def test_zero_added_weight(self):
        result = compute_1rm(70, 0, 10)
        expected = 70 * (1 + 0.0333 * 9) - 70
        assert result == pytest.approx(expected)


class TestComputeUnweightedReps:
    def test_known_value(self):
        one_rm = 20.0
        bw = 64.0
        expected = 1 + 20 / (64 * 0.0333)
        assert compute_unweighted_reps(bw, one_rm) == pytest.approx(expected)

    def test_symmetry_round_trip(self):
        """compute_unweighted_reps(bw, compute_1rm(bw, 0, n)) ≈ n"""
        bw = 64.0
        for n in [5, 10, 15, 20]:
            one_rm = compute_1rm(bw, 0, n)
            recovered = compute_unweighted_reps(bw, one_rm)
            assert recovered == pytest.approx(n, abs=1e-6)


class TestCompute1RMGrid:
    def test_default_shape(self):
        aw, reps, grid = compute_1rm_grid(64)
        assert aw.shape == (31,)  # 0..30 inclusive
        assert reps.shape == (25,)  # 1..25 inclusive
        assert grid.shape == (25, 31)

    def test_custom_range_shape(self):
        aw, reps, grid = compute_1rm_grid(70, weight_range=(5, 10), reps_range=(2, 6))
        assert aw.shape == (6,)  # 5..10
        assert reps.shape == (5,)  # 2..6
        assert grid.shape == (5, 6)

    def test_grid_values_match_scalar(self):
        bw = 64.0
        aw, reps, grid = compute_1rm_grid(bw, weight_range=(0, 5), reps_range=(1, 3))
        for ri, r in enumerate(reps):
            for wi, w in enumerate(aw):
                expected = round(compute_1rm(bw, float(w), int(r)), 1)
                assert grid[ri, wi] == pytest.approx(expected)
