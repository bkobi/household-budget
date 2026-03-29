"""
Drop-in replacement for get_db() that instruments every SQLite query.
Slow queries (> SLOW_QUERY_MS) are automatically shipped to Elasticsearch.
"""

import sqlite3
import time
import app as _app_module
from app.logger import log_slow_query, SLOW_QUERY_MS


class _InstrumentedCursor:
    def __init__(self, cursor: sqlite3.Cursor) -> None:
        self._cur = cursor

    def execute(self, sql: str, params=None):
        t0 = time.perf_counter()
        result = self._cur.execute(sql, params) if params is not None else self._cur.execute(sql)
        duration_ms = (time.perf_counter() - t0) * 1000
        if duration_ms >= SLOW_QUERY_MS:
            log_slow_query(sql, duration_ms, params)
        return result

    def executescript(self, sql: str):
        return _InstrumentedCursor(self._cur).execute(sql) if False else self._cur.executescript(sql)

    def fetchone(self):          return self._cur.fetchone()
    def fetchall(self):          return self._cur.fetchall()
    def fetchmany(self, n):      return self._cur.fetchmany(n)

    @property
    def lastrowid(self):         return self._cur.lastrowid
    @property
    def rowcount(self):          return self._cur.rowcount
    @property
    def description(self):       return self._cur.description


class _InstrumentedConnection:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn
        self._conn.row_factory = sqlite3.Row

    def execute(self, sql: str, params=None):
        return _InstrumentedCursor(self._conn.cursor()).execute(sql, params)

    def executescript(self, sql: str):
        return self._conn.executescript(sql)

    def cursor(self):
        return _InstrumentedCursor(self._conn.cursor())

    def commit(self):            self._conn.commit()
    def close(self):             self._conn.close()
    def __enter__(self):         return self
    def __exit__(self, *a):      self._conn.__exit__(*a)


def get_instrumented_db() -> _InstrumentedConnection:
    return _InstrumentedConnection(sqlite3.connect(_app_module.DB_PATH))
