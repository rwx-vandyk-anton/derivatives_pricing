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
    - Accrual start = exact start_date
    - Accrual end = unadjusted period end
    - Pay date = business-day adjusted accrual end (returned)
    - Returns tuples: (start_date, pay_date, year_fraction)
    """
    start_date: pydate
    end_date: pydate
    calendar: ql.Calendar = ql.TARGET()
    day_count: ql.DayCounter = ql.Actual360()
    payment_convention: ql.BusinessDayConvention = ql.Following
    tenor: ql.Period = ql.Period(ql.Quarterly)

    def generate(self) -> List[Tuple[pydate, pydate, float]]:
        ql_start = to_ql(self.start_date)
        ql_end   = to_ql(self.end_date)

        # Keep accrual boundaries unadjusted so first/last are exact
        schedule = ql.Schedule(
            ql_start,
            ql_end,
            self.tenor,
            self.calendar,
            ql.Unadjusted,              # accrual start boundary
            ql.Unadjusted,              # accrual end boundary
            ql.DateGeneration.Forward,
            False
        )

        periods: List[Tuple[pydate, pydate, float]] = []
        for i in range(1, len(schedule)):
            accrual_start = schedule[i - 1]
            accrual_end   = schedule[i]
            pay_date = self.calendar.adjust(accrual_end, self.payment_convention)
            yf = self.day_count.yearFraction(accrual_start, accrual_end)
            periods.append((to_py(accrual_start), to_py(pay_date), yf))
        return periods
