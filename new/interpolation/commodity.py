import pandas as pd
import numpy as np
from datetime import datetime
from scipy.interpolate import CubicHermiteSpline


def load_vol_surface(csv_path: str):
    """
    Loads a volatility surface CSV robustly, regardless of whether moneyness headers
    are strings, integers, or floats.
    """
    df = pd.read_csv(csv_path)

    # Clean column names and convert possible numeric ones to floats
    cleaned_cols = []
    for c in df.columns:
        c_str = str(c).strip()
        if c_str.lower() == "date":
            cleaned_cols.append("Date")
        else:
            try:
                cleaned_cols.append(float(c_str))
            except ValueError:
                cleaned_cols.append(c_str)

    df.columns = cleaned_cols
    df["Date"] = pd.to_datetime(df["Date"]).dt.date

    # Identify numeric moneyness columns
    moneyness_cols = [c for c in df.columns if isinstance(c, (int, float))]
    moneyness_cols.sort()

    # Reorder DataFrame columns
    df = df[["Date"] + moneyness_cols]

    return df, moneyness_cols


def hermite_interp_moneyness(vols: np.ndarray, moneyness: np.ndarray, target_m: float) -> float:
    """Performs Hermite interpolation along the moneyness axis."""
    dydx = np.gradient(vols, moneyness)
    spline = CubicHermiteSpline(moneyness, vols, dydx)
    return float(spline(target_m))


def interpolate_vol(df: pd.DataFrame, moneyness_cols: list, strike: float, spot: float, target_date: datetime) -> float:
    """Interpolates vol for given strike, spot, and target date (Hermite on moneyness, linear on time)."""
    target_date = target_date.date()
    target_moneyness = (strike / spot - 1) * 100

    df = df.sort_values("Date")
    dates = df["Date"].values

    # Boundaries
    if target_date <= dates[0]:
        vols = df.iloc[0, 1:].astype(float).values
        return hermite_interp_moneyness(vols, moneyness_cols, target_moneyness)
    if target_date >= dates[-1]:
        vols = df.iloc[-1, 1:].astype(float).values
        return hermite_interp_moneyness(vols, moneyness_cols, target_moneyness)

    # Interpolate between two nearest dates
    idx_next = np.searchsorted(dates, target_date)
    date_prev, date_next = dates[idx_next - 1], dates[idx_next]
    vols_prev = df.loc[df["Date"] == date_prev].iloc[0, 1:].astype(float).values
    vols_next = df.loc[df["Date"] == date_next].iloc[0, 1:].astype(float).values

    vol_prev = hermite_interp_moneyness(vols_prev, moneyness_cols, target_moneyness)
    vol_next = hermite_interp_moneyness(vols_next, moneyness_cols, target_moneyness)

    # Linear interpolation in time
    t0 = (target_date - date_prev).days
    t1 = (date_next - date_prev).days
    return vol_prev + (t0 / t1) * (vol_next - vol_prev)
