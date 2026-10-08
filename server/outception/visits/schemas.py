from datetime import date
from typing import Literal

from pydantic import BaseModel


class RaceRow(BaseModel):
    """One frame of a bar chart race: a day, a bar, its value."""

    date: date
    name: str
    value: int


RaceMode = Literal["products", "reach", "visits"]


class Race(BaseModel):
    """Rows for the chart, every day present for every name. `mode` tells
    the client what the names are: products racing by views, one product's
    views against its clicks, or site visits by page or country."""

    mode: RaceMode
    rows: list[RaceRow]
