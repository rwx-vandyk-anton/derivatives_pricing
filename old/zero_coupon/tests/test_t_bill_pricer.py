import unittest
from datetime import date
import math as m

from zero_coupon.instruments.treasury_bill import TreasuryBill
from discount.discount import YieldCurve
from zero_coupon.pricers.t_bill_pricer import TreasuryBillPricer


class TestTreasuryBillPricer(unittest.TestCase):
    def setUp(self):

        # ─── Build timeline ───────────────────────────────────────────────
        self.value_date = date(2025, 6, 19)
        self.maturity_date = date(2025, 9, 17)  # 90 days later
        self.maturities = [date(2025, 9, 17),
                           date(2025, 12, 17)]
        t = (self.maturity_date - self.value_date).days / 365

        # ─── Yield curve ─────────────────────────────────────────────────
        self.discount_rate = 0.05
        self.zero_rates = [-m.log(1 - self.discount_rate * t) / t,
                           0.03]
        self.yc = YieldCurve(self.zero_rates, self.maturities, self.value_date)

        # ─── Treasury Bill ──────────────────────────────────────────────
        self.face_value = 1000.0
        self.bill = TreasuryBill(
            self.face_value,
            self.discount_rate,
            self.maturity_date,
            self.value_date,
        )
        self.pricer = TreasuryBillPricer(self.yc, self.bill)

    def test_price_by_discount_yield(self):
        price = self.pricer.price()
        expected = 100 * (
            1 - self.discount_rate
            * (self.maturity_date - self.value_date).days / 365.0
        )

        print(f"\n T-Bill Price (per 100 nominal): {price:.6e}")

        self.assertAlmostEqual(price, expected, places=8)

    def test_present_value(self):
        value = self.pricer.value()
        r = self.zero_rates[0]
        T = (self.maturity_date - self.value_date).days / 365.0
        expected = self.face_value * m.exp(-r * T)

        print(f"\n T-Bill Value: {value:.6e}")

        self.assertAlmostEqual(value, expected, places=8)

    def test_pv01(self):
        pv01 = self.pricer.pv01()
        value = self.pricer.value()
        T = (self.maturity_date - self.value_date).days / self.yc.py_day_count
        expected = -value * T

        print(f"\n PV01: {pv01:.6e}")

        self.assertAlmostEqual(pv01, expected, places=8)


if __name__ == "__main__":
    unittest.main()
