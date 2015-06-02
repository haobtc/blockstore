import sys
import logging
logging.basicConfig()

from bsd.database import conn as dbconn
from datafix import update_tx_addrs
from bson.binary import Binary
from bsd.tx import remove_db_tx, get_db_tx, get_tx_db_block, update_addrs
from bsd.tx import update_vin_hash

def main():
    netname = sys.argv[1]
    txid = Binary(sys.argv[2].decode('hex'))
    conn = dbconn(netname)
    dtx = conn.tx.find_one({'hash': txid})
    if dtx:
        print 'update'
        update_addrs(conn, dtx)
        update_vin_hash(conn, dtx)
    
if __name__ == '__main__':
    main()
