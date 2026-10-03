"""The catalog: every declared thing the wall can show, as data. Validated at
startup; every id referenced anywhere resolves or the load fails."""

from .loader import Catalog, CatalogError, load_catalog

__all__ = ["Catalog", "CatalogError", "load_catalog"]
