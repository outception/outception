from typing import Any, Literal

from pydantic import BaseModel, EmailStr, Field

MESSAGE_CHARS = 2000


class FeedbackCreate(BaseModel):
    message: str = Field(min_length=3, max_length=MESSAGE_CHARS)
    email: EmailStr | None = None
    surface: Literal["web", "app"] = "web"
    # Where the sheet was opened: page, card id, app version. Small.
    context: dict[str, Any] | None = Field(default=None, max_length=12)
