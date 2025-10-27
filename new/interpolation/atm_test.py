import numpy as np
import pandas as pd
from datetime import datetime
from pandas.tseries.holiday import USFederalHolidayCalendar


# ------------------------------------------------------------
# Business-day ACT/252 year fraction with U.S. holidays
# ------------------------------------------------------------
def business_yearfrac_us(start_date, end_date):
    """
    Compute ACT/252 year fraction using U.S. business days and holidays.
    Works for datetime, pandas.Timestamp, or numpy.datetime64.
    """
    # Ensure pure datetime type
    start_date = pd.Timestamp(start_date).to_pydatetime()
    end_date = pd.Timestamp(end_date).to_pydatetime()

    # U.S. holiday calendar
    cal = USFederalHolidayCalendar()
    holidays = cal.holidays(start=start_date, end=end_date)

    # Generate business days excluding weekends + holidays
    bdays = pd.bdate_range(start=start_date, end=end_date, holidays=holidays)

    # Number of business days (exclude start)
    n_bdays = max(len(bdays) - 1, 0)
    return n_bdays / 252.0


# ------------------------------------------------------------
# Linear-on-total-variance interpolation
# ------------------------------------------------------------
def interpolate_linear_on_variance(date1, vol1, date2, vol2, target_date, valuation_date=None):
    """
    Interpolates volatility (annualized) linearly on total variance between two maturities.
    Uses ACT/252 (U.S. business-day) time convention.
    """
    # Ensure datetime types
    date1 = pd.Timestamp(date1).to_pydatetime()
    date2 = pd.Timestamp(date2).to_pydatetime()
    target_date = pd.Timestamp(target_date).to_pydatetime()

    if valuation_date is None:
        # pick earliest between date1 and target_date as base
        valuation_date = date1 if date1 < target_date else target_date
    else:
        valuation_date = pd.Timestamp(valuation_date).to_pydatetime()

    # Compute year fractions
    t1 = business_yearfrac_us(valuation_date, date1)
    t2 = business_yearfrac_us(valuation_date, date2)
    t  = business_yearfrac_us(valuation_date, target_date)

    if t <= 0 or t2 == t1:
        raise ValueError("Invalid time fractions — check your input dates.")

    # Linear interpolation on total variance
    w1 = vol1**2 * t1
    w2 = vol2**2 * t2
    w_t = w1 + (w2 - w1) * (t - t1) / (t2 - t1)

    # Convert back to annualized volatility
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
