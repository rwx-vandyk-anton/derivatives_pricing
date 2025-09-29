import QuantLib as ql

# Need to add more conventions. These are only a start and therefore incomplete.
CONVENTIONS = {
    "USD-LIBOR-3M": {
        "calendar": ql.UnitedStates(m=ql.UnitedStates.GovernmentBond),
        "day_count": ql.Actual360(),
        "business_day_convention": ql.ModifiedFollowing,
        "settlement_days": 2,
        "index": lambda curve: ql.USDLibor(ql.Period("3M"), curve)
    },
    "USD-SOFR": {
        "calendar": ql.UnitedStates(m=ql.UnitedStates.GovernmentBond),
        "day_count": ql.Actual360(),
        "business_day_convention": ql.Following,
        "settlement_days": 2,
        "index": lambda curve: ql.Sofr(curve)
    }
}