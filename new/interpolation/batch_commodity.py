import pandas as pd
import numpy as np
from datetime import datetime
from pathlib import Path


def batch_vol_interpolation(vol_surface_path: str, test_cases_path: str, output_path: str = None):
    """
    Runs batch interpolation of vols for multiple test cases.
    Adds columns: Interpolated Vol, Abs Diff.
    """
    df_surface, moneyness_cols = load_vol_surface(vol_surface_path)
    df_cases = pd.read_csv(test_cases_path)

    results = []
    for _, row in df_cases.iterrows():
        target_date = row["Target Date"]
        strike = row["Strike"]
        spot = row["Spot"]
        actual_vol = row["Actual Vol"]

        interp_vol = interpolate_vol(df_surface, moneyness_cols, strike, spot, pd.to_datetime(target_date))
        abs_diff = abs(interp_vol - actual_vol)

        results.append({
            "Target Date": target_date,
            "Strike": strike,
            "Spot": spot,
            "Actual Vol": actual_vol,
            "Interpolated Vol": interp_vol,
            "Abs Diff": abs_diff
        })

    df_out = pd.DataFrame(results)
    if output_path:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        df_out.to_csv(output_path, index=False)
        print(f"✅ Results saved to {output_path}")

    return df_out