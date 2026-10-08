import pytest
from reauth.factors.backup_codes import (
    AlreadyUsedBackupCodeException,
    InvalidBackupCodeException,
)

from outception.auth.factors import BackupCodesFactor
from outception.config import settings
from outception.kit.crypto import get_token_hash_candidates
from outception.models import BackupCodesEnrollment, User
from outception.postgres import AsyncSession
from tests.fixtures.database import SaveFixture


@pytest.mark.asyncio
class TestBackupCodesFactorVerify:
    @pytest.fixture
    def rotated(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            settings, "HASH_SECRETS", {"k1": "retired", "k2": "current"}
        )
        monkeypatch.setattr(settings, "CURRENT_HASH_SECRET_ID", "k2")

    async def _enroll_under(
        self,
        save_fixture: SaveFixture,
        user: User,
        secret_id: str,
        codes: list[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> BackupCodesEnrollment:
        monkeypatch.setattr(settings, "CURRENT_HASH_SECRET_ID", secret_id)
        hashes = [get_token_hash_candidates(code)[secret_id] for code in codes]
        monkeypatch.setattr(settings, "CURRENT_HASH_SECRET_ID", "k2")
        enrollment = BackupCodesEnrollment(
            identity_id=user.id, codes_hashes=hashes, used_codes_hashes=[]
        )
        await save_fixture(enrollment)
        return enrollment

    async def test_accepts_a_code_hashed_under_a_retired_secret(
        self,
        save_fixture: SaveFixture,
        session: AsyncSession,
        user: User,
        rotated: None,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        enrollment = await self._enroll_under(
            save_fixture, user, "k1", ["AAAAAAAAAA", "BBBBBBBBBB"], monkeypatch
        )

        factor = BackupCodesFactor(session)
        verified = await factor.verify(user.id, "AAAAAAAAAA")

        current = get_token_hash_candidates("AAAAAAAAAA")["k2"]
        assert current in verified.codes_hashes
        assert verified.used_codes_hashes == [current]

        await session.refresh(enrollment)
        assert current in enrollment.codes_hashes
        assert enrollment.used_codes_hashes == [current]

    async def test_leaves_the_other_codes_under_their_secret(
        self,
        save_fixture: SaveFixture,
        session: AsyncSession,
        user: User,
        rotated: None,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        enrollment = await self._enroll_under(
            save_fixture, user, "k1", ["AAAAAAAAAA", "BBBBBBBBBB"], monkeypatch
        )

        factor = BackupCodesFactor(session)
        await factor.verify(user.id, "AAAAAAAAAA")

        await session.refresh(enrollment)
        assert get_token_hash_candidates("BBBBBBBBBB")["k1"] in enrollment.codes_hashes

    async def test_rejects_an_unknown_code(
        self,
        save_fixture: SaveFixture,
        session: AsyncSession,
        user: User,
        rotated: None,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        await self._enroll_under(save_fixture, user, "k1", ["AAAAAAAAAA"], monkeypatch)

        factor = BackupCodesFactor(session)
        with pytest.raises(InvalidBackupCodeException):
            await factor.verify(user.id, "ZZZZZZZZZZ")

    async def test_rejects_a_code_already_used_under_a_retired_secret(
        self,
        save_fixture: SaveFixture,
        session: AsyncSession,
        user: User,
        rotated: None,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        enrollment = await self._enroll_under(
            save_fixture, user, "k1", ["AAAAAAAAAA"], monkeypatch
        )
        enrollment.used_codes_hashes = list(enrollment.codes_hashes)
        await save_fixture(enrollment)

        factor = BackupCodesFactor(session)
        with pytest.raises(AlreadyUsedBackupCodeException):
            await factor.verify(user.id, "AAAAAAAAAA")
