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

def main(netname, start_height, n=100):
    conn = dbconn(netname)
    for height in xrange(start_height, start_height + n):
        b = conn.block.find_one({'height': height, 'isMain': True})
        if not b:
            break
        txids = [v['t'] for v in conn.txblock.find({'b': b['hash']})]
        cnt = conn.tx.find({'hash': {'$in': txids}}).count()
        if cnt != b['cntTxes']:
            print 'cnt mismatch', b['hash'].encode('hex'), b['height'], cnt, b['cntTxes']
        else:
            print 'block at height', height

if __name__ == '__main__':
    main(sys.argv[1], int(sys.argv[2]), int(sys.argv[3]))
    
