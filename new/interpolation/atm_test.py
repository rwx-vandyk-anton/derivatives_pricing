import numpy as np
import pandas as pd
from datetime import datetime
from pandas.tseries.holiday import USFederalHolidayCalendar


# ------------------------------------------------------------
# Business-day ACT/252 year fraction (U.S. holidays)
# ------------------------------------------------------------
def business_yearfrac_us(start_date, end_date):
    """
    Compute ACT/252 year fraction using U.S. business days and holidays.
    Works with modern pandas versions (≥2.0).
    """
    # Convert to datetime
    start_date = pd.Timestamp(start_date).to_pydatetime()
    end_date = pd.Timestamp(end_date).to_pydatetime()

    if end_date <= start_date:
        return 0.0

    # Generate US holiday list as Python datetimes
    cal = USFederalHolidayCalendar()
    holidays_index = cal.holidays(start=start_date, end=end_date)
    holidays = [h.to_pydatetime() for h in holidays_index]

    # Generate business days (excluding weekends and holidays)
    bdays = pd.bdate_range(start=start_date, end=end_date, holidays=holidays)

    # Number of business days between the two dates
    n_bdays = len(bdays) - 1  # exclude start date
    return n_bdays / 252.0


# ------------------------------------------------------------
# Linear-on-total-variance interpolation
# ------------------------------------------------------------
def interpolate_linear_on_variance(date1, vol1, date2, vol2, target_date, valuation_date=None):
    """
    Interpolates volatility linearly on total variance between two maturities.
    Uses ACT/252 (U.S. business-day) time convention.
    """
    # Normalize types
    date1 = pd.Timestamp(date1).to_pydatetime()
    date2 = pd.Timestamp(date2).to_pydatetime()
    target_date = pd.Timestamp(target_date).to_pydatetime()
    valuation_date = pd.Timestamp(valuation_date or min(date1, target_date)).to_pydatetime()

    # Year fractions
    t1 = business_yearfrac_us(valuation_date, date1)
    t2 = business_yearfrac_us(valuation_date, date2)
    t  = business_yearfrac_us(valuation_date, target_date)

    if t <= 0 or t2 <= t1:
        raise ValueError("Invalid or zero time intervals — check input dates.")

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
