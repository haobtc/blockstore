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
from bsd.block import get_block_db_tx_list

def main(conn, start, count):
    for dblock in conn.block.find({'height': {'$gte': start}, 'isMain': True}).sort([('height', 1)]).limit(count):
        #print dblock['height']
        txlist = get_block_db_tx_list(conn, dblock['hash'])
        if len(txlist) != dblock['cntTxes']:
            print dblock['height'], dblock['hash'].encode('hex')

if __name__ == '__main__':
    netname = sys.argv[1]
    start = int(sys.argv[2])
    count = int(sys.argv[3])
    conn = dbconn(netname)
    main(conn, start, count)

