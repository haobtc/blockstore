import sys
import time
import logging
import logging.config
logging.config.fileConfig('etc/logging.conf')

from bsd.database import conn as dbconn
from bsd.database import transaction
from bsd.misc import itercol, fetchcol, titercol
from bsd.block import remove_block, get_tip_block
from bsd.addr import gen_tx_stats, undo_tx_stats
from bsd.tx import add_dep, remove_dep
from bsd.tasks import watch_addrtx_task, unwatch_tx_task


def run_txtasks(conn, n):
    watch_addrtx_task(conn, n)
    unwatch_tx_task(conn, n)

if __name__ == '__main__':
    all_netnames =  ['bitcoin', 'dogecoin', 'litecoin', 'darkcoin']
    netnames = [n for n in sys.argv[1:] if n in all_netnames]
    if not netnames:
        netnames = all_netnames
    start_time = time.time()
    for netname in netnames:
        #for netname in
        conn = dbconn(netname)
        run_txtasks(conn, 1000)
    end_time = time.time()
    if end_time - start_time < 5:
        time.sleep(5 - end_time + start_time)
