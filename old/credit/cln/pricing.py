from typing import Callable, Sequence
from datetime import date
from discount.discount import YieldCurve

def cln_price_dates(
    survival_func: Callable[[date], float],
    curve: YieldCurve,
    payment_dates: Sequence[date],
    year_fractions: Sequence[float],
    coupon: float,
    recovery: float,
    notional: float = 1.0
) -> float:
    """
    Prices a Credit-Linked Note (CLN) using calendar dates and YieldCurve.
    
    Assumes:
    - Default terminates future coupons and principal.
    - Upon default, a recovery % of notional is paid at the time of default.
    """
    # Expected coupon payments (while alive)
    pv_coupons = sum(
        coupon * delta * curve.get_discount_factor(d) * survival_func(d)
        for d, delta in zip(payment_dates, year_fractions)
    )

    # Expected principal repayment (survival to final date)
    final_date = payment_dates[-1]
    pv_principal = notional * curve.get_discount_factor(final_date) * survival_func(final_date)

    # Expected recovery upon default
    expected_loss = 0.0
    for i, d in enumerate(payment_dates):
        prev_date = payment_dates[i - 1] if i > 0 else curve.py_value_date
        expected_loss += curve.get_discount_factor(d) * (
            survival_func(prev_date) - survival_func(d)
        )
    pv_recovery = recovery * notional * expected_loss

    return notional * pv_coupons + pv_principal + pv_recovery
