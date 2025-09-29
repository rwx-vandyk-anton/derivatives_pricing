import numpy as np
from datetime import date
from typing import List, Union

class HazardRateModel:
    """
    A “spot‐hazard” model, referenced off a user‑supplied valuation date:

      λ(t) = piecewise‐linear interp of your input spot rates (flat outside)
      S(t) = exp(–λ(t) * t)
      forward_hazard_rate(t1,t2) = average of λ(t1) and λ(t2)

    Here t may be a date (converted ACT/360 from the valuation date) or a float (years).
    """

    def __init__(
        self,
        pillar_dates: List[date],
        spot_hazard_rates: List[float],
        valuation_date: date,
        day_count_basis: int = 360
    ):
        if len(pillar_dates) != len(spot_hazard_rates):
            raise ValueError("pillar_dates and spot_hazard_rates must match length")

        # Sort the pillars ascending
        pairs = sorted(zip(pillar_dates, spot_hazard_rates), key=lambda x: x[0])
        self.pillar_dates, self.rates = zip(*pairs)

        self.ref_date    = valuation_date
        self.day_count   = day_count_basis

        # Build the array of times (in years) from valuation_date to each pillar
        self.times = [
            (pd - self.ref_date).days / self.day_count
            for pd in self.pillar_dates
        ]

    def _to_years(self, t: Union[date, float]) -> float:
        """Convert a date or float to years since valuation_date."""
        if isinstance(t, date):
            return (t - self.ref_date).days / self.day_count
        return float(t)

    def intensity(self, t: Union[date, float]) -> float:
        """
        Spot hazard λ(t):
        - linear interp between your pillar rates
        - flat before the first pillar / after the last
        """
        y = self._to_years(t)
        return float(np.interp(
            y,
            self.times,
            self.rates,
            left=self.rates[0],
            right=self.rates[-1]
        ))

    def survival_probability(self, t: Union[date, float]) -> float:
        """
        S(t) = exp(-λ(t) * t)
        """
        y = self._to_years(t)
        if y <= 0:
            return 1.0
        λ = self.intensity(y)
        return 1 - 1/((1+λ)**y)

    def forward_hazard_rate(
        self,
        t1: Union[date, float],
        t2: Union[date, float]
    ) -> float:
        """
        Simple average hazard over [t1, t2]:
          (λ(t1) + λ(t2)) / 2
        """
        y1, y2 = self._to_years(t1), self._to_years(t2)
        λ1, λ2 = self.intensity(y1), self.intensity(y2)
        return 0.5 * (λ1 + λ2)
