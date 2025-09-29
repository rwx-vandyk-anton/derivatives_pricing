import QuantLib as ql
import math

"""
The following bond option pricer uses the Black'76 model for pricing European bond options, both zero coupon and coupon-bearing types. 
"""

class MarketEnvironment:
    """
    Market environment including calendar, day count convention, and risk-free rate.
    """
    def __init__(self, valuation_date, risk_free_rate, calendar, day_count):
        self.calendar = calendar
        self.valuation_date = calendar.adjust(valuation_date)
        ql.Settings.instance().evaluationDate = self.valuation_date
        self.day_count = day_count
        self.discount_curve = ql.FlatForward(
                                            self.valuation_date, 
                                            risk_free_rate, 
                                            day_count
                                )


class BondBuilder:
    """
    Creates a bond object (zero-coupon or coupon-bearing).
    """
    def __init__(self, 
                 issue_date, 
                 maturity_date, 
                 face_value,
                 coupon_rate=0.0, 
                 frequency=ql.Annual, 
                 calendar=None, 
                 day_count=None):
        self.issue_date = issue_date
        self.maturity_date = maturity_date
        self.face_value = face_value
        self.coupon_rate = coupon_rate
        self.frequency = frequency
        self.calendar = calendar
        self.day_count = day_count

    def build(self):
        schedule = ql.Schedule(
                        self.issue_date, 
                        self.maturity_date,
                        ql.Period(self.frequency), 
                        self.calendar,
                        ql.Unadjusted, 
                        ql.Unadjusted,
                        ql.DateGeneration.Backward, 
                        False
                    )

        if self.coupon_rate == 0.0:
            bond = ql.ZeroCouponBond(
                                    0, 
                                    self.calendar, 
                                    self.face_value,
                                    self.maturity_date, 
                                    ql.Unadjusted, 
                                    self.face_value,
                                    self.issue_date
                    )
            
        else:
            bond = ql.FixedRateBond(
                                    0, 
                                    self.face_value, 
                                    schedule,
                                    [self.coupon_rate], 
                                    self.day_count
                    )
            
        return bond


