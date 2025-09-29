from discount import *
from datetime import date

zero_rates = [0.06, 0.07, 
              0.08, 0.09]
maturities = [date(2025, 6, 16), date(2025, 7, 16), 
              date(2025, 8, 16), date(2025, 9, 16)]
valuation_date = date(2025, 6, 15) # today

date_in_future = date(2025, 9, 15)

zero_curve = YieldCurve(zero_rates, maturities, valuation_date)

discount_curve = YieldCurve(discount_rates, maturities, valuation_date)

discount_factor = zero_curve.get_zero_rate(date_in_future)

print(discount_factor)