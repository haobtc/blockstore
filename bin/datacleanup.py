import logging
logging.basicConfig()

import time
from bsd.database import conn as dbconn
from bsd.database import transaction
from bsd.misc import itercol, idslice
from bsd.block import remove_block, get_tip_block
from bsd.helper import generated_seconds
from bsd.tx import remove_db_tx, get_tx_db_block

def cleanup_blocks(conn):
    tip_block = get_tip_block(conn)
    if not tip_block:
        return
    for block in idslice(conn.block, 86400 * 2, 86300):
        if not block['isMain']:
            logging.warn('block %s is outdated, cleaning up', block['hash'].encode('hex'))
            with transaction(conn) as conn:
                remove_block(conn, block['hash'], cleanup_txes=True)

def cleanup_txes(conn):
    for dtx in idslice(conn.tx, 86400 * 2, 86300):
        b, _ = get_tx_db_block(conn, dtx)
        if not b:
            with transaction(conn) as conn:
                remove_db_tx(conn, dtx)

def main():
    for netname in ['bitcoin', 'dogecoin', 'litecoin', 'darkcoin']:
        conn = dbconn(netname)
        cleanup_blocks(conn)
        cleanup_txes(conn)

if __name__ == '__main__':
    for  _ in xrange(1000):
        main()
        time.sleep(5 * 60)
