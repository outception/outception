from outception.auth import tasks as auth
from outception.dummy import tasks as dummy
from outception.email import tasks as email
from outception.feedback import tasks as feedback
from outception.launches import tasks as launches
from outception.news import retention as news_retention
from outception.news import tasks as news
from outception.oauth2 import tasks as oauth2

__all__ = [
    "auth",
    "dummy",
    "email",
    "feedback",
    "launches",
    "news",
    "news_retention",
    "oauth2",
]
