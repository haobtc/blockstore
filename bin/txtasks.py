import sys
import logging
import logging.config
logging.config.fileConfig('etc/logging.conf')

from bsd.database import conn as dbconn
from bsd.database import transaction
from bsd.misc import itercol, fetchcol, titercol
from bsd.block import remove_block, get_tip_block
from bsd.addr import gen_tx_stats, undo_tx_stats
from bsd.tx import add_dep, remove_dep
from bsd.tasks import constructive_task, destructive_task

def run_txtasks(conn, n):
    constructive_task(conn, n)
    destructive_task(conn, n)
                
if __name__ == '__main__':
    #all_netnames =  ['bitcoin', 'dogecoin', 'litecoin', 'darkcoin']
    all_netnames =  ['bitcoin', 'dogecoin', 'litecoin']
    netnames = [n for n in sys.argv[1:] if n in all_netnames]
    if not netnames:
        netnames = all_netnames
    for netname in netnames:
        #for netname in
        conn = dbconn(netname)
        run_txtasks(conn, 1000)
