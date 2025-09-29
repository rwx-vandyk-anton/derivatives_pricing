from hazard_curve import HazardRateCurve
from datetime import date
from discount import ZeroCurve
from cashflow_utils import CDSCashflowSchedule
import QuantLib as ql


val = date(2025, 7, 28)
curve = HazardRateCurve(val)
curve.load_from_csv(r"C:\Coding\derivatives-pricing\credit\cds_final\test_hazard_rates.csv")  # CSV: YYYY-MM-DD, 0.0123
s_prob = curve.survival_probability(date(2028, 3, 15))
print(f"S(2028-03-15) = {s_prob:.6f}")


discount_curve = ZeroCurve(val)
discount_curve.load_from_csv(r"C:\Coding\derivatives-pricing\credit\cds_final\dummy_curve_data.csv")  # CSV: YYYY-MM-DD, 0.085
df = discount_curve.discount_factor(val, date(2028, 3, 15))
print(f"DF(2025-07-28 -> 2028-03-15) = {df:.6f}")


from datetime import date
import QuantLib as ql

sch = CDSCashflowSchedule(
    start_date=date(2024, 4, 25),
    end_date=date(2029, 4, 25),
    calendar=ql.SouthAfrica(),
    day_count=ql.Actual365Fixed(),
)

for s, p, yf in sch.generate():
    print(s, p, yf)