from __future__ import annotations
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Dict
import csv
import math

# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------

def year_fraction(start: date, end: date) -> float:
    """Year fraction ACT/365F."""
    return (end - start).days / 365.0


# ---------------------------------------------------------------------------
# Zero Curve (NACA spot) -> Discount Factors & Forward Rates (no interpolation)
# ---------------------------------------------------------------------------

@dataclass
class ZeroCurve:
    """
    Zero curve with *NACA/365* spot pillars at exact dates (no interpolation).

    CSV schema (two columns; header optional):
        Date, ZeroNACA
        01/01/2026,0.0825
        01/01/2027,0.0830
        ...

    Conventions & formulas
    ----------------------
    - Input spot is NACA r_NA(d) (nominal annual compounding, ACT/365 base year).
    - Discount factor to date d at t years from valuation_date:
          D(d) = (1 + r_NA(d))^{-t}
    - Discount factor between two pillar dates A->B: DF = D(B)/D(A).
    - Forward rates over [A,B] with Δ = t_B - t_A:
         * Continuous:   f_cont = -ln(DF)/Δ
         * NACA/365:     f_naca = DF^{-1/Δ} - 1

    Notes
    -----
    - *Exact-date requirement:* All queried dates must exist in the CSV. No interpolation.
    - Rows prior to valuation_date are ignored; at least one row on/after valuation_date is required.
    """

    valuation_date: date
    _pillars: Dict[date, float] = field(default_factory=dict, init=False)  # stores NACA spot by date

    # ---------------------------- Loading ----------------------------------
    def load_from_csv(self, filepath: str) -> None:
        """Load pillars from CSV with two columns: Date(dd/mm/yyyy), ZeroNACA (nominal annual / 365)."""
        rows: Dict[date, float] = {}
        with open(filepath, newline="") as f:
            rdr = csv.reader(f)
            for row in rdr:
                if not row or len(row) < 2:
                    continue
                d_raw, r_raw = row[0].strip(), row[1].strip()
                # parse date in dd/mm/yyyy format
                try:
                    d = datetime.strptime(d_raw, "%d/%m/%Y").date()
                except Exception:
                    continue  # skip header or invalid
                # parse NACA
                try:
                    r_naca = float(r_raw)
                except Exception:
                    continue
                if d >= self.valuation_date:
                    rows[d] = r_naca
        if not rows:
            raise ValueError("CSV contains no rows on/after valuation_date.")
        # sort into pillars
        self._pillars = dict(sorted(rows.items()))

    # ----------------------------- API -------------------------------------
    def discount_factor(self, d_from: date, d_to: date) -> float:
        """Discount factor from d_from -> d_to (exact match required)."""
        if d_from == d_to:
            return 1.0
        if d_from not in self._pillars or d_to not in self._pillars:
            raise KeyError("Both dates must exist in pillar set.")
        tA = year_fraction(self.valuation_date, d_from)
        tB = year_fraction(self.valuation_date, d_to)
        rA = self._pillars[d_from]
        rB = self._pillars[d_to]
        # D(t) = (1 + r_NA)^(-t)
        DA = (1.0 + rA) ** (-tA)
        DB = (1.0 + rB) ** (-tB)
        return DB / DA

    def forward_rate_cont(self, d_start: date, d_end: date) -> float:
        """Continuous forward rate over [d_start, d_end] (exact match required)."""
        if d_start not in self._pillars or d_end not in self._pillars:
            raise KeyError("Both dates must exist in pillar set.")
        t0 = year_fraction(self.valuation_date, d_start)
        t1 = year_fraction(self.valuation_date, d_end)
        if t1 <= t0:
            raise ValueError("d_end must be after d_start")
        df = self.discount_factor(d_start, d_end)
        return -math.log(df) / (t1 - t0)

    def forward_rate_naca(self, d_start: date, d_end: date) -> float:
        """Equivalent annual NACA/365 forward over [d_start, d_end]."""
        if d_start not in self._pillars or d_end not in self._pillars:
            raise KeyError("Both dates must exist in pillar set.")
        t0 = year_fraction(self.valuation_date, d_start)
        t1 = year_fraction(self.valuation_date, d_end)
        if t1 <= t0:
            raise ValueError("d_end must be after d_start")
        df = self.discount_factor(d_start, d_end)
        delta = t1 - t0
        return (df ** (-1.0 / delta)) - 1.0


# ------------------------------- Example -----------------------------------
if __name__ == "__main__":
    # Example usage:
    # val = date(2025, 9, 22)
    # curve = ZeroCurveNACA(val)
    # curve.load_from_csv("zeros.csv")  # CSV: dd/mm/yyyy, NACA spot e.g. 0.085
    # d1, d2 = date(2026,1,1), date(2027,1,1)
    # print("DF(val->d1)", curve.discount_factor(val, d1))
    # print("DF(d1->d2)", curve.discount_factor(d1, d2))
    # print("f_cont(d1,d2)", curve.forward_rate_cont(d1, d2))
    # print("f_naca(d1,d2)", curve.forward_rate_naca(d1, d2))
    pass