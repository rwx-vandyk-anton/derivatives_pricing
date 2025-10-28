import pandas as pd
import numpy as np
from datetime import date, datetime
import matplotlib.pyplot as plt


# ==========================================================
# Utility Functions
# ==========================================================

def act365(start_date: date, end_date: date) -> float:
    """ACT/365F day count convention."""
    return (end_date - start_date).days / 365.0


# ==========================================================
# Hermite Interpolation Core
# ==========================================================

def hermite_interpolation(t_points, r_points, t_eval):
    """
    Hermite interpolation for continuous rates.

    Parameters
    ----------
    t_points : array-like
        Year fractions from valuation date.
    r_points : array-like
        Continuous rates at each pillar (ACT/365 basis).
    t_eval : float or np.ndarray
        Target year fraction(s).

    Returns
    -------
    float or np.ndarray
        Interpolated rate(s).
    """
    t_points = np.array(t_points, dtype=float)
    r_points = np.array(r_points, dtype=float)
    n = len(t_points)
    h = np.diff(t_points)
    slopes = np.diff(r_points) / h

    # Compute boundary derivatives (slope at endpoints)
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

    # Vectorized evaluation
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


# ==========================================================
# Curve Class Wrapper
# ==========================================================

class HermiteCurve:
    """
    Hermite interpolated continuous yield curve.
    Provides continuous rate and discount factor at arbitrary dates.
    """

    def __init__(self, csv_path: str, valuation_date: date):
        df = pd.read_csv(csv_path)
        df["Date"] = pd.to_datetime(df["Date"]).dt.date

        if "Year Frac" not in df.columns:
            df["Year Frac"] = [act365(valuation_date, d) for d in df["Date"]]

        df = df.sort_values(by="Year Frac")
        self.df = df.reset_index(drop=True)
        self.valuation_date = valuation_date

        self.t_points = df["Year Frac"].to_numpy()
        self.r_points = df["Rate"].to_numpy()

    # ------------------------------------------------------

    def get_cont_rate(self, target_date: date) -> float:
        """Interpolates continuous rate at the given date."""
        t_eval = act365(self.valuation_date, target_date)
        return float(hermite_interpolation(self.t_points, self.r_points, t_eval))

    # ------------------------------------------------------

    def get_discount_factor(self, target_date: date) -> float:
        """Returns discount factor for the given date."""
        t_eval = act365(self.valuation_date, target_date)
        r_eval = hermite_interpolation(self.t_points, self.r_points, t_eval)
        return float(np.exp(-r_eval * t_eval))

    # ------------------------------------------------------

    def plot(self):
        """Plots the curve (rates vs year fractions)."""
        grid = np.linspace(self.t_points.min(), self.t_points.max(), 200)
        rates = hermite_interpolation(self.t_points, self.r_points, grid)
        plt.plot(self.t_points, self.r_points, "o", label="Data")
        plt.plot(grid, rates, "-", label="Hermite Interpolation")
        plt.xlabel("Year Fraction (t)")
        plt.ylabel("Continuous Rate")
        plt.title("Hermite Interpolated Yield Curve")
        plt.legend()
        plt.grid(True)
        plt.show()
