from bsd.database import conn as dbconn
from bsd.database import transaction
from bson.binary import Binary
import json
from bsd.tx import update_addrs
from bsd.misc import itercol
import datetime, pytz

conn = dbconn('bitcoin')
tx = conn.tx.find().sort([('_id',-1)]).limit(1)[0]
gtime = tx['_id'].generation_time

d =  utc_now() - gtime
print d.days * 86400 + d.seconds

