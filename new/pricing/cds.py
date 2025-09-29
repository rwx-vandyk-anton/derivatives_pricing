import pandas as pd
from datetime import date as pydate, timedelta
from typing import List, Tuple

# Each schedule row: (accrual_start_date, pay_date, year_fraction_for_period)
Schedule = List[Tuple[pydate, pydate, float]]

def build_cds_premium_df(
    schedule: Schedule,
    hazard_curve,                 # survival_probability(d: date) -> float
    discount_curve,               # discount_factor(val_date: date, d: date) -> float
    val_date: pydate,
    nominal: float,
    rate: float
) -> pd.DataFrame:
    """
    Build CDS premium-leg cashflow DataFrame.

    survival            = S(pay_date - 1 day) / S(val_date + 1 day)
    discount_factor     = DF(val_date -> pay_date)
    cashflow            = nominal * rate * year_fraction

    accrual_df          = DF(val_date -> midpoint_date), where midpoint_date is:
                            - FIRST ROW: midpoint of [val_date, pay_date]
                            - OTHER ROWS: midpoint of [accrual_start, pay_date]
                          midpoint uses round((end - start).days / 2)

    accrual_prob_term   = 0.5 * (survival_prev - survival_curr) with survival_prev for first row = 1

    pv                  = survival*cashflow*discount_factor
                          + accrual_prob_term*accrual_df*cashflow
    """
    cols = [
        "accrual_start", "pay_date", "year_fraction",
        "survival", "discount_factor", "cashflow",
        "accrual_df", "accrual_prob_term", "pv"
    ]

    if not schedule:
        return pd.DataFrame(columns=cols)

    # Base frame (keep Python date objects; no .dt usage)
    df = pd.DataFrame(schedule, columns=["accrual_start", "pay_date", "year_fraction"])

    # Keep only rows with pay_date strictly after valuation date
    df = df[df["pay_date"] > val_date].reset_index(drop=True)
    if df.empty:
        return pd.DataFrame(columns=cols)

    # Normalization denominator: survival one day after valuation date
    denom_date = val_date + timedelta(days=1)
    denom = max(hazard_curve.survival_probability(denom_date), 1e-16)

    # Survival to (pay_date - 1 day), normalized
    survivals = []
    for pay in df["pay_date"]:
        s = hazard_curve.survival_probability(pay - timedelta(days=1)) / denom
        survivals.append(s)
    df["survival"] = survivals

    # Discount factor to pay_date
    dfs_pay = [discount_curve.discount_factor(val_date, pay) for pay in df["pay_date"]]
    df["discount_factor"] = dfs_pay

    # Fixed premium cashflow amount per period
    df["cashflow"] = nominal * rate * df["year_fraction"]

    # Midpoint DF:
    # - first row: midpoint of [val_date, pay_date]
    # - others:    midpoint of [accrual_start, pay_date]
    mid_dfs: List[float] = []
    for i, row in df.iterrows():
        start = row["accrual_start"] if i > 0 else val_date
        pay   = row["pay_date"]
        days = (pay - start).days
        mid_date = start + timedelta(days=round(days / 2))
        mid_dfs.append(discount_curve.discount_factor(val_date, mid_date))
    df["accrual_df"] = mid_dfs

    # accrual_prob_term with prev survival = 1 for the first row
    accrual_prob_terms: List[float] = []
    prev_s = 1.0
    for s_curr in df["survival"]:
        accrual_prob_terms.append(0.5 * (prev_s - s_curr))
        prev_s = s_curr
    df["accrual_prob_term"] = accrual_prob_terms

    # PV per row
    df["pv"] = (
        df["survival"] * df["cashflow"] * df["discount_factor"]
        + df["accrual_prob_term"] * df["accrual_df"] * df["cashflow"]
    )

    return df[cols]
