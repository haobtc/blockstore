import logging
import logging.config
logging.config.fileConfig('etc/logging.conf')

import time
from bsd.database import conn as dbconn
from bsd.database import transaction
from bsd.misc import itercol, idslice
from bsd.block import remove_block, get_tip_block
from bsd.helper import generated_seconds, get_netname
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
    n = 0
    m = 0
    for dtx in idslice(conn.tx, 86400 * 2, 86300):
        n += 1
        b, _ = get_tx_db_block(conn, dtx)
        if not b:
            logging.warn('removing outdated %s tx %s', get_netname(conn), dtx['hash'].encode('hex'))
            with transaction(conn) as conn:
                remove_db_tx(conn, dtx)
                m += 1

    logging.warn('cleanup outdated %s txes  cleaned=%s, total=%s', get_netname(conn), m, n)

def main():
    for netname in ['litecoin', 'darkcoin', 'dogecoin', 'bitcoin']:
        conn = dbconn(netname)
        cleanup_blocks(conn)
        cleanup_txes(conn)

if __name__ == '__main__':
    main()
    time.sleep(3600)
