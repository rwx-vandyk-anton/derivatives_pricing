from .pricing import cln_price
from ..hazard_rate_model.model import HazardRateModel
from ..hazard_rate_model.utils import bootstrap_hazard_curve
import numpy as np
from typing import Callable


def discount_rate_factory(r: float) -> Callable[[float], float]:
    """
    Flat‐rate discount function D(t) = exp(-r*t).
    """
    return lambda t: np.exp(-r * t)


def piecewise_intensity_factory(hazard_curve):
    def intensity(t: float) -> float:
        for T, lam in hazard_curve:
            if t <= T:
                return lam
        return hazard_curve[-1][1]
    return intensity


def main():
    # 1) Market inputs
    market_tenors = [1.0, 3.0, 5.0, 7.0, 10.0]
    market_spreads = np.array([0.01, 0.0125, 0.015, 0.0175, 0.02])
    recovery = 0.4
    r_free = 0.015
    tenor = 6.0
    coupon = 0.0175

    # 2) Hazard model
    haz_curve = bootstrap_hazard_curve(market_tenors, market_spreads, recovery)
    intensity = piecewise_intensity_factory(haz_curve)
    model = HazardRateModel(intensity, T_max=tenor)
    S = model.survival_probability

    # 3) Cashflow setup
    payment_times = np.array([i * 0.5 for i in range(1, 6 + 1)])
    year_fractions = np.full_like(payment_times, 0.5)
    D = discount_rate_factory(r_free)

    # 4) CLN price
    cln_val = cln_price(
        survival_func=S,
        discount_func=D,
        payment_times=payment_times,
        year_fractions=year_fractions,
        coupon=coupon,
        recovery=recovery,
        notional=1.0
    )
    print(f"CLN Price for {tenor:.0f}Y maturity with {coupon*1e4:.1f} bps coupon: {cln_val:.4f}")


if __name__ == "__main__":
    main()