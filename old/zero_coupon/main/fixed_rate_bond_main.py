from datetime import date

from discount.discount import YieldCurve
from zero_coupon.instruments.fixed_rate_bond import FixedRateBond
from zero_coupon.pricers.fixed_rate_bond_pricer import (
    FixedRateBondPricer,
)


def main():
    issue_date = date(2025, 6, 19)
    value_date = date(2025, 6, 24)
    zero_rates = [0.05, 0.06, 0.07, 0.08]
    mats = [
        date(2025, 12, 19),
        date(2026, 6, 19),
        date(2026, 12, 21),
        date(2027, 6, 21),
    ]
    yc = YieldCurve(zero_rates, mats, value_date)

    frb = FixedRateBond(
        notional=1_000_000,
        issue_date=issue_date,
        maturity_date=date(2027, 6, 19),
        coupon_rate=0.065,
        frequency="semi-annual",
    )
    pricer = FixedRateBondPricer(frb, yc)
    pricer.print_details()


if __name__ == "__main__":
    main()
