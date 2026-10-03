"""Units: what a call costs against a cap. Free lanes count calls, the paid
lane counts tokens through the cost table."""

# Units per thousand tokens for paid models; one call on a free lane is one
# unit. The table is keyed by the provider id, not a vendor name, so the
# lane chains can be read without knowing who serves them.
PAID_UNITS_PER_KTOKEN: dict[str, float] = {
    "paid": 1.0,
}

MIN_UNITS = 1


def estimate_units(
    *, provider: str, prompt_chars: int, typical_reply_tokens: int
) -> int:
    """A conservative estimate for the reservation: tokens in from the
    rendered prompt length, tokens out from the lane's typical reply size."""
    rate = PAID_UNITS_PER_KTOKEN.get(provider)
    if rate is None:
        return MIN_UNITS
    tokens_in = prompt_chars / 4
    return max(MIN_UNITS, int((tokens_in + typical_reply_tokens) / 1000 * rate + 0.999))


def real_units(*, provider: str, tokens_in: int, tokens_out: int) -> int:
    rate = PAID_UNITS_PER_KTOKEN.get(provider)
    if rate is None:
        return MIN_UNITS
    return max(MIN_UNITS, int((tokens_in + tokens_out) / 1000 * rate + 0.999))
