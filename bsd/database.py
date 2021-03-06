import pymongo
import os, sys
from pymongo import DESCENDING, ASCENDING
from contextlib import contextmanager
import settings

dbconns = {}

db_client = None
def dbclient():
    # TODO: configurable database settings
    global db_client
    if db_client is None:
        url = settings.db_conn
        db_client = pymongo.MongoClient(url, maxPoolSize=1)
    return db_client

def conn(netname):
    c = dbclient()['blockstore_%s' % netname]
    return c

@contextmanager
def transaction(conn, isolation='mvcc'):
    conn.command('beginTransaction', isolation=isolation)
    try:
        yield conn
        conn.command('commitTransaction')
    except:
        conn.command('rollbackTransaction')
        raise


def rollback(conn):
    conn.command('rollbackTransaction')
