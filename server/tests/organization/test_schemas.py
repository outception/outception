import pytest
from pydantic import ValidationError

from outception.organization.schemas import OrganizationCreate, OrganizationUpdate


class TestBlockedWords:
    @pytest.mark.parametrize(
        "name",
        [
            "Porn Hub",
            "Sex Shop",
            "NSFW Art",
            "xxx studio",
            "SeX",
            "PORN",
        ],
    )
    def test_blocked_name_on_create(self, name: str) -> None:
        with pytest.raises(ValidationError, match="not allowed"):
            OrganizationCreate(name=name, slug="clean-slug")

    @pytest.mark.parametrize(
        "slug",
        [
            "porn-shop",
            "sex-shop",
            "nsfw-art",
            "xxx-studio",
        ],
    )
    def test_blocked_slug_on_create(self, slug: str) -> None:
        with pytest.raises(ValidationError, match="not allowed"):
            OrganizationCreate(name="Clean Name", slug=slug)

    @pytest.mark.parametrize(
        "name",
        [
            "Porn Hub",
            "Sex Shop",
            "NSFW Art",
        ],
    )
    def test_blocked_name_on_update(self, name: str) -> None:
        with pytest.raises(ValidationError, match="not allowed"):
            OrganizationUpdate(name=name)

    @pytest.mark.parametrize(
        "name",
        [
            "Essex County",
            "Middlesex Corp",
            "Sextant Navigation",
            "Acme Inc",
        ],
    )
    def test_allows_substring_matches(self, name: str) -> None:
        org = OrganizationCreate(name=name, slug="clean-slug")
        assert org.name == name

    def test_update_without_name_skips_validation(self) -> None:
        org = OrganizationUpdate(name=None)
        assert org.name is None


class TestSlugMaxLength:
    def test_slug_at_max_length_allowed(self) -> None:
        slug = "a" * 64
        org = OrganizationCreate(name="Clean Name", slug=slug)
        assert org.slug == slug

    def test_slug_too_long_rejected(self) -> None:
        slug = "a" * 65
        with pytest.raises(ValidationError, match="at most 64 characters"):
            OrganizationCreate(name="Clean Name", slug=slug)
