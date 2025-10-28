import pandas as pd
import numpy as np
from datetime import date


# ==========================================================
# Utility
# ==========================================================

def act365(start_date: date, end_date: date) -> float:
    """ACT/365F day count convention."""
    return (end_date - start_date).days / 365.0


# ==========================================================
# Hermite Interpolation Core (on r*t)
# ==========================================================

def hermite_interpolation(y_points, t_points, t_eval):
    """
    Hermite interpolation on y = r * t values.
    """
    t_points = np.array(t_points, dtype=float)
    y_points = np.array(y_points, dtype=float)
    n = len(t_points)
    h = np.diff(t_points)
    slopes = np.diff(y_points) / h

    # Boundary derivatives
    y_prime = np.zeros(n)
    y_prime[0] = ((2 * h[0] + h[1]) * slopes[0] - h[0] * slopes[1]) / (h[0] + h[1])
    y_prime[-1] = ((2 * h[-1] + h[-2]) * slopes[-1] - h[-1] * slopes[-2]) / (h[-1] + h[-2])

    # Interior derivatives
    for i in range(1, n - 1):
        y_prime[i] = ((h[i] * slopes[i - 1]) + (h[i - 1] * slopes[i])) / (h[i - 1] + h[i])

    def hermite_segment(i, t):
        t0, t1 = t_points[i], t_points[i + 1]
        y0, y1 = y_points[i], y_points[i + 1]
        y0p, y1p = y_prime[i], y_prime[i + 1]
        m = (t - t0) / (t1 - t0)
        g1 = (t1 - t0) * y0p
        c1 = (t1 - t0) * y1p

        return (
            (1 - m) * y0
            + m * y1
            + m * (1 - m) * ((1 - m) * (y1 - y0) - (1 - m) * g1 + m * c1)
        )

    # Evaluate at target t_eval
    t_eval = np.atleast_1d(t_eval)
    result = np.zeros_like(t_eval)
    for j, t in enumerate(t_eval):
        if t <= t_points[0]:
            result[j] = y_points[0]
        elif t >= t_points[-1]:
            result[j] = y_points[-1]
        else:
            i = np.searchsorted(t_points, t) - 1
            result[j] = hermite_segment(i, t)
    return result if len(result) > 1 else result[0]


# ==========================================================
# Hermite Curve Class
# ==========================================================

class HermiteCurve:
    """
    Hermite interpolated continuous yield curve (R1 method)
    Interpolates on r*t, i.e. log(DF) space.
    """

    def __init__(self, csv_path: str, valuation_date: date):
        df = pd.read_csv(csv_path)
        df["Date"] = pd.to_datetime(df["Date"]).dt.date

        if "Year Frac" not in df.columns:
            df["Year Frac"] = [act365(valuation_date, d) for d in df["Date"]]

        df = df.sort_values(by="Year Frac").reset_index(drop=True)
        self.df = df
        self.valuation_date = valuation_date

        self.t_points = df["Year Frac"].to_numpy()
        self.r_points = df["Rate"].to_numpy()
        self.y_points = self.t_points * self.r_points  # Interpolation in y = r*t space

    # ------------------------------------------------------

    def get_cont_rate(self, target_date: date) -> float:
        """Interpolated continuous rate r(t) at given date."""
        t_eval = act365(self.valuation_date, target_date)
        if t_eval == 0:
            return self.r_points[0]
        y_interp = hermite_interpolation(self.y_points, self.t_points, t_eval)
        return float(y_interp / t_eval)

    # ------------------------------------------------------

    def get_discount_factor(self, target_date: date) -> float:
        """Discount factor DF(t) = exp(-r(t)*t)"""
        t_eval = act365(self.valuation_date, target_date)
        y_interp = hermite_interpolation(self.y_points, self.t_points, t_eval)
        return float(np.exp(-y_interp))