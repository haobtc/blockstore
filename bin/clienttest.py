from app.database import conn as dbconn
from app.database import transaction
from bson.binary import Binary
import json
from app.tx import update_addrs
from app.misc import itercol
import datetime, pytz

conn = dbconn('bitcoin')
tx = conn.tx.find().sort([('_id',-1)]).limit(1)[0]
gtime = tx['_id'].generation_time

d =  utc_now() - gtime
print d.days * 86400 + d.seconds

