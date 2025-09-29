from datetime import date


class TreasuryBill:
    """
    Details of the Treasury Bill
    """

    def __init__(
        self,
        face_value: float,
        discount_rate: float,
        maturity_date: date,
        value_date: date,
        day_count: float = 365,
    ):
        """
        :param face_value: par amount (e.g. 100)
        :param discount_rate: annual discount yield (e.g. 0.05 for 5%)
        :param maturity_date: date when the bill matures
        :param value_date: valuation date
        """
        if maturity_date < value_date:
            raise ValueError("maturity_date must be on or after value_date")

        self.face_value = face_value
        self.discount_rate = discount_rate
        self.maturity_date = maturity_date
        self.value_date = value_date
        self.day_count = day_count
