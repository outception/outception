from typing import Annotated

from fastapi import Depends

from outception.auth.dependencies import Authenticator
from outception.auth.models import AuthSubject, User

# Any authenticated user can follow sources. Accepts web sessions and API
# tokens so both the web wall and the mobile feed can use it.
NewsUser = Annotated[
    AuthSubject[User],
    Depends(Authenticator(required_scopes=set(), allowed_subjects={User})),
]
