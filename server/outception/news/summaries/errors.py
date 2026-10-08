"""The summary path's exceptions: what the routes turn into status codes
and what the budget marks as a failure."""

from outception.exceptions import OutceptionError

from ..fetch import NewsFetchError


class SummariesNotConfigured(OutceptionError):
    def __init__(self) -> None:
        super().__init__("Summaries are not configured", 503)


class SummaryUnavailable(OutceptionError):
    expected = True

    def __init__(self) -> None:
        super().__init__("Summary is unavailable for this article", 502)


class NoArticleText(NewsFetchError):
    """The page did not yield an article, but may have exposed a short
    publisher-written teaser (description tag, paywall standfirst)."""

    def __init__(self, reason: str, teaser: str | None = None) -> None:
        super().__init__(reason)
        self.teaser = teaser


class LiveDeadlinePassed(NewsFetchError):
    """A live tap ran out of time before the model started writing."""
