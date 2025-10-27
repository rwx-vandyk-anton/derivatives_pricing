import pandas as pd
from datetime import datetime
from typing import List, Tuple


def bilinear_vol_interpolation_from_csv(
    csv_path: str,
    strike: float,
    forward: float,
    cashflow_start: datetime,
    valuation_date: datetime
) -> float:
    """
    Perform bilinear interpolation on a volatility surface loaded from a CSV file.

    Parameters:
    -----------
    csv_path : str
        Path to the CSV file containing volatility surface data.
        Expected columns:
            'Expiry', 'Strike', 'Forward Vol', 'Year Frac'
        - 'Expiry' (ignored)
        - 'Strike' = moneyness
        - 'Forward Vol' = volatility value
        - 'Year Frac' = year fraction

    strike : float
        Strike price.
    forward : float
        Forward rate.
    cashflow_start : datetime
        Cashflow start date.
    valuation_date : datetime
        Valuation date.

    Returns:
    --------
    float
        Interpolated volatility.
    """
    # Load CSV data
    df = pd.read_csv(csv_path)

    # Rename for consistency
    df.columns = [col.strip() for col in df.columns]

    # Extract relevant columns
    data = df[["Strike", "Forward Vol", "Year Frac"]].values.tolist()

    # Compute target values
    target_moneyness = (strike - forward) * 100
    target_year_frac = (cashflow_start - valuation_date).days / 365

    # Unique sorted axes
    moneyness_values = sorted(set(row[0] for row in data))
    year_frac_values = sorted(set(row[2] for row in data))

    # Find bounding values
    y1, y2 = _find_bounds(year_frac_values, target_year_frac)
    m1, m2 = _find_bounds(moneyness_values, target_moneyness)

    # Get the four corner volatilities
    vol_y1_m1 = _get_vol(data, y1, m1)
    vol_y1_m2 = _get_vol(data, y1, m2)
    vol_y2_m1 = _get_vol(data, y2, m1)
    vol_y2_m2 = _get_vol(data, y2, m2)

    # Interpolate along moneyness first
    if m2 == m1:
        vol_y1 = vol_y1_m1
        vol_y2 = vol_y2_m1
    else:
        vol_y1 = _linear_interp(m1, m2, vol_y1_m1, vol_y1_m2, target_moneyness)
        vol_y2 = _linear_interp(m1, m2, vol_y2_m1, vol_y2_m2, target_moneyness)

    # Interpolate along year fraction
    if y2 == y1:
        result = vol_y1
    else:
        result = _linear_interp(y1, y2, vol_y1, vol_y2, target_year_frac)

    return result


def _find_bounds(sorted_values: List[float], target: float) -> Tuple[float, float]:
    """Find the two bounding values in a sorted list."""
    if target <= sorted_values[0]:
        return sorted_values[0], sorted_values[0]
    if target >= sorted_values[-1]:
        return sorted_values[-1], sorted_values[-1]

    for i in range(len(sorted_values) - 1):
        if sorted_values[i] <= target <= sorted_values[i + 1]:
            return sorted_values[i], sorted_values[i + 1]

    raise ValueError(f"Could not find bounds for target value {target}")


def _get_vol(data: List[List[float]], year_frac: float, moneyness: float) -> float:
    """Retrieve vol for a given (year_frac, moneyness) pair."""
    for row in data:
        if abs(row[0] - moneyness) < 1e-9 and abs(row[2] - year_frac) < 1e-9:
            return row[1]
    raise ValueError(f"Could not find vol for year_frac={year_frac}, moneyness={moneyness}")


def _linear_interp(x1: float, x2: float, y1: float, y2: float, x: float) -> float:
    """Perform linear interpolation."""
    if x2 == x1:
        return y1
    return y1 + (y2 - y1) * (x - x1) / (x2 - x1)
