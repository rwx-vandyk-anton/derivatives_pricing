import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from pandas.tseries.holiday import USFederalHolidayCalendar


def _us_business_days_between(start_date: datetime, end_date: datetime) -> int:
    """
    Count U.S. business days between start_date (exclusive) and end_date (inclusive).
    Weekends removed, and US Federal holidays removed.

    This is intentionally done with an explicit loop to avoid pandas
    truth-value / ambiguity issues.
    """
    # normalize inputs to plain python datetime
    start_date = pd.Timestamp(start_date).to_pydatetime()
    end_date = pd.Timestamp(end_date).to_pydatetime()

    if end_date <= start_date:
        return 0

    # build holiday set once for fast membership tests
    cal = USFederalHolidayCalendar()
    holidays_idx = cal.holidays(start=start_date, end=end_date)
    us_holidays = set(h.to_pydatetime().date() for h in holidays_idx)

    # walk forward one day at a time
    current = start_date + timedelta(days=1)
    count = 0
    while current <= end_date:
        is_weekday = current.weekday() < 5  # 0=Mon,...,4=Fri
        is_holiday = current.date() in us_holidays
        if is_weekday and not is_holiday:
            count += 1
        current += timedelta(days=1)

    return count


def business_yearfrac_us(start_date, end_date, trading_days_per_year: int = 252) -> float:
    """
    Compute ACT/252 style year fraction using U.S. business days.
    We count the number of business days between start_date and end_date,
    then divide by 252.

    Parameters
    ----------
    start_date : datetime-like
    end_date   : datetime-like
    trading_days_per_year : int
        Usually 252. Can be changed if your desk uses 253/255/etc.

    Returns
    -------
    float
        Year fraction in trading years.
    """
    start_date = pd.Timestamp(start_date).to_pydatetime()
    end_date   = pd.Timestamp(end_date).to_pydatetime()

    if end_date <= start_date:
        return 0.0

    n_bdays = _us_business_days_between(start_date, end_date)
    return n_bdays / float(trading_days_per_year)


def interpolate_linear_on_variance(date1,
                                   vol1,
                                   date2,
                                   vol2,
                                   target_date,
                                   valuation_date=None,
                                   trading_days_per_year: int = 252) -> float:
    """
    Interpolate annualized vol at target_date using linear-on-total-variance
    between (date1, vol1) and (date2, vol2). Time is measured in ACT/252
    U.S. business-day terms.

    Parameters
    ----------
    date1 : datetime-like
        First pillar expiry (earlier).
    vol1 : float
        Annualized implied vol at date1 (e.g. 0.20 = 20%).
    date2 : datetime-like
        Second pillar expiry (later).
    vol2 : float
        Annualized implied vol at date2 (e.g. 0.60 = 60%).
    target_date : datetime-like
        The date you want to interpolate to (must be between date1 and date2).
    valuation_date : datetime-like, optional
        Base date from which maturities are measured.
        If None, we default to the earliest of date1 and target_date.
    trading_days_per_year : int
        Denominator for ACT/252-style scaling (default 252).

    Returns
    -------
    float
        Interpolated annualized volatility at target_date.
    """
    # normalize inputs to python datetime
    d1 = pd.Timestamp(date1).to_pydatetime()
    d2 = pd.Timestamp(date2).to_pydatetime()
    dtgt = pd.Timestamp(target_date).to_pydatetime()

    if valuation_date is None:
        base = d1 if d1 <= dtgt else dtgt
    else:
        base = pd.Timestamp(valuation_date).to_pydatetime()

    # compute business-day year fractions
    t1 = business_yearfrac_us(base, d1, trading_days_per_year)
    t2 = business_yearfrac_us(base, d2, trading_days_per_year)
    tt = business_yearfrac_us(base, dtgt, trading_days_per_year)

    if tt <= 0.0:
        raise ValueError("Target time fraction is not positive. Check your dates.")
    if t2 <= t1:
        raise ValueError("date2 must be after date1 under this time basis.")
    if not (t1 <= tt <= t2):
        # Not strictly required mathematically, but good sanity
        raise ValueError("target_date must lie between date1 and date2 in time.")

    # total variances at the pillars
    w1 = (vol1 ** 2) * t1
    w2 = (vol2 ** 2) * t2

    # linear interpolation of total variance
    w_t = w1 + (w2 - w1) * (tt - t1) / (t2 - t1)

    # convert back to annualized vol at target maturity
    vol_t = np.sqrt(w_t / tt)
    return vol_t


# -----------------------------------------------------------------
# Example usage / sanity check
# -----------------------------------------------------------------
if __name__ == "__main__":
    d1 = datetime(2025, 1, 1)
    d2 = datetime(2026, 1, 1)
    target = datetime(2025, 7, 1)

    v1 = 0.20  # 20%
    v2 = 0.60  # 60%

    ans = interpolate_linear_on_variance(
        date1=d1,
        vol1=v1,
        date2=d2,
        vol2=v2,
        target_date=target,
        valuation_date=None,           # auto-choose base
        trading_days_per_year=252      # ACT/252 style
    )

    print(f"Interpolated vol on {target.date()}: {ans:.4%}")
