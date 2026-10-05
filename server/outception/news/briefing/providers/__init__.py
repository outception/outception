"""The two push transports. Each takes one subscription and one message
and returns `delivered`, `gone` (the endpoint is dead; drop the row) or
`failed` (try again tomorrow). Vendor names stay in these modules."""

from typing import Literal

Outcome = Literal["delivered", "gone", "failed"]

__all__ = ["Outcome"]
