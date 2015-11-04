import logging
import logging.config
logging.config.fileConfig('etc/logging.conf')

import time
from bsd.database import conn as dbconn
from bsd.database import transaction
from bsd.misc import itercol, idslice
from bsd.block import remove_block, get_tip_block
from bsd.helper import generated_seconds, get_netname
from bsd.tx import remove_db_tx, get_tx_db_block, add_dep
from bsd.addr import watch_addrtx, gen_tx_stats

def cleanup_blocks(conn):
    tip_block = get_tip_block(conn)
    if not tip_block:
        return
    for block in idslice(conn.block, 86400 * 2, 3600 * 3):
        if not block['isMain']:
            logging.warn('block %s is outdated, cleaning up', block['hash'].encode('hex'))
            with transaction(conn) as conn:
                remove_block(conn, block['hash'], cleanup_txes=True)

def cleanup_txes(conn):
    n = 0
    m = 0
    for dtx in idslice(conn.tx, 86400 * 2, 3600 * 3):
        n += 1
        b, _ = get_tx_db_block(conn, dtx)
        if not b:
            logging.warn('removing outdated %s tx %s', get_netname(conn), dtx['hash'].encode('hex'))
            with transaction(conn) as conn:
                remove_db_tx(conn, dtx)
                m += 1

    logging.warn('cleanup outdated %s txes  cleaned=%s, total=%s', get_netname(conn), m, n)


def check_stat_txes(conn):
    for dtx in idslice(conn.tx, 3600 * 2, 2800):
        gen_tx_stats(conn, dtx)
        add_dep(conn, dtx)

def fix_watch_addrtx(conn):
    t = 0
    for addrtx in idslice(conn.addrtx, 86400, 600):
        t += 1
        watch_addrtx(conn, addrtx)
    print t

def main():
    for netname in ['litecoin', 'darkcoin', 'dogecoin', 'bitcoin']:
        logging.info('start cleanup %s', netname)
        conn = dbconn(netname)
        cleanup_blocks(conn)
        cleanup_txes(conn)
        check_stat_txes(conn)
        fix_watch_addrtx(conn)
        logging.info('end cleanup %s', netname)

if __name__ == '__main__':
    main()
    time.sleep(3600)
