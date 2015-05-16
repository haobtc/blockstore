import sys
import logging
import logging.config
logging.config.fileConfig('etc/logging.conf')

import time
from bsd.database import conn as dbconn
from bsd.database import transaction
from bsd.misc import itercol, idslice
from bsd.block import remove_block, get_tip_block
from bsd.helper import generated_seconds, get_netname
from bsd.tx import remove_db_tx, get_tx_db_block, update_addrs

def fix_tx_addrs(conn, start_secs, stop_secs):
    for dtx in idslice(conn.tx, start_secs, stop_secs):
        update_addrs(conn, dtx)
        #update_vin_hash(conn, dtx)

def main():
    netname = sys.argv[1]
    start_secs = int(sys.argv[2])
    stop_secs = int(sys.argv[3])
    conn = dbconn(netname)
    fix_tx_addrs(conn, start_secs, stop_secs)

if __name__ == '__main__':
    main()
