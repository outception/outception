from typing import Annotated

from fastapi import Depends

from outception.auth.dependencies import Authenticator
from outception.auth.models import AuthSubject, Organization, User
from outception.auth.scope import Scope

_CLIRead = Authenticator(
    required_scopes={
        Scope.organizations_read,
        Scope.organizations_write,
    },
    allowed_subjects={User, Organization},
)
CLIRead = Annotated[AuthSubject[User | Organization], Depends(_CLIRead)]
