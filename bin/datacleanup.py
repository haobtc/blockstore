import logging
logging.basicConfig()

from app.database import conn as dbconn
from app.database import transaction
from app.misc import itercol, idslice
from app.block import remove_block, get_tip_block
from app.helper import generated_seconds
from app.tx import remove_db_tx, get_tx_db_block

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

if __name__ == '__main__':
    for netname in ['bitcoin']:
        conn = dbconn(netname)
        cleanup_blocks(conn)
        cleanup_txes(conn)
        
