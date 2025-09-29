from hazard.hazard_curve import HazardRateCurve
from datetime import date
from discount_engine.discount import ZeroCurve
from cashflow.utils import CDSCashflowSchedule
import QuantLib as ql
from pricing.cds import  build_cds_premium_df


val = date(2025, 7, 28)
curve = HazardRateCurve(val)
curve.load_from_csv(r"C:\Coding\derivatives-pricing\new\hazard\test_hazard_rates.csv")  # CSV: YYYY-MM-DD, 0.0123
s_prob = curve.survival_probability(date(2028, 3, 15))

discount_curve = ZeroCurve(val)
discount_curve.load_from_csv(r"C:\Coding\derivatives-pricing\new\discount_engine\dummy_curve_data.csv")  # CSV: YYYY-MM-DD, 0.085
df = discount_curve.discount_factor(val, date(2028, 3, 15))

sch = CDSCashflowSchedule(
    start_date=date(2024, 4, 25),
    end_date=date(2029, 4, 25),
    calendar=ql.SouthAfrica(),       # holiday calendar
    payment_convention=ql.Following, # how to roll pay dates
    tenor=ql.Period(ql.Quarterly)    # quarterly payments
)
periods = sch.generate()

df_prem = build_cds_premium_df(
    schedule=periods,
    hazard_curve=curve,
    discount_curve=discount_curve,
    val_date=date(2025, 7, 28),
    nominal=70046000,
    rate=0.0059,  
)

print(df_prem)