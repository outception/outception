from typing import Annotated

from fastapi import Depends

from outception.auth.dependencies import Authenticator
from outception.auth.models import AuthSubject, User
from outception.auth.scope import Scope

# Any authenticated user can read their own promotions. Accepts web sessions
# and API tokens (web sessions carry all scopes; a token needs read or write).
# Write implies read, so a write-scoped token can read too.
PromotionUser = Annotated[
    AuthSubject[User],
    Depends(
        Authenticator(
            required_scopes={Scope.promotions_read, Scope.promotions_write},
            allowed_subjects={User},
        )
    ),
]

# Buying a promotion (a paid action) and changing promotion preferences require
# the write scope, so a narrowly read-scoped token can't spend on the user's
# behalf.
PromotionUserWrite = Annotated[
    AuthSubject[User],
    Depends(
        Authenticator(
            required_scopes={Scope.promotions_write},
            allowed_subjects={User},
        )
    ),
]
