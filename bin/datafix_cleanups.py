import logging
logging.basicConfig()

from app.database import conn as dbconn
from app.database import transaction
from app.misc import itercol
from app.helper import generated_seconds
from app.block import remove_block, get_tip_block
from app.tx import remove_db_tx, get_db_tx, get_tx_db_block, update_addrs

def logwarn(fmt, *args):
    print fmt % args

def check_cnt_txes(conn):
    for block in itercol(conn, conn.block, 'check_block._id', 1000):
        cnt_txes = conn.tx.find({'bhs': block['hash']}).count()
        if cnt_txes != block['cntTxes']:
            logwarn('cnt txes mismatch block=%s, %s vs. %s', block['hash'].encode('hex'), cnt_txes, block['cntTxes'])

def update_tx_addrs(conn):
    for dtx in itercol(conn, conn.tx, 'update_addrs.tx._id', 100000):
        update_addrs(conn, dtx)

def add_spt(conn):
    for dtx in itercol(conn, conn.tx, 'spt.tx._id', 100000):
        for i, input in enumerate(dtx['vin']):
            if not input.get('hash'):
                continue
             
            source_tx = get_db_tx(conn, input['hash'], projection=['hash', 'vout'])
            if not source_tx:
                logwarn('source tx not found %s', input['hash'])
                continue

            output = source_tx['vout'][input['n']]
            if not output:
                logwarn('cannot find output for %s at %s', input['hash'], input['n'])

            update = {}
            update['vout.%d.w' % input['n']] = True
            conn.tx.update({'hash': input['hash']}, {'$set': update})

            addrs = input.get('addrs')
            if not addrs and output.get('addrs'):
                input['addrs'] = outpt['addrs']
                input['v'] = output['v']
                update = {}
                update['vin.%d.addrs' % i] = input['addrs']
                update['vin.%d.v' % i] = input['v']
                logging.info('add vin addrs and v %s %s', dtx['hash'], i)
                conn.tx.update({'hash': dtx['hash']}, {'$set': update})

def cleanup_blocks(conn):
    tip_block = get_tip_block(conn)
    if not tip_block:
        return
    for block in itercol(conn, conn.block, 'cleanup_block._id', 1000):
        if not block['isMain'] and block['timestamp'] < tip_block.timestamp - 86400:
            logwarn('block %s is outdated, cleaning up', block['hash'].encode('hex'))
            with transaction(conn) as conn:
                remove_block(conn, block['hash'], cleanup_txes=True)

def cleanup_txes(conn):
    for dtx in itercol(conn, conn.tx, 'cleanup_txes._id', 100000):
        if generated_seconds(dtx['_id'].generation_time) > 86400:
            b, _ = get_tx_db_block(conn, dtx)
            if not b:
                logwarn('tx %s is outdated, cleaning up', dtx['hash'].encode('hex'))
                with transaction(conn) as conn:
                    remove_db_tx(conn, dtx)

if __name__ == '__main__':
    print 'start data fix'
    for netname in ['bitcoin']:
        #cleanup_database(netname)
        conn = dbconn(netname)
        #check_cnt_txes(conn)
        add_spt(conn)
        #update_tx_addrs(conn)
        cleanup_blocks(conn)
        cleanup_txes(conn)
        
