import logging
logging.basicConfig()

import sys
from app.database import conn as dbconn
from app.database import transaction
from bson.binary import Binary
import json
from app.tx import update_addrs
from app.misc import itercol
from app.block import rewind_tip

conn = dbconn(sys.argv[1])
height = int(sys.argv[2])

with transaction(conn, isolation='serializable') as conn:
    v, m = rewind_tip(conn, height)
    if not v:
        print m

