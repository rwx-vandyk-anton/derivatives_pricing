import QuantLib as ql

"""
This FX option pricer uses the Garman-Kohlhagen model. This is an extension to the Black-Scholes model adjusted for dividend 
yielding stocks applied to FX. The domestic and foreign interest rates are still assumed to be flat and the volatility. This 
should be a sufficient assumption for cases where the vanilla European FX options are short-dated (maturity < 1 year).

"""


# Currency-specific day-count conventions
CURRENCY_CONVENTIONS = {
    "USD": {"day_count": ql.Actual360(), "calendar": ql.UnitedStates()},
    "EUR": {"day_count": ql.Actual360(), "calendar": ql.TARGET()},
    "GBP": {"day_count": ql.Actual365Fixed(), "calendar": ql.UnitedKingdom()},
    "JPY": {"day_count": ql.Actual365Fixed(), "calendar": ql.Japan()},
    # Need to add more currencies to the list
}

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
                 base_ccy: str,
                 quote_ccy: str,
                 valuation_date: ql.Date = None):

        self.spot = spot
        self.domestic_rate = domestic_rate
        self.foreign_rate = foreign_rate
        self.volatility = volatility
        self.maturity = maturity_in_years
        self.strike = strike
        self.option_type = option_type.lower()
        self.notional = notional

        self.base_ccy = base_ccy.upper()
        self.quote_ccy = quote_ccy.upper()

        self._set_conventions()

        if valuation_date is None:
            self.valuation_date = ql.Date.todaysDate()
        else:
            self.valuation_date = valuation_date
        ql.Settings.instance().evaluationDate = self.valuation_date

        self._build_pricing_components()

    def _set_conventions(self):
        self.base_convention = CURRENCY_CONVENTIONS.get(self.base_ccy, {
            "day_count": ql.Actual365Fixed(), "calendar": ql.TARGET()
        })
        self.quote_convention = CURRENCY_CONVENTIONS.get(self.quote_ccy, {
            "day_count": ql.Actual365Fixed(), "calendar": ql.TARGET()
        })

        self.base_day_count = self.base_convention["day_count"]
        self.quote_day_count = self.quote_convention["day_count"]
        self.base_calendar = self.base_convention["calendar"]
        self.quote_calendar = self.quote_convention["calendar"]

        self.combined_calendar = ql.JointCalendar(self.base_calendar, self.quote_calendar)

    def _build_pricing_components(self):
        # Construct curves with appropriate day count conventions
        self.domestic_curve = ql.FlatForward(self.valuation_date,
                                             ql.QuoteHandle(ql.SimpleQuote(self.domestic_rate)),
                                             self.quote_day_count)

        self.foreign_curve = ql.FlatForward(self.valuation_date,
                                            ql.QuoteHandle(ql.SimpleQuote(self.foreign_rate)),
                                            self.base_day_count)

        # Construct volatility
        self.vol_ts = ql.BlackConstantVol(self.valuation_date,
                                          self.combined_calendar,
                                          ql.QuoteHandle(ql.SimpleQuote(self.volatility)),
                                          ql.Actual365Fixed())  # Vols typically use Actual/365

        # Spot handle
        self.spot_handle = ql.QuoteHandle(ql.SimpleQuote(self.spot))

        # Garman-Kohlhagen process
        self.process = ql.BlackScholesMertonProcess(self.spot_handle,
                                                    ql.YieldTermStructureHandle(self.foreign_curve),
                                                    ql.YieldTermStructureHandle(self.domestic_curve),
                                                    ql.BlackVolTermStructureHandle(self.vol_ts)
            )

    def price(self):
        maturity_date = self.combined_calendar.advance(self.valuation_date, 
                                                        ql.Period(int(self.maturity * 365 + 0.5), ql.Days))
        payoff = ql.PlainVanillaPayoff(ql.Option.Call if self.option_type == 'call' else ql.Option.Put, self.strike)
        exercise = ql.EuropeanExercise(maturity_date)

        fx_option = ql.VanillaOption(payoff, exercise)
        engine = ql.AnalyticEuropeanEngine(self.process)
        fx_option.setPricingEngine(engine)

        return fx_option.NPV() * self.notional

    def calculate_greeks(self):
        maturity_date = self.combined_calendar.advance(self.valuation_date, 
                                                        ql.Period(int(self.maturity * 365 + 0.5), ql.Days))  # just double check this again
        payoff = ql.PlainVanillaPayoff(ql.Option.Call if self.option_type == 'call' else ql.Option.Put, self.strike)
        exercise = ql.EuropeanExercise(maturity_date)

        fx_option = ql.VanillaOption(payoff, exercise)
        engine = ql.AnalyticEuropeanEngine(self.process)
        fx_option.setPricingEngine(engine)

        delta = fx_option.delta()
        gamma = fx_option.gamma()
        vega = fx_option.vega()

        return delta, gamma, vega


if __name__ == "__main__":
    pricer = FXOptionPricer(
        spot=1.10,
        domestic_rate=0.03,
        foreign_rate=0.01,
        volatility=0.12,
        maturity_in_years=0.5,
        strike=1.12,
        option_type="put",
        notional=100_000,
        base_ccy="EUR",
        quote_ccy="USD"
    )

    price = pricer.price()
    print(f"The price of the FX {pricer.option_type} option is: {price:.4f} {pricer.quote_ccy}")

    delta, gamma, vega = pricer.calculate_greeks()
    print(f"Delta: {delta:.4f} (per unit of spot), Gamma: {gamma:.4f} (per unit^2), Vega: {vega:.4f} (per 1% vol change)")



"""
Notes:
1. As it stands, the code assumes the domestic currency is USD. Extensions need to made to take in any currency pair and use
the relevant calendars and daycount conventions. (done in version 2).
2. Extensions can be made to take into account when an actual interest rate curve is used without switching to something more
complicated like Hull-White. This is done by using the discount factor over the life of the option to obtain the effective interest
rate over the period i.e. r_eff = -(1/T)*log(P(0,T)).
3. Add some error handling for inputs from users.
4. Add deployment to Excel features.

"""