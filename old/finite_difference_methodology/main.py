# Standard library imports
import QuantLib as ql

# Local module imports
from barrier_option_pricer import *
from vanilla_option_pricer import *


def run_barrier():
    # === Barrier Option Pricing ===
    # === Market and Option Parameters ===
    spot_price = 95.0
    strike_price = 100.0
    barrier = 90.0  # Make sure this barrier makes sense for given barrier type
    risk_free_rate = 0.10
    volatility = 0.25
    dividend_yield = 0.05
    valuation_date = ql.Date(16, 6, 2025)
    maturity_date = ql.Date(16, 9, 2025)

    # === Option Definitions ===
    option_type = "Call"           # "Call" or "Put"
    barrier_type = "DownIn"      # "DownOut", "DownIn", "UpIn", "UpOut"
    exercise_type = "European"    # only "European" is supported for barrier options

    # === QuantLib Calendar and Day Count Convention ===
    calendar = ql.SouthAfrica()
    day_counter = ql.Actual365Fixed()

    # === Time steps for finite difference method (FDM) ===
    time_steps = [
        25, 50, 75, 100, 150, 200, 250, 300,
        350, 400, 450, 500, 1000, 2000, 3000, 4000
    ]

    # === Barrier Option Pricer Object ===
    pricer = BarrierOptionPricer(
        spot_price=spot_price,
        strike_price=strike_price,
        barrier=barrier,
        risk_free_rate=risk_free_rate,
        volatility=volatility,
        dividend_yield=dividend_yield,
        valuation_date=valuation_date,
        maturity_date=maturity_date,
        option_type=option_type,
        barrier_type=barrier_type,
        exercise_type=exercise_type,
        calendar=calendar,
        day_counter=day_counter
    )

    # Price using different grid sizes
    results = pricer.batch_price(time_steps)

    # Print barrier option prices
    for steps, price in results.items():
        print(f"{barrier_type} {option_type} Price, {steps} time partitions: {price:.4f}")

    # Print Greeks
    print(pricer.calculate_greeks(time_steps))

    # Plot convergence of option price
    pricer.plot_price_convergence(time_steps, style='ggplot')

    # Export barrier option pricing report
    pricer.export_report(time_steps)


def run_american_equity():
    # === Vanilla Equity Option Pricing ===
    # === Market and Option Parameters ===
    spot_price = 95.0
    strike_price = 100.0
    risk_free_rate = 0.10
    volatility = 0.25
    dividend_yield = 0.05
    valuation_date = ql.Date(16, 6, 2025)
    maturity_date = ql.Date(16, 9, 2025)

    # === Option Definitions ===
    option_type = "Call"           # "Call" or "Put"
    exercise_type = "American"    # "European", "American" is supported for conventional options

    # === QuantLib Calendar and Day Count Convention ===
    calendar = ql.SouthAfrica()
    day_counter = ql.Actual365Fixed()

    # === Time steps for finite difference method (FDM) ===
    time_steps = [
        25, 50, 75, 100, 150, 200, 250, 300,
        350, 400, 450, 500, 1000, 2000, 3000, 4000
    ]
    # === Vanilla Equity Option Pricer Object===
    pricer_vanilla = VanillaOptionPricer(
        spot_price=spot_price,
        strike_price=strike_price,
        risk_free_rate=risk_free_rate,
        volatility=volatility,
        dividend_yield=dividend_yield,
        valuation_date=valuation_date,
        maturity_date=maturity_date,
        option_type=option_type,
        exercise_type=exercise_type,
        calendar=calendar,
        day_counter=day_counter
    )

    # Vanilla option calculations
    pricer_vanilla.calculate_greeks(time_steps)
    pricer_vanilla.plot_price_convergence(time_steps)
    pricer_vanilla.export_report(time_steps)


def run_american_fx():
    # === Vanilla FX Option Pricer Object ===
    # === Market and Option Parameters ===
    spot_price = 18.0
    strike_price = 17.5
    domestic_risk_free_rate = 0.08  # Domestic rate (ZAR)
    volatility = 0.25
    foreign_risk_free_rate = 0.05  # Foreign rate (USD)
    valuation_date = ql.Date(16, 6, 2025)
    maturity_date = ql.Date(16, 9, 2025)

    # === Option Definitions ===
    option_type = "Call"           # "Call" or "Put"
    exercise_type = "American"    # "European", "American" is supported for conventional options

    # === QuantLib Calendar and Day Count Convention ===
    calendar = ql.SouthAfrica()
    day_counter = ql.Actual365Fixed()

    # === Time steps for finite difference method (FDM) ===
    time_steps = [
        25, 50, 75, 100, 150, 200, 250, 300,
        350, 400, 450, 500, 1000, 2000, 3000, 4000
    ]

    fx_pricer_vanilla = VanillaOptionPricer(
        spot_price=spot_price,             # e.g., USDZAR spot
        strike_price=strike_price,
        risk_free_rate=domestic_risk_free_rate,
        volatility=volatility,
        dividend_yield=foreign_risk_free_rate,
        valuation_date=valuation_date,
        maturity_date=maturity_date,
        option_type=option_type,
        exercise_type=exercise_type,
        calendar=calendar,
        day_counter=day_counter
    )

    # FX option calculations
    fx_pricer_vanilla.calculate_greeks(time_steps)
    fx_pricer_vanilla.plot_price_convergence(time_steps)
    fx_pricer_vanilla.export_report_fx(time_steps)


run_barrier()
run_american_equity()
run_american_fx()
