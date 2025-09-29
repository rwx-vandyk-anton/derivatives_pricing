# hazard_curve.py

import csv
import re
from typing import List, Tuple, Optional

import QuantLib as ql


from datetime import date, timedelta
from dateutil.relativedelta import relativedelta



def import_hazard_curve(csv_file: str) -> List[Tuple[str, float]]:
    """
    Reads a CSV with columns "Tenor" and "Rate" (delimiter can be ',' or ';',
    and it'll tolerate a BOM on the Tenor header) and returns a list of
    (tenor_str, hazard_rate) pairs.
    """
    data: List[Tuple[str, float]] = []
    with open(csv_file, newline="", encoding="utf-8-sig") as f:
        sample = f.read(1024)
        f.seek(0)
        dialect = csv.Sniffer().sniff(sample, delimiters=";,")
        reader = csv.DictReader(f, dialect=dialect)

        for row in reader:
            tenor_key = "Tenor"
            if tenor_key not in row:
                bom_key = next((k for k in row if k.strip().endswith("Tenor")), None)
                tenor_key = bom_key or tenor_key

            tenor = row[tenor_key].strip()
            rate = float(row["Rate"])
            data.append((tenor, rate))
    return data


def allocate_hazard_dates(
    value_date: date,
    tenors: List[str],
    calendar: Optional[ql.Calendar] = None,
    spot_lag: int = 2,
    spot_lag_convention: int = ql.Following
) -> List[date]:
    """
    Build pillar dates by:
      1) moving value_date → spot_date (T+spot_lag business days)
      2) doing a pure calendar roll for each tenor
      3) if that roll lands on Sunday, bump by spot_lag business days
    """
    # 1) Compute spot date
    if calendar is None:
        spot_date = value_date + timedelta(days=spot_lag)
    else:
        ql_val  = ql.Date(value_date.day, value_date.month, value_date.year)
        ql_spot = calendar.advance(ql_val, spot_lag, ql.Days, spot_lag_convention)
        spot_date = date(ql_spot.year(), ql_spot.month(), ql_spot.dayOfMonth())

    pillar_dates: List[date] = []
    for tenor in tenors:
        m = re.fullmatch(r"\s*(\d+)\s*([mMyY])\s*", tenor)
        if not m:
            raise ValueError(f"Cannot parse tenor '{tenor}'")
        n, unit = int(m.group(1)), m.group(2).lower()

        # 2) Pure calendar roll
        if unit == "m":
            raw_date = spot_date + relativedelta(months=n)
        else:  # 'y'
            raw_date = spot_date + relativedelta(years=n)

        # 3) Sunday bump?
        if raw_date.weekday() == 6:  # Sunday == 6
            if calendar is None:
                new_date = raw_date + timedelta(days=spot_lag)
            else:
                ql_raw = ql.Date(raw_date.day, raw_date.month, raw_date.year)
                ql_adj = calendar.advance(ql_raw, spot_lag, ql.Days, spot_lag_convention)
                new_date = date(ql_adj.year(), ql_adj.month(), ql_adj.dayOfMonth())
        else:
            new_date = raw_date

        pillar_dates.append(new_date)

    return pillar_dates
