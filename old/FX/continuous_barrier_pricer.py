import QuantLib as ql
from abc import ABC, abstractmethod
from typing import Optional

"""
The code below is used to value Barrier options and allows for their variants, specifically: down-and-out, up-and-out, up-and-out, up-and-in. These
have a European excercise type and can be calls or puts. It allows for an underlying of equities, and FX.

Important notes:
1. A major assumption in this model implementation is that the underlying is continuously monitored. The case for discrete monitoring is covered by
a different model.
2. ql.AnalyticBarrierEngine() is based on Black-Scholes framework does not support the computation of Greeks.
3. ql.FdBlackScholesBarrierEngine() is based on the Black-Scholes PDE and supports Greeks computation via finite difference methods. This is the one
used in the implementation.
4. Delta and gamma are supported in ql.FdBlackScholesBarrierEngine(), but vega is not. Therefore, a custom vega method has been implemented.
"""

class BarrierOptionPricer(ABC):
    def __init__(
        self,
        spot: float,
        strike: float,
        barrier: float,
        notional: float,
        maturity_date: ql.Date,
        option_type: int,  # ql.Option.Call or ql.Option.Put
        barrier_type: int,  # ql.Barrier.UpIn, ql.Barrier.DownOut, ql.Barrier.UpOut, ql.Barrier.UpOut
        calendar: ql.Calendar,
        day_count: ql.DayCounter,  # Day count convention
        business_convention: int,  # Business day convention
        valuation_date: ql.Date,
        risk_free_rate: float,
        dividend_yield: float,
        volatility: float,
        is_fx: bool = False,
        domestic_currency: Optional[str] = None,
        foreign_currency: Optional[str] = None,
    ):
        self.spot = spot
        self.strike = strike
        self.barrier = barrier
        self.notional = notional
        self.maturity_date = maturity_date
        self.option_type = option_type
        self.barrier_type = barrier_type
        self.calendar = calendar
        self.day_count = day_count
        self.business_convention = business_convention
        self.valuation_date = valuation_date
        self.risk_free_rate = risk_free_rate
        self.dividend_yield = dividend_yield
        self.volatility = volatility
        self.is_fx = is_fx
        self.domestic_currency = domestic_currency
        self.foreign_currency = foreign_currency

        self._set_up_environment()

    def _set_up_environment(self):
        ql.Settings.instance().evaluationDate = self.valuation_date

        self.spot_handle = ql.QuoteHandle(ql.SimpleQuote(self.spot))

        self.flat_term_structure = ql.YieldTermStructureHandle(
            ql.FlatForward(self.valuation_date, self.risk_free_rate, self.day_count)
        )
        self.dividend_term_structure = ql.YieldTermStructureHandle(
            ql.FlatForward(self.valuation_date, self.dividend_yield, self.day_count)
        )
        self.volatility_term_structure = ql.BlackVolTermStructureHandle(
            ql.BlackConstantVol(self.valuation_date, self.calendar, self.volatility, self.day_count)
        )

        self.risk_free_curve = self.flat_term_structure
        self.dividend_curve = self.dividend_term_structure
        self.vol_curve = self.volatility_term_structure

        self.bsm_process = ql.BlackScholesMertonProcess(
            self.spot_handle, self.risk_free_curve, self.dividend_curve, self.vol_curve
        )


    def custom_vega(self, bump_size: float = 0.0001) -> float:
        """
        Calculate vega using central difference method where volatility is perturbed by 1 basis point.
        """

        original_vol = self.volatility

        # Bump up
        vol_up_quote = ql.SimpleQuote(original_vol + bump_size)
        vol_up_handle = ql.BlackVolTermStructureHandle(
            ql.BlackConstantVol(self.valuation_date, self.calendar, ql.QuoteHandle(vol_up_quote), self.day_count)
        )
        process_up = ql.BlackScholesMertonProcess(
            self.spot_handle,
            self.risk_free_curve,
            self.dividend_curve,
            vol_up_handle
        )
        engine_up = ql.FdBlackScholesBarrierEngine(process_up)
        option_up = self._create_barrier_option()
        option_up.setPricingEngine(engine_up)
        price_up = option_up.NPV()

        # Bump down
        vol_down_quote = ql.SimpleQuote(original_vol - bump_size)
        vol_down_handle = ql.BlackVolTermStructureHandle(
            ql.BlackConstantVol(self.valuation_date, self.calendar, ql.QuoteHandle(vol_down_quote), self.day_count)
        )
        process_down = ql.BlackScholesMertonProcess(
            self.spot_handle,
            self.risk_free_curve,
            self.dividend_curve,
            vol_down_handle
        )
        engine_down = ql.FdBlackScholesBarrierEngine(process_down)
        option_down = self._create_barrier_option()
        option_down.setPricingEngine(engine_down)
        price_down = option_down.NPV()

        # First order central difference
        vega = (price_up - price_down) / (2 * bump_size)

        return vega 


    def _create_barrier_option(self):
        payoff = ql.PlainVanillaPayoff(self.option_type, self.strike)
        exercise = ql.EuropeanExercise(self.maturity_date)

        return ql.BarrierOption(
            self.barrier_type,
            self.barrier,
            0.0,  # No rebate in this implementation
            payoff,
            exercise
        )
       
    def price_and_greeks(self):
        option = self._create_barrier_option()
        engine = ql.FdBlackScholesBarrierEngine(self.bsm_process)  # test case for engine supporting Greeks
        option.setPricingEngine(engine)

        npv = option.NPV() * self.notional
        delta = option.delta() * self.notional
        gamma = option.gamma() * self.notional
        vega_ = self.custom_vega() * self.notional

        return {
            f"Barrier option price (in {self.domestic_currency}) is": npv,
            f"Option delta (in {self.domestic_currency})": delta,
            f"Option gamma (in {self.domestic_currency})": gamma,
            f"Option vega (in {self.domestic_currency})": vega_
        }


