from __future__ import annotations
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import List, Tuple
import csv
import math

# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------

def year_fraction(start: date, end: date, basis: str = "ACT/365F") -> float:
    """
    Compute year fraction between two dates (default ACT/365 Fixed).

    Parameters
    ----------
    start : date
        Start date (inclusive for day count purposes).
    end : date
        End date (exclusive for day count purposes in this simple convention).
    basis : str
        Only "ACT/365F" supported for now.

    Returns
    -------
    float
        Year fraction between start and end.
    """
    if basis.upper() != "ACT/365F":
        raise NotImplementedError("Only ACT/365F is supported in this utility.")
    return (end - start).days / 365.0


# ---------------------------------------------------------------------------
# Hazard Rate Curve Handler
# ---------------------------------------------------------------------------

@dataclass
class HazardRateCurve:
    """
    Piecewise-linear *instantaneous* (continuous) hazard-rate curve with
    survival calculation via numerical integration.

    The curve is provided as calendar *dates* with associated *spot* instantaneous
    hazard rates (per annum, continuous). Between supplied knots, the
    instantaneous hazard λ(t) is linearly interpolated in t (in years from the
    valuation date). Survival is computed as:

        S(T) = exp( - ∫_0^T λ(τ) dτ )

    where the integral is evaluated using a trapezoidal rule on the union of the
    curve's knot times and the query horizon T.

    Notes
    -----
    - Extrapolation is *flat* outside the provided range: left and right values
      equal the nearest endpoint rate.
    - CSV is expected to have two columns, with header row optional:
        1) Date in ISO format YYYY-MM-DD
        2) Continuous instantaneous hazard (per annum), e.g. 0.015 for 1.5%
    - Rows on or before the valuation date are ignored (the curve starts at > t0).
      At t=0 a synthetic knot is created using the first available rate for
      stability.
    """

    valuation_date: date
    _times: List[float] = field(default_factory=list, init=False)   # year-fractions from valuation_date
    _rates: List[float] = field(default_factory=list, init=False)   # instantaneous hazard λ(t)

    # ---------------------------- Loading ----------------------------------
    def load_from_csv(self, filepath: str, date_format: str | None = None) -> None:
        """
        Populate the curve from a CSV with two columns: Date, HazardRate.

        Parameters
        ----------
        filepath : str
            Path to CSV file. Header optional. Extra columns ignored.
        date_format : str | None
            Optional strptime pattern, e.g. "%d/%m/%Y". If None, will try
            datetime.fromisoformat.
        """
        rows: List[Tuple[date, float]] = []
        with open(filepath, newline="") as f:
            reader = csv.reader(f)
            # Peek first row to detect header by attempting parse
            first = next(reader)

            def parse_row(row: List[str]) -> Tuple[date, float] | None:
                if not row or len(row) < 2:
                    return None
                d_raw, r_raw = row[0].strip(), row[1].strip()
                # Parse date
                try:
                    d = datetime.strptime(d_raw, date_format).date() if date_format else date.fromisoformat(d_raw)
                except Exception:
                    # Not a data row (likely header)
                    return None
                # Parse rate
                try:
                    r = float(r_raw)
                except Exception:
                    return None
                return d, r

            parsed = parse_row(first)
            if parsed is not None:
                rows.append(parsed)
            # Continue
            for row in reader:
                parsed = parse_row(row)
                if parsed is not None:
                    rows.append(parsed)

        # Filter strictly after valuation_date, sort by date
        rows = [(d, r) for (d, r) in rows if d > self.valuation_date]
        if not rows:
            raise ValueError("CSV contains no rows strictly after valuation date.")
        rows.sort(key=lambda x: x[0])

        # Build times & rates
        times: List[float] = []
        rates: List[float] = []

        # Synthetic t=0 knot at the first observed rate (for stable interpolation)
        first_rate = rows[0][1]
        times.append(0.0)
        rates.append(first_rate)

        for d, r in rows:
            t = year_fraction(self.valuation_date, d, basis="ACT/365F")
            if t <= 0.0:
                continue
            if times and abs(t - times[-1]) < 1e-12:
                # If duplicate time (unlikely), keep the last rate
                rates[-1] = r
            else:
                times.append(t)
                rates.append(r)

        if len(times) < 2:
            # Ensure at least two points for interpolation/extrapolation
            # Duplicate the first with a small positive time step
            times.append(1e-8)
            rates.append(rates[0])

        self._times = times
        self._rates = rates

    # ------------------------ Interpolation core ----------------------------
    def _interp_lambda(self, t: float) -> float:
        """Linear interpolation (flat extrapolation) of instantaneous hazard at time t (years)."""
        # Manual interp to avoid numpy dependency
        times, rates = self._times, self._rates
        if t <= times[0]:
            return rates[0]
        if t >= times[-1]:
            return rates[-1]
        # Binary search for interval
        lo, hi = 0, len(times) - 1
        while hi - lo > 1:
            mid = (lo + hi) // 2
            if times[mid] <= t:
                lo = mid
            else:
                hi = mid
        # Linear interpolation
        t0, t1 = times[lo], times[hi]
        r0, r1 = rates[lo], rates[hi]
        w = (t - t0) / (t1 - t0)
        return r0 + w * (r1 - r0)

    # ------------------------ Survival probability -------------------------
    def survival_probability(self, end_date: date) -> float:
        """
        Compute S(0, T) given an *end date* using trapezoidal integration of λ(t).

        Parameters
        ----------
        end_date : date
            Horizon date for survival probability.

        Returns
        -------
        float
            Survival probability S(T) = exp(-∫_0^T λ(τ) dτ).
        """
        T = year_fraction(self.valuation_date, end_date, basis="ACT/365F")
        if T <= 0.0:
            return 1.0

        # Build integration grid: 0, (all knots within (0,T)), T
        grid: List[float] = [0.0]
        for t in self._times[1:]:  # skip synthetic 0 point at index 0
            if 0.0 < t < T:
                grid.append(t)
        grid.append(T)
        grid.sort()

        # Trapezoidal integration of λ(t)
        integral = 0.0
        lam_prev = self._interp_lambda(grid[0])
        for i in range(1, len(grid)):
            t0, t1 = grid[i - 1], grid[i]
            lam_curr = self._interp_lambda(t1)
            dt = t1 - t0
            integral += 0.5 * (lam_prev + lam_curr) * dt
            lam_prev = lam_curr

        return math.exp(-integral)
