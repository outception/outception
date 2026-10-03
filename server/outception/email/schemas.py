import json
import sys
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, Discriminator, TypeAdapter


class EmailTemplate(StrEnum):
    login_code = "login_code"
    oauth2_leaked_client = "oauth2_leaked_client"
    oauth2_leaked_token = "oauth2_leaked_token"


class EmailProps(BaseModel):
    email: str


class LoginCodeProps(EmailProps):
    code: str
    code_lifetime_minutes: int
    domain: str


class LoginCodeEmail(BaseModel):
    template: Literal[EmailTemplate.login_code] = EmailTemplate.login_code
    props: LoginCodeProps


class OAuth2LeakedClientProps(EmailProps):
    token_type: str
    client_name: str
    notifier: str
    url: str


class OAuth2LeakedClientEmail(BaseModel):
    template: Literal[EmailTemplate.oauth2_leaked_client] = (
        EmailTemplate.oauth2_leaked_client
    )
    props: OAuth2LeakedClientProps


class OAuth2LeakedTokenProps(EmailProps):
    client_name: str
    notifier: str
    url: str


class OAuth2LeakedTokenEmail(BaseModel):
    template: Literal[EmailTemplate.oauth2_leaked_token] = (
        EmailTemplate.oauth2_leaked_token
    )
    props: OAuth2LeakedTokenProps


Email = Annotated[
    LoginCodeEmail | OAuth2LeakedClientEmail | OAuth2LeakedTokenEmail,
    Discriminator("template"),
]

EmailAdapter: TypeAdapter[Email] = TypeAdapter(Email)

if __name__ == "__main__":
    schema = EmailAdapter.json_schema(
        mode="serialization", ref_template="#/components/schemas/{model}"
    )
    openapi = {
        "openapi": "3.1.0",
        "info": {"title": "Email templates", "version": "1.0.0"},
        "paths": {},
        "components": {"schemas": schema.pop("$defs", {})},
    }
    json.dump(openapi, sys.stdout)
