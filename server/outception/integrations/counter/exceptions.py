class CounterError(Exception):
    """The counter did not answer, or answered with something unexpected."""


class CounterNotConfigured(CounterError):
    """No key or project id: the sync has nothing to read."""
