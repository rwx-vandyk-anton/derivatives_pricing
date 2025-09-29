"""
Instrument definitions for zero-coupon bond, T-bill, fixed-rate bond,
and floater.
"""
from .zero_coupon_bond import ZeroCouponBond
from .treasury_bill import TreasuryBill
from .fixed_rate_bond import FixedRateBond
from .floating_rate_note import FloatingRateNote
from .inflation_linked_bond import InflationLinkedBond

__all__ = [
    "ZeroCouponBond",
    "TreasuryBill",
    "FixedRateBond",
    "FloatingRateNote",
    "InflationLinkedBond"
]
