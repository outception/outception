"""The catalog: every declared thing the wall can show, as data. Validated at
startup; every id referenced anywhere resolves or the load fails. The
registry over it is what the routes serve."""

from functools import cache

from .loader import Catalog, CatalogError, load_catalog
from .registry import Registry


@cache
def catalog() -> Catalog:
    return load_catalog()


@cache
def registry() -> Registry:
    return Registry(catalog())


__all__ = ["Catalog", "CatalogError", "Registry", "catalog", "load_catalog", "registry"]
