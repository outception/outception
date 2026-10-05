"""The publication boundary: automation builds, a named human publishes.
Every workflow job that deploys, submits or pushes a release artifact
runs in the protected `production` environment, which requires a
reviewer. A job that builds and stores an artifact without shipping it
does not need one."""

from pathlib import Path
from typing import Any

import pytest
import yaml

WORKFLOWS = Path(__file__).resolve().parent.parent.parent / ".github" / "workflows"

# Workflow -> jobs that publish.
PUBLISHING_JOBS = {
    "deploy.yml": {"deploy"},
    "app-build.yml": {"build"},
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
