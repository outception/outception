from fastapi import APIRouter

from outception.auth.endpoints import router as auth_router
from outception.config import settings
from outception.oauth2.endpoints.oauth2 import router as oauth2_router
from outception.user.endpoints import router as user_router

router = APIRouter(prefix="/v1")

# The account surface is only mounted when accounts are enabled. With it off,
# /users, /auth and /oauth2 simply do not exist, so nothing can reach them.
# The public news wall never needs an account, so its routers (added in M2)
# are always mounted.
if settings.ACCOUNTS_ENABLED:
    # /users
    router.include_router(user_router)
    # /auth
    router.include_router(auth_router)
    # /oauth2
    router.include_router(oauth2_router)
