from datetime import date

from discount.discount import YieldCurve
from zero_coupon.instruments.floating_rate_note import FloatingRateNote
from zero_coupon.pricers.floating_rate_note_pricer import (
    FloatingRateNotePricer,
)


def main():
    today = date(2025, 6, 25)
    issue_date = date(2020, 6, 19)
    last_reset_date = date(2025, 6, 19)
    next_coupon_date = date(2025, 9, 19)
    maturity = date(2026, 6, 19)

    zero_rates = [0.0350, 0.0375, 0.0390, 0.0400]
    mats = [
        date(2025, 9, 19),
        date(2025, 12, 19),
        date(2026, 3, 19),
        maturity,
    ]
    yc = YieldCurve(zero_rates, mats, today)

    frn = FloatingRateNote(
        notional=100_000.0,
        issue_date=issue_date,
        settlement_date=today,
        maturity_date=maturity,
        next_coupon_date=next_coupon_date,
        last_reset_date=last_reset_date,
        last_reset_rate=0.0350,
        issue_spread=0.0025,
        frequency="quarterly"
    )

    pricer = FloatingRateNotePricer(frn, yc, 0.0040)
    pricer.print_details()


if __name__ == "__main__":
    main()
