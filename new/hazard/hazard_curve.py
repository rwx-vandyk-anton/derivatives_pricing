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


def _parse_date_str(s: str, preferred_fmt: Optional[str] = None) -> Optional[date]:
    """
    Parse a date string trying (in order): preferred_fmt (if given),
    ISO 'YYYY-MM-DD', and 'DD/MM/YYYY'. Returns None if all fail.
    """
    s = s.strip()
    fmts = []
    if preferred_fmt:
        fmts.append(preferred_fmt)
    fmts.extend(["%Y-%m-%d", "%d/%m/%Y"])

    # Try datetime.strptime with known formats
    for fmt in fmts:
        try:
            return datetime.strptime(s, fmt).date()
        except Exception:
            pass

    # Last chance: fromisoformat for strict ISO (handles e.g. '2026-01-01')
    try:
        return date.fromisoformat(s)
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Hazard Rate Curve Handler
# ---------------------------------------------------------------------------

@dataclass
class HazardRateCurve:
    valuation_date: date
    _times: List[float] = field(default_factory=list, init=False)
    _rates: List[float] = field(default_factory=list, init=False)

    # ---------------------------- Loading ----------------------------------
    def load_from_csv(self, filepath: str, date_format: str | None = None) -> None:
        """
        Populate the curve from a CSV with two columns: Date, HazardRate.

        Parameters
        ----------
        filepath : str
            Path to CSV file. Header optional. Extra columns ignored.
        date_format : str | None
            Optional strptime pattern, e.g. "%d/%m/%Y".
        """
        rows: List[Tuple[date, float]] = []
        # utf-8-sig strips a possible BOM (ï»¿) on the first header cell
        with open(filepath, newline="", encoding="utf-8-sig") as f:
            reader = csv.reader(f)

            # Peek first row to detect header by attempting parse
            try:
                first = next(reader)
            except StopIteration:
                raise ValueError("CSV is empty.")

            def parse_row(row: List[str]) -> Tuple[date, float] | None:
                if not row or len(row) < 2:
                    return None
                d_raw, r_raw = row[0].strip(), row[1].strip()

                # Parse date (accept multiple formats)
                d = _parse_date_str(d_raw, preferred_fmt=date_format)
                if d is None:
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
                rates[-1] = r
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
        for t in self._times[1:]:
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
