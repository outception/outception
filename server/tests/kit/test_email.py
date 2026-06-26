import pytest

from outception.kit.email import EmailNotValidError, unalias_email


class TestUnaliasEmail:
    def test_strips_alias_suffix(self) -> None:
        assert unalias_email("pieter+123@outception.com") == "pieter@outception.com"

    def test_strips_only_first_plus(self) -> None:
        assert unalias_email("pieter+a+b@outception.com") == "pieter@outception.com"

    def test_passes_through_when_no_alias(self) -> None:
        assert unalias_email("pieter@outception.com") == "pieter@outception.com"

    def test_invalid_email_raises(self) -> None:
        with pytest.raises(EmailNotValidError):
            unalias_email("not-an-email")
