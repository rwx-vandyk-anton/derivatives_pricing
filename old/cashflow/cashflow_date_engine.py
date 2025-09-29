# cashflow/cashflow_date_engine.py

import QuantLib as ql
from datetime import date
from typing import List, Optional

def generate_cashflow_dates(
    start_date: date,
    end_date: date,
    tenor: ql.Period = ql.Period(3, ql.Months),
    calendar: ql.Calendar = ql.SouthAfrica(),
    convention: int = ql.Following,
    end_of_month: bool = True,
    first_roll_date: Optional[date] = None
) -> List[date]:
    """
    Generate cashflow dates between start_date and end_date, with an optional
    custom stub using `first_roll_date`.

    Parameters:
    -----------
    start_date : date
        The effective date of the first period.
    end_date : date
        The maturity or termination date.
    tenor : ql.Period
        Length of each regular period (default 3M).
    calendar : ql.Calendar
        Holiday calendar for rolling.
    convention : int
        Business‑day roll for each date (e.g. ql.Following, ql.Preceding).
    end_of_month : bool
        Apply end‑of‑month rule if True.
    first_roll_date : Optional[date]
        If provided, QL will create a stub from start_date→first_roll_date,
        then equal tenors thereafter.  If None, no custom stub is applied.

    Returns:
    --------
    List[date]
        All schedule dates (including start_date and end_date), as Python dates.
    """
    # 1) Python → QuantLib Date
    ql_start = ql.Date(start_date.day, start_date.month, start_date.year)
    ql_end   = ql.Date(end_date.day,   end_date.month,   end_date.year)

    # 2) Build the Schedule
    if first_roll_date:
        ql_first = ql.Date(
            first_roll_date.day,
            first_roll_date.month,
            first_roll_date.year
        )
        sched = ql.Schedule(
            ql_start,
            ql_end,
            tenor,
            calendar,
            convention,
            convention,
            ql.DateGeneration.Forward,
            end_of_month,
            ql_first
        )
    else:
        sched = ql.Schedule(
            ql_start,
            ql_end,
            tenor,
            calendar,
            convention,
            convention,
            ql.DateGeneration.Forward,
            end_of_month
        )

    # 3) QuantLib Date → Python date
    return [
        date(d.year(), d.month(), d.dayOfMonth())
        for d in sched
    ]
