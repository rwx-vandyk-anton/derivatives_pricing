import unittest
import os
import shutil
import csv
import math
from datetime import date

from zero_coupon.instruments.zero_coupon_bond import ZeroCouponBond
from discount.discount import YieldCurve
from zero_coupon.pricers.zero_coupon_bond_pricer import ZeroCouponBondPricer


class TestZeroCouponBondPricer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Clean up any old outputs once before all tests
        project_root = os.getcwd()
        cls.results_dir = os.path.join(project_root, 'results')
        shutil.rmtree(cls.results_dir, ignore_errors=True)

    def setUp(self):
        # ─── Build timeline ───────────────────────────────────────────────
        self.val_date = date(2025, 6, 19)
        self.maturities = [date(2026, 6, 19)]

        # ─── Yield curve ─────────────────────────────────────────────────
        self.zero_rates = [0.05]
        self.curve = YieldCurve(
            zero_rates=self.zero_rates,
            maturities=self.maturities,
            value_date=self.val_date
        )

        # ─── Zero Coupon Bond ──────────────────────────────────────────────
        face_value = 1000
        self.bond = ZeroCouponBond(
            face_value, maturity_date=self.maturities[0]
        )
        self.pricer = ZeroCouponBondPricer(self.bond, self.curve)

        # ─── Define Results Path ─────────────────────────────────────────────
        self.expected_file = os.path.join(
            self.results_dir,
            f"zc_bond_{self.bond.maturity_date}.csv"
        )

    def test_present_value(self):
        # PV = 1000 * exp(-0.05 * 1)
        expected = 1_000 * math.exp(-0.05 * 1.0)
        npv = self.pricer.present_value()

        print(f"\n NPV: {npv:.6e}")

        self.assertAlmostEqual(npv, expected, places=4)

    def test_pv01(self):
        # PV01 = T * PV * 1e-4 = 1 * PV * 1e-4
        pv01 = self.pricer.pv01()

        print(f"\n pv01: {pv01:.6e}")

        self.pricer.print_details
        self.assertGreater(pv01, 0.0)

    def tearDown(self):
        shutil.rmtree(self.results_dir, ignore_errors=True)

    def test_export_to_csv(self):
        # Ensure results folder is clean
        if os.path.isdir(self.results_dir):
            for f in os.listdir(self.results_dir):
                os.remove(os.path.join(self.results_dir, f))

        # Run print_details to generate CSV
        self.pricer.print_details()

        # Check file exists
        self.assertTrue(os.path.exists(self.expected_file),
                        f"CSV file not found at {self.expected_file}")

        # Read and verify contents
        with open(self.expected_file, newline='') as csvfile:
            reader = csv.reader(csvfile)
            header = next(reader)
            row = next(reader)

        self.assertEqual(header, [
            'face_value', 'maturity_date', 'valuation_date',
            'zero_rate_cc', 'present_value', 'pv01'
        ])

        # Validate numeric fields
        face_value = float(row[0])
        self.assertEqual(face_value, 1000.0)

        # Zero rate formatted with percent sign
        self.assertTrue(row[3].endswith('%'))
        pv = float(row[4])
        self.assertAlmostEqual(pv, self.pricer.present_value(), places=4)
        pv01 = float(row[5])
        self.assertAlmostEqual(pv01, self.pricer.pv01(), places=4)


if __name__ == "__main__":
    unittest.main()
