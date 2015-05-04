import sys

import app.tx as apptx
import app.misc as appmisc
import app.block as appblock

from app.database import conn as dbconn
from app.database import dbclient, transaction
from bson.binary import Binary
def copy_blocks(netname, nblocks):
    sc = dbclient()['blocks_%s' % netname]
    dc  = dbconn(netname)
    
    tip = appblock.get_tip_block(dc)
    times = 0
    while True:
        times += 1
        if times > nblocks:
            break
        #print 'tip height', tip.height
        if tip:
            h = tip.height + 1
        else:
            h = 0
        nb = sc.block.find_one({'height': h, 'isMain': True})
        if not nb:
            raise Exception('No sorce block found')
        tb = appblock.db2t_block(sc, nb)
        if tip:
            assert tb.prevHash == tip.hash

        txs = list(sc.tx.find({'bhs': nb['hash']}))
        if len(txs) != nb['cntTxes']:
            raise Exception('unmatched tx length %s %s %s', (len(txs), nb['cntTxes'], tb.hash.encode('hex')))
        
        for dtx in txs:
            dtx.pop('_id', None)

        txs = [apptx.db2t_tx(sc, tx, db_block=nb)
               for tx in txs]
        txs = [(t.blockIndex, t) for t in txs]
        txs.sort()
        txs = [t for i, t in txs]
        txids = [tx.hash for tx in txs]
        missing_txids = set(apptx.get_missing_txid_list(dc, txids))
        
        missing_txs = []
        for tx in txs:
            if Binary(tx.hash) in missing_txids:
                missing_txs.append(tx)

        with transaction(dc) as dc:
            for tx in missing_txs:
                v, m = apptx.verify_tx_chain(dc, tx)
                if not v:
                    raise Exception('not verified %s %s' % (tx.hash.encode('hex'), m))
                apptx.save_tx(dc, tx)

        for dtx in appmisc.itercol(dc, dc.tx, 
                                   'update_addrs.tx._id',
                                   len(txs)+2):
            apptx.update_addrs(dc, dtx)
        appblock.add_block(dc, tb, txids)
        tip = tb
        
if __name__ == '__main__':
    copy_blocks(sys.argv[1], int(sys.argv[2]))
