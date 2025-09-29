import QuantLib as ql  # type: ignore
from datetime import date
from typing import Dict, Tuple, List


class CPITermStructure:
    """
    Builds a handle to a ZeroInflationTermStructure that
    (a) interpolates your historical first-of-month CPI fixings
    (b) if given inflation swap quotes + a nominal curve, bootstraps
        a market-implied forward-CPI curve via PiecewiseZeroInflation.
    """
    def __init__(
        self,
        historical_cpi: Dict[date, float],
        inflation_swap_quotes: List[Tuple[ql.Period, float]],
        nominal_curve_handle: ql.YieldTermStructureHandle,
        observation_lag: ql.Period = ql.Period(4, ql.Months),
        calendar: ql.Calendar = ql.SouthAfrica(),
        frequency=ql.Monthly,
        day_counter: ql.DayCounter = ql.Actual365Fixed(),
        availability_lag: ql.Period = ql.Period(1, ql.Months),
        currency: ql.Currency = ql.ZARCurrency(),
    ):
        # sort & store
        self._cpi_data = sorted(historical_cpi.items())
        self.observation_lag = observation_lag
        self.calendar = calendar
        self.frequency = frequency
        self.day_counter = day_counter
        self.availability_lag = availability_lag
        self.currency = currency
        self.inflation_swap_quotes = inflation_swap_quotes or []
        self.nominal_curve_handle = nominal_curve_handle

    def build_handle(
        self, base_date: date
    ) -> ql.ZeroInflationTermStructureHandle:
        """
        Return a Handle[ZeroInflationTermStructure] that
        covers both historical CPI (lagged interpolation)
        and projects future CPI by capitalizing the latest
        published index with your real zero curve.
        """
        # 1) set value date and issue date
        ql_value_date = self.nominal_curve_handle.referenceDate()
        ql_base_date = ql.Date(base_date.day, base_date.month, base_date.year)

        # 2) set issue date lag, so data can be filtered from here
        ql_base_date_lagged = self.calendar.advance(
            ql_base_date,
            -self.availability_lag
        )
        ql_base_date_start = date(
            ql_base_date_lagged.year(),
            ql_base_date_lagged.month(),
            1
        )

        # 2) filter historical CPI data
        #    to only include data from the value period start
        #    (e.g. 1 months before the base date)
        filtered_cpi_data = [
            (cpi_date, cpi) for cpi_date, cpi in self._cpi_data
            if cpi_date >= ql_base_date_start
        ]
        if (
            not filtered_cpi_data
            or filtered_cpi_data[0][0] > ql_base_date_start
        ):
            raise ValueError(
                "No CPI data available for the specified base date. "
                "Ensure that the base date is after the earliest CPI data."
            )

        # 3) Build a dummy empty handle
        dummy_zero_curve = ql.ZeroInflationTermStructureHandle()

        # 5) otherwise bootstrap market implied forward-CPI levels
        # 5a) temp index seeded with history
        region = ql.CustomRegion("South Africa", "ZA")
        temp_zero_index = ql.ZeroInflationIndex(
            "CPI SA YoY",               # family name
            region,                     # region
            False,                      # revised?
            self.frequency,             # frequency of the published index
            self.availability_lag,      # availability lag
            ql.ZARCurrency(),           # currency
            dummy_zero_curve,           # ZeroInflationTermStructureHandle
        )
        for cpi_date, cpi in filtered_cpi_data:
            temp_zero_index.addFixing(
                ql.Date(cpi_date.day, cpi_date.month, cpi_date.year),
                cpi
            )

        # 5b) build helpers from real swap quotes
        helpers = []
        for mat_date, quote in self.inflation_swap_quotes:
            maturity_date = ql.Date(
                mat_date.day, mat_date.month, mat_date.year
            )
            helpers.append(
                ql.ZeroCouponInflationSwapHelper(
                    ql.QuoteHandle(ql.SimpleQuote(quote/100)),
                    self.observation_lag,
                    maturity_date,
                    self.calendar,
                    ql.ModifiedFollowing,
                    self.day_counter,
                    temp_zero_index,
                    ql.CPI.Linear,
                    self.nominal_curve_handle
                )
            )

        # 5c) Bootstrap the PieceWiseZeroInflation curve
        pw_inflation_curve = ql.PiecewiseZeroInflation(
            ql_value_date,
            self.calendar,
            self.day_counter,
            self.availability_lag,
            self.frequency,
            0.03,  # initial zero-CPI guess or initial value
            helpers
        )
        pw_inflation_curve.enableExtrapolation()
        return ql.ZeroInflationTermStructureHandle(pw_inflation_curve)

    def build_index(self, issue_date: date) -> ql.ZeroInflationIndex:
        """
        Wrap the TS handle in QuantLib's built-in ZACPI index, seeded with
        fixings. This index will:
          - apply the 4/3m lag + linear interpolation for past dates
          - use your forward curve for future dates
        """
        # Initiate term structure handle
        term_struct_handle = self.build_handle(issue_date)

        # wrap in a full ZeroInflationIndex where we can force interpolation
        zar_region = ql.CustomRegion("South Africa", "ZA")
        zar_cpi_index = ql.ZeroInflationIndex(
            "CPI-SA",
            zar_region,
            False,
            self.frequency,
            self.availability_lag,
            ql.ZARCurrency(),
            term_struct_handle
        )
        # seed all historical fixings
        # (so that first-4m fixings come from your table)
        for cpi_date, cpi in self._cpi_data:
            ql_cpi_date = ql.Date(cpi_date.day, cpi_date.month, cpi_date.year)
            zar_cpi_index.addFixing(ql_cpi_date, cpi)
        return zar_cpi_index
