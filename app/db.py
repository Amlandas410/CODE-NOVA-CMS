from contextlib import contextmanager
from flask import current_app
import mysql.connector


def init_app(app):
    # Connections are opened lazily so /login can load even before MySQL is configured.
    app.extensions["code_nova_cms_db"] = True


@contextmanager
def get_db():
    cfg=current_app.config
    connect_args = {
        "host": cfg["MYSQL_HOST"],
        "port": cfg["MYSQL_PORT"],
        "database": cfg["MYSQL_DATABASE"],
        "user": cfg["MYSQL_USER"],
        "password": cfg["MYSQL_PASSWORD"],
        "autocommit": False,
    }
    if cfg.get("MYSQL_SSL"):
        connect_args["ssl_disabled"] = False
        if cfg.get("MYSQL_SSL_CA"):
            connect_args["ssl_ca"] = cfg["MYSQL_SSL_CA"]
    conn=mysql.connector.connect(**connect_args)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def query(sql, params=(), one=False, dictionary=True):
    with get_db() as conn:
        cur=conn.cursor(dictionary=dictionary)
        cur.execute(sql, params)
        rows=cur.fetchone() if one else cur.fetchall()
        cur.close()
        return rows


def execute(sql, params=(), many=False):
    with get_db() as conn:
        cur=conn.cursor()
        if many: cur.executemany(sql, params)
        else: cur.execute(sql, params)
        last_id=cur.lastrowid
        cur.close()
        return last_id
