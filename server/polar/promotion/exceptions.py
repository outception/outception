from polar.exceptions import PolarError


class PromotionUnavailable(PolarError):
    def __init__(self) -> None:
        super().__init__(
            "Paid promotions aren't configured.",
            status_code=503,
        )
