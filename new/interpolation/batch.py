import pandas as pd
from datetime import datetime
from vol_interpolator import bilinear_vol_interpolation_from_csv  # import your previous function

def batch_test_vol_interpolator(
    surface_csv_path: str,
    test_csv_path: str,
    valuation_date: str = "2025-07-28"
) -> pd.DataFrame:
    """
    Runs a batch test of the bilinear volatility interpolator using a test CSV.

    Parameters:
    -----------
    surface_csv_path : str
        Path to the main volatility surface CSV (used by the interpolator).
    test_csv_path : str
        Path to the test CSV containing Start Date, Forward Rate, Strike, and Vol columns.
    valuation_date : str
        Constant valuation date in format YYYY/MM/DD.

    Returns:
    --------
    pd.DataFrame
        DataFrame containing actual vol, interpolated vol, and relative absolute error.
    """
    # Load test dataset
    df_test = pd.read_csv(test_csv_path)
    df_test.columns = [c.strip() for c in df_test.columns]

    # Parse date
    val_date = datetime.strptime(valuation_date, "%Y/%m/%d")

    results = []

    for _, row in df_test.iterrows():
        start_date = datetime.strptime(str(row["Start Date"]), "%Y-%m-%d")
        forward = float(row["Forward Rate"])
        strike = float(row["Strike"])
        actual_vol = float(row["Vol"])

        # Run interpolator
        interpolated_vol = bilinear_vol_interpolation_from_csv(
            csv_path=surface_csv_path,
            strike=strike,
            forward=forward,
            cashflow_start=start_date,
            valuation_date=val_date
        )

        # Relative Absolute Error
        rae = abs(interpolated_vol - actual_vol) / actual_vol if actual_vol != 0 else None

        results.append({
            "Start Date": start_date,
            "Forward Rate": forward,
            "Strike": strike,
            "Actual Vol": actual_vol,
            "Interpolated Vol": interpolated_vol,
            "Relative Abs Error": rae
        })

    # Return as DataFrame
    results_df = pd.DataFrame(results)
    return results_df
