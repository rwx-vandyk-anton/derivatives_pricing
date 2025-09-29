# =============== hazard_rate_model/utils.py ===============
"""
Utility functions for hazard curve calibration.
"""
import numpy as np

def bootstrap_hazard_curve(maturities, spreads, recovery=0.4):
    """
    Simple bootstrap from CDS spreads to piecewise constant hazard rates.
    maturities: list of times
    spreads: list of CDS spreads (annualized)
    recovery: recovery rate
    """
    # placeholder implementation
    lambdas = spreads / (1 - recovery)
    return list(zip(maturities, lambdas))
