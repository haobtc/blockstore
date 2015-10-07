import logging
from misc import itercol, fetchcol, titercol
from addr import gen_tx_stats, undo_tx_stats, unwatch_tx, watch_addrtx
from tx import add_dep, remove_dep
from bson.objectid import ObjectId

def watch_addrtx_task(conn, n):
    key = 'watch.addrtx._id'
    v = conn.var.find_one({'key': key})
    if not v:
        v = {'key': key, 'objid': ObjectId()}
        conn.var.insert(v)
        
    for addrtx in titercol(conn, conn.addrtx, key, n):
        watch_addrtx(conn, addrtx)

def unwatch_tx_task(conn, n):
    for dtx in titercol(conn, conn.removedtx, 'watch.removedtx._id', n):
        unwatch_tx(conn, dtx)

def constructive_task(conn, n):
    for dtx in titercol(conn, conn.tx, 'addrstat.tx._id', n):
        gen_tx_stats(conn, dtx)

    for dtx in titercol(conn, conn.tx, 'txdep.tx._id', n):
        add_dep(conn, dtx)

    #watch_addrtx_task(conn, n * 2)

def destructive_task(conn, n):
    for dtx in titercol(conn, conn.removedtx, 'addrstat.removedtx._id', n):
        undo_tx_stats(conn, dtx)

    for dtx in titercol(conn, conn.removedtx, 'txdep.removedtx._id', n):
        remove_dep(conn, dtx)

    #unwatch_tx_task(conn, n)
