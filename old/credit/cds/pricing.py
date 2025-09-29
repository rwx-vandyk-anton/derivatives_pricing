# credit/cds/pricing.py

from datetime import date
import numpy as np
from typing import Sequence, List, Tuple
from discount.discount import YieldCurve
from credit.hazard_rate_model.model import HazardRateModel


def protection_leg_pv_forward(
    hazard_model: HazardRateModel,
    curve: YieldCurve,
    payment_dates: Sequence[date],
    recovery: float,
    notional: float = 1.0,
    valuation_date: date = None,
) -> float:
    """
    Default (protection) leg PV:
      Sum over each payment interval of the default probability times discount.
    Assumes `payment_dates` starts at or before valuation_date and ends at
    maturity.
    """
    if valuation_date is None:
        valuation_date = curve.py_value_date

    # Rebase survival & discount
    day_basis = curve.py_day_count
    t0 = (valuation_date - curve.py_value_date).days / day_basis
    S_prev = hazard_model.survival_probability(t0)
    D0     = curve.get_discount_factor(valuation_date)

    pv = 0.0
    # start at the first future date
    for dt in payment_dates:
        if dt <= valuation_date:
            continue
        # time from value_date
        t = (dt - curve.py_value_date).days / day_basis
        S = hazard_model.survival_probability(t)    # S(t)
        D = curve.get_discount_factor(dt) / D0       # discount conditional

        # default prob over [prev, t] = S_prev - S
        dp = S_prev - S
        pv += dp * D
        S_prev = S

    return (1 - recovery) * notional * pv


def premium_leg_pv_forward(
    hazard_model: HazardRateModel,
    curve: YieldCurve,
    payment_dates: List[date],
    year_fractions: List[float],
    spread: float,
    notional: float = 1.0,
    valuation_date: date = None,
) -> float:
    """
    Premium (fee) leg PV:
      Σ_j [ spread * Δ_j * D(t_j) * S(t_j) ]
    where t_j ∈ payment_dates after valuation_date.
    """
    if valuation_date is None:
        valuation_date = curve.py_value_date

    day_basis = curve.py_day_count
    t0 = (valuation_date - curve.py_value_date).days / day_basis
    S0 = hazard_model.survival_probability(t0)
    D0 = curve.get_discount_factor(valuation_date)

    pv = 0.0
    # scheduled coupons
    for dt, Δ in zip(payment_dates[1:], year_fractions):
        if dt <= valuation_date:
            continue
        t = (dt - curve.py_value_date).days / day_basis
        S = hazard_model.survival_probability(t) / S0
        D = curve.get_discount_factor(dt) / D0
        pv += spread * Δ * S * D

    return notional * pv


def cds_pv_forward(
    hazard_model: HazardRateModel,
    curve: YieldCurve,
    payment_dates: Sequence[date],
    year_fractions: Sequence[float],
    spread: float,
    recovery: float,
    notional: float = 1.0,
    valuation_date: date = None,
) -> float:
    """
    Net CDS PV = premium_leg - protection_leg
    """
    prot = protection_leg_pv_forward(
        hazard_model, curve, payment_dates,
        recovery, notional, valuation_date
    )
    prem = premium_leg_pv_forward(
        hazard_model, curve, list(payment_dates),
        list(year_fractions), spread, notional, valuation_date
    )
    return prem - prot


def cds_sensitivities_forward(
    hazard_model: HazardRateModel,
    curve: YieldCurve,
    payment_dates: Sequence[date],
    year_fractions: Sequence[float],
    spread: float,
    recovery: float,
    notional: float = 1.0,
    valuation_date: date = None
) -> dict:
    """
    PV01 and spread sensitivity by bumping spread by 1bp.
    """
    bump = 1e-4
    pv   = cds_pv_forward(
        hazard_model, curve, payment_dates, year_fractions,
        spread, recovery, notional, valuation_date
    )
    pv_bumped = cds_pv_forward(
        hazard_model, curve, payment_dates, year_fractions,
        spread + bump, recovery, notional, valuation_date
    )
    sens = pv_bumped - pv
    return {"pv": pv, "pv01": sens, "spread_sensitivity": sens}


def premium_leg_cashflow_pvs(
    hazard_model: HazardRateModel,
    curve: YieldCurve,
    payment_dates: Sequence[date],
    year_fractions: Sequence[float],
    spread: float,
    notional: float = 1.0,
    valuation_date: date = None
) -> List[Tuple[date, float, float]]:
    """
    Returns (date, cashflow, PV) for each scheduled coupon after valuation_date,
    including accrual‐on‐default via a 0.5*marginal_PD uplift to survival.
    """
    if valuation_date is None:
        valuation_date = curve.py_value_date

    day_basis = curve.py_day_count
    # survival & discount rebasing
    t0 = (valuation_date - curve.py_value_date).days / day_basis
    S0 = hazard_model.survival_probability(t0)
    D0 = curve.get_discount_factor(valuation_date)

    cf_list: List[Tuple[date, float, float]] = []
    prev_S = 1.0  # survival immediately after valuation_date

    for dt, Δ in zip(payment_dates[1:], year_fractions):
        if dt <= valuation_date:
            continue

        # coupon amount
        cf_amt = notional * spread * Δ

        # time in years since curve.value_date
        t = (dt - curve.py_value_date).days / 360

        # conditional survival at dt
        S = hazard_model.survival_probability(t) / S0

        # marginal default probability over (prev, dt)
        marginal_pd = prev_S - S


        # bump survival by half the marginal PD
        S_adj = S + 0.5 * marginal_pd

        # conditional discount factor
        D = curve.get_discount_factor(dt) / D0

        # price = coupon * adjusted survival * discount
        cf_pv = cf_amt * S_adj * D

        cf_list.append((dt, cf_amt, cf_pv))

        # update for next interval
        prev_S = S

    return cf_list