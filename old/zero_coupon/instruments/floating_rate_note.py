from datetime import date

import QuantLib as ql  # type: ignore
from discount.discount import YieldCurve


class FloatingRateNote:
    """
    Floating rate note (FRN) instrument definition.
    frequency: "monthly", "quarterly", "semi-annual", or "annual"
    """

    _FREQ_TO_MONTHS = {
        "monthly": 1,
        "quarterly": 3,
        "semi-annual": 6,
        "semiannual": 6,
        "annual": 12,
    }

    def __init__(
        self,
        notional: float,
        issue_date: date,
        settlement_date: date,
        next_coupon_date: date,
        maturity_date: date,
        last_reset_date: date,
        last_reset_rate: float,
        issue_spread: float,
        frequency: str = "quarterly",
        calendar: ql.Calendar = ql.SouthAfrica(),
    ):
        freq_key = frequency.strip().lower()
        if freq_key not in self._FREQ_TO_MONTHS:
            raise ValueError(
                f"Unsupported frequency '{frequency}'. "
                f"Choose from {list(self._FREQ_TO_MONTHS)}"
            )
        self.issue_date = issue_date
        self.notional = notional
        self.settlement_date = settlement_date
        self.next_coupon_date = next_coupon_date
        self.maturity_date = maturity_date
        self.last_reset_date = last_reset_date
        self.last_reset_rate = last_reset_rate
        self.issue_spread = issue_spread
        self.frequency_str = freq_key
        self.freq_months = self._FREQ_TO_MONTHS[freq_key]
        self.calendar = calendar

    def to_quantlib_bond(
        self,
        yield_curve: YieldCurve,
        discount_curve: ql.YieldTermStructureHandle
    ) -> ql.FloatingRateBond:
        # 1) set evaluation date
        ql_settle_date = ql.Date(
            self.settlement_date.day,
            self.settlement_date.month,
            self.settlement_date.year,
        )
        ql.Settings.instance().evaluationDate = ql_settle_date

        # Build Curve handle
        forward_handle = yield_curve.discount_curve

        # Build the IborIndex dynamically from freq_months
        tenor_periods = ql.Period(self.freq_months, ql.Months)
        index_name = f"{self.freq_months}mJibar"
        index = ql.IborIndex(
            index_name,
            tenor_periods,
            2,
            ql.ZARCurrency(),
            self.calendar,
            ql.ModifiedFollowing,
            False,
            yield_curve.day_count,
            forward_handle,
        )

        # Register the last reset fixing date and rate
        fix_date = index.fixingDate(ql_settle_date)
        index.addFixing(fix_date, self.last_reset_rate)

        # Build schedule with the same tenor frequency
        ql_maturity_date = ql.Date(
            self.maturity_date.day,
            self.maturity_date.month,
            self.maturity_date.year,
        )

        ql_first_coupon = ql.Date(
            self.next_coupon_date.day,
            self.next_coupon_date.month,
            self.next_coupon_date.year,
        )

        ql_issue_date = ql.Date(
            self.issue_date.day,
            self.issue_date.month,
            self.issue_date.year,
        )
        schedule = ql.Schedule(
            ql_settle_date,
            ql_maturity_date,
            tenor_periods,
            self.calendar,
            ql.ModifiedFollowing,
            ql.ModifiedFollowing,
            ql.DateGeneration.Forward,
            False,
            ql_first_coupon,
        )

        # Create the FloatingRateBond
        bond = ql.FloatingRateBond(
            settlementDays=0,
            faceAmount=100.0,  # face amount per unit
            schedule=schedule,
            index=index,
            paymentDayCounter=yield_curve.day_count,
            paymentConvention=ql.ModifiedFollowing,
            fixingDays=2,
            gearings=[1.0],
            spreads=[self.issue_spread],
            inArrears=False,
            redemption=100.0,         # redemption value at maturity
            issueDate=ql_issue_date,
            exCouponPeriod=ql.Period(10, ql.Days),  # exCouponPeriod
            exCouponCalendar=self.calendar,          # exCouponCalendar
            exCouponConvention=ql.ModifiedFollowing,  # exCouponConvention
            exCouponEndOfMonth=False,               # exCouponEndOfMonth
        )

        # Attach pricing engine
        bond.setPricingEngine(ql.DiscountingBondEngine(discount_curve))
        return bond

    def cashflow_dates_and_amounts(self, ql_bond: ql.FloatingRateBond):
        """
        Return a list of (python_date, amount) for each cash flow.
        """
        ql_cfs = [cf for cf in ql_bond.cashflows() if cf.amount() != 0.0]
        out = []
        # handle all but the last two separately
        for cf in ql_cfs[:-2]:
            d = cf.date()
            out.append(
                (date(d.year(), d.month(), d.dayOfMonth()), cf.amount())
            )

        # now combine the penultimate coupon + redemption
        last_coupon = ql_cfs[-2]
        redemption = ql_cfs[-1]
        d = last_coupon.date()  # same as redemption.date()
        total = last_coupon.amount() + redemption.amount()
        out.append((date(d.year(), d.month(), d.dayOfMonth()), total))

        return out
