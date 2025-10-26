from datetime import datetime
from typing import Dict, List, Tuple


def bilinear_vol_interpolation(
    vol_surface_json: Dict,
    strike: float,
    forward: float,
    cashflow_start: datetime,
    valuation_date: datetime
) -> float:
    """
    Perform bilinear interpolation on a volatility surface.

    Parameters:
    -----------
    vol_surface_json : dict
        JSON containing volatility surface data with structure:
        {"data": [[moneyness, year_frac, vol], ...]}
        where moneyness = (strike - forward) * 100
    strike : float
        Strike price
    forward : float
        Forward rate
    cashflow_start : datetime
        Cashflow start date
    valuation_date : datetime
        Valuation date

    Returns:
    --------
    float
        Interpolated volatility
    """
    # Calculate target moneyness and year fraction
    target_moneyness = (strike - forward) * 100
    target_year_frac = (cashflow_start - valuation_date).days / 365

    # Extract data points
    data = vol_surface_json["data"]

    # Extract unique moneyness and year_frac values
    moneyness_values = sorted(set(row[0] for row in data))
    year_frac_values = sorted(set(row[1] for row in data))

    # Find the bounding year_frac values
    y1, y2 = _find_bounds(year_frac_values, target_year_frac)

    # Find the bounding moneyness values
    m1, m2 = _find_bounds(moneyness_values, target_moneyness)

    # Find the 4 corner points
    vol_y1_m1 = _get_vol(data, y1, m1)
    vol_y1_m2 = _get_vol(data, y1, m2)
    vol_y2_m1 = _get_vol(data, y2, m1)
    vol_y2_m2 = _get_vol(data, y2, m2)

    # Perform bilinear interpolation
    # First interpolate along moneyness for each year_frac
    if m2 == m1:
        vol_y1 = vol_y1_m1
        vol_y2 = vol_y2_m1
    else:
        vol_y1 = _linear_interp(m1, m2, vol_y1_m1, vol_y1_m2, target_moneyness)
        vol_y2 = _linear_interp(m1, m2, vol_y2_m1, vol_y2_m2, target_moneyness)

    # Then interpolate along year_frac
    if y2 == y1:
        result = vol_y1
    else:
        result = _linear_interp(y1, y2, vol_y1, vol_y2, target_year_frac)

    return result


def _find_bounds(sorted_values: List[float], target: float) -> Tuple[float, float]:
    """
    Find the two values that bound the target value.

    Parameters:
    -----------
    sorted_values : list
        Sorted list of values
    target : float
        Target value to find bounds for

    Returns:
    --------
    tuple
        (lower_bound, upper_bound)
    """
    if target <= sorted_values[0]:
        return sorted_values[0], sorted_values[0]
    if target >= sorted_values[-1]:
        return sorted_values[-1], sorted_values[-1]

    for i in range(len(sorted_values) - 1):
        if sorted_values[i] <= target <= sorted_values[i + 1]:
            return sorted_values[i], sorted_values[i + 1]

    raise ValueError(f"Could not find bounds for target value {target}")


def _get_vol(data: List[List[float]], year_frac: float, moneyness: float) -> float:
    """
    Get volatility for a specific (year_frac, moneyness) point.

    Parameters:
    -----------
    data : list
        List of [moneyness, year_frac, vol] rows
    year_frac : float
        Year fraction value
    moneyness : float
        Moneyness value

    Returns:
    --------
    float
        Volatility at the specified point
    """
    for row in data:
        if abs(row[1] - year_frac) < 1e-9 and abs(row[0] - moneyness) < 1e-9:
            return row[2]  # Third column is volatility (index 2)

    raise ValueError(f"Could not find vol for year_frac={year_frac}, moneyness={moneyness}")


def _linear_interp(x1: float, x2: float, y1: float, y2: float, x: float) -> float:
    """
    Perform linear interpolation.

    Parameters:
    -----------
    x1, x2 : float
        X bounds
    y1, y2 : float
        Y values at x1 and x2
    x : float
        Target x value

    Returns:
    --------
    float
        Interpolated y value
    """
    if x2 == x1:
        return y1
    return y1 + (y2 - y1) * (x - x1) / (x2 - x1)
