from outception.auth import tasks as auth
from outception.dummy import tasks as dummy
from outception.email import tasks as email
from outception.oauth2 import tasks as oauth2

__all__ = [
    "auth",
    "dummy",
    "email",
    "oauth2",
]
