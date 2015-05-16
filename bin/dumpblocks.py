import sys

import pymongo

from bsd.database import conn as dbconn
from bsd.database import dbclient, transaction
from bsd.misc import get_dbobj_list

def main(netname, start_height, stop_height):
    #dc = pymongo.MongoClient('mongodb://localhost:27027', maxPoolSize=1)['blockdump']
    dc = dbclient()['blockdump']
    dc.block.remove({})
    dc.txblock.remove({})
    dc.tx.remove({})
    dc.txblock.ensure_index('b')
    sc = dbconn(netname)
    for height in xrange(start_height, stop_height):
        block = sc.block.find_one({'height': height, 'isMain': True})
        print 'block', block, height
        if not block:
            break
        print 'dumping block', block['hash'].encode('hex')
        block.pop('_id', None)
        rels = list(sc.txblock.find({'b': block['hash']}))
        print len(rels)
        for rel in rels:
            rel.pop('_id', None)

        txes = get_dbobj_list(sc, sc.tx, [r['t'] for r in rels])
        assert len(txes) == block['cntTxes'], 'len %s vs. cntTxes %s' % (len(txes), block['cntTxes'])

        for tx in txes:
            tx.pop('_id', None)
        print 'begin transaction'
        with transaction(dc) as dc:
            dc.block.save(block)
            for rel in rels:
                dc.txblock.save(rel)
            for tx in txes:
                dc.tx.save(tx)


if __name__ == '__main__':
    netname = sys.argv[1]
    start_height = int(sys.argv[2])
    stop_height = int(sys.argv[3])
    assert stop_height > start_height
    main(netname, start_height, stop_height)
    
    
