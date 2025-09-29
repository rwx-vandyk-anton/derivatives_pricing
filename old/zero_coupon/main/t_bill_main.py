from datetime import date

from discount.discount import YieldCurve
from zero_coupon.instruments.treasury_bill import TreasuryBill
from zero_coupon.pricers.t_bill_pricer import TreasuryBillPricer
import math as m


def main():
    val_date = date(2025, 6, 19)
    disc_rate = 0.05
    maturity = date(2026, 6, 19)
    t = (maturity - val_date).days / 365
    z_rates = -m.log(1 - disc_rate * t) / t

    yc = YieldCurve(z_rates, maturity, val_date)

    t_bill = TreasuryBill(
        face_value=1_000,
        discount_rate=disc_rate,
        maturity_date=maturity,
        value_date=val_date
    )
    pricer = TreasuryBillPricer(yc, t_bill)
    pricer.print_details()


if __name__ == "__main__":
    main()
