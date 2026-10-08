"""The publication boundary: automation builds, a named human publishes.
Every workflow job that deploys, submits or pushes a release artifact
runs in the protected `production` environment, which requires a
reviewer. A job that builds and stores an artifact without shipping it
does not need one."""

import re
from pathlib import Path
from typing import Any

import pytest
import yaml

WORKFLOWS = Path(__file__).resolve().parent.parent.parent / ".github" / "workflows"

# Workflow -> jobs that publish.
PUBLISHING_JOBS = {
    "deploy.yml": {"deploy"},
    "app-build.yml": {"build"},
    # The ops tasks reach the host with the same credentials as a deploy.
    "ops-logs.yml": {"logs"},
    "ops-prune.yml": {"prune"},
    "ops-delete-user.yml": {"delete-user"},
    "ops-source-health.yml": {"health"},
}


def _jobs(name: str) -> dict[str, dict[str, Any]]:
    data = yaml.safe_load((WORKFLOWS / name).read_text())
    return data["jobs"]


@pytest.mark.parametrize(("workflow", "jobs"), sorted(PUBLISHING_JOBS.items()))
def test_publishing_jobs_sit_behind_the_boundary(workflow: str, jobs: set[str]) -> None:
    found = _jobs(workflow)
    for job in jobs:
        assert job in found, f"{workflow} lost its {job} job"
        env = found[job].get("environment")
        name = env["name"] if isinstance(env, dict) else env
        assert name == "production", (
            f"{workflow}:{job} must run in the production environment"
        )


def test_build_jobs_are_automation() -> None:
    build = _jobs("deploy.yml")["build"]
    assert "environment" not in build


def test_no_workflow_submits_to_a_store() -> None:
    """Store submission is a hand-run step; nothing in CI calls it."""
    for path in WORKFLOWS.glob("*.y*ml"):
        text = path.read_text()
        assert "eas submit" not in text, path.name
        assert "upload-google-play" not in text, path.name


@pytest.mark.parametrize(
    "workflow", sorted(path.name for path in WORKFLOWS.glob("*.y*ml"))
)
def test_ssh_steps_pin_the_host_key(workflow: str) -> None:
    """Every SSH step carries the fingerprint input and is preceded by the
    step that refuses to run while the variable is unset: without the pin
    the client would trust whoever answers and ship the secrets to it."""
    for job in _jobs(workflow).values():
        steps = job.get("steps", [])
        for index, step in enumerate(steps):
            if not str(step.get("uses", "")).startswith("appleboy/ssh-action@"):
                continue
            assert step.get("with", {}).get("fingerprint"), (
                f"{workflow}: no fingerprint"
            )
            assert index > 0, f"{workflow}: the SSH step must follow the pin check"
            assert steps[index - 1].get("name") == "Host key is pinned", (
                f"{workflow}: the SSH step must follow the pin check"
            )


# Keys only the host may hold: Caddy's DNS token, the backup's passphrase and
# bucket credentials, and the alert and health hooks.
HOST_ONLY = [
    "CF_API_TOKEN",
    "OUTCEPTION_BACKUP_PASSPHRASE",
    "OUTCEPTION_BACKUP_S3_ACCESS_KEY_ID",
    "OUTCEPTION_BACKUP_S3_SECRET_ACCESS_KEY",
    "OUTCEPTION_BACKUP_S3_BUCKET",
    "OUTCEPTION_ALERT_WEBHOOK_URL",
    "OUTCEPTION_HEALTHCHECK_URL",
]
APP_KEYS = ["OUTCEPTION_SECRET", "OUTCEPTION_S3_FILES_BUCKET_NAME", "OUTCEPTION_ENV"]


def test_the_app_env_leaves_out_every_host_only_key() -> None:
    """The deploy writes the app containers' env file by filtering the
    host's; the filter must catch every host-only name, digits and all."""
    text = (WORKFLOWS.parent.parent / "deploy" / "app-env.sh").read_text()
    match = re.search(r"grep -v -E '([^']+)'", text)
    assert match, "app-env.sh no longer filters with grep -v -E"
    pattern = re.compile(match.group(1))
    for key in HOST_ONLY:
        assert pattern.search(f"{key}=value"), f"{key} would reach the app"
    for key in APP_KEYS:
        assert not pattern.search(f"{key}=value"), f"{key} would be dropped"


def test_the_app_env_is_written_after_the_env_changes() -> None:
    """The deploy mints keys and moves the database inside .env.prod; the
    app's copy must be taken after that, or the containers start on the
    old values."""
    text = (WORKFLOWS / "deploy.yml").read_text()
    written = text.index("bash ./app-env.sh")
    for change in (
        "env_set OUTCEPTION_ENCRYPTION_LOCAL_KEY",
        "env_set OUTCEPTION_POSTGRES_DATABASE",
    ):
        assert text.index(change) < written, f"{change} comes after .env.app"
    assert written < text.index("until compose pull")
