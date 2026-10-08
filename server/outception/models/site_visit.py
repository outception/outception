from datetime import date

from sqlalchemy import Date, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from outception.kit.db.models import RecordModel


class SiteVisit(RecordModel):
    """Site visits as the counter reports them, one row per day and key:
    the key is a page path or a visitor country, told apart by the
    dimension. Replaced on every sync, never summed."""

    __tablename__ = "site_visits"
    __table_args__ = (
        Index(
            "ix_site_visits_dimension_day_key", "dimension", "day", "key", unique=True
        ),
    )

    day: Mapped[date] = mapped_column(Date, nullable=False)
    dimension: Mapped[str] = mapped_column(String(16), nullable=False)
    key: Mapped[str] = mapped_column(String(200), nullable=False)
    views: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
