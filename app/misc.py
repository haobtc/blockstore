import time
from pymongo import DESCENDING, ASCENDING
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

def itercol(conn, col, key, n):
    for _ in xrange(n):
        v = get_var(conn, key)
        obj = None
        t = 0
        if v:
            objid = v['objid']
            t = v.get('times', 0)
            objs = list(col.
                        find({'_id': {'$gt': objid}}).
                        sort([('_id', 1)]).limit(1))
            if objs:
                obj = objs[0]
        else:
            obj = col.find_one()
        if not obj:
            break
        yield obj
        set_var(conn, key, objid=obj['_id'], times=t+1)

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
                         {'$set': {'borrowed': 0}})
    
def push_peers(conn, peers):
    now_time = int(time.time())
    for peer in peers:
        conn.peerpool.update({'host': peer.host, 'port': peer.port},
                             {'$set': {'lastSeen': now_time}},
                             upsert=True)

    return_borrowed_peers(conn)

def pop_peers(conn, n):
    return_borrowed_peers(conn)
    now_time = int(time.time())
    arr = list(conn.peerpool.find().sort([('borrowed', DESCENDING),
                                          ('lastSeen', DESCENDING)]).limit(n))
    peers = []
    for p in arr:
        peer = ttypes.Peer(host=p['host'], port=p['port'], time=p['lastSeen'])
        peers.append(peer)
        conn.peerpool.update({'host': peer.host, 'port': peer.port},
                             {'$set': {
                                 'borrowed': 1,
                                 'lastBorrowed': now_time}})
    return peers