class BondOptionPricer:
    """
    Calculates the actual price of the option and the related sensitivities.
    """
    def __init__(self, bond, market_env, option_type, strike, expiry_date, volatility, option_notional):
        self.bond = bond
        self.market_env = market_env
        self.option_type = option_type
        self.strike = strike
        self.expiry_date = market_env.calendar.adjust(expiry_date)
        self.volatility = volatility
        self.option_notional = option_notional

        self.bond.setPricingEngine(
            ql.DiscountingBondEngine(ql.YieldTermStructureHandle(market_env.discount_curve))
        )

    def _forward_price(self):
        clean_price = self.bond.cleanPrice()
        dirty_price = self.bond.dirtyPrice()
        accrued = self.bond.accruedAmount()
        forward_price = dirty_price * (
            (1 + self.market_env.discount_curve.zeroRate(
                self.expiry_date, self.market_env.day_count, ql.Continuous).rate()) ** (
                    self.market_env.day_count.yearFraction(
                        self.market_env.valuation_date, self.expiry_date))
        )
        return forward_price

    def price(self):
        fwd = self._forward_price()
        std_dev = self.volatility * math.sqrt(
            self.market_env.day_count.yearFraction(self.market_env.valuation_date, self.expiry_date)
        )

        option = ql.VanillaOption(
            ql.PlainVanillaPayoff(self.option_type, self.strike),
            ql.EuropeanExercise(self.expiry_date)
        )

        flat_vol_ts = ql.BlackConstantVol(
            self.market_env.valuation_date, self.market_env.calendar,
            ql.QuoteHandle(ql.SimpleQuote(self.volatility)),
            self.market_env.day_count
        )

        black_process = ql.BlackProcess(
            ql.QuoteHandle(ql.SimpleQuote(fwd)),
            ql.YieldTermStructureHandle(self.market_env.discount_curve),
            ql.BlackVolTermStructureHandle(flat_vol_ts)
        )

        option.setPricingEngine(ql.AnalyticEuropeanEngine(black_process))
        return option.NPV() * self.option_notional

    def risk_measures(self, bump_size=0.0001):
        base_price = self.price()

        # Delta
        original_fwd = self._forward_price()
        bumped_up = original_fwd * (1 + bump_size)
        bumped_down = original_fwd * (1 - bump_size)

        self.volatility = self.volatility
        delta = (self._option_price_with_fwd(bumped_up) -
                 self._option_price_with_fwd(bumped_down)) / (2 * original_fwd * bump_size)

        # Gamma
        gamma = (self._option_price_with_fwd(bumped_up) -
                 2 * base_price +
                 self._option_price_with_fwd(bumped_down)) / ((original_fwd * bump_size) ** 2)

        # Vega
        bumped_vol_up = self.volatility + bump_size
        bumped_vol_down = self.volatility - bump_size
        vega = (self._option_price_with_vol(bumped_vol_up) -
                self._option_price_with_vol(bumped_vol_down)) / (2 * bump_size)

        # DV01, Duration, Convexity
        ytm = self.bond.bondYield(
            self.bond.cleanPrice(), self.market_env.day_count,
            ql.Compounded, self.bond.frequency()
        )

        dv01 = self.bond.basisPointValue()  # Convert from cents to full units
        duration = self.bond.duration(self.market_env.day_count, ql.Compounded)
        convexity = self.bond.convexity(self.market_env.day_count, ql.Compounded)

        return {
            "Bond option delta": delta,
            "Bond option gamma": gamma,
            "Bond option vega": vega,
            "Underlying bond DV01": dv01,
            "Underlying bond duration": duration,
            "Underlying bond convexity": convexity
        }

    def _option_price_with_fwd(self, forward):
        flat_vol_ts = ql.BlackConstantVol(
            self.market_env.valuation_date, self.market_env.calendar,
            ql.QuoteHandle(ql.SimpleQuote(self.volatility)),
            self.market_env.day_count
        )

        process = ql.BlackProcess(
            ql.QuoteHandle(ql.SimpleQuote(forward)),
            ql.YieldTermStructureHandle(self.market_env.discount_curve),
            ql.BlackVolTermStructureHandle(flat_vol_ts)
        )

        option = ql.VanillaOption(
            ql.PlainVanillaPayoff(self.option_type, self.strike),
            ql.EuropeanExercise(self.expiry_date)
        )
        option.setPricingEngine(ql.AnalyticEuropeanEngine(process))
        return option.NPV()

    def _option_price_with_vol(self, vol):
        fwd = self._forward_price()
        flat_vol_ts = ql.BlackConstantVol(
            self.market_env.valuation_date, self.market_env.calendar,
            ql.QuoteHandle(ql.SimpleQuote(vol)),
            self.market_env.day_count
        )

        process = ql.BlackProcess(
            ql.QuoteHandle(ql.SimpleQuote(fwd)),
            ql.YieldTermStructureHandle(self.market_env.discount_curve),
            ql.BlackVolTermStructureHandle(flat_vol_ts)
        )

        option = ql.VanillaOption(
            ql.PlainVanillaPayoff(self.option_type, self.strike),
            ql.EuropeanExercise(self.expiry_date)
        )
        option.setPricingEngine(ql.AnalyticEuropeanEngine(process))
        return option.NPV() 



if __name__ == "__main__":
    
    # Test case
    # Market setup

    calendar = ql.UnitedStates()
    day_count = ql.ActualActual()
    market_env = MarketEnvironment(
        valuation_date=ql.Date(15, 5, 2025),
        risk_free_rate=0.03,
        calendar=calendar,
        day_count=day_count
    )

    # Bond setup: Change coupon_rate to 0.0 for zero-coupon bond
    bond_builder = BondBuilder(
        issue_date=ql.Date(15, 5, 2020),
        maturity_date=ql.Date(15, 5, 2030),
        face_value=100.0,
        coupon_rate=0.05,  # Use 0.0 for zero-coupon
        frequency=ql.Semiannual,
        calendar=calendar,
        day_count=day_count
    )

    bond = bond_builder.build()

    # Option setup
    pricer = BondOptionPricer(
        bond=bond,
        market_env=market_env,
        option_type=ql.Option.Call,
        strike=95.0,
        expiry_date=ql.Date(15, 5, 2026),
        volatility=0.15,
        option_notional=100_000
    )

    option_price = pricer.price()
    #sensitivities = pricer.risk_measures()

    print(f"Option price: {option_price:.4f}")
    """print("Risk Sensitivities:")
    for k, v in sensitivities.items():
        print(f"  {k}: {v:.6f}") 
     """
    
"""
Notes:
1. Need to fix the error with the calculation of sensitivities.


"""