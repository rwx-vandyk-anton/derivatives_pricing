import numpy as np
from typing import List, Sequence
from datetime import date

class SurvivalCurveModel:
    """
    A survival‐curve model that approximates survival‐probability interpolation
    and default‐time sampling via linear interpolation, avoiding root‐finding.
    """

    def __init__(
        self,
        times: Sequence[float],
        survival_probs: Sequence[float],
    ):
        """
        Parameters
        ----------
        times : Sequence[float]
            Times (in years) at which survival probabilities are defined.
        survival_probs : Sequence[float]
            Survival probabilities S(t) at the corresponding times.
        """
        # sort inputs by increasing time
        pairs = sorted(zip(times, survival_probs), key=lambda x: x[0])
        self.t_grid = np.array([t for t, _ in pairs], dtype=float)
        self.S_grid = np.array([s for _, s in pairs], dtype=float)
        # precompute cumulative hazard H(t) = -ln S(t)
        self.H_grid = -np.log(self.S_grid)
        # maximum horizon
        self.T_max = float(self.t_grid[-1])
        # for compatibility with functions that expect .pillar_dates
        self.pillar_dates: List[date] = []

    def survival_probability(self, t: float) -> float:
        """
        Return S(t) by linear interpolation on (t_grid, S_grid),
        clamped to [0, T_max], with S(0)=1 enforced.
        """
        if t <= 0.0:
            return 1.0
        if t >= self.T_max:
            return float(self.S_grid[-1])
        return float(np.interp(t, self.t_grid, self.S_grid))

    def default_time(self) -> float:
        """
        Simulate default time via inverse‐transform sampling:
          - Draw u ~ U(0,1)
          - F(t) = 1 – S(t)
          - If u > F(T_max), return inf (no default within horizon)
          - Else find t with F(t) = u by interpolation
        Returns
        -------
        float
            Default time in years, or np.inf if beyond T_max.
        """
        u = np.random.rand()
        F_grid = 1.0 - self.S_grid
        F_max = F_grid[-1]
        if u > F_max:
            return np.inf
        # invert F(t)=u ⇒ t = interp(u, F_grid, t_grid)
        return float(np.interp(u, F_grid, self.t_grid))

    def forward_hazard_rate(self, t1: float, t2: float) -> float:
        """
        Compute average forward hazard rate over (t1, t2):
          h_f = [H(t2) - H(t1)] / (t2 - t1),
        where H(t) = -ln S(t).
        """
        # clamp into [0, T_max]
        t1c = min(max(t1, 0.0), self.T_max)
        t2c = min(max(t2, 0.0), self.T_max)
        if t2c <= t1c:
            return 0.0
        H1 = float(np.interp(t1c, self.t_grid, self.H_grid))
        H2 = float(np.interp(t2c, self.t_grid, self.H_grid))
        return (H2 - H1) / (t2c - t1c)
