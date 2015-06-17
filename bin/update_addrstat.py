import sys
import logging
import logging.config
logging.config.fileConfig('etc/logging.conf')


from bsd.database import conn as dbconn
from bsd.database import transaction, rollback
from bsd.misc import itercol
from bson.binary import Binary
from bsd.block import remove_block, get_tip_block
from bsd.tx import get_db_tx, ensure_input_addrs, get_related_db_tx_list, get_related_db_addr_tx_list, new_get_unspent
from bsd.addr import gen_tx_stats, undo_tx_stats

def main(conn, address):
    conn.addrstat.remove({'_id': address})
    for dtx in get_related_db_addr_tx_list(conn, [address], id_order=1):
        with transaction(conn) as conn:
            print dtx['hash'].encode('hex')
            gen_tx_stats(conn, dtx, force_new_tx=True, filter_addrs=[address])
    # urefs = []
    # for utxo in new_get_unspent(conn, [address]):
    #     uref = Binary('#'.join([utxo.txid, pack('>I', utxo.vout)]))
    #     urefs.append(uref)
    # conn.addrstat.update({'_id': address}, {'$set': {'u': urefs}})

if __name__ == '__main__':
    netname = sys.argv[1]
    address = sys.argv[2]
    conn = dbconn(netname)
    main(conn, address)
        
