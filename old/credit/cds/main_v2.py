import numpy as np
from pricing import fair_cds_spread, discount_rate_factory


def survival_func_factory(hazard: float):
    """
    Returns a constant hazard-rate survival function S(t) = exp(-λ * t)
    """
    return lambda t: np.exp(-hazard * t)


def main():
    # --- Parameters ---
    hazard = 0.02        # Constant hazard rate (2%)
    recovery = 0.4       # 40% recovery rate
    r = 0.04             # Discount rate (4%)
    tenor = 0.5          # 6-month maturity
    freq = 1/12          # Monthly payments

    # --- Time Grid ---
    payment_times = np.linspace(freq, tenor, int(tenor / freq))
    year_fractions = np.full_like(payment_times, freq)

    # --- Functions ---
    S = survival_func_factory(hazard)
    D = discount_rate_factory(r)  # Uses 1/(1 + r)^t

    # --- Compute Fair Spread ---
    s_fair = fair_cds_spread(
        survival_func=S,
        discount_func=D,
        payment_times=payment_times,
        year_fractions=year_fractions,
        recovery=recovery
    )

    print(f"Fair CDS Spread for {tenor:.2f}y maturity: {s_fair * 1e4:.2f} bps")


if __name__ == "__main__":
    main()
