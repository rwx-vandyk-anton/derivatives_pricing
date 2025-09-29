import QuantLib as ql
from market_conventions import CONVENTIONS

"""
This pricer values a vanilla interest rate swap with a fixed-for-floating structure. Other leg structure types fixed-for-fixed, 
floating-for-floating are not included in this code. 
"""
class VanillaSwapPricer:
    def __init__(self, 
                 notional, 
                 start_date, 
                 maturity, 
                 fixed_rate,
                 fixed_leg_index_name, 
                 floating_leg_index_name,
                 discount_curve_handle, 
                 fixed_leg_curve_handle, 
                 floating_leg_curve_handle):
        
        self.notional = notional
        self.start_date = start_date
        self.maturity_input = maturity
        self.maturity = ql.Period(maturity)
        self.fixed_rate = fixed_rate

        self.fixed_leg_index_name = fixed_leg_index_name
        self.floating_leg_index_name = floating_leg_index_name

        self.fixed_conventions = CONVENTIONS[fixed_leg_index_name]
        self.floating_conventions = CONVENTIONS[floating_leg_index_name]

        self.discount_curve_handle = discount_curve_handle
        self.fixed_curve_handle = fixed_leg_curve_handle
        self.floating_curve_handle = floating_leg_curve_handle

        self.swap = self._build_swap()

    def _build_schedule(self, calendar, convention, frequency):
        return ql.Schedule(
            self.start_date,
            self.fixed_conventions['calendar'].advance(self.start_date, self.maturity), # end date obeying leg conventions
            ql.Period(frequency),  # tenor
            calendar,
            convention,  # Business day convention
            convention,  # Termination date convention
            ql.DateGeneration.Forward,  # Date generation rule   
            False                       # End-of-month rule
        )

    def _build_swap(self):
        fixed_schedule = self._build_schedule(
            self.fixed_conventions['calendar'],
            self.fixed_conventions['business_day_convention'],
            ql.Annual
        )

        floating_schedule = self._build_schedule(
            self.floating_conventions['calendar'],
            self.floating_conventions['business_day_convention'],
            ql.Semiannual
        )

        fixed_leg_day_count = self.fixed_conventions['day_count']
        float_leg_day_count = self.floating_conventions['day_count']

        floating_index = self.floating_conventions['index'](self.floating_curve_handle)

        swap = ql.VanillaSwap(
            ql.VanillaSwap.Payer,
            self.notional,
            fixed_schedule,
            self.fixed_rate,
            fixed_leg_day_count,
            floating_schedule,
            floating_index,
            0.0,
            float_leg_day_count
        )

        engine = ql.DiscountingSwapEngine(self.discount_curve_handle)
        swap.setPricingEngine(engine)
        return swap

    def results(self):
        return {
            "Swap NPV": self.swap.NPV(),
            "Fixed Leg PV": self.swap.fixedLegNPV(),
            "Floating Leg PV": self.swap.floatingLegNPV(),
            "Fair Rate": self.swap.fairRate(),
            "Fair Spread": self.swap.fairSpread()
        }

    def pv01(self, bump_size=1e-4):
        original_rate = self.fixed_rate

        bumped_rate = original_rate + bump_size
        bumped_swap = VanillaSwapPricer(
            self.notional,
            self.start_date,
            self.maturity_input,
            bumped_rate,
            fixed_leg_index_name= self.fixed_leg_index_name, #self.fixed_conventions, #CONVENTIONS[fixed_leg_index_name], #fixed_leg_index_name,
            floating_leg_index_name=self.floating_leg_index_name, #, self.floating_conventions, #CONVENTIONS[floating_leg_index_name], #floating_leg_index_name
            discount_curve_handle=self.discount_curve_handle,
            fixed_leg_curve_handle=self.fixed_curve_handle,
            floating_leg_curve_handle=self.floating_curve_handle
        )
        return bumped_swap.swap.NPV() - self.swap.NPV()