from typing import Annotated

from fastapi import Depends

from polar.auth.dependencies import Authenticator
from polar.auth.models import AuthSubject, Organization, User
from polar.auth.scope import Scope

_CLIRead = Authenticator(
    required_scopes={
        Scope.organizations_read,
        Scope.organizations_write,
    },
    allowed_subjects={User, Organization},
)
CLIRead = Annotated[AuthSubject[User | Organization], Depends(_CLIRead)]
