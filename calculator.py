"""Pull-up 1RM calculator using the modified Epley formula.

Formula (from workout-temple.com):
  1RM = (bodyweight + added_weight) * (1 + 0.0333 * (reps - 1)) - bodyweight

Inverse (unweighted reps from 1RM):
  reps = 1 + 1RM / (bodyweight * 0.0333)
"""

import numpy as np


def compute_1rm(bodyweight: float, added_weight: float, reps: int) -> float:
    """Compute the estimated 1-rep-max added weight for weighted pull-ups."""
    return (bodyweight + added_weight) * (1 + 0.0333 * (reps - 1)) - bodyweight


def compute_unweighted_reps(bodyweight: float, one_rm: float) -> float:
    """Back-calculate estimated reps at zero added weight from a known 1RM.

    Derived by setting added_weight=0 in the 1RM formula and solving for reps:
      1RM = BW * 0.0333 * (reps - 1)
      reps = 1 + 1RM / (BW * 0.0333)
    """
    return 1 + one_rm / (bodyweight * 0.0333)


def compute_1rm_grid(
    bodyweight: float,
    weight_range: tuple[float, float] = (0, 30),
    reps_range: tuple[int, int] = (1, 25),
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return arrays for added weights, reps, and the 2-D 1RM grid.

    Returns
    -------
    added_weights : 1-D array  (columns / x-axis)
    reps          : 1-D array  (rows / y-axis)
    rm_grid       : 2-D array  shape (len(reps), len(added_weights))
    """
    added_weights = np.arange(weight_range[0], weight_range[1] + 1, dtype=float)
    reps = np.arange(reps_range[0], reps_range[1] + 1, dtype=int)

    w_grid, r_grid = np.meshgrid(added_weights, reps)
    rm_grid = (bodyweight + w_grid) * (1 + 0.0333 * (r_grid - 1)) - bodyweight

    return added_weights, reps, np.round(rm_grid, 1)
