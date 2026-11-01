from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from psycopg import Connection
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from .config import Settings


class Database:
    """Small lifecycle wrapper around the server-only Postgres pool."""

    def __init__(self, settings: Settings) -> None:
        self._queue_name = settings.queue_name
        self._pool = ConnectionPool(
            conninfo=settings.database_url.get_secret_value(),
            min_size=settings.database_pool_min_size,
            max_size=settings.database_pool_max_size,
            kwargs={"row_factory": dict_row},
            open=False,
        )

    def open(self) -> None:
        self._pool.open()
        self._pool.wait(timeout=10)

    def close(self) -> None:
        self._pool.close()

    @contextmanager
    def connection(self) -> Iterator[Connection]:
        with self._pool.connection() as connection:
            yield connection

    def ready(self) -> bool:
        try:
            with self.connection() as connection:
                with connection.cursor() as cursor:
                    cursor.execute("select 1")
                    cursor.execute("select 1 from pgmq.meta where queue_name = %s", (self._queue_name,))
                    return cursor.fetchone() is not None
        except Exception:
            return False
