from typing import Sequence, Callable
from datetime import date
from discount.discount import YieldCurve

def year_fraction(start: date, end: date, py_day_count: float) -> float:
    return (end - start).days / py_day_count


def basket_premium_leg_pv(
    survival_funcs: Sequence[Callable[[float], float]],  # sequence of all different hazard rate functions
    yield_curve: YieldCurve,  # global discount engine
    payment_dates: Sequence[date],  # Fixed for all counterparties
    valuation_date: date,
    spread: float,  # Input parameter, but in spread pricing it is static to 1
    notional: float = 1.0,  # Doesn’t affect spread, only PVs
    weights: Sequence[float] = None  # assumed equal if not defined
) -> float:  # returns the premium leg PV
    """
    Premium leg of a linear credit basket: sum of expected coupons across all names
    """
    n = len(survival_funcs)  # number of assets in the basket
    if weights is None:
        weights = [1.0 / n] * n  # default to equally weighted

    py_day_count = yield_curve.py_day_count

    # compute t values and year fractions
    t_vals = [year_fraction(valuation_date, d, py_day_count) for d in payment_dates]
    year_fractions = [
        year_fraction(payment_dates[i - 1], d, py_day_count) if i > 0
        else year_fraction(valuation_date, d, py_day_count)
        for i, d in enumerate(payment_dates)
    ]

    total_pv = 0.0
    for w, S in zip(weights, survival_funcs):
        pv_sched = sum(
            spread * delta * yield_curve.get_discount_factor(d) * S(t)
            for d, t, delta in zip(payment_dates, t_vals, year_fractions)
        )
        # spread is what we are solving for, delta is just the year fraction
        # essentially PV'ing all premiums of the instrument

        # this next line does accrual in between premium dates, assumes uniform survival during the period,
        # i.e., default occurs halfway through the two dates.
        accrual = sum(
            0.5 * delta * yield_curve.get_discount_factor(d) *
            (S(t_vals[i - 1]) if i > 0 else 1.0 - S(t))
            for i, (d, t, delta) in enumerate(zip(payment_dates, t_vals, year_fractions))
        )

        # Total PV for basket premium leg is weighted, the accrual is also added to the general premium leg
        total_pv += w * (pv_sched + spread * accrual) * notional

    return total_pv


def basket_protection_leg_pv(
    survival_funcs: Sequence[Callable[[float], float]],
    yield_curve: YieldCurve,  # global discount engine
    payment_dates: Sequence[date],
    valuation_date: date,
    recovery_rates: Sequence[float],
    notional: float = 1.0,
    weights: Sequence[float] = None
) -> float:
    """
    Protection leg of a linear basket: sum of expected losses across all names
    """
    n = len(survival_funcs)
    if weights is None:
        weights = [1.0 / n] * n

    py_day_count = yield_curve.py_day_count
    t_vals = [year_fraction(valuation_date, d, py_day_count) for d in payment_dates]

    total_pv = 0.0
    for w, S, rec in zip(weights, survival_funcs, recovery_rates):
        prev_S = S(0.0)  # initialise, should be = 1
        leg = 0.0
        for t, d in zip(t_vals, payment_dates):
            S_t = S(t)  # define the survival function
            # discount the probability of default at a particular time
            leg += yield_curve.get_discount_factor(d) * (prev_S - S_t)
            prev_S = S_t
        # Sum all exposures in the basket
        total_pv += w * (1.0 - rec) * leg * notional

    return total_pv


def fair_basket_cds_spread(
    # Calculates the fair basket spread
    survival_funcs: Sequence[Callable[[float], float]],
    yield_curve: YieldCurve,
    payment_dates: Sequence[date],
    valuation_date: date,
    recovery_rates: Sequence[float],
    notional: float = 1.0,
    weights: Sequence[float] = None
) -> float:
    """
    Computes fair spread such that PV_premium = PV_protection across the basket
    """
    # calculate protection leg pv
    prot_pv = basket_protection_leg_pv(
        survival_funcs, yield_curve, payment_dates,
        valuation_date, recovery_rates, notional, weights
    )

    # spread cancels in denominator of premium leg
    denom = basket_premium_leg_pv(
        survival_funcs, yield_curve, payment_dates,
        valuation_date, spread=1.0,  # input single unit into spread as we are calculating for this spread
        notional=notional, weights=weights
    )

    # protection divided by premium leg gives you the premium
    return prot_pv / denom
