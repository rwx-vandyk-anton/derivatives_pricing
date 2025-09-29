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

_DATE_FMTS: tuple[str, ...] = ("%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d")

def _parse_date_str(s: str, preferred_fmt: Optional[str] = None) -> Optional[date]:
    s = (s or "").strip()
    fmts = ([preferred_fmt] if preferred_fmt else []) + list(_DATE_FMTS)
    for fmt in fmts:
        try:
            return datetime.strptime(s, fmt).date()
        except Exception:
            pass
    try:
        return date.fromisoformat(s)
    except Exception:
        return None

def _parse_float(s: str) -> Optional[float]:
    if s is None:
        return None
    s = s.strip().replace(" ", "")
    if "," in s and "." not in s:
        s = s.replace(",", ".")
    try:
        return float(s)
    except Exception:
        return None

# ---------------------------------------------------------------------------
# Hazard Rate Curve (λ(t) piecewise-linear; simple exp with λ(T) * T)
# ---------------------------------------------------------------------------

@dataclass
class HazardRateCurve:
    valuation_date: date
    _times: List[float] = field(default_factory=list, init=False)   # year-fractions
    _rates: List[float] = field(default_factory=list, init=False)   # λ at knots

    def load_from_csv(self, filepath: str, date_format: str | None = None) -> None:
        rows: List[Tuple[date, float]] = []
        with open(filepath, newline="", encoding="utf-8-sig") as f:
            reader = csv.reader(f)
            for row in reader:
                if not row or len(row) < 2:
                    continue
                d = _parse_date_str(row[0], preferred_fmt=date_format)
                r = _parse_float(row[1])
                if d is None or r is None:
                    continue
                rows.append((d, r))

        rows = [(d, r) for (d, r) in rows if d > self.valuation_date]
        if not rows:
            raise ValueError("CSV contains no rows strictly after valuation date.")
        rows.sort(key=lambda x: x[0])

        times: List[float] = [0.0]
        rates: List[float] = [rows[0][1]]  # synthetic t=0 with first rate

        for d, r in rows:
            t = year_fraction(self.valuation_date, d, basis="ACT/365F")
            if t <= 0.0:
                continue
            if abs(t - times[-1]) < 1e-12:
                rates[-1] = r
            else:
                times.append(t)
                rates.append(r)

        if len(times) < 2:
            times.append(1e-8)
            rates.append(rates[0])

        self._times = times
        self._rates = rates

    def survival_probability(self, end_date: date) -> float:
        """
        Line-for-line match of the VBA-style logic you showed, but:
        - First compute the interpolated HAZARD RATE (no time scaling).
        - Finally plug that rate into exp(-rate * year_fraction).

        Uses the curve's knots loaded into self._times (year-fractions from valuation_date)
        and self._rates (instantaneous hazards at those knots). Assumes self._times[0] == 0.0
        is a synthetic entry; the first real knot is index 1.
        """
        T = year_fraction(self.valuation_date, end_date, basis="ACT/365F")
        if T <= 0.0:
            return 1.0

        times = self._times
        rates = self._rates
        if not times or not rates:
            raise ValueError("Hazard curve not initialized.")

        # first real knot index (skip synthetic 0.0 if present)
        first = 1 if len(times) >= 2 and abs(times[0]) < 1e-16 else 0

        # Before first knot -> use first knot's rate
        if T <= times[first]:
            lam = rates[first]
            return math.exp(-lam * T)

        # After last knot -> use last knot's rate
        if T >= times[-1]:
            lam = rates[-1]
            return math.exp(-lam * T)

        # Find bracketing knots so that times[lo] <= T <= times[hi]
        lo, hi = first, len(times) - 1
        while hi - lo > 1:
            mid = (lo + hi) // 2
            if times[mid] <= T:
                lo = mid
            else:
                hi = mid

        t0, t1 = times[lo], times[hi]
        r0, r1 = rates[lo], rates[hi]

        # LINEAR INTERPOLATION OF THE HAZARD RATE (no time scaling here)
        w = (T - t0) / (t1 - t0) if t1 != t0 else 0.0
        lam = r0 + w * (r1 - r0)

        # FINAL STEP: plug interpolated rate into exponential with the year fraction
        return math.exp(-lam * T)
