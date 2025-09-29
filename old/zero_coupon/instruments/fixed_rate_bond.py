from datetime import date

import QuantLib as ql  # type: ignore

from discount.discount import YieldCurve


class FixedRateBond:
    """
    Fixed-rate bond instrument using QuantLib.
    All vanilla bonds here pay semi-annual coupons by default.
    """

    def __init__(
        self,
        notional: float,
        issue_date: date,
        maturity_date: date,
        coupon_rate: float,
        frequency: str = "semi-annual",
        calendar: ql.Calendar = ql.SouthAfrica(),
        day_counter: ql.DayCounter = ql.Actual365Fixed(),
    ):
        # Map frequency of payment periods
        freq_map = {
            "annual":   (ql.Annual,   ql.Period(1, ql.Years)),
            "semi-annual": (ql.Semiannual, ql.Period(6, ql.Months)),
            "quarterly": (ql.Quarterly, ql.Period(3, ql.Months)),
            "monthly":  (ql.Monthly,  ql.Period(1, ql.Months)),
        }
        freq_key = frequency.lower()
        if freq_key not in freq_map:
            raise ValueError(f"Unsupported frequency '{frequency}'")
        self.ql_frequency, self.ql_tenor = freq_map[freq_key]

        # Build payment schedule
        self.issue_date = ql.Date(
            issue_date.day,
            issue_date.month,
            issue_date.year
        )
        self.maturity_date = ql.Date(
            maturity_date.day,
            maturity_date.month,
            maturity_date.year
        )
        self.calendar = calendar
        self.schedule = ql.Schedule(
            self.issue_date,
            self.maturity_date,
            self.ql_tenor,
            calendar,
            ql.ModifiedFollowing,
            ql.ModifiedFollowing,
            ql.DateGeneration.Backward,
            False,
        )

        # store plain-vanilla inputs
        self.notional = notional
        self.coupon_rate = coupon_rate
        self.day_counter = day_counter

    def to_quantlib_bond(self, yield_curve: YieldCurve) -> ql.FixedRateBond:
        """
        Create a QuantLib FixedRateBond, attach a DiscountingBondEngine from
        existing YieldCurve.discount_curve handle, and return it.
        """
        bond = ql.FixedRateBond(
            0,                        # settlementDays
            100,                      # faceAmount
            self.schedule,            # schedule
            [self.coupon_rate],       # coupons
            self.day_counter,         # dayCounter (accrual)
            ql.ModifiedFollowing,     # paymentConvention
            100.0,                    # redemption
            self.issue_date,          # issueDate
            self.calendar,            # paymentCalendar
            ql.Period(10, ql.Days),   # exCouponPeriod
            self.calendar,            # exCouponCalendar
            ql.ModifiedFollowing,     # exCouponConvention
            False                      # exCouponEndOfMonth
        )
        engine = ql.DiscountingBondEngine(yield_curve.discount_curve)
        bond.setPricingEngine(engine)
        return bond
