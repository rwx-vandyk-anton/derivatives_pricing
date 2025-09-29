import pandas as pd
from datetime import date as pydate, timedelta
from typing import List, Tuple

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
    survival            = S(pay_date - 1 day) / S(val_date + 1 day)
    accrual_df          = DF(val_date -> midpoint_date), midpoint_date = start + round((pay-start).days/2)
    accrual_prob_term   = 0.5 * (survival_prev - survival_curr) with survival_prev for first row = 1
    pv                  = survival*cashflow*discount_factor + accrual_prob_term*accrual_df*cashflow
    """
    cols = ["accrual_start", "pay_date", "year_fraction",
            "survival", "discount_factor", "cashflow",
            "accrual_df", "accrual_prob_term", "pv"]

    if not schedule:
        return pd.DataFrame(columns=cols)

    df = pd.DataFrame(schedule, columns=["accrual_start", "pay_date", "year_fraction"])

    # Keep only rows with pay_date strictly after val_date
    df = df[df["pay_date"] > val_date].reset_index(drop=True)

    # Denominator: survival one day after valuation date
    denom_date = val_date + timedelta(days=1)
    denom = max(hazard_curve.survival_probability(denom_date), 1e-16)

    # Survival to (pay_date - 1 day), normalized
    df["survival"] = df["pay_date"].apply(lambda d: hazard_curve.survival_probability(d - timedelta(days=1))) / denom

    # DF(val_date -> pay_date)
    df["discount_factor"] = df["pay_date"].apply(lambda d: discount_curve.discount_factor(val_date, d))

    # Fixed premium cashflow amount
    df["cashflow"] = nominal * rate * df["year_fraction"]

    # Midpoint of period (rounded) and its DF
    def midpoint_df(row):
        start, pay = row["accrual_start"], row["pay_date"]
        days = (pay - start).days
        mid = start + timedelta(days=round(days / 2))
        return discount_curve.discount_factor(val_date, mid)

    df["accrual_df"] = df.apply(midpoint_df, axis=1)

    # accrual_prob_term with prev survival = 1 for the first row
    surv = df["survival"].to_numpy()
    accrual_prob = []
    for i, s_curr in enumerate(surv):
        s_prev = 1.0 if i == 0 else surv[i - 1]
        accrual_prob.append(0.5 * (s_prev - s_curr))
    df["accrual_prob_term"] = accrual_prob

    # PV per row
    df["pv"] = df["survival"] * df["cashflow"] * df["discount_factor"] \
             + df["accrual_prob_term"] * df["accrual_df"] * df["cashflow"]

    return df
