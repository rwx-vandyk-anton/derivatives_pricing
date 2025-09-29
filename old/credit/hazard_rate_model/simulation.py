# =============== hazard_rate_model/simulation.py ===============
"""
Run Monte Carlo simulations of default times.
"""
import numpy as np
from .model import HazardRateModel


class SimulationRunner:
    """
    Runs multiple simulations of default times given a hazard model.
    """
    def __init__(self, model: HazardRateModel):
        self.model = model

    def run(self, num_sims: int, horizon: float):
        """
        Perform num_sims draws of default times, truncated at horizon.
        Returns array of shape (num_sims,) with default times or np.inf if no default.
        """
        times = np.zeros(num_sims)
        for i in range(num_sims):
            t = self.model.default_time()
            times[i] = t if t <= horizon else np.inf
        return times