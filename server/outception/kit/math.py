import math
from decimal import Decimal


def outception_round(number: int | float | Decimal) -> int:
    """
    Round to nearest integer, but round .5 away from 0.
    This means `outception_round(8.5) == 9.0` and `outception_round(-8.5) == -9.0`.

    We can't use Python's built-in `round()` as that rounds 0.5 to 0.0.
    """
    if number >= 0:
        return math.ceil(number) if number - int(number) >= 0.5 else math.floor(number)
    else:
        return math.floor(number) if number - int(number) <= -0.5 else math.ceil(number)
