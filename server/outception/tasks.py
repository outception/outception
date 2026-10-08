from outception.auth import tasks as auth
from outception.dummy import tasks as dummy
from outception.email import tasks as email
from outception.feedback import tasks as feedback
from outception.launches import tasks as launches
from outception.news import retention as news_retention
from outception.news import tasks as news
from outception.news.clusters import tasks as news_clusters
from outception.oauth2 import tasks as oauth2
from outception.visits import tasks as visits

__all__ = [
    "auth",
    "dummy",
    "email",
    "feedback",
    "launches",
    "news",
    "news_clusters",
    "news_retention",
    "oauth2",
    "visits",
]
