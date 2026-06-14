# db_pool.py - Database connection pool manager
# Tech stack: psycopg2.pool, threading
# Purpose: Shared PostgreSQL connection pool for production use.

import os
import psycopg2
from psycopg2 import pool
from utils.config_handler import database_conf
from utils.logger_handler import logger
import threading

_connection_pool = None
_pool_lock = threading.Lock()
_POOL_MIN_CONN = int(os.environ.get("DB_POOL_MIN_CONN", "2"))
_POOL_MAX_CONN = int(os.environ.get("DB_POOL_MAX_CONN", "10"))


def get_connection_pool():
    global _connection_pool
    if _connection_pool is None:
        with _pool_lock:
            if _connection_pool is None:
                try:
                    _connection_pool = pool.ThreadedConnectionPool(
                        _POOL_MIN_CONN, _POOL_MAX_CONN,
                        host=database_conf["host"],
                        port=database_conf["port"],
                        user=database_conf["user"],
                        password=database_conf["password"],
                        database=database_conf["database"],
                    )
                    logger.info("[DB_Pool] Connection pool created")
                except Exception as e:
                    logger.error("[DB_Pool] Failed: " + str(e))
                    raise
    return _connection_pool


def get_db_session():
    p = get_connection_pool()
    return p.getconn()


def put_db_session(conn):
    p = get_connection_pool()
    p.putconn(conn)


def close_all_connections():
    global _connection_pool
    if _connection_pool is not None:
        _connection_pool.closeall()
        _connection_pool = None
        logger.info("[DB_Pool] All connections closed")


def check_db_health() -> bool:
    conn = None
    try:
        conn = get_db_session()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        cursor.close()
        return True
    except:
        return False
    finally:
        if conn:
            put_db_session(conn)
