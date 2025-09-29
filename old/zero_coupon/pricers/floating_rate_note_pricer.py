import os
import csv
from zero_coupon.instruments.floating_rate_note import FloatingRateNote
from discount.discount import YieldCurve


class FloatingRateNotePricer:
    """
    Wraps QuantLib FloatingRateBond pricing and solves for
    the discount margin (z-spread) that makes clean price = 100.
    """

    def __init__(
        self,
        frn: FloatingRateNote,
        yield_curve: YieldCurve,
        market_spread=None,
    ):
        self.frn = frn
        self.yield_curve = yield_curve
        self.market_spread = (
            frn.issue_spread if market_spread is None else market_spread
        )
        self.ql_frn_bond = self.frn.to_quantlib_bond(
            yield_curve=self.yield_curve,
            discount_curve=self.yield_curve.discount_curve
        )

    def _discount_factors(self) -> list[float]:
        """
        Build simple-annual discount factors for each cash flow date
        inclusive of market spread.
        """
        cash_flow_list = self.frn.cashflow_dates_and_amounts(self.ql_frn_bond)
        settle_date = self.frn.settlement_date

        cashflow_dates = [settle_date] + [date[0] for date in cash_flow_list]

        discount_factors = []
        prev_discount_factor = 1.0  # start with 100% at settlement date
        for i in range(1, len(cashflow_dates)):
            start = cashflow_dates[i - 1]
            end = cashflow_dates[i]

            days = (end - start).days
            tau = days / self.yield_curve.py_day_count

            if start == self.frn.settlement_date:
                r = self.frn.last_reset_rate
            else:
                r = self.yield_curve.forward_rate(
                    start,
                    end
                )
            rate = r + self.market_spread

            discount_factor = prev_discount_factor / (1 + rate * tau)
            discount_factors.append(discount_factor)
            prev_discount_factor = discount_factor

        return discount_factors

    def dirty_price(self) -> float:
        """Manual calculation of dirty price (NPV) using cash flows."""
        cash_flow_list = self.frn.cashflow_dates_and_amounts(self.ql_frn_bond)

        cash_flows = [date[1] for date in cash_flow_list]
        discount_factors = self._discount_factors()

        # Calculate NPV as sum of cash flows times discount factors
        npv = sum(cf * df for cf, df in zip(cash_flows, discount_factors))
        return npv

    def clean_price(self) -> float:
        """Manual calculation of clean price."""
        dirty_price = self.dirty_price()
        accrued_interest = self.accrued_amount()
        clean_price = dirty_price - accrued_interest
        return clean_price

    def accrued_amount(self) -> float:
        """QuantLib accrued interest from last coupon to settlement."""
        return self.ql_frn_bond.accruedAmount()

    def print_details(self) -> None:
        dirty_price = self.dirty_price()
        dirty_price_nom = (dirty_price / 100) * self.frn.notional

        clean_price = self.clean_price()
        clean_price_nom = (clean_price / 100) * self.frn.notional

        accrued_interest = self.accrued_amount()
        accrued_interest_nom = (accrued_interest / 100) * self.frn.notional

        market_spread = self.market_spread * 100  # convert to percentage

        print("=" * 60)
        print("Floating Rate Note (QuantLib) Pricing")
        print(f"  Notional         : {self.frn.notional:,.2f}")
        print(f"  Settlement date  : {self.frn.settlement_date}")
        print(f"  Maturity date    : {self.frn.maturity_date}")
        print(f"  Last reset date  : {self.frn.last_reset_date}")
        print(f"  Last reset rate  : {self.frn.last_reset_rate:.4%}")
        print(f"  Frequency        : {self.frn.frequency_str.title()}")
        print(f"  Issue spread (IS): {self.frn.issue_spread:.4%}")
        print("-" * 60)
        print(f"Dirty price             : {dirty_price:,.6f}")
        print(f"Dirty price (Nominal)   : {dirty_price_nom:,.6f}")
        print(f"Clean price             : {clean_price:,.6f}")
        print(f"Clean price (Nominal)   : {clean_price_nom:,.6f}")
        print(f"Accrued amount          : {accrued_interest:,.6f}")
        print(f"Accrued amount (Nominal): {accrued_interest_nom:,.6f}")
        print(f"Market spread (MS)      : {market_spread:.4f}%")
        print("-" * 60)
        print("Floating Rate Note Cash flows")
        for c in self.ql_frn_bond.cashflows():
            print('%20s %12f' % (c.date(), c.amount()))
        print("=" * 60)

        # export to CSV
        root = os.path.dirname(os.path.dirname(__file__))
        outdir = os.path.join(root, "results")
        os.makedirs(outdir, exist_ok=True)
        fname = f"frn_{self.frn.maturity_date}.csv"
        path = os.path.join(outdir, fname)

        rows = [
            ("Notional",                 f"{self.frn.notional:,.2f}"),
            ("Settlement date",          self.frn.settlement_date),
            ("Maturity date",            self.frn.maturity_date),
            ("Frequency",                self.frn.frequency_str),
            ("Last reset date",          self.frn.last_reset_date),
            ("Last reset rate",          f"{self.frn.last_reset_rate:.4%}"),
            ("Issue spread",             f"{self.frn.issue_spread:.4%}"),
            ("Dirty price",              f"{dirty_price:.6f}"),
            ("Dirty price (Nominal)",    f"{dirty_price_nom:.6f}"),
            ("Clean price",              f"{clean_price:.6f}"),
            ("Clean price (Nominal)",    f"{clean_price_nom:.6f}"),
            ("Accrued amount",           f"{accrued_interest:.6f}"),
            ("Accrued amount (Nominal)", f"{accrued_interest_nom:.6f}"),
            ("Market spread",            f"{market_spread:.4f}%"),
        ]
        with open(path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerows(rows)

        print(f"Results exported to {path}")
