from enum import StrEnum
from typing import TYPE_CHECKING, Annotated, cast

import pycountry
from pydantic.json_schema import WithJsonSchema


class CountryData:
    alpha_2: str


_ALL_COUNTRIES: set[str] = {
    cast(CountryData, country).alpha_2 for country in pycountry.countries
}
_SUPPORTED_COUNTRIES: set[str] = _ALL_COUNTRIES - {
    # US Trade Embargos
    "CU",
    "IR",
    "KP",
    "SY",
    "RU",
}
ALL_COUNTRIES = sorted(_ALL_COUNTRIES)
SUPPORTED_COUNTRIES = sorted(_SUPPORTED_COUNTRIES)

if TYPE_CHECKING:

    class CountryAlpha2(StrEnum):
        pass

    class CountryAlpha2Input(StrEnum):
        pass
else:
    CountryAlpha2 = Annotated[
        StrEnum("CountryAlpha2", [(country, country) for country in ALL_COUNTRIES]),
        WithJsonSchema(
            {
                "type": "string",
                "title": "CountryAlpha2",
                "enum": ALL_COUNTRIES,
                "x-speakeasy-enums": ALL_COUNTRIES,
            }
        ),
    ]
    CountryAlpha2Input = Annotated[
        StrEnum(
            "CountryAlpha2Input",
            [(country, country) for country in SUPPORTED_COUNTRIES],
        ),
        WithJsonSchema(
            {
                "type": "string",
                "title": "CountryAlpha2Input",
                "enum": SUPPORTED_COUNTRIES,
                "x-speakeasy-enums": SUPPORTED_COUNTRIES,
            }
        ),
    ]
