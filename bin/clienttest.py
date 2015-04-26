from app.database import conn as dbconn
from app.database import transaction
from bson.binary import Binary
import json
from app.tx import update_addrs
from app.misc import itercol

conn = dbconn('bitcoin')
for dtx in itercol(conn, conn.tx, 'update_addrs.tx._id', 1000):
    update_addrs(conn, dtx)


