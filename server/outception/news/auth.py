from typing import Annotated

from fastapi import Depends

from outception.auth.dependencies import Authenticator
from outception.auth.models import AuthSubject, User
from outception.auth.scope import Scope

# Any authenticated user can follow sources. Accepts web sessions (which carry
# every scope) and API tokens so both the web wall and the mobile feed can use
# it - but tokens must actually hold the user scopes: the news surface has no
# scopes of its own, so the generic user read/write pair is the narrowest gate.
NewsUser = Annotated[
    AuthSubject[User],
    Depends(Authenticator(required_scopes={Scope.user_read}, allowed_subjects={User})),
]

NewsUserWrite = Annotated[
    AuthSubject[User],
    Depends(Authenticator(required_scopes={Scope.user_write}, allowed_subjects={User})),
]
