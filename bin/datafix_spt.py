from bsd.database import conn as dbconn
from datafix import add_spt

if __name__ == '__main__':
    print 'start data spt fix'
    for netname in ['bitcoin', 'dogecoin', 'litecoin', 'darkcoin']:
        #cleanup_database(netname)
        conn = dbconn(netname)
        #check_cnt_txes(conn)
        add_spt(conn)
        #update_tx_addrs(conn)
        #cleanup_blocks(conn)
        #cleanup_txes(conn)
        
