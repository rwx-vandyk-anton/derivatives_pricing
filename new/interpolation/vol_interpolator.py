import json
from datetime import datetime
from typing import Dict, List, Tuple


def bilinear_vol_interpolation(
    vol_surface_path: str,
    strike: float,
    forward: float,
    cashflow_start: datetime,
    valuation_date: datetime
) -> float:
    """
    Perform bilinear interpolation on a volatility surface loaded from a JSON file.

    Parameters:
    -----------
    vol_surface_path : str
        Path to the JSON file containing the volatility surface data.
        Expected structure:
        {
            "<surface_name>": {
                "Surface": {
                    ".Curve": {
                        "meta": [...],
                        "data": [
                            [moneyness, year_frac, tenor, vol],
                            ...
                        ]
                    }
                }
            }
        }
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
    # Load JSON data from file
    with open(vol_surface_path, "r") as f:
        full_json = json.load(f)

    # Get the first key dynamically (e.g., "InterestRateVol.ZAR_CAPFLOOR_SMILE_ICE/+7.500000")
    surface_key = next(iter(full_json.keys()))
    data = full_json[surface_key]["Surface"][".Curve"]["data"]

    # Calculate target moneyness and year fraction
    target_moneyness = (strike - forward) * 100
    target_year_frac = (cashflow_start - valuation_date).days / 365

    # Extract unique moneyness and year_frac values
    moneyness_values = sorted(set(row[0] for row in data))
    year_frac_values = sorted(set(row[1] for row in data))

    # Find bounding year_frac and moneyness
    y1, y2 = _find_bounds(year_frac_values, target_year_frac)
    m1, m2 = _find_bounds(moneyness_values, target_moneyness)

    # Get the 4 corner volatilities
    vol_y1_m1 = _get_vol(data, y1, m1)
    vol_y1_m2 = _get_vol(data, y1, m2)
    vol_y2_m1 = _get_vol(data, y2, m1)
    vol_y2_m2 = _get_vol(data, y2, m2)

    # Interpolate along moneyness
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
    if target <= sorted_values[0]:
        return sorted_values[0], sorted_values[0]
    if target >= sorted_values[-1]:
        return sorted_values[-1], sorted_values[-1]

    for i in range(len(sorted_values) - 1):
        if sorted_values[i] <= target <= sorted_values[i + 1]:
            return sorted_values[i], sorted_values[i + 1]

    raise ValueError(f"Could not find bounds for target value {target}")


def _get_vol(data: List[List[float]], year_frac: float, moneyness: float) -> float:
    for row in data:
        if abs(row[1] - year_frac) < 1e-9 and abs(row[0] - moneyness) < 1e-9:
            return row[3]  # 4th column = volatility
    raise ValueError(f"Could not find vol for year_frac={year_frac}, moneyness={moneyness}")


def _linear_interp(x1: float, x2: float, y1: float, y2: float, x: float) -> float:
    if x2 == x1:
        return y1
    return y1 + (y2 - y1) * (x - x1) / (x2 - x1)
