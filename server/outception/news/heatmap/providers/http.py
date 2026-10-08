"""The fetchers every table provider calls, through this module so a test
can stand in for them in one place."""

from ...fetch import NewsFetchError, fetch_bytes, fetch_html, fetch_json, fetch_text

__all__ = ["NewsFetchError", "fetch_bytes", "fetch_html", "fetch_json", "fetch_text"]
