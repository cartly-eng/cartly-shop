import os
import sys
import threading
import time

import psycopg2
import psycopg2.pool

from shop.config import SERVICE
from shop.observability import DB_POOL_IN_USE, log

_pool = None


def dsn():
    return (f"host={os.environ.get('DB_HOST', 'postgres')} port={os.environ.get('DB_PORT', '5432')} "
            f"dbname={os.environ.get('DB_NAME', 'shop')} user={os.environ.get('DB_USER', 'shop')} "
            f"password={os.environ.get('DB_PASSWORD', '')} connect_timeout=3 application_name={SERVICE} "
            f"options='-c statement_timeout={os.environ.get('DB_STATEMENT_TIMEOUT_MS', '5000')}'")


POOL_MAX = int(os.environ.get("DB_POOL_MAX", "10"))
POOL_TIMEOUT_S = float(os.environ.get("DB_POOL_TIMEOUT_S", "30"))
_slots = threading.BoundedSemaphore(POOL_MAX)


def pool():
    global _pool
    if _pool is None:
        _pool = psycopg2.pool.ThreadedConnectionPool(1, POOL_MAX, dsn())
    return _pool


class conn:
    def __enter__(self):
        # Wait for a free pooled connection instead of failing fast with PoolError.
        if not _slots.acquire(timeout=POOL_TIMEOUT_S):
            raise psycopg2.pool.PoolError(f"timed out after {POOL_TIMEOUT_S}s waiting for a database connection")
        try:
            self.c = pool().getconn()
        except Exception:
            _slots.release()
            raise
        DB_POOL_IN_USE.labels(SERVICE).inc()
        return self.c

    def __exit__(self, exc_type, exc, tb):
        broken = exc_type is not None and issubclass(exc_type, (psycopg2.OperationalError, psycopg2.InterfaceError))
        if exc_type is None:
            self.c.commit()
        else:
            try:
                self.c.rollback()
            except Exception:
                broken = True
        pool().putconn(self.c, close=broken)
        _slots.release()
        DB_POOL_IN_USE.labels(SERVICE).dec()
        return False


def verify_on_startup():
    for attempt in range(1, 4):
        try:
            with conn() as c, c.cursor() as cur:
                cur.execute("SELECT 1")
            log.info("database connection verified")
            return
        except psycopg2.OperationalError as e:
            err = str(e).strip()
            log.error(f"database connection failed on startup: {err}", extra={"attempt": attempt, "error": err})
            if "password authentication failed" in err:
                break
            time.sleep(2)
    log.critical("cannot reach database with configured credentials, exiting")
    sys.exit(1)
