import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime


def hermite_interpolation(t_points, r_points, t_eval):
    """
    Hermite interpolation based on provided formula.
    t_points: array of year fractions
    r_points: array of continuous rates
    t_eval: scalar or array of year fractions to evaluate
    """
    t_points = np.array(t_points, dtype=float)
    r_points = np.array(r_points, dtype=float)
    n = len(t_points)
    h = np.diff(t_points)
    slopes = np.diff(r_points) / h

    # Boundary derivatives
    r_prime = np.zeros(n)
    r_prime[0] = ((2 * h[0] + h[1]) * slopes[0] - h[0] * slopes[1]) / (h[0] + h[1])
    r_prime[-1] = ((2 * h[-1] + h[-2]) * slopes[-1] - h[-1] * slopes[-2]) / (h[-1] + h[-2])

    # Interior derivatives
    for i in range(1, n - 1):
        r_prime[i] = ((h[i] * slopes[i - 1]) + (h[i - 1] * slopes[i])) / (h[i - 1] + h[i])

    def hermite_segment(i, t):
        t0, t1 = t_points[i], t_points[i + 1]
        r0, r1 = r_points[i], r_points[i + 1]
        r0p, r1p = r_prime[i], r_prime[i + 1]

        m = (t - t0) / (t1 - t0)
        g1 = (t1 - t0) * r0p
        c1 = (t1 - t0) * r1p

        return (
            (1 - m) * r0
            + m * r1
            + m * (1 - m) * ((1 - m) * (r1 - r0) - (1 - m) * g1 + m * c1)
        )

    # Handle scalar or vector t_eval
    t_eval = np.atleast_1d(t_eval)
    result = np.zeros_like(t_eval)

    for j, t in enumerate(t_eval):
        if t <= t_points[0]:
            result[j] = r_points[0]
        elif t >= t_points[-1]:
            result[j] = r_points[-1]
        else:
            i = np.searchsorted(t_points, t) - 1
            result[j] = hermite_segment(i, t)

    return result if len(result) > 1 else result[0]


def run_hermite_from_csv(csv_path, t_eval_points=None, plot=True):
    """
    Loads a CSV and runs Hermite interpolation.
    The CSV must have columns: 'Date', 'Rate', 'Year Frac'.
    """
    df = pd.read_csv(csv_path)
    df = df.dropna(subset=["Year Frac", "Rate"])
    df = df.sort_values(by="Year Frac")

    t_points = df["Year Frac"].to_numpy()
    r_points = df["Rate"].to_numpy()

    # Default evaluation points (dense grid)
    if t_eval_points is None:
        t_eval_points = np.linspace(t_points.min(), t_points.max(), 200)

    r_interp = hermite_interpolation(t_points, r_points, t_eval_points)

    # Plot result
    if plot:
        plt.figure(figsize=(8, 4))
        plt.plot(t_points, r_points, "o", label="Data")
        plt.plot(t_eval_points, r_interp, "-", label="Hermite Interpolation")
        plt.xlabel("Year Fraction (t)")
        plt.ylabel("Rate (continuous ACT/365)")
        plt.title("Hermite Interpolated Curve")
        plt.legend()
        plt.grid(True)
        plt.tight_layout()
        plt.show()

    return pd.DataFrame({"YearFrac": t_eval_points, "InterpolatedRate": r_interp})

