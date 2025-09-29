import QuantLib as ql

"""
This FX option pricer uses the Garman-Kohlhagen model. This is an extension to the Black-Scholes model adjusted for dividend yielding
        stocks applied to FX. The domestic and foreign interest rates are still assumed to be flat and the volatility. This should be a 
        sufficient assumption for cases where the vanilla European FX options are short dated (maturity < 1 year). 
        
        Notes:
        1. As it stands, the code assumes the domestic currency is USD. Extensions need to made to take in any currency pair and use
        the relevant calendars and daycount conventions.
        2. Extensions can be made to take into account when an actual interest rate curve is used without switching to something more
        complicated like Hull-White. This is done by using the discount factor over the life of the option to obtain the effective interest
        rate over the period i.e. r_eff = -(1/T)*log(P(0,T))

"""

class FXOptionPricer:
    def __init__(self, 
                 spot: float,
                 domestic_rate: float,
                 foreign_rate: float,
                 volatility: float,
                 maturity_in_years: float,
                 strike: float,
                 option_type: str,  # 'call' or 'put'
                 notional: float,
                 valuation_date: ql.Date = None ):
        """
        Parameters:
            spot (float): Spot FX rate (e.g., EUR/USD)
            domestic_rate (float): Domestic interest rate (e.g., USD)
            foreign_rate (float): Foreign interest rate (e.g., EUR)
            volatility (float): Implied volatility (annualized, decimal)
            maturity_in_years (float): Time to maturity in years
            strike (float): Strike price of the option
            option_type (str): 'call' or 'put'
            valuation_date (ql.Date): Optional, defaults to today
        """
        self.spot = spot
        self.domestic_rate = domestic_rate
        self.foreign_rate = foreign_rate
        self.volatility = volatility
        self.maturity = maturity_in_years
        self.strike = strike
        self.option_type = option_type.lower()
        self.notional = notional

        self.calendar = ql.TARGET()
        self.day_count = ql.Actual360()

        if valuation_date is None:
            self.valuation_date = ql.Date.todaysDate()
        else:
            self.valuation_date = valuation_date
        ql.Settings.instance().evaluationDate = self.valuation_date

        self._build_pricing_components()

    def _build_pricing_components(self):
        # Construct curves
        self.domestic_curve = ql.FlatForward(self.valuation_date,
                                             ql.QuoteHandle(ql.SimpleQuote(self.domestic_rate)),
                                             self.day_count)
        self.foreign_curve = ql.FlatForward(self.valuation_date,
                                            ql.QuoteHandle(ql.SimpleQuote(self.foreign_rate)),
                                            self.day_count)

        # Construct volatility
        self.vol_ts = ql.BlackConstantVol(self.valuation_date,
                                          self.calendar,
                                          ql.QuoteHandle(ql.SimpleQuote(self.volatility)),
                                          self.day_count)

        # Underlying spot FX rate to be modelled with Garman-Kolhagen model
        self.spot_handle = ql.QuoteHandle(ql.SimpleQuote(self.spot))

        # Build the Garman-Kohlhagen process
        self.process = ql.BlackScholesMertonProcess(
            self.spot_handle,
            ql.YieldTermStructureHandle(self.foreign_curve),
            ql.YieldTermStructureHandle(self.domestic_curve),
            ql.BlackVolTermStructureHandle(self.vol_ts)
        )

    def price(self):
        maturity_date = self.calendar.advance(self.valuation_date, ql.Period(int(self.maturity * 365), ql.Days))
        payoff = ql.PlainVanillaPayoff(ql.Option.Call if self.option_type == 'call' else ql.Option.Put, self.strike)
        exercise = ql.EuropeanExercise(maturity_date)

        fx_option = ql.VanillaOption(payoff, exercise)
        engine = ql.AnalyticEuropeanEngine(self.process)
        fx_option.setPricingEngine(engine)

        return fx_option.NPV() * self.notional

    def calculate_greeks(self):
        maturity_date = self.calendar.advance(self.valuation_date, ql.Period(int(self.maturity * 365), ql.Days))
        payoff = ql.PlainVanillaPayoff(ql.Option.Call if self.option_type == 'call' else ql.Option.Put, self.strike)
        exercise = ql.EuropeanExercise(maturity_date)

        fx_option = ql.VanillaOption(payoff, exercise)
        engine = ql.AnalyticEuropeanEngine(self.process)
        fx_option.setPricingEngine(engine)

        fx_delta = fx_option.delta()
        fx_gamma = fx_option.gamma()
        fx_vega = fx_option.vega()

        return fx_delta, fx_gamma, fx_vega



if __name__ == "__main__":
    # Test case parameters
    pricer = FXOptionPricer(
        spot=1.10,                # EUR/USD spot rate
        domestic_rate=0.23,       # USD interest rate (3%)
        foreign_rate=0.01,        # EUR interest rate (1%)
        volatility=0.12,          # 12% implied vol
        maturity_in_years=0.5,    # 6 months to maturity
        strike=1.12,              # Strike price
        option_type="put",        # Call option
        notional=100_000
    )
    
    price = pricer.price()
    print(f"The price of the FX {pricer.option_type} option is: {price:.4f} USD")

    delta, gamma, vega = pricer.calculate_greeks()
    print(f"Delta: {delta:.4f} (per 1 unit of spot)")
    print(f"Gamma: {gamma:.4f} (per 1 unit² of spot)")
    print(f"Vega: {vega:.4f} (per 1% vol change)")