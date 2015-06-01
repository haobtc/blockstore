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

def main(netname):
    conn = dbconn(netname)
    b = appblock.get_tip_block(conn)
    if b:
        print b.height
    else:
        print 0

if __name__ == '__main__':
    main(sys.argv[1])
    
