from __future__ import annotations
from dataclasses import dataclass
from typing import List, Tuple
from datetime import date as pydate
import QuantLib as ql

def to_ql(d: pydate) -> ql.Date:
    return ql.Date(d.day, d.month, d.year)

def to_py(d: ql.Date) -> pydate:
    return pydate(d.year(), d.month(), d.dayOfMonth())

@dataclass
class CDSCashflowSchedule:
    """
    Quarterly schedule (no IMM):
    - Pay date = business-day adjusted accrual end.
    - Year fraction = (pay_date - start_display).days / 365.0  (ACT/365 pay-to-pay)
      *For the last period only*, add +1 day before dividing by 365.
    - Returned tuples: (start_display, pay_date, year_fraction)
      where start_display = previous row's pay_date; first row uses true start_date.
    """
    start_date: pydate
    end_date: pydate
    calendar: ql.Calendar = ql.TARGET()
    payment_convention: ql.BusinessDayConvention = ql.Following
    tenor: ql.Period = ql.Period(ql.Quarterly)

    def generate(self) -> List[Tuple[pydate, pydate, float]]:
        ql_start = to_ql(self.start_date)
        ql_end   = to_ql(self.end_date)

        # Unadjusted accrual boundaries
        sched = ql.Schedule(
            ql_start, ql_end, self.tenor, self.calendar,
            ql.Unadjusted, ql.Unadjusted, ql.DateGeneration.Forward, False
        )

        if len(sched) < 2:
            return []

        # Adjusted pay dates
        pay_dates = [to_py(self.calendar.adjust(sched[i], self.payment_convention))
                     for i in range(1, len(sched))]

        # Displayed starts: first = true start, then previous pay date
        starts = [to_py(sched[0])] + pay_dates[:-1]

        periods: List[Tuple[pydate, pydate, float]] = []
        last_idx = len(pay_dates) - 1
        for i, (s, p) in enumerate(zip(starts, pay_dates)):
            days = (p - s).days
            if i == last_idx:
                days += 1  # add one day for the final period only
            yf = days / 365.0
            periods.append((s, p, yf))

        return periods
