import json
import sys
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, Discriminator, TypeAdapter

from polar.notifications.notification import (
    MaintainerAccountCreditsGrantedNotificationPayload,
    MaintainerNewPaidSubscriptionNotificationPayload,
    MaintainerNewProductSaleNotificationPayload,
)


class EmailTemplate(StrEnum):
    login_code = "login_code"
    email_update = "email_update"
    oauth2_leaked_client = "oauth2_leaked_client"
    oauth2_leaked_token = "oauth2_leaked_token"
    organization_access_token_leaked = "organization_access_token_leaked"
    organization_invite = "organization_invite"
    personal_access_token_leaked = "personal_access_token_leaked"
    notification_new_sale = "notification_new_sale"
    notification_new_subscription = "notification_new_subscription"
    notification_credits_granted = "notification_credits_granted"


class EmailProps(BaseModel):
    email: str


class LoginCodeProps(EmailProps):
    code: str
    code_lifetime_minutes: int
    domain: str


class LoginCodeEmail(BaseModel):
    template: Literal[EmailTemplate.login_code] = EmailTemplate.login_code
    props: LoginCodeProps


class EmailUpdateProps(EmailProps):
    token_lifetime_minutes: int
    url: str


class EmailUpdateEmail(BaseModel):
    template: Literal[EmailTemplate.email_update] = EmailTemplate.email_update
    props: EmailUpdateProps


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


class OrganizationAccessTokenLeakedProps(EmailProps):
    organization_access_token: str
    notifier: str
    url: str


class OrganizationAccessTokenLeakedEmail(BaseModel):
    template: Literal[EmailTemplate.organization_access_token_leaked] = (
        EmailTemplate.organization_access_token_leaked
    )
    props: OrganizationAccessTokenLeakedProps


class OrganizationInviteProps(EmailProps):
    organization_name: str
    inviter_email: str
    invite_url: str


class OrganizationInviteEmail(BaseModel):
    template: Literal[EmailTemplate.organization_invite] = (
        EmailTemplate.organization_invite
    )
    props: OrganizationInviteProps


class PersonalAccessTokenLeakedProps(EmailProps):
    personal_access_token: str
    notifier: str
    url: str


class PersonalAccessTokenLeakedEmail(BaseModel):
    template: Literal[EmailTemplate.personal_access_token_leaked] = (
        EmailTemplate.personal_access_token_leaked
    )
    props: PersonalAccessTokenLeakedProps


class NotificationNewSaleEmail(BaseModel):
    template: Literal[EmailTemplate.notification_new_sale] = (
        EmailTemplate.notification_new_sale
    )
    props: MaintainerNewProductSaleNotificationPayload


class NotificationNewSubscriptionEmail(BaseModel):
    template: Literal[EmailTemplate.notification_new_subscription] = (
        EmailTemplate.notification_new_subscription
    )
    props: MaintainerNewPaidSubscriptionNotificationPayload


class NotificationCreditsGrantedEmail(BaseModel):
    template: Literal[EmailTemplate.notification_credits_granted] = (
        EmailTemplate.notification_credits_granted
    )
    props: MaintainerAccountCreditsGrantedNotificationPayload


Email = Annotated[
    LoginCodeEmail
    | EmailUpdateEmail
    | OAuth2LeakedClientEmail
    | OAuth2LeakedTokenEmail
    | OrganizationAccessTokenLeakedEmail
    | OrganizationInviteEmail
    | PersonalAccessTokenLeakedEmail
    | NotificationNewSaleEmail
    | NotificationNewSubscriptionEmail
    | NotificationCreditsGrantedEmail,
    Discriminator("template"),
]

EmailAdapter: TypeAdapter[Email] = TypeAdapter(Email)


if __name__ == "__main__":
    openapi_schema = {
        "openapi": "3.1.0",
        "paths": {},
        "components": {
            "schemas": EmailAdapter.json_schema(
                mode="serialization", ref_template="#/components/schemas/{model}"
            )["$defs"]
        },
    }
    sys.stdout.write(json.dumps(openapi_schema, indent=2))
