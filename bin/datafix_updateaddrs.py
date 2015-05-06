import logging
logging.basicConfig()

from bsd.database import conn as dbconn
from datafix import update_tx_addrs

def logwarn(fmt, *args):
    print fmt % args

if __name__ == '__main__':
    print 'start data fix update dataaddrs'
    for netname in ['bitcoin', 'dogecoin', 'litecoin', 'darkcoin']:
        #cleanup_database(netname)
        conn = dbconn(netname)
        #check_cnt_txes(conn)
        update_tx_addrs(conn)
        
