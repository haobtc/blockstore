import logging
import logging.config
logging.config.fileConfig('etc/logging.conf')

import sys
import time
from bsd.database import conn as dbconn
from bsd.database import transaction
from bsd.tx import get_db_tx, add_dep
from bsd.addr import gen_tx_stats

def main():
    netname = sys.argv[1]
    conn = dbconn(netname)
    for txid in sys.argv[2:]:
        print txid
        txid = txid.decode('hex')
        dtx = get_db_tx(conn, txid)
        if dtx is None:
            continue
        with transaction(conn) as conn:
            gen_tx_stats(conn, dtx)
            add_dep(conn, dtx)

if __name__ == '__main__':
    main()
