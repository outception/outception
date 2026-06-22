from typing import Annotated

from fastapi import Depends

from polar.auth.dependencies import Authenticator
from polar.auth.models import AuthSubject, User

# Any authenticated user can buy a promotion and read their own promotions.
PromotionUser = Annotated[
    AuthSubject[User],
    Depends(Authenticator(required_scopes=set(), allowed_subjects={User})),
]
