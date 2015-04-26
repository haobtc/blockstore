from bson.binary import Binary
from bson.objectid import ObjectId
from helper import resolve_network
import database  

def get_var(conn, key):
    return conn.var.find_one({'key': key})

def set_var(conn, key, **kw):
    conn.var.update({'key': key}, {'$set': kw}, upsert=True)

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


