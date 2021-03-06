import sys
import logging
import logging.config
logging.config.fileConfig('etc/logging.conf')

from bsd.database import conn as dbconn
from bsd.database import transaction
from bsd.misc import itercol, fetchcol, titercol
from bsd.block import remove_block, get_tip_block
from bsd.addr import gen_tx_stats, undo_tx_stats
from bsd.tx import add_dep, remove_dep
from bsd.tasks import constructive_task, destructive_task

def aux_tasks(conn, n):
    constructive_task(conn, n)
    destructive_task(conn, n)
    return
    #for _ in xrange(n):
    #    with transaction(conn) as conn:
    #dtx = fetchcol(conn, conn.tx, 'addrstat.tx._id')
    print 'gen'
    for dtx in titercol(conn, conn.tx, 'addrstat.tx._id', n):
        gen_tx_stats(conn, dtx)
    print 'undo'
    for dtx in titercol(conn, conn.removedtx, 'addrstat.removedtx._id', n):
        undo_tx_stats(conn, dtx)

    print 'add dep'
    for dtx in titercol(conn, conn.tx, 'txdep.tx._id', n):
        add_dep(conn, dtx)

    print 'remove_dep'
    for dtx in titercol(conn, conn.removedtx, 'txdep.removedtx._id', n):
        remove_dep(conn, dtx)
                
if __name__ == '__main__':
    all_netnames =  ['bitcoin', 'dogecoin', 'litecoin', 'darkcoin']
    netnames = [n for n in sys.argv[1:] if n in all_netnames]
    if not netnames:
        netnames = all_netnames
    for netname in netnames:
        #for netname in
        conn = dbconn(netname)
        aux_tasks(conn, 100000)
        
