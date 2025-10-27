import pandas as pd
import numpy as np
from datetime import datetime

# ------------------------------------------------------------
#  Business-day year fraction calculator (ACT/252)
#  using U.S. business days and holidays
# ------------------------------------------------------------
def business_yearfrac_us(start_date: datetime, end_date: datetime) -> float:
    """
    Compute ACT/252 year fraction using U.S. business days and holidays.

    Parameters
    ----------
    start_date : datetime
        Valuation or start date.
    end_date : datetime
        Expiry or target date.

    Returns
    -------
    float
        Year fraction (business days / 252).
    """
    # US holiday calendar
    us_cal = pd.tseries.holiday.USFederalHolidayCalendar()
    holidays = us_cal.holidays(start=start_date, end=end_date)
    
    # Generate all business days between start and end
    bdays = pd.bdate_range(start=start_date, end=end_date, holidays=holidays)
    n_bdays = len(bdays) - 1 if len(bdays) > 0 else 0  # exclude start date
    
    return n_bdays / 252.0


# ------------------------------------------------------------
#  Linear-on-total-variance interpolation
# ------------------------------------------------------------
def interpolate_linear_on_variance(date1, vol1, date2, vol2, target_date, valuation_date=None):
    """
    Interpolate volatility (or rate) linearly on total variance between two expiries.

    Parameters
    ----------
    date1 : datetime
        First expiry date (earlier).
    vol1 : float
        Annualized vol/rate at date1 (e.g. 0.20 for 20%).
    date2 : datetime
        Second expiry date (later).
    vol2 : float
        Annualized vol/rate at date2 (e.g. 0.60 for 60%).
    target_date : datetime
        Intermediate date to interpolate for.
    valuation_date : datetime, optional
        Base date to measure year fractions from. Defaults to min(date1, target_date).

    Returns
    -------
    float
        Interpolated annualized volatility.
    """
    if valuation_date is None:
        valuation_date = min(date1, target_date)

    # Compute year fractions using business days (ACT/252)
    t1 = business_yearfrac_us(valuation_date, date1)
    t2 = business_yearfrac_us(valuation_date, date2)
    t  = business_yearfrac_us(valuation_date, target_date)

    # Total variances
    w1 = vol1**2 * t1
    w2 = vol2**2 * t2

    # Linear interpolation on total variance
    w_t = w1 + (w2 - w1) * (t - t1) / (t2 - t1)

    # Convert back to annualized vol
    vol_t = np.sqrt(w_t / t)

    return vol_t


# ------------------------------------------------------------
# Example usage
# ------------------------------------------------------------
if __name__ == "__main__":
    d1 = datetime(2026, 1, 28)
    d2 = datetime(2026, 4, 28)
    target = datetime(2025, 2, 17)

    v1 = 0.116275  # 20%
    v2 = 0.120725 # 60%

    interpolated = interpolate_linear_on_variance(d1, v1, d2, v2, target)
    print(f"Interpolated vol on {target.date()}: {interpolated:.4%}")
