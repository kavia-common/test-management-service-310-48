"""Database helper module using psycopg2 connection pooling for Robot Framework service."""

import os
from contextlib import contextmanager
from psycopg2 import pool
from psycopg2.extras import RealDictCursor

DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/robotdb"
)


class DBPool:
    """Singleton wrapper for psycopg2 ThreadedConnectionPool."""

    _pool = None

    @classmethod
    def init(cls, minconn: int = 1, maxconn: int = 10) -> None:
        """Initialize the threaded connection pool."""
        if cls._pool is None:
            cls._pool = pool.ThreadedConnectionPool(
                minconn, maxconn, dsn=DATABASE_URL
            )

    @classmethod
    @contextmanager
    def get_conn(cls):
        """Context manager that yields a connection and returns it to the pool."""
        if cls._pool is None:
            raise RuntimeError("Database pool not initialized. Call DBPool.init().")

        conn = cls._pool.getconn()
        try:
            yield conn
        finally:
            cls._pool.putconn(conn)


def fetchall(query: str, params: tuple = ()) -> list[dict]:
    """Execute a SELECT query and return all rows."""
    with DBPool.get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, params)
            return cur.fetchall()


def fetchone(query: str, params: tuple = ()) -> dict | None:
    """Execute a SELECT query and return a single row."""
    with DBPool.get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, params)
            conn.commit()
            return cur.fetchone()


def execute(query: str, params: tuple = ()) -> None:
    """Execute a SQL query (INSERT, UPDATE, DELETE)."""
    with DBPool.get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)
            conn.commit()


def insert_fetchone(query: str, params: tuple = ()) -> dict | None:
    """Execute an INSERT ... RETURNING query and return the inserted row."""
    with DBPool.get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, params)
            row = cur.fetchone()
            conn.commit()
            return row


def init_db_pool() -> None:
    """Wrapper for backward compatibility."""
    DBPool.init()
