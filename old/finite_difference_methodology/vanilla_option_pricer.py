import os
from math import ceil
from datetime import datetime

import matplotlib.pyplot as plt
import QuantLib as ql


class VanillaOptionPricer:
    """
    A class to price vanilla European or American options using the finite difference method.
    """

    def __init__(self,
                 spot_price: float,
                 strike_price: float,
                 risk_free_rate: float,
                 volatility: float,
                 dividend_yield: float,
                 valuation_date: ql.Date,
                 maturity_date: ql.Date,
                 option_type: str,
                 exercise_type: str,
                 calendar,
                 day_counter):
        """
        Initialise market data, option parameters, and setup QuantLib objects.
        """

        # Set global valuation date
        ql.Settings.instance().evaluationDate = valuation_date

        # Store parameters
        self.spot_price = spot_price
        self.strike_price = strike_price
        self.risk_free_rate = risk_free_rate
        self.volatility = volatility
        self.dividend_yield = dividend_yield
        self.valuation_date = valuation_date
        self.maturity_date = maturity_date
        self.option_type_str = option_type
        self.exercise_type_str = exercise_type
        self.calendar = calendar
        self.day_counter = day_counter

        # Set up market data curves
        self.underlying = ql.SimpleQuote(spot_price)
        self.dividend_curve = ql.FlatForward(valuation_date, dividend_yield, day_counter)
        self.risk_free_curve = ql.FlatForward(valuation_date, risk_free_rate, day_counter)
        self.volatility_curve = ql.BlackConstantVol(valuation_date, calendar, volatility, day_counter)

        # Build pricing process
        self.process = ql.BlackScholesMertonProcess(
            ql.QuoteHandle(self.underlying),
            ql.YieldTermStructureHandle(self.dividend_curve),
            ql.YieldTermStructureHandle(self.risk_free_curve),
            ql.BlackVolTermStructureHandle(self.volatility_curve)
        )

        # Define option payoff and exercise
        self.option_type = getattr(ql.Option, option_type)
        self.payoff = ql.PlainVanillaPayoff(self.option_type, strike_price)
        self.exercise = self._get_exercise()

        # Construct QuantLib vanilla option
        self.option = ql.VanillaOption(self.payoff, self.exercise)

    def _get_exercise(self):
        """
        Return QuantLib exercise object based on user input.
        """
        if self.exercise_type_str.lower() == "european":
            return ql.EuropeanExercise(self.maturity_date)
        elif self.exercise_type_str.lower() == "american":
            return ql.AmericanExercise(self.valuation_date, self.maturity_date)
        else:
            raise ValueError(f"Unsupported exercise type: {self.exercise_type_str}")

    def price(self, time_steps: int, scheme=ql.FdmSchemeDesc.CrankNicolson()):
        """
        Price the option using finite difference method.
        """
        engine = ql.FdBlackScholesVanillaEngine(
            self.process, time_steps, time_steps, 0, scheme
        )
        self.option.setPricingEngine(engine)
        return self.option.NPV()

    def batch_price(self, time_steps_list):
        """
        Price the option over a range of time steps.
        """
        return {steps: self.price(steps) for steps in time_steps_list}

    def plot_price_convergence(self, time_steps_list, style='seaborn-v0_8-darkgrid'):
        """
        Plot option price as a function of time step granularity.
        """
        prices = self.batch_price(time_steps_list)

        if style in plt.style.available:
            plt.style.use(style)
        else:
            print(f"Style '{style}' not found. Using default.")

        plt.figure(figsize=(10, 6))
        plt.plot(list(prices.keys()), list(prices.values()), marker='o', linestyle='-')
        plt.title(
            f"{self.option_type_str} Option Price vs Time Steps "
            f"({self.exercise_type_str} Exercise)"
        )
        plt.xlabel("Time Steps")
        plt.ylabel("Option Price")
        plt.grid(True)
        plt.tight_layout()
        plt.show()

    def calculate_greeks(self, time_steps):
        """
        Calculate and return option greeks.
        """
        time_step = time_steps[-1]  # Use most granular time step for Greeks
        engine = ql.FdBlackScholesVanillaEngine(
            self.process, time_step, time_step, 0, ql.FdmSchemeDesc.CrankNicolson()
        )
        self.option.setPricingEngine(engine)

        greeks = {
            "Delta": self.option.delta(),  # delta, gamma, theta are the only supported greeks
            "Gamma": self.option.gamma(),
            "Theta (Daily)": self.option.theta()/365,  # daily theta
        }

        self.greeks = greeks
        self.greeks_time_step = time_step
        return greeks

    def export_report(self, time_steps_list):
        """
        Export a report containing pricing results and greeks (if calculated).
        """
        results = self.batch_price(time_steps_list)
        timestamp = datetime.now().strftime("%Y-%m-%d %H%M%S")
        filename = f"vanilla_option_report {timestamp}.txt"

        report_lines = [
            "Vanilla Option Pricing Report",
            f"Generated: {timestamp}",
            "-" * 40,
            "Market        : South Africa (ZAR-denominated option)",
            "Calendar      : South Africa",
            "Day Count     : Actual/365 (Fixed)",
            "-" * 40,
            f"Option Type     : {self.option_type_str}",
            f"Exercise Type   : {self.exercise_type_str}",
            f"Spot Price      : {self.spot_price}",
            f"Strike Price    : {self.strike_price}",
            f"Risk-Free Rate  : {self.risk_free_rate}",
            f"Volatility      : {self.volatility}",
            f"Dividend Yield  : {self.dividend_yield}",
            f"Valuation Date  : {self.valuation_date.ISO()}",
            f"Maturity Date   : {self.maturity_date.ISO()}",
            "",
            "Pricing Results (Time Steps -> Option Price):"
        ]

        for steps, price in results.items():
            report_lines.append(f"  {steps:5} steps : {price:.6f}")

        if hasattr(self, "greeks"):
            report_lines.append(f"\nGreeks (calculated with {self.greeks_time_step} time steps):")
            for greek, value in self.greeks.items():
                report_lines.append(f"  {greek:<6}: {value:.6f}")

        script_dir = os.path.dirname(os.path.abspath(__file__))
        filepath = os.path.join(script_dir, filename)

        with open(filepath, "w") as f:
            f.write("\n".join(report_lines))

        print(f"Report saved to: {filepath}")

    def export_report_fx(self, time_steps_list):
        """
        Export a version of the report tailored for FX options (domestic/foreign rates).
        """
        results = self.batch_price(time_steps_list)
        timestamp = datetime.now().strftime("%Y-%m-%d %H%M%S")
        filename = f"vanilla_option_report {timestamp}.txt"

        report_lines = [
            "Vanilla Option Pricing Report (FX)",
            f"Generated: {timestamp}",
            "-" * 40,
            "Market        : South Africa (ZAR-denominated option)",
            "Calendar      : South Africa",
            "Day Count     : Actual/365 (Fixed)",
            "-" * 40,
            f"Option Type              : {self.option_type_str}",
            f"Exercise Type            : {self.exercise_type_str}",
            f"Spot Price               : {self.spot_price}",
            f"Strike Price             : {self.strike_price}",
            f"Domestic Risk-Free Rate  : {self.risk_free_rate}",
            f"Foreign Risk-Free Rate   : {self.dividend_yield}",
            f"Volatility               : {self.volatility}",
            f"Valuation Date           : {self.valuation_date.ISO()}",
            f"Maturity Date            : {self.maturity_date.ISO()}",
            "",
            "Pricing Results (Time Steps -> Option Price):"
        ]

        for steps, price in results.items():
            report_lines.append(f"  {steps:5} steps : {price:.6f}")

        if hasattr(self, "greeks"):
            report_lines.append(f"\nGreeks (calculated with {self.greeks_time_step} time steps):")
            for greek, value in self.greeks.items():
                report_lines.append(f"  {greek:<6}: {value:.6f}")

        script_dir = os.path.dirname(os.path.abspath(__file__))
        filepath = os.path.join(script_dir, filename)

        with open(filepath, "w") as f:
            f.write("\n".join(report_lines))

        print(f"Report saved to: {filepath}")
