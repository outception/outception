from datetime import date
from typing import Literal

from pydantic import BaseModel

Dimension = Literal["path", "country"]


class VisitRow(BaseModel):
    """Views on one day for one page path or one visitor country."""

    day: date
    dimension: Dimension
    key: str
    views: int
