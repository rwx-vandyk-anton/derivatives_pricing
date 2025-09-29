from datetime import date
import numpy as np
from typing import Sequence, List, Tuple
from discount.discount import YieldCurve
from credit.hazard_rate_model.survival_model import SurvivalCurveModel
import QuantLib as ql


def _build_eval_grid(
    survival_model: SurvivalCurveModel,
    curve: YieldCurve,
    valuation_date: date,
    final_maturity: date
) -> List[date]:
    """
    Build a monthly evaluation grid from valuation_date to final_maturity, inclusive.
    """
    # use curve.calendar if available, else default
    calendar = getattr(curve, "calendar", ql.SouthAfrica())
    ql_start = ql.Date(valuation_date.day, valuation_date.month, valuation_date.year)
    ql_end   = ql.Date(final_maturity.day, final_maturity.month, final_maturity.year)

    # Generate a monthly schedule (1‑month tenor)
    ql_schedule = ql.Schedule(
        ql_start,
        ql_end,
        ql.Period(1, ql.Months),
        calendar,
        ql.Following,
        ql.Following,
        ql.DateGeneration.Forward,
        False
    )

    # Convert to Python dates and ensure final date is included
    grid = [date(d.year(), d.month(), d.dayOfMonth()) for d in ql_schedule]
    if grid[-1] != final_maturity:
        grid.append(final_maturity)

    return sorted(set(grid))


def protection_leg_pv_forward(
    survival_model: SurvivalCurveModel,
    curve: YieldCurve,
    recovery: float,
    maturity_date: date,
    notional: float = 1.0,
    valuation_date: date = None,
) -> float:
    if valuation_date is None:
        valuation_date = curve.py_value_date

    grid = _build_eval_grid(survival_model, curve, valuation_date, maturity_date)

    pv_prot = 0.0
    for t_i, t_im1 in zip(grid[1:], grid[:-1]):
        df = curve.get_discount_factor(t_i)

        # convert to year fractions
        t_i_y   = (t_i   - curve.py_value_date).days / curve.py_day_count
        t_im1_y = (t_im1 - curve.py_value_date).days / curve.py_day_count

        # survival probabilities
        S_i   = survival_model.survival_probability(t_i_y)
        S_im1 = survival_model.survival_probability(t_im1_y)

        # default probability in (t_im1, t_i)
        dp = S_im1 - S_i

        pv_prot += df * (1 - recovery) * notional * dp

    return pv_prot


def premium_leg_pv_forward(
    survival_model: SurvivalCurveModel,
    curve: YieldCurve,
    payment_dates: List[date],
    year_fractions: List[float],
    spread: float,
    maturity_date: date,
    notional: float = 1.0,
    valuation_date: date = None,
) -> float:
    if valuation_date is None:
        valuation_date = curve.py_value_date

    pv_fee = 0.0
    for s_j, s_jm1, Δ_j in zip(
        payment_dates[1:], payment_dates[:-1], year_fractions
    ):
        if s_j <= valuation_date:
            continue

        df = curve.get_discount_factor(s_j)

        t_j   = (s_j   - curve.py_value_date).days / curve.py_day_count
        t_jm1 = (s_jm1 - curve.py_value_date).days / curve.py_day_count

        S_j   = survival_model.survival_probability(t_j)
        S_jm1 = survival_model.survival_probability(t_jm1)

        # pA = 1 - S; adjustment = 1 - pA_j + 0.5*(pA_j - pA_jm1)
        pA_j   = 1 - S_j
        pA_jm1 = 1 - S_jm1
        adjustment = 1 - pA_j + 0.5 * (pA_j - pA_jm1)

        pv_fee += df * spread * notional * Δ_j * adjustment

    return pv_fee


def cds_pv_forward(
    survival_model: SurvivalCurveModel,
    curve: YieldCurve,
    payment_dates: Sequence[date],
    year_fractions: Sequence[float],
    spread: float,
    recovery: float,
    maturity_date: date,
    notional: float = 1.0,
    valuation_date: date = None,
) -> float:
    pv_prem = premium_leg_pv_forward(
        survival_model, curve,
        list(payment_dates), list(year_fractions),
        spread, maturity_date, notional, valuation_date
    )
    pv_prot = protection_leg_pv_forward(
        survival_model, curve,
        recovery, maturity_date, notional, valuation_date
    )
    return pv_prem - pv_prot


def cds_sensitivities_forward(
    survival_model: SurvivalCurveModel,
    curve: YieldCurve,
    payment_dates: Sequence[date],
    year_fractions: Sequence[float],
    spread: float,
    recovery: float,
    notional: float = 1.0,
    valuation_date: date = None
) -> dict:
    bump = 1e-4  # 1bp
    pv   = cds_pv_forward(
        survival_model, curve, payment_dates, year_fractions,
        spread, recovery, maturity_date=payment_dates[-1],
        notional=notional, valuation_date=valuation_date
    )
    pv_bumped = cds_pv_forward(
        survival_model, curve, payment_dates, year_fractions,
        spread + bump, recovery,
        maturity_date=payment_dates[-1],
        notional=notional, valuation_date=valuation_date
    )
    sens = pv_bumped - pv
    return {
        "pv":                pv,
        "pv01":              sens,
        "spread_sensitivity": sens
    }


def premium_leg_cashflow_pvs(
    survival_model: SurvivalCurveModel,
    curve: YieldCurve,
    payment_dates: Sequence[date],
    year_fractions: Sequence[float],
    spread: float,
    notional: float = 1.0,
    valuation_date: date = None
) -> List[Tuple[date, float, float]]:
    """
    Returns (date, raw cashflow, PV) for each payment after valuation_date,
    using FIS-style premium formula with survival curve.
    """
    if valuation_date is None:
        valuation_date = curve.py_value_date

    cf_details: List[Tuple[date, float, float]] = []
    for s_j, s_jm1, Δ_j in zip(
        payment_dates[1:], payment_dates[:-1], year_fractions
    ):
        if s_j <= valuation_date:
            continue

        df = curve.get_discount_factor(s_j)

        t_j   = (s_j   - curve.py_value_date).days / curve.py_day_count
        t_jm1 = (s_jm1 - curve.py_value_date).days / curve.py_day_count

        S_j   = survival_model.survival_probability(t_j)
        S_jm1 = survival_model.survival_probability(t_jm1)

        pA_j   = 1 - S_j
        pA_jm1 = 1 - S_jm1
        adjustment = 1 - pA_j + 0.5 * (pA_j - pA_jm1)

        cashflow = notional * spread * Δ_j
        cf_pv    = df * cashflow * adjustment
        cf_details.append((s_j, cashflow, cf_pv))

    return cf_details