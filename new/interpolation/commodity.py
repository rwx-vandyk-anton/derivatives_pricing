import pandas as pd
import numpy as np
from datetime import datetime


def load_vol_surface(csv_path: str):
    df = pd.read_csv(csv_path)
    df.columns = [str(c).strip() for c in df.columns]
    df["Date"] = pd.to_datetime(df["Date"]).dt.date

    moneyness_cols = []
    for c in df.columns:
        if c == "Date":
            continue
        try:
            moneyness_cols.append(float(c))
        except ValueError:
            pass

    moneyness_cols.sort()
    df = df[["Date"] + [str(m) for m in moneyness_cols]]
    return df, moneyness_cols


# ----------------------------
# FIS cubic Hermite interpolation in strike/moneyness
# ----------------------------
def fis_cubic_interp(x, y, s):
    """
    Implements FIS cubic Hermite interpolation for the strike (moneyness) axis.

    Parameters
    ----------
    x : list or np.ndarray
        Moneyness grid (sorted ascending)
    y : list or np.ndarray
        Corresponding vol values
    s : float
        Target moneyness (strike coordinate)

    Returns
    -------
    float
        Interpolated volatility at s
    """

    x = np.array(x, dtype=float)
    y = np.array(y, dtype=float)
    n = len(x)

    # Clamp if outside bounds (flat extrapolation)
    if s <= x[0]:
        return float(y[0])
    if s >= x[-1]:
        return float(y[-1])

    # Find surrounding interval
    i = np.searchsorted(x, s) - 1
    i = np.clip(i, 0, n - 2)

    # Get four neighboring points if possible
    x0 = x[max(i - 1, 0)]
    x1 = x[i]
    x2 = x[i + 1]
    x3 = x[min(i + 2, n - 1)]

    y0 = y[max(i - 1, 0)]
    y1 = y[i]
    y2 = y[i + 1]
    y3 = y[min(i + 2, n - 1)]

    # Calculate finite-difference slopes (FIS-style)
    d0 = (y1 - y0) / (x1 - x0)
    d1 = ((y2 - y1) / (x2 - x1) - d0) / (x2 - x0)
    d2 = ((y3 - y2) / (x3 - x2) - (y2 - y1) / (x2 - x1) - d1 * (x3 - x1)) / (x3 - x0)

    # Piecewise cubic polynomial
    if x0 <= s <= x2:
        v = (
            y0
            + d0 * (s - x0)
            + d1 * (s - x0) * (s - x1)
            + d2 * (s - x0) * (s - x1) * (s - x2)
        )
    else:
        v = (
            y1
            + d0 * (s - x1)
            + d1 * (s - x1) * (s - x2)
            + d2 * (s - x1) * (s - x2) * (s - x3)
        )
    return float(v)


# ----------------------------
# Linear interpolation across dates
# ----------------------------
def interpolate_vol(df, moneyness_cols, strike, spot, target_date):
    target_date = target_date.date()
    target_m = (strike / spot - 1) * 100
    df = df.sort_values("Date")
    dates = df["Date"].values

    if target_date <= dates[0]:
        vols = df.iloc[0, 1:].astype(float).values
        return fis_cubic_interp(moneyness_cols, vols, target_m)
    if target_date >= dates[-1]:
        vols = df.iloc[-1, 1:].astype(float).values
        return fis_cubic_interp(moneyness_cols, vols, target_m)

    idx_next = np.searchsorted(dates, target_date)
    date_prev, date_next = dates[idx_next - 1], dates[idx_next]
    vols_prev = df.loc[df["Date"] == date_prev].iloc[0, 1:].astype(float).values
    vols_next = df.loc[df["Date"] == date_next].iloc[0, 1:].astype(float).values

    v_prev = fis_cubic_interp(moneyness_cols, vols_prev, target_m)
    v_next = fis_cubic_interp(moneyness_cols, vols_next, target_m)

    t0 = (target_date - date_prev).days
    t1 = (date_next - date_prev).days
    return v_prev + (t0 / t1) * (v_next - v_prev)
