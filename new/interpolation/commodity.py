import pandas as pd
import numpy as np
from datetime import datetime
from scipy.interpolate import CubicHermiteSpline


def load_vol_surface(csv_path: str) -> pd.DataFrame:
    """
    Loads the volatility surface CSV into a DataFrame.
    Expects columns: Date, and then moneyness levels as numeric headers (-40, -20, 0, 10, etc.)
    """
    df = pd.read_csv(csv_path)
    df["Date"] = pd.to_datetime(df["Date"]).dt.date
    moneyness_cols = [float(c) for c in df.columns if c != "Date"]
    moneyness_cols.sort()
    df = df[["Date"] + [str(m) for m in moneyness_cols]]
    return df, moneyness_cols


def hermite_interp_moneyness(vols: np.ndarray, moneyness: np.ndarray, target_m: float) -> float:
    """
    Performs Hermite interpolation along the moneyness axis.
    Approximates derivatives using finite differences.
    """
    dydx = np.gradient(vols, moneyness)
    spline = CubicHermiteSpline(moneyness, vols, dydx)
    return float(spline(target_m))


def interpolate_vol(
    df: pd.DataFrame,
    moneyness_cols: list,
    strike: float,
    spot: float,
    target_date: datetime
) -> float:
    """
    Interpolates volatility for a given strike, spot, and target date.

    Parameters
    ----------
    df : pd.DataFrame
        Volatility surface with 'Date' and moneyness columns.
    moneyness_cols : list
        Sorted list of moneyness levels.
    strike : float
        Strike price.
    spot : float
        Spot price.
    target_date : datetime
        Date for which to interpolate volatility.

    Returns
    -------
    float
        Interpolated volatility value.
    """
    target_date = target_date.date()
    target_moneyness = (strike / spot - 1) * 100

    # Ensure sorting
    df = df.sort_values("Date")
    dates = df["Date"].values

    # Handle before/after range dates
    if target_date <= dates[0]:
        vols = df.iloc[0, 1:].astype(float).values
        return hermite_interp_moneyness(vols, moneyness_cols, target_moneyness)
    if target_date >= dates[-1]:
        vols = df.iloc[-1, 1:].astype(float).values
        return hermite_interp_moneyness(vols, moneyness_cols, target_moneyness)

    # Find surrounding dates
    idx_next = np.searchsorted(dates, target_date)
    date_prev = dates[idx_next - 1]
    date_next = dates[idx_next]

    vols_prev = df.loc[df["Date"] == date_prev].iloc[0, 1:].astype(float).values
    vols_next = df.loc[df["Date"] == date_next].iloc[0, 1:].astype(float).values

    vol_prev = hermite_interp_moneyness(vols_prev, moneyness_cols, target_moneyness)
    vol_next = hermite_interp_moneyness(vols_next, moneyness_cols, target_moneyness)

    # Linear interpolation in time
    t0 = (target_date - date_prev).days
    t1 = (date_next - date_prev).days
    w = t0 / t1
    return vol_prev + w * (vol_next - vol_prev)
