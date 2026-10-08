"""Who the admin list is: the addresses in settings, plus any account
flagged by hand in the database. One answer for the API's gates and for
the user record the web reads."""

from outception.config import settings
from outception.models import User


def is_admin_address(email: str) -> bool:
    admins = {address.lower() for address in settings.ADMIN_EMAILS}
    return email.lower() in admins


def is_admin(user: User) -> bool:
    return bool(user.is_admin) or is_admin_address(user.email)
