import time
import logging
from pymongo import DESCENDING, ASCENDING
import pymongo.errors
from datetime  import datetime, timedelta
from bson.binary import Binary
from bson.objectid import ObjectId
from helper import resolve_network, utc_now
from blockstore import BlockStoreService, ttypes
import database

def get_var(conn, key):
    return conn.var.find_one({'key': key})

def set_var(conn, key, **kw):
    conn.var.update({'key': key}, {'$set': kw}, upsert=True)

def clear_var(conn, key):
    conn.var.remove({'key': key})

def set_peers(conn, peers):
    set_var(conn, 'peers', peers=peers)

def get_peers(conn):
    v = get_var(conn, 'peers')
    if not v:
        # for backward compatibility
        v = get_var(conn, 'peers.%s' % resolve_network(conn.nettype))
    if v:
        return v['peers']
    return []

# cursor on collections

def itercol(conn, col, key, n, batch=1):
    #for _ in xrange(n):
    total = 0
    while total <= n:
        v = get_var(conn, key)
        obj = None
        t = 0
        if v:
            objid = v['objid']
            t = v.get('times', 0)
            objs = list(col.
                        find({'_id': {'$gt': objid}}).
                        sort([('_id', 1)]).
                        limit(batch))
        else:
            objs = list(col.find().
                        sort([('_id', 1)]).
                        limit(batch))
        if len(objs) == 0:
            break
        total += len(objs)
        t += len(objs)
        for obj in objs:
            yield obj
        set_var(conn, key, objid=obj['_id'], times=t)

def fetchcol(conn, col, key):
    v = get_var(conn, key)
    obj = None
    if v:
        objid = v['objid']
        t = v.get('times', 0)
        objs = list(col.
                    find({'_id': {'$gt': objid}}).
                    sort([('_id', 1)]).
                    limit(1))
    else:
        objs = list(col.find().
                    sort([('_id', 1)]).
                    limit(1))
        t = 0
    if len(objs) == 0:
        return

    t += 1
    obj = objs[0]
    for _ in xrange(5):
        try:
            set_var(conn, key, objid=obj['_id'], times=t)
            break
        except pymongo.errors.OperationFailure:
            logging.error('pymongo operation failure at set_var(%s, %s)', key, obj['_id'], exc_info=True)
            time.sleep(0.01)
    return obj

def titercol(conn, col, key, n, isolation='mvcc'):
    for _ in xrange(n):
        with database.transaction(conn, isolation=isolation) as conn:
            obj = fetchcol(conn, col, key)
            if not obj:
                return
            yield obj

def idslice(col, start_seconds, end_seconds=0):
    start_delta = timedelta(seconds=start_seconds)
    
    start_objid = ObjectId.from_datetime(utc_now() - start_delta)
    end_delta = timedelta(seconds=end_seconds)
    end_objid = ObjectId.from_datetime(utc_now() - end_delta)
    for obj in col.find({'_id': {'$gte': start_objid,
                                 '$lt': end_objid}}).sort('_id'):
        yield obj


def return_borrowed_peers(conn):
    # return the borrowed pool
    now_time = int(time.time())
    conn.peerpool.update({'borrowed': 1, 'lastBorrowed': {'$lt': now_time - 300}},
                         {'$set': {'borrowed': 0}},
                         multi=True)
    
def push_peers(conn, peers):
    now_time = int(time.time())
    for peer in peers:
        conn.peerpool.update({'host': peer.host, 'port': peer.port},
                             {'$set': {'lastSeen': now_time, 'version': (peer.version or 0)}},
                             upsert=True)

    return_borrowed_peers(conn)

def pop_peers(conn, n):
    return_borrowed_peers(conn)
    now_time = int(time.time())
    arr = list(conn.peerpool.find().sort([('borrowed', DESCENDING),
                                          ('version', DESCENDING),
                                          ('lastSeen', DESCENDING),
                                      ]).limit(n))
    peers = []
    for p in arr:
        peer = ttypes.Peer(host=p['host'], port=p['port'], time=p['lastSeen'], version=p.get('version', 0))
        peers.append(peer)
        conn.peerpool.update({'host': peer.host, 'port': peer.port},
                             {'$set': {
                                 'borrowed': 1,
                                 'lastBorrowed': now_time}})
    return peers

def get_dbobj_list(conn, col, objids, keep_order=False, key='hash'):
    if not objids:
        return []

    arr = list(col.find({key: {'$in': objids}}))
    if keep_order:
        key_map = dict((dobj[key], dobj) for dobj in arr)
        objs = []
        for objid in objids:
            dobj = key_map.get(objid)
            if dobj:
                objs.append(dobj)
        arr = objs
    return arr
