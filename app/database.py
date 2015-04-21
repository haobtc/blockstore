import pymongo

from pymongo import DESCENDING, ASCENDING
from contextlib import contextmanager

dbconns = {}

db_client = None
def dbclient():
    global db_client
    if db_client is None:
        url = 'mongodb://localhost:27017/'
        db_client = pymongo.MongoClient(url)
    return db_client
    
def conn(netname):
    return dbclient()['blocks_%s' % netname]

@contextmanager
def transaction(conn):
    conn.runCommand('beginTransaction')
    try:
        yield conn
        conn.runCommand('commitTransaction')
    except:
        conn.runCommand('rollbackTransaction')
        import traceback
        traceback.print_exc()
        raise

        
