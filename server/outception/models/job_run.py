"""One row per model call or build: what ran, on which lane, which model
answered, under which prompt version, and how it ended. The operator
surface beside the health codes."""

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from sqlalchemy import TIMESTAMP, ForeignKey, Index, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from outception.kit.db.models import IDModel
from outception.kit.extensions.sqlalchemy import StringEnum


class JobKind(StrEnum):
    summary = "summary"
    score = "score"
    resolve = "resolve"
    build = "build"
    scrub_eval = "scrub_eval"


class JobState(StrEnum):
    queued = "queued"
    running = "running"
    completed = "completed"
    failed = "failed"
    timed_out = "timed_out"
    cancelled = "cancelled"


class JobRun(IDModel):
    __tablename__ = "job_runs"
    __table_args__ = (
        Index("ix_job_runs_kind_started_at", "kind", "started_at"),
        Index("ix_job_runs_subject", "subject"),
        Index(
            "ix_job_runs_open",
            "state",
            postgresql_where="state IN ('queued', 'running')",
        ),
    )

    kind: Mapped[JobKind] = mapped_column(StringEnum(JobKind), nullable=False)
    # A url digest, a cluster id, a profile id.
    subject: Mapped[str] = mapped_column(String(256), nullable=False)
    state: Mapped[JobState] = mapped_column(
        StringEnum(JobState), nullable=False, default=JobState.queued
    )
    lane: Mapped[str] = mapped_column(String(32), nullable=False)
    served_model: Mapped[str | None] = mapped_column(String(128), nullable=True)
    # From the prompt file's front matter.
    prompt_version: Mapped[str | None] = mapped_column(String(32), nullable=True)
    # sha256 of the rendered prompt; the text itself lives in Redis for a day.
    prompt_digest: Mapped[str | None] = mapped_column(String(64), nullable=True)
    tokens_in: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tokens_out: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # refusal | quota | auth | transient | malformed | internal
    error_class: Mapped[str | None] = mapped_column(String(32), nullable=True)
    # Scrubbed, truncated to 500 characters.
    error_detail: Mapped[str | None] = mapped_column(String(500), nullable=True)
    retry_of: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("job_runs.id", ondelete="set null"), nullable=True
    )
    started_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False
    )
    finished_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )
