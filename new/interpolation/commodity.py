import pandas as pd
import numpy as np
from datetime import datetime
from scipy.interpolate import CubicHermiteSpline


def load_vol_surface(csv_path: str) -> tuple[pd.DataFrame, list[float]]:
    """
    Loads the volatility surface CSV into a DataFrame.
    Fixes spacing and type issues in column names automatically.
    """
    df = pd.read_csv(csv_path)

    # --- Clean column names ---
    df.columns = [str(c).strip() for c in df.columns]  # remove whitespace
    df["Date"] = pd.to_datetime(df["Date"]).dt.date

    # Extract numeric moneyness levels robustly
    moneyness_cols = []
    for c in df.columns:
        if c == "Date":
            continue
        try:
            m = float(c)
            moneyness_cols.append(m)
        except ValueError:
            pass  # ignore any non-numeric columns if present

    moneyness_cols.sort()
    df = df[["Date"] + [str(m) for m in moneyness_cols]]
    return df, moneyness_cols


def hermite_interp_moneyness(vols: np.ndarray, moneyness: np.ndarray, target_m: float) -> float:
    """Hermite interpolation across moneyness."""
    dydx = np.gradient(vols, moneyness)
    spline = CubicHermiteSpline(moneyness, vols, dydx)
    return float(spline(target_m))


def interpolate_vol(df, moneyness_cols, strike, spot, target_date):
    """Linear on time, Hermite on moneyness."""
    target_date = target_date.date()
    target_moneyness = (strike / spot - 1) * 100

    df = df.sort_values("Date")
    dates = df["Date"].values

    if target_date <= dates[0]:
        vols = df.iloc[0, 1:].astype(float).values
        return hermite_interp_moneyness(vols, moneyness_cols, target_moneyness)
    if target_date >= dates[-1]:
        vols = df.iloc[-1, 1:].astype(float).values
        return hermite_interp_moneyness(vols, moneyness_cols, target_moneyness)

    idx_next = np.searchsorted(dates, target_date)
    date_prev, date_next = dates[idx_next - 1], dates[idx_next]
    vols_prev = df.loc[df["Date"] == date_prev].iloc[0, 1:].astype(float).values
    vols_next = df.loc[df["Date"] == date_next].iloc[0, 1:].astype(float).values

    vol_prev = hermite_interp_moneyness(vols_prev, moneyness_cols, target_moneyness)
    vol_next = hermite_interp_moneyness(vols_next, moneyness_cols, target_moneyness)

    t0 = (target_date - date_prev).days
    t1 = (date_next - date_prev).days
    return vol_prev + (t0 / t1) * (vol_next - vol_prev)
