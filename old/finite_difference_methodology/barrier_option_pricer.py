# Standard library imports
import os
from math import ceil
from datetime import datetime

# Third-party imports
import QuantLib as ql
import matplotlib.pyplot as plt


class BarrierOptionPricer:
    """
    A class to price vanilla barrier options using the finite difference method.
    """
    def __init__(
        self,
        spot_price: float,
        strike_price: float,
        barrier: float,
        risk_free_rate: float,
        volatility: float,
        dividend_yield: float,
        valuation_date: ql.Date,
        maturity_date: ql.Date,
        option_type: str,
        barrier_type: str,
        exercise_type: str,
        calendar,
        day_counter
    ):
        # Set evaluation date
        ql.Settings.instance().evaluationDate = valuation_date

        # Store input parameters
        self.spot_price = spot_price
        self.strike_price = strike_price
        self.barrier = barrier
        self.risk_free_rate = risk_free_rate
        self.volatility = volatility
        self.dividend_yield = dividend_yield
        self.valuation_date = valuation_date
        self.maturity_date = maturity_date
        self.calendar = calendar
        self.day_counter = day_counter

        # Market data
        self.underlying = ql.SimpleQuote(spot_price)
        self.dividend_curve = ql.FlatForward(valuation_date, dividend_yield, day_counter)
        self.risk_free_curve = ql.FlatForward(valuation_date, risk_free_rate, day_counter)
        self.volatility_curve = ql.BlackConstantVol(valuation_date, calendar, volatility, day_counter)

        self.process = ql.BlackScholesMertonProcess(
            ql.QuoteHandle(self.underlying),
            ql.YieldTermStructureHandle(self.dividend_curve),
            ql.YieldTermStructureHandle(self.risk_free_curve),
            ql.BlackVolTermStructureHandle(self.volatility_curve)
        )

        # Option components
        self.barrier_type_str = barrier_type
        self.option_type_str = option_type
        self.exercise_type_str = exercise_type
        self.option_type = getattr(ql.Option, option_type)
        self.barrier_type = getattr(ql.Barrier, barrier_type)

        self.payoff = ql.PlainVanillaPayoff(self.option_type, self.strike_price)
        self.exercise = self._get_exercise()

        self.barrier_option = ql.BarrierOption(
            self.barrier_type, self.barrier, 0.0, self.payoff, self.exercise
        )
        

    def _get_exercise(self):
        if self.exercise_type_str.lower() == "european":
            return ql.EuropeanExercise(self.maturity_date)
        elif self.exercise_type_str.lower() == "american":
            return ql.AmericanExercise(self.valuation_date, self.maturity_date)
        else:
            raise ValueError(f"Unsupported exercise type: {self.exercise_type_str}")

    def price(self, time_steps: int, scheme=ql.FdmSchemeDesc.CrankNicolson()):
        engine = ql.FdBlackScholesBarrierEngine(
            self.process, 
            time_steps, 
            time_steps, # assumes we are using square matrix of equal time and asset price steps
            0, 
            scheme 
        )
        self.barrier_option.setPricingEngine(engine)
        return self.barrier_option.NPV()

    def batch_price(self, time_steps_list):
        """ Run FDM for a list of time steps """
        return {steps: self.price(steps) for steps in time_steps_list} 

    def plot_price_convergence(self, time_steps_list, style='seaborn-darkgrid'):
        """Plot option price as a function of number of time steps to see convergence"""
        prices = self.batch_price(time_steps_list)

        if style in plt.style.available:
            plt.style.use(style)
        else:
            print(f"Warning: Style '{style}' not found. Using default.")

        plt.figure(figsize=(10, 6))
        plt.plot(list(prices.keys()), list(prices.values()), marker='o', linestyle='-')
        plt.title(f"{self.barrier_type_str} Option Price vs Time Steps ({self.exercise_type_str} Exercise)")
        plt.xlabel("Time Steps")
        plt.ylabel("Option Price")
        plt.grid(True)
        plt.tight_layout()
        plt.show()

    def calculate_greeks(self, time_steps):
        """Calculate option Greeks using the current model."""
        time_step = time_steps[-1]

        engine = ql.FdBlackScholesBarrierEngine(
            self.process,
            time_step,
            time_step, # assumes we are using square matrix of equal time and asset price steps
            0,
            ql.FdmSchemeDesc.CrankNicolson()
        )
        self.barrier_option.setPricingEngine(engine)

        greeks = {
            "Delta": self.barrier_option.delta(),  # delta, gamma, theta are the only supported greeks
            "Gamma": self.barrier_option.gamma(),
            "Theta (Daily)": self.barrier_option.theta()/365,  # daily theta
        }

        self.greeks = greeks
        return greeks

    def export_report(self, time_steps_list):
        """Export a report with parameters and pricing results."""
        results = self.batch_price(time_steps_list)
        self.greeks_time_steps = time_steps_list[-1]

        timestamp = datetime.now().strftime("%Y-%m-%d %H%M%S")
        filename = f"barrier_option_report {timestamp}.txt"

        report_lines = [
            "Barrier Option Pricing Report",
            f"Generated: {timestamp}",
            "-" * 40,
            "Market        : South Africa (ZAR-denominated option)",
            "Calendar      : South Africa",
            "Day Count     : Actual/365 (Fixed)",
            "-" * 40,
            f"Option Type     : {self.option_type_str}",
            f"Barrier Type    : {self.barrier_type_str}",
            f"Exercise Type   : {self.exercise_type_str}",
            f"Spot Price      : {self.spot_price}",
            f"Strike Price    : {self.strike_price}",
            f"Barrier Level   : {self.barrier}",
            f"Risk-Free Rate  : {self.risk_free_rate}",
            f"Volatility      : {self.volatility}",
            f"Dividend Yield  : {self.dividend_yield}",
            f"Valuation Date  : {self.valuation_date.ISO()}",
            f"Maturity Date   : {self.maturity_date.ISO()}",
            "",
            "Pricing Results (Time Steps -> Option Price):",
        ]

        for steps, price in results.items():
            report_lines.append(f"  {steps:5} steps : {price:.6f}")

        report_lines.append(f"\nGreeks (calculated with {self.greeks_time_steps} time steps):")
        for greek, value in self.greeks.items():
            report_lines.append(f"  {greek:<6}: {value:.6f}")

        script_dir = os.path.dirname(os.path.abspath(__file__))
        filepath = os.path.join(script_dir, filename)

        with open(filepath, "w") as f:
            f.write("\n".join(report_lines))

        print(f"Report saved to: {filepath}")
