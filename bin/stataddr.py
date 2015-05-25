import logging
logging.basicConfig()

from bsd.database import conn as dbconn
from bsd.database import transaction
from bsd.misc import itercol
from bsd.block import remove_block, get_tip_block
from bsd.addr import gen_tx_stats, undo_tx_stats

def logwarn(fmt, *args):
    print fmt % args

def stat_addr(conn, n):
    for _ in xrange(int(n/10)):
        with transaction(conn) as conn:
            for dtx in itercol(conn, conn.tx, 'addrstat.tx._id', 10):
                gen_tx_stats(conn, dtx)
    
    if False:
        for _ in xrange(int(n/10)):
            with transaction(conn) as conn:
                for dtx in itercol(conn, conn.removedtx, 'undo_addrstat.tx._id', 10):
                    undo_tx_stats(conn, dtx)
                
if __name__ == '__main__':
    #for netname in ['bitcoin', 'dogecoin', 'litecoin', 'darkcoin']:
    for netname in ['bitcoin']:
        conn = dbconn(netname)
        stat_addr(conn, 1000)
        
