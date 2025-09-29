from __future__ import annotations
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import List, Tuple, Optional
import csv
import math

# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------

def year_fraction(start: date, end: date, basis: str = "ACT/365F") -> float:
    if basis.upper() != "ACT/365F":
        raise NotImplementedError("Only ACT/365F is supported in this utility.")
    return (end - start).days / 365.0


# Accepted date formats (ordered)
_DATE_FMTS: tuple[str, ...] = ("%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d")

def _parse_date_str(s: str, preferred_fmt: Optional[str] = None) -> Optional[date]:
    """
    Try preferred_fmt (if given) then the known formats in _DATE_FMTS.
    Returns None if all fail.
    """
    s = (s or "").strip()
    fmts = ([preferred_fmt] if preferred_fmt else []) + list(_DATE_FMTS)

    for fmt in fmts:
        try:
            return datetime.strptime(s, fmt).date()
        except Exception:
            pass

    # Final attempt: strict ISO
    try:
        return date.fromisoformat(s)
    except Exception:
        return None


def _parse_float(s: str) -> Optional[float]:
    """
    Parse a float allowing comma decimal separators and stray spaces.
    Returns None if it cannot be parsed.
    """
    if s is None:
        return None
    s = s.strip().replace(" ", "")
    # Handle European comma decimal
    if "," in s and "." not in s:
        s = s.replace(",", ".")
    try:
        return float(s)
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Hazard Rate Curve Handler
# ---------------------------------------------------------------------------

@dataclass
class HazardRateCurve:
    """
    Piecewise-linear instantaneous hazard-rate curve λ(t) with survival
    S(T) = exp(-∫_0^T λ(τ) dτ), integrated via trapezoid rule on knot union.
    """
    valuation_date: date
    _times: List[float] = field(default_factory=list, init=False)   # year-fractions from valuation_date
    _rates: List[float] = field(default_factory=list, init=False)   # instantaneous hazard λ(t)

    # ---------------------------- Loading ----------------------------------
    def load_from_csv(self, filepath: str, date_format: str | None = None) -> None:
        """
        Populate from CSV with columns: Date, HazardRate (header optional).
        Accepts dates in YYYY-MM-DD, DD/MM/YYYY, or YYYY/MM/DD.
        """
        rows: List[Tuple[date, float]] = []

        # utf-8-sig removes a potential BOM (ï»¿) on the first cell
        with open(filepath, newline="", encoding="utf-8-sig") as f:
            reader = csv.reader(f)

            for row in reader:
                if not row or len(row) < 2:
                    continue

                d_raw, r_raw = row[0].strip(), row[1].strip()

                # Date
                d = _parse_date_str(d_raw, preferred_fmt=date_format)
                if d is None:
                    # Likely a header or bad row—skip
                    continue

                # Rate (continuous instantaneous, per annum)
                r = _parse_float(r_raw)
                if r is None:
                    continue

                rows.append((d, r))

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
                rates[-1] = r  # replace duplicate time
            else:
                times.append(t)
                rates.append(r)

        if len(times) < 2:
            times.append(1e-8)
            rates.append(rates[0])

        self._times = times
        self._rates = rates

    # ------------------------ Interpolation core ----------------------------
    def _interp_lambda(self, t: float) -> float:
        """Linear interpolation with flat extrapolation for λ(t)."""
        times, rates = self._times, self._rates
        if t <= times[0]:
            return rates[0]
        if t >= times[-1]:
            return rates[-1]
        lo, hi = 0, len(times) - 1
        while hi - lo > 1:
            mid = (lo + hi) // 2
            if times[mid] <= t:
                lo = mid
            else:
                hi = mid
        t0, t1 = times[lo], times[hi]
        r0, r1 = rates[lo], rates[hi]
        w = (t - t0) / (t1 - t0)
        return r0 + w * (r1 - r0)

    # ------------------------ Survival probability -------------------------
    def survival_probability(self, end_date: date) -> float:
        T = year_fraction(self.valuation_date, end_date, basis="ACT/365F")
        if T <= 0.0:
            return 1.0

        grid: List[float] = [0.0]
        for t in self._times[1:]:  # skip synthetic 0
            if 0.0 < t < T:
                grid.append(t)
        grid.append(T)
        grid.sort()

        integral = 0.0
        lam_prev = self._interp_lambda(grid[0])
        for i in range(1, len(grid)):
            t0, t1 = grid[i - 1], grid[i]
            lam_curr = self._interp_lambda(t1)
            dt = t1 - t0
            integral += 0.5 * (lam_prev + lam_curr) * dt
            lam_prev = lam_curr

        return math.exp(-integral)
