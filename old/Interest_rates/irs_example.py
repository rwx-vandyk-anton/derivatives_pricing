import QuantLib as ql
from interest_rate_swap_pricer import VanillaSwapPricer
from market_conventions import CONVENTIONS

# Evaluation setup
today = ql.Date(6, 5, 2025)
ql.Settings.instance().evaluationDate = today

# Dummy flat curves (replace with bootstrapped curve handles in production)
flat_rate = 0.025
curve = ql.FlatForward(today, flat_rate, ql.Actual365Fixed())
curve_handle = ql.YieldTermStructureHandle(curve)

# Swap definition
notional = 10_000_000
start_date = ql.UnitedStates().advance(today, 2, ql.Days)
maturity = "5Y"
fixed_rate = 0.03
fixed_leg_index_name = "USD-SOFR"
floating_leg_index_name = "USD-LIBOR-3M"

# Instantiate and price
pricer = VanillaSwapPricer(
    notional,
    start_date,
    maturity,
    fixed_rate,
    fixed_leg_index_name,
    floating_leg_index_name,
    discount_curve_handle=curve_handle,
    fixed_leg_curve_handle=curve_handle,
    floating_leg_curve_handle=curve_handle
)

# Results
print("Swap Results:")
for k, v in pricer.results().items():
    print(f"{k}: {v:,.2f}")

print(f"PV01: {pricer.pv01():,.2f}")
