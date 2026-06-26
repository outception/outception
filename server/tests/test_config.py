import pytest
from pydantic import ValidationError

from outception.config import INSECURE_DEFAULT_SECRET, Environment, Settings


class TestRequireStrongSecret:
    @pytest.mark.parametrize("env", [Environment.production, Environment.sandbox])
    def test_hosted_env_rejects_default_secret(self, env: Environment) -> None:
        with pytest.raises(ValidationError):
            Settings(ENV=env, SECRET=INSECURE_DEFAULT_SECRET)

    @pytest.mark.parametrize("env", [Environment.production, Environment.sandbox])
    def test_hosted_env_accepts_strong_secret(self, env: Environment) -> None:
        settings = Settings(ENV=env, SECRET="a-strong-unique-secret-value")
        assert settings.SECRET == "a-strong-unique-secret-value"

    @pytest.mark.parametrize("env", [Environment.development, Environment.testing])
    def test_local_env_allows_default_secret(self, env: Environment) -> None:
        # The default is fine locally; the guard only fires for hosted envs.
        settings = Settings(ENV=env, SECRET=INSECURE_DEFAULT_SECRET)
        assert settings.SECRET == INSECURE_DEFAULT_SECRET
