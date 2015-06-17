import sys
import logging
import logging.config
logging.config.fileConfig('etc/logging.conf')

from bsd.database import conn as dbconn
from bsd.database import transaction
from bsd.misc import itercol
from bsd.block import remove_block, get_tip_block
from bsd.addr import gen_tx_stats, undo_tx_stats
from bsd.tx import add_dep, remove_dep

def logwarn(fmt, *args):
    print fmt % args

def aux_tasks(conn, n):
    with transaction(conn) as conn:
        for dtx in itercol(conn, conn.tx, 'addrstat.tx._id', n):
            gen_tx_stats(conn, dtx)
    
    if False:
        with transaction(conn) as conn:
            for dtx in itercol(conn, conn.removedtx, 'undo_addrstat.tx._id', n):
                undo_tx_stats(conn, dtx)

    for dtx in itercol(conn, conn.tx, 'txdep.tx._id', n, batch=10):
        with transaction(conn) as conn:
            add_dep(conn, dtx)

    for dtx in itercol(conn, conn.removedtx, 'txdep.removedtx._id', n, batch=10):
        with transaction(conn) as conn:
            add_dep(conn, dtx)
                
if __name__ == '__main__':
    all_netnames =  ['bitcoin', 'dogecoin', 'litecoin', 'darkcoin']
    netnames = [n for n in sys.argv[1:] if n in all_netnames]

        netnames = all_netnames
    for netname in all_netnames:
        #for netname in
        conn = dbconn(netname)
        aux_tasks(conn, 1000)
        
