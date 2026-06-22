from fastapi import APIRouter

import polar.news.sources  # noqa: F401 — registers source getters on import
from polar.auth.endpoints import router as auth_router
from polar.billing.endpoints import router as billing_router
from polar.email_update.endpoints import router as email_update_router
from polar.eventstream.endpoints import router as stream_router
from polar.integrations.github.endpoints import router as github_router
from polar.news.endpoints import router as news_router
from polar.oauth2.endpoints.oauth2 import router as oauth2_router
from polar.organization.endpoints import router as organization_router
from polar.organization_access_token.endpoints import (
    router as organization_access_token_router,
)
from polar.personal_access_token.endpoints import router as pat_router
from polar.promotion.endpoints import router as promotion_router
from polar.user.endpoints import router as user_router

router = APIRouter(prefix="/v1")

# /users
router.include_router(user_router)
# /integrations/github
router.include_router(github_router)
# /personal_access_tokens
router.include_router(pat_router)
# /stream
router.include_router(stream_router)
# /organizations
router.include_router(organization_router)
# /auth
router.include_router(auth_router)
# /oauth2
router.include_router(oauth2_router)
# /organization-access-tokens
router.include_router(organization_access_token_router)
# /update-email
router.include_router(email_update_router)
# /news
router.include_router(news_router)
# /promotions
router.include_router(promotion_router)
# /billing
router.include_router(billing_router)
