import sys

import logging
import logging.config
logging.config.fileConfig('etc/logging.conf')

import pymongo

import bsd.tx as apptx
import bsd.misc as appmisc
import bsd.block as appblock

import bsd.helper as helper

from bsd.database import conn as dbconn
from bsd.database import dbclient, transaction
from bson.binary import Binary

def copy_blocks(netname, nblocks):
    helper.get_netname = lambda(conn): netname

    #sc = dbclient()['blocks_%s' % netname]
    #sc = pymongo.MongoClient('mongodb://localhost:27017', maxPoolSize=1)['blocks_%s' % netname]
    sc = dbclient()['blockdump']
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
            raise Exception('No sorce block at %d found' %  h)
        tb = appblock.db2t_block(sc, nb)
        if tip:
            assert tb.prevHash == tip.hash, 'tip=%s tb=%s prevHash=%s' % (tip.hash.encode('hex'), tb.hash.encode('hex'), tb.prevHash.encode('hex'))

        #txs = list(sc.tx.find({'bhs': nb['hash']}))
        txs = apptx.get_db_tx_list_in_block(sc, nb['hash'])
        if len(txs) != nb['cntTxes']:
            raise Exception('unmatched tx length %s %s %s', (len(txs), nb['cntTxes'], tb.hash.encode('hex')))

        if False:
            presert_times = 0
            for dtx in txs:
                dtx.pop('_id', None)
            
                ddtx = dtx.copy()
                #ddtx.pop('bhs', None)
                #ddtx.pop('bis', None)
                ddtx.pop('vh', None)
                ddtx.pop('ia', None)
                ddtx.pop('oa', None)

                # simple verification
                verified = True
                for input in ddtx['vin']:
                    input.pop('k', None)
                    if 'hash' in input and 'addrs' not in input:
                        verified = False
                        break

                if verified:
                    try:
                        dc.tx.insert(ddtx)
                        presert_times += 1
                    except pymongo.errors.DuplicateKeyError:
                        print 'tx exists %s' % ddtx['hash'].encode('hex')
            #print 'pre insert times', presert_times

        tblock = appblock.db2t_block(sc, nb)
        txs = [apptx.db2t_tx(sc, tx,
                             db_block=nb, tblock=tblock,
                             ensure_input=False)
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
                    for input in tx.inputs:
                        print 'ss', input.hash.encode('hex'), input.vout
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
