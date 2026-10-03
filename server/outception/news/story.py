"""One story across its publishers: the cluster with every member, for
the coverage line and the share page."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from outception.exceptions import ResourceNotFound
from outception.postgres import AsyncSession

from .clusters import repository
from .registry import SOURCES


class StoryMember(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    source_id: str = Field(alias="sourceId")
    source_name: str = Field(alias="sourceName")
    logo: str | None = None
    title: str
    url: str
    pub_date: int | None = Field(default=None, alias="pubDate")
    seen_at: int = Field(alias="seenAt")


class StoryResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    title: str
    publisher_count: int = Field(alias="publisherCount")
    lead_source_id: str = Field(alias="leadSourceId")
    lead_source_name: str = Field(alias="leadSourceName")
    first_seen_at: int = Field(alias="firstSeenAt")
    last_seen_at: int = Field(alias="lastSeenAt")
    items: list[StoryMember]


def _ms(when: datetime) -> int:
    return int(when.timestamp() * 1000)


def _name(source_id: str) -> str:
    return str(SOURCES.get(source_id, {}).get("name") or source_id)


async def get_story(session: AsyncSession, story_id: str) -> StoryResponse:
    try:
        cluster_id = UUID(story_id)
    except ValueError as e:
        raise ResourceNotFound("Unknown story") from e
    cluster = await repository.get(session, cluster_id)
    if cluster is None:
        raise ResourceNotFound("Unknown story")
    members = await repository.members(session, cluster_id)
    return StoryResponse.model_validate(
        {
            "id": str(cluster.id),
            "title": cluster.title,
            "publisherCount": cluster.publisher_count,
            "leadSourceId": cluster.lead_source_id,
            "leadSourceName": _name(cluster.lead_source_id),
            "firstSeenAt": _ms(cluster.first_seen_at),
            "lastSeenAt": _ms(cluster.last_seen_at),
            "items": [
                {
                    "sourceId": member.source_id,
                    "sourceName": _name(member.source_id),
                    "logo": str(SOURCES.get(member.source_id, {}).get("logo") or "")
                    or None,
                    "title": member.title,
                    "url": member.url,
                    "pubDate": _ms(member.pub_date) if member.pub_date else None,
                    "seenAt": _ms(member.seen_at),
                }
                for member in members
            ],
        }
    )
