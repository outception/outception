import pytest

from outception.config import settings


@pytest.fixture(autouse=True)
def _paid_model_id(monkeypatch: pytest.MonkeyPatch) -> None:
    """The tree never names the paid lane's model; the tests need one so the
    paid provider counts as configured when a key is set."""
    monkeypatch.setattr(settings, "SUMMARY_MODEL", "paid-model-for-tests")
