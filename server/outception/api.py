from fastapi import APIRouter

import outception.news.sources  # noqa: F401 — registers source getters on import
from outception.auth.endpoints import router as auth_router
from outception.billing.endpoints import router as billing_router
from outception.email_update.endpoints import router as email_update_router
from outception.eventstream.endpoints import router as stream_router
from outception.integrations.github.endpoints import router as github_router
from outception.news.endpoints import router as news_router
from outception.oauth2.endpoints.oauth2 import router as oauth2_router
from outception.organization.endpoints import router as organization_router
from outception.organization_access_token.endpoints import (
    router as organization_access_token_router,
)
from outception.personal_access_token.endpoints import router as pat_router
from outception.promotion.endpoints import router as promotion_router
from outception.user.endpoints import router as user_router

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
