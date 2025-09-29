"""
Market data and curve definitions shared by all zero_coupon models.
"""
from .yield_curve import YieldCurve
from .cpi_publication import CPIPublication

__all__ = [
    "YieldCurve",
    "CPIPublication",
]
