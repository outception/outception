import dramatiq

from outception.worker._broker import get_broker
from outception.worker._encoder import JSONEncoder

# Entrypoint for workers whose queues never touch PostgreSQL. Building the broker
# without the SQLAlchemy middleware avoids creating a database engine/pool the
# worker would never use. The broker must be set as the global broker before
# `outception.tasks` is imported, so actors are declared against it rather than the
# default (database-backed) broker created by `outception.worker`.
broker = get_broker(database=False)
dramatiq.set_broker(broker)
dramatiq.set_encoder(JSONEncoder(broker))

from outception import tasks  # noqa: E402
from outception.logfire import configure_logfire  # noqa: E402
from outception.logging import configure as configure_logging  # noqa: E402
from outception.sentry import configure_sentry  # noqa: E402

configure_sentry()
configure_logfire("worker")
configure_logging(logfire=True)

__all__ = ["broker", "tasks"]
