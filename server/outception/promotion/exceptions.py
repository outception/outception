from outception.exceptions import OutceptionError


class PromotionUnavailable(OutceptionError):
    def __init__(self) -> None:
        super().__init__(
            "Paid promotions aren't configured.",
            status_code=503,
        )