class FXBarrierOptionPricer(BarrierOptionPricer):
    def __init__(
        self,
        *args,
        **kwargs
    ):
        if kwargs.get("is_fx") and kwargs.get("domestic_currency") and kwargs.get("foreign_currency"):
            currency_pair = kwargs["domestic_currency"] + "/" + kwargs["foreign_currency"]
            print(f"Pricing FX Barrier Option for {currency_pair}")
        super().__init__(*args, **kwargs)


# Test case example
if __name__ == "__main__":

    spot = 100.0
    strike = 100.0
    barrier = 95.0
    notional = 1_000_000
    maturity_date = ql.Date(19, 5, 2026)
    option_type = ql.Option.Call
    barrier_type = ql.Barrier.DownOut
    calendar = ql.TARGET()
    day_count = ql.Actual365Fixed()
    business_convention = ql.Following
    valuation_date = ql.Date(19, 5, 2025)
    risk_free_rate = 0.03
    dividend_yield = 0.01
    volatility = 0.2

    pricer = FXBarrierOptionPricer(
        spot=spot,
        strike=strike,
        barrier=barrier,
        notional=notional,
        maturity_date=maturity_date,
        option_type=option_type,
        barrier_type=barrier_type,
        calendar=calendar,
        day_count=day_count,
        business_convention=business_convention,
        valuation_date=valuation_date,
        risk_free_rate=risk_free_rate,
        dividend_yield=dividend_yield,
        volatility=volatility,
        is_fx=True,
        domestic_currency="EUR",
        foreign_currency="USD"
    )

    results = pricer.price_and_greeks()
    for key, value in results.items():
        print(f"{key}: {value:.2f}")


# 3977524.16  # AnalyticBarrierEngine() price result
# 3977659.71  # FdBlackScholesBarrierEngine() price result

"""
Notes:
1. Add market conventions dictionary to adapt to changes in currency automatically.

"""