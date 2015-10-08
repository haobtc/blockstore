import sys
import time
import logging
import logging.config
logging.config.fileConfig('etc/logging.conf')

from bsd.database import conn as dbconn
from bsd.database import transaction
from bsd.misc import itercol, idslice
from bsd.helper import generated_seconds
from bsd.block import remove_block, get_tip_block
from bsd.tx import remove_db_tx, get_db_tx, get_tx_db_block, update_addrs, add_dep
from bsd.addr import get_addr_set, gen_tx_stats

def main(conn, start, end):
    for dtx in idslice(conn.tx, start, end):
        sus = False
        for a in get_addr_set(dtx):
            if  not conn.addrtx.find_one({'a': a, 't': dtx['hash']}):
                sus = True
                break
        if sus:
            print dtx['hash'].encode('hex')
            with transaction(conn) as conn:
                gen_tx_stats(conn, dtx)
                add_dep(conn, dtx)

if __name__ == '__main__':
    netname = sys.argv[1]
    start = int(sys.argv[2])
    end = int(sys.argv[3])
    if len(sys.argv) >= 5:
        sleep_time = float(sys.argv[4])
    else:
        sleep_time = 0
    conn = dbconn(netname)
    main(conn, start, end)
    time.sleep(sleep_time)
