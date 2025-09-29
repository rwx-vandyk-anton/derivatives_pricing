import numpy as np
from ..hazard_rate_model.model import HazardRateModel
from ..hazard_rate_model.utils import bootstrap_hazard_curve
from ..hazard_rate_model.simulation import SimulationRunner
from .pricing import  fair_cds_spread, empirical_cds_spread

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
    # 1) Market‐standard inputs for calibration
    market_tenors = [1.0, 3.0, 5.0, 7.0, 10.0]
    market_spreads = np.array([0.01, 0.0125, 0.015, 0.0175, 0.02])
    recovery = 0.4
    r_free = 0.015

    # 2) Bootstrap spreads into intensity model
    haz_curve = bootstrap_hazard_curve(market_tenors, market_spreads, recovery)
    intensity = piecewise_intensity_factory(haz_curve)

    # 3) We choose a random tenor here say 6 years
    tenor = 6.0
    # Create the hazard rate model object
    model = HazardRateModel(intensity, T_max=tenor)
    # Create the hazard rate simulation object
    sim_runner = SimulationRunner(model)

    # 4) Simulate default times using the simulation object
    num_sims = 100000
    default_times = sim_runner.run(num_sims=num_sims, horizon=tenor)

    # 5) Build discount function and payment schedule (6 year maturity with semi‐annual payments)
    D = discount_rate_factory(r_free)
    payment_times = np.array([i * 0.5 for i in range(1, 6 + 1)])
    # Use full_like, very cool function!
    year_fractions = np.full_like(payment_times, 0.5)

    # 6) Get theoretical par‐spread via analytic formula
    # Define S to be the survival probability function from the hazard model object
    S = model.survival_probability

    # Use our calculate fair_cds_spread function
    s_analytic = fair_cds_spread(S, D, payment_times, year_fractions, recovery)
    print(f"Analytic par spread for {tenor:.0f} y CDS: {s_analytic*1e4:.1f} bps")

    # 7) Get the empirical par‐spread via simulation
    s_empirical = empirical_cds_spread(
        default_times,
        payment_times,
        year_fractions,
        D,
        recovery
    )
    print(f"Empirical par spread for {tenor:.0f} y CDS: {s_empirical*1e4:.1f} bps")


if __name__ == "__main__":
    main()