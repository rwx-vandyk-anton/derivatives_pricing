import os
import csv

import QuantLib as ql  # type: ignore

from zero_coupon.instruments.fixed_rate_bond import FixedRateBond
from discount.discount import YieldCurve


class FixedRateBondPricer:
    """
    Wraps a QuantLib FixedRateBond, exposes dirty/clean price, YTM
    """
    def __init__(
        self,
        bond_def: FixedRateBond,
        yield_curve: YieldCurve,
    ):
        self.bond_def = bond_def
        self.yield_curve = yield_curve
        self.ql_fix_bond = bond_def.to_quantlib_bond(self.yield_curve)

    def dirty_price(self) -> float:
        return self.ql_fix_bond.dirtyPrice()

    def clean_price(self) -> float:
        return self.ql_fix_bond.cleanPrice()

    def accrued_amount(self) -> float:
        return self.ql_fix_bond.accruedAmount()

    def yield_to_maturity(self) -> float:
        # QuantLib’s YTM solver:
        ytm = self.ql_fix_bond.bondYield(
            self.clean_price(),        # clean price per 100
            self.yield_curve.day_count,
            ql.Compounded,
            self.bond_def.ql_frequency
        )
        return ytm

    def print_details(self) -> None:
        dirty_price = self.dirty_price()
        clean_price = self.clean_price()
        accrued_int = self.accrued_amount()
        ytm = self.yield_to_maturity() * 100

        print("=" * 60)
        print("Fixed-Rate Bond (QuantLib) Details")
        print(f"  Issue date:     {self.bond_def.issue_date}")
        print(f"  Maturity date:  {self.bond_def.maturity_date}")
        print(f"  Notional:       {self.bond_def.notional:,.0f}")
        print(f"  Coupon rate:    {self.bond_def.coupon_rate:.4%}")
        print(f"  Frequency:      {self.bond_def.ql_frequency}")
        print("-" * 60)
        print(f"Dirty price       : {dirty_price:,.6f}")
        print(f"Accrued amount    : {accrued_int:,.6f}")
        print(f"Clean price       : {clean_price:,.6f}")
        print(f"Yield to maturity : {ytm:.6f}%")
        print("-" * 60)
        print("Fixed Rate Bond Cash flows:")
        for c in self.ql_fix_bond.cashflows():
            print('%20s %12f' % (c.date(), c.amount()))
        print("=" * 60)

        # export
        root = os.path.dirname(os.path.dirname(__file__))
        out = os.path.join(root, "results")
        os.makedirs(out, exist_ok=True)
        fn = f"frb_{self.bond_def.maturity_date}.csv"
        path = os.path.join(out, fn)
        rows = [
            ("Dirty price",       f"{dirty_price:.6f}"),
            ("Accrued amount",    f"{accrued_int:.6f}"),
            ("Clean price",       f"{clean_price:.6f}"),
            ("Yield to maturity", f"{ytm:.6f}%"),
        ]
        with open(path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerows(rows)
        print(f"Results exported to {path}")
