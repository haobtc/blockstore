import logging
import logging.config
logging.config.fileConfig('etc/logging.conf')

import sys
import time
from bsd.database import conn as dbconn
from bsd.database import transaction
from bsd.tx import remove_db_tx, get_db_tx

def cleanup_tx(conn, txid):
    dtx = get_db_tx(conn, txid)
    if dtx is None:
        return
    with transaction(conn) as conn:
        remove_db_tx(conn, dtx)

def main():
    netname = sys.argv[1]
    txid = sys.argv[2]
    txid = txid.decode('hex')
    conn = dbconn(netname)
    cleanup_tx(conn, txid)
    

if __name__ == '__main__':
    main()
