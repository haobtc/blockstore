from app.database import conn as dbconn
from app.misc import itercol

def cleanup_database(netname):
    conn = dbconn(netname)
    for block in itercol(conn, conn.block, 'check_block._id', 1000):
        cnt_txes = conn.tx.find({'bhs': block['hash']}).count()
        print block['hash'].encode('hex')
        if cnt_txes != block['cntTxes']:
            print 'cnt txes mismatch', block['hash'].encode('hex'), cnt_txes, 'vs.', block['cntTxes']

if __name__ == '__main__':
    for netname in ['bitcoin']:
        cleanup_database(netname)

