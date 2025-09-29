import os
import csv

import QuantLib as ql  # type: ignore
from zero_coupon.instruments.inflation_linked_bond import (
    InflationLinkedBond,
)


class InflationLinkedBondPricer:
    def __init__(self, instrument: InflationLinkedBond):
        self.instrument = instrument
        self.bond = self.instrument.bond
        self.index_ratio = self.instrument.index_ratio()

    def dirty_price(self) -> float:
        dirty_price = self.bond.dirtyPrice() * self.index_ratio
        return dirty_price

    def clean_price(self) -> float:
        clean_price = self.bond.cleanPrice() * self.index_ratio
        return clean_price

    def accrued_amount(self) -> float:
        accrued_amount = self.bond.accruedAmount() * self.index_ratio
        return accrued_amount

    def yield_to_maturity(self) -> float:
        # QuantLib’s YTM solver:
        ytm = self.bond.bondYield(
            self.clean_price(),        # clean price per 100
            self.instrument.real_yield_curve.day_count,
            ql.Compounded,
            self.instrument.ql_frequency
        )
        return ytm

    def print_details(self) -> None:
        dirty_price = self.dirty_price()
        clean_price = self.clean_price()
        accrued_int = self.accrued_amount()
        ytm = self.yield_to_maturity() * 100

        print("=" * 60)
        print("Inflation-Linked Bond (QuantLib) Details")
        print(f"  Issue date:     {self.instrument.issue_date}")
        print(f"  Settlement Date:{self.bond.settlementDate()}")
        print(f"  Maturity date:  {self.instrument.maturity_date}")
        print(f"  Notional:       {self.instrument.notional:,.0f}")
        print(f"  Coupon rate:    {self.instrument.coupon_rate:.4%}")
        print(f"  Frequency:      {self.instrument.freq_key}")
        print("-" * 60)
        print(f"Dirty price       : {dirty_price:,.6f}")
        print(f"Accrued amount    : {accrued_int:,.6f}")
        print(f"Clean price       : {clean_price:,.6f}")
        print(f"Yield to maturity : {ytm:.6f}%")
        print("-" * 60)
        print("Inflation-Linked Bond Cash flows:")
        for c in self.bond.cashflows():
            print('%20s %12f' % (c.date(), c.amount()))
        print("=" * 60)

        # export
        root = os.path.dirname(os.path.dirname(__file__))
        out = os.path.join(root, "results")
        os.makedirs(out, exist_ok=True)
        fn = f"ilb_{self.instrument.maturity_date}.csv"
        path = os.path.join(out, fn)
        rows = [
            ("Issue Date",        f"{self.instrument.issue_date}"),
            ("Settlement Date",   f"{self.bond.settlementDate()}"),
            ("Maturity Date",     f"{self.instrument.maturity_date}"),
            ("Notional",          f"{self.instrument.notional:,.2f}"),
            ("Frequency",         f"{self.instrument.freq_key}"),
            ("Coupon Rate",       f"{self.instrument.coupon_rate:.4%}"),
            ("Dirty price",       f"{dirty_price:.6f}"),
            ("Accrued amount",    f"{accrued_int:.6f}"),
            ("Clean price",       f"{clean_price:.6f}"),
            ("Yield to maturity", f"{ytm:.6f}%"),
        ]
        with open(path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerows(rows)
        print(f"Results exported to {path}")
