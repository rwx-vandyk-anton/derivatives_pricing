from discount.discount import YieldCurve
from zero_coupon.instruments.treasury_bill import TreasuryBill
import math as m


class TreasuryBillPricer:
    """
    Price T-bills via:
      - simple discount: P = Par*(1 - d·n/365)

            where:
                P = Price
                Par = Par value of 100
                d = T-Bill Discount rate
                n = days until maturity date

    Values T-bills via zero coupon bond formulae
      - formula: V = F * exp(-r * T)

            where:
                V = value of T-bill at value date
                F = Face value of T-bill (notional)
                r = Corresponding zero rate for time period
                T = Year fraction of period
    """

    def __init__(self, yield_curve: YieldCurve, t_bill: TreasuryBill):
        self.yield_curve = yield_curve
        self.contract = t_bill

    def price(self):
        discount_rate = self.contract.discount_rate
        t = (
            (self.contract.maturity_date - self.contract.value_date).days
            / self.contract.day_count
        )
        par = 100

        price = par * (1 - discount_rate * t)
        return price

    def value(self):
        face_value = self.contract.face_value
        t = (
            (self.contract.maturity_date - self.contract.value_date).days
            / self.contract.day_count
        )
        zero_rate = self.yield_curve.get_zero_rate(self.contract.maturity_date)

        value = face_value * m.exp(-zero_rate * t)
        return value

    def pv01(self) -> float:
        """
        Analytic PV01 = dV/dr = -T * V
        where T is year fraction (using the curve's day-count basis).
        """
        value = self.value()
        t = (
            (self.contract.maturity_date - self.contract.value_date).days
            / self.contract.day_count
        )
        pv01 = -t * value
        return pv01

    def print_details(self) -> None:
        """Pretty-print details and both prices + PV01."""
        bill = self.contract
        price = self.price()
        value = self.value()
        pv01 = self.pv01()

        print("Treasury Bill Details")
        print(f"  Face value:      {bill.face_value}")
        print(f"  Maturity date:   {bill.maturity_date}")
        print(f"  Valuation date:  {bill.value_date}")
        print(f"  Discount rate:   {bill.discount_rate:.6%}")
        print("-" * 50)
        print(f"Price:       {price:.6f}")
        print(f"Present Value:   {value:.6f}")
        print(f"PV01 (dV/dr):                  {pv01:.6f}")
