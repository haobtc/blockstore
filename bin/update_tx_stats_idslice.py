import sys
import logging
import logging.config
logging.config.fileConfig('etc/logging.conf')

import time
from bsd.database import conn as dbconn
from bsd.database import transaction
from bsd.misc import itercol, idslice
from bsd.helper import generated_seconds, get_netname
from bsd.addr import gen_tx_stats, undo_tx_stats, unwatch_tx, watch_addrtx
from bsd.tx import add_dep, remove_dep

def main(conn, start_since, end_since):
    print 'gen tx stats'
    for i, dtx in enumerate(idslice(conn.tx, start_since, end_since)):
        if i % 1000 == 0:
            print i
        gen_tx_stats(conn, dtx)
        add_dep(conn, dtx)
    
if __name__ == '__main__':
    netname = sys.argv[1]
    start_since = int(sys.argv[2])
    end_since = int(sys.argv[3])
    conn = dbconn(netname)
    main(conn, start_since, end_since)

    
