import logging
logging.basicConfig()

import sys
from bsd.database import conn as dbconn
from bsd.database import transaction
from bson.binary import Binary
import json
from bsd.tx import update_addrs
from bsd.misc import itercol
from bsd.block import rewind_tip

conn = dbconn(sys.argv[1])
height = int(sys.argv[2])

with transaction(conn, isolation='serializable') as conn:
    v, m = rewind_tip(conn, height)
    if not v:
        print m

